"""파이프라인 오케스트레이터 — Skills.md §4 실행 순서 STEP 1~9.

run_snapshot(end_date) → 단일 영업일 분석 결과 dict 반환.

STEP 1  데이터 수집           [Layer 1]
STEP 2  정제 + 지표 계산        [Layer 2]
STEP 3  5개 리스크 등급          [Layer 3]
STEP 4  Override (OVR-01/06/02) [rules.override]
STEP 5  국면 + 가중치           [Layer 4]
STEP 6  통합 점수               [Layer 4]
STEP 7  전략 + 자산 배분         [Layer 5]
STEP 8  인사이트                [Layer 6]
STEP 9  알림                    [rules.alert]
EOD     STATE 저장              [Layer 1]

GUARD: 각 STEP은 이전 결과가 정상일 때만 진입.
외부 API 실패 시 RuntimeError 전파 (호출자가 prev_day 폴백 처리).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

# Layer 1
from layer1_data.kospi_fetcher import get_kospi_ohlcv, get_foreign_net_buying
from layer1_data.macro_fetcher import EcosClient
from layer1_data.cleaner import clean_dataframe, clean_series, align_to_business_days
from layer1_data import state as state_mod

# Layer 2
from layer2_indicator import price as p_ind
from layer2_indicator import volatility as v_ind
from layer2_indicator import liquidity as l_ind
from layer2_indicator import downside as d_ind
from layer2_indicator import derived as derived_ind
from layer2_indicator.monte_carlo import simulate_paths, mc_mdd_p50_series

# Layer 3
from layer3_risk import market as risk_market
from layer3_risk import volatility as risk_volatility
from layer3_risk import liquidity as risk_liquidity
from layer3_risk import downside as risk_downside
from layer3_risk import macro as risk_macro

# Layer 4
from layer4_scoring.phase import determine_phase, select_weights
from layer4_scoring.score import compute as score_compute

# Layer 5
from layer5_strategy.strategy import compute as strategy_compute

# Layer 6
from layer6_insight.insight import generate as insight_generate

# Rules
from rules.override import apply_step4
from rules import alert as alert_mod


def _to_yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _to_yyyymm(d: date) -> str:
    return d.strftime("%Y%m")


def run_snapshot(
    end_date: date,
    lookback_days: int = 400,
    save: bool = False,
) -> dict[str, Any]:
    """단일 영업일 종합 분석 → dict.

    end_date: 분석 기준일 (영업일).
    lookback_days: 데이터 수집 윈도우 (252 + 120 MA buffer 약 400).
    save: True면 STATE를 data/state.json에 저장 (운영 모드).
    """
    end_dt = end_date
    start_dt = end_dt - timedelta(days=lookback_days)
    end_str = _to_yyyymmdd(end_dt)
    start_str = _to_yyyymmdd(start_dt)

    # ─────────────────────────────────────────────────────
    # STEP 1 — 데이터 수집
    # ─────────────────────────────────────────────────────
    ecos = EcosClient()
    kospi_raw = get_kospi_ohlcv(start_str, end_str)
    if kospi_raw.empty:
        raise RuntimeError("STEP 1: KOSPI OHLCV empty")

    # 환율 / 금리 (일별)
    fx_raw = ecos.get_fx_rate(start_str, end_str)
    base_rate_raw = ecos.get_base_rate(start_str, end_str)
    # CPI / M2 / US (월별, 12개월 추가 lookback for YoY)
    yoy_lookback_start = (end_dt - timedelta(days=lookback_days + 400))
    cpi_raw = ecos.get_cpi_yoy(_to_yyyymm(yoy_lookback_start), _to_yyyymm(end_dt))
    m2_raw = ecos.get_m2_growth(_to_yyyymm(yoy_lookback_start), _to_yyyymm(end_dt))
    us_raw = ecos.get_us_base_rate(_to_yyyymm(yoy_lookback_start), _to_yyyymm(end_dt))

    # 외국인은 일별 루프 비용이 크므로 마지막 30영업일만
    fi_start = (end_dt - timedelta(days=45)).strftime("%Y%m%d")
    fi_raw = get_foreign_net_buying(fi_start, end_str)

    # ─────────────────────────────────────────────────────
    # STEP 2 — 정제 + 지표 계산
    # ─────────────────────────────────────────────────────
    kospi, _ = clean_dataframe(kospi_raw, start_str, end_str)
    fx       = align_to_business_days(fx_raw, start_str, end_str)
    base_kr  = align_to_business_days(base_rate_raw, start_str, end_str)
    cpi      = align_to_business_days(cpi_raw, start_str, end_str)
    m2       = align_to_business_days(m2_raw, start_str, end_str)
    us_rate  = align_to_business_days(us_raw, start_str, end_str)
    fi       = fi_raw.reindex(kospi.index, method=None)  # 30일 윈도우만 보유

    close, high, low, vol, val = (kospi["close"], kospi["high"], kospi["low"],
                                   kospi["volume"], kospi["value"])

    # Layer 2 시리즈 산출
    ma20_s   = p_ind.moving_average(close, 20)
    ma60_s   = p_ind.moving_average(close, 60)
    ma120_s  = p_ind.moving_average(close, 120)
    disp20_s = p_ind.disparity(close, 20)
    disp60_s = p_ind.disparity(close, 60)
    adx_s    = p_ind.adx(high, low, close, 14)
    cdec_s   = p_ind.consec_decline(close)

    hv20_s = v_ind.historical_volatility(close, 20)
    hv60_s = v_ind.historical_volatility(close, 60)

    vol_ratio_s = l_ind.vol_ratio(vol, 20)
    val_ratio_s = l_ind.val_ratio(val, 20)
    vol_streak_s = l_ind.vol_streak(vol, 20)

    mdd60_s = d_ind.mdd(close, 60)
    mdd252_s = d_ind.mdd(close, 252)
    var95_s = d_ind.var_95(close, 252)
    cvar95_s = d_ind.cvar_95(close, 252)

    # MC forward-looking 메트릭 — Risk-D 등급 산정 입력
    paths_60  = simulate_paths(close, horizon=60)
    paths_252 = simulate_paths(close, horizon=252)
    mdd_60_mc_dict  = d_ind.mc_mdd_percentiles(paths_60)
    mdd_252_mc_dict = d_ind.mc_mdd_percentiles(paths_252)
    var_cvar_mc     = d_ind.mc_var_cvar_1d(paths_60)

    # MC p50 60일 MDD 시계열 (시각화용)
    mdd60_mc_p50_s = mc_mdd_p50_series(close, horizon=60, n_paths=2_000)

    # 최신 영업일 스칼라
    last = kospi.index[-1]

    def at(s: pd.Series, default=None):
        try:
            v = s.loc[last]
            return float(v) if pd.notna(v) else default
        except KeyError:
            return default

    ma20, ma60, ma120 = at(ma20_s), at(ma60_s), at(ma120_s)
    disp20, disp60   = at(disp20_s), at(disp60_s)
    adx_v            = at(adx_s)
    consec_decline_v = int(at(cdec_s, 0))
    hv20, hv60       = at(hv20_s), at(hv60_s)
    vol_ratio_hv_v   = (hv20 / hv60) if (hv20 and hv60) else 1.0
    vol_ratio_v      = at(vol_ratio_s)
    val_ratio_v      = at(val_ratio_s)
    vol_streak_v     = int(at(vol_streak_s, 0))
    mdd60, mdd252    = at(mdd60_s), at(mdd252_s)
    var95, cvar95    = at(var95_s), at(cvar95_s)
    mdd_recovery_v   = derived_ind.mdd_recovery_months(close.tail(252))

    # 매크로 파생
    fx_today = at(fx)
    fx_daily = derived_ind.fx_change(fx, 1).iloc[-1] if len(fx) >= 2 else 0.0
    fx_weekly = derived_ind.fx_change(fx, 5).iloc[-1] if len(fx) >= 6 else 0.0
    fx_daily = float(fx_daily) if pd.notna(fx_daily) else 0.0
    fx_weekly = float(fx_weekly) if pd.notna(fx_weekly) else 0.0

    base_today = at(base_kr)
    base_prev_month = base_kr.iloc[-22] if len(base_kr) >= 22 else base_today
    base_rate_delta_v = float((base_today or 0) - (base_prev_month or 0))

    us_today = at(us_rate)
    rate_spread_curr_v = (base_today or 0) - (us_today or 0)
    rate_spread_prev_v = rate_spread_curr_v  # 단순화
    if len(base_kr) >= 22 and len(us_rate) >= 22:
        rate_spread_prev_v = float(base_kr.iloc[-22] - us_rate.iloc[-22])

    cpi_yoy_v = at(cpi, 0.0)
    cpi_prev = cpi.iloc[-22] if len(cpi) >= 22 else cpi_yoy_v
    cpi_delta_v = float((cpi_yoy_v or 0) - (cpi_prev or 0))

    m2_curr = at(m2, 0.0)
    m2_prev = m2.iloc[-22] if len(m2) >= 22 else m2_curr
    m2_contraction_v = bool(derived_ind.m2_contraction(m2).iloc[-1]) if len(m2) >= 2 else False
    m2_slowdown_v    = bool(derived_ind.m2_growth_slowdown(m2).iloc[-1]) if len(m2) >= 2 else False
    m2_expansion_v   = bool(derived_ind.m2_expansion(m2).iloc[-1]) if len(m2) >= 2 else False

    fi_monthly_v = float(fi.tail(22).sum()) / 1_000_000 if len(fi) > 0 else 0.0  # 백만원 → 조원 환산
    fi_5d_cum_v  = float(fi.tail(5).sum()) / 1_000_000 if len(fi) > 0 else 0.0
    fi_streak_sell_v = 0
    fi_streak_buy_v  = 0
    for v in reversed(fi.dropna().tolist()):
        if v < 0: fi_streak_sell_v += 1
        else: break
    for v in reversed(fi.dropna().tolist()):
        if v > 0: fi_streak_buy_v += 1
        else: break

    # MA flags
    ma_bullish_v      = (ma20 or 0) > (ma60 or 0) > (ma120 or 0)
    ma_bearish_full_v = (ma20 or 0) < (ma60 or 0) < (ma120 or 0)
    ma_converging_v   = bool(derived_ind.ma_converging(pd.Series([ma20]), pd.Series([ma60])).iloc[-1])

    timestamp = last.strftime("%Y-%m-%d")

    # ─────────────────────────────────────────────────────
    # STEP 3 — 5 리스크 등급
    # ─────────────────────────────────────────────────────
    risk_a = risk_market.evaluate(
        ma20=ma20, ma60=ma60, ma120=ma120,
        disp_ma20=disp20, disp_ma60=disp60,
        adx=adx_v, consec_decline=consec_decline_v,
        timestamp=timestamp,
    )
    risk_b = risk_volatility.evaluate(
        hv20=hv20, hv60=hv60, vol_ratio_hv=vol_ratio_hv_v, vkospi=None,
        timestamp=timestamp,
    )
    risk_c = risk_liquidity.evaluate(
        vol_ratio=vol_ratio_v, vol_streak=vol_streak_v,
        val_ratio=val_ratio_v, conc_ratio=None,
        timestamp=timestamp,
    )
    risk_d = risk_downside.evaluate(
        mdd_60=mdd60, mdd_252=mdd252, var_95=var95, cvar=cvar95,
        mdd_recovery_months=mdd_recovery_v,
        mdd_60_mc=mdd_60_mc_dict,
        mdd_252_mc=mdd_252_mc_dict,
        var_95_mc=var_cvar_mc["var"],
        cvar_mc=var_cvar_mc["cvar"],
        timestamp=timestamp,
    )
    risk_e = risk_macro.evaluate(
        fx_rate=fx_today,
        base_rate_delta=base_rate_delta_v,
        rate_spread_curr=rate_spread_curr_v,
        cpi_yoy=cpi_yoy_v,
        fi_monthly=fi_monthly_v,
        m2_growth_curr=m2_curr,
        m2_contraction=m2_contraction_v,
        m2_growth_slowdown=m2_slowdown_v,
        fx_daily_change=fx_daily,
        fx_weekly_change=fx_weekly,
        fi_streak_sell=fi_streak_sell_v,
        fi_streak_buy=fi_streak_buy_v,
        fi_5d_cum=fi_5d_cum_v,
        cpi_delta=cpi_delta_v,
        rate_spread_prev=rate_spread_prev_v,
        m2_expansion=m2_expansion_v,
        timestamp=timestamp,
    )
    risks = {"market": risk_a, "volatility": risk_b, "liquidity": risk_c,
             "downside": risk_d, "macro": risk_e}

    # ─────────────────────────────────────────────────────
    # STEP 4 — Override (OVR-01 검증 / OVR-06 / OVR-02)
    # ─────────────────────────────────────────────────────
    state = state_mod.load_state() if save else state_mod.get_default_state()
    active_alerts: list[str] = []
    step4 = apply_step4(risks, active_alerts)
    critical_count_v = step4["critical_count"]

    # ─────────────────────────────────────────────────────
    # STEP 5-6 — 국면 + 가중치 + 통합 점수
    # ─────────────────────────────────────────────────────
    phase = determine_phase(
        ma_bullish=ma_bullish_v, ma_bearish_full=ma_bearish_full_v,
        ma_converging=ma_converging_v, adx=adx_v, consec_decline=consec_decline_v,
    )
    weights = select_weights(phase)
    scn04 = bool(risk_e.details.flags.get("scn04_flag"))
    score_result = score_compute(
        market_grade=risk_a.grade, volatility_grade=risk_b.grade,
        macro_grade=risk_e.grade, liquidity_grade=risk_c.grade,
        downside_grade=risk_d.grade, weights=weights, scn04_flag=scn04,
    )

    # ─────────────────────────────────────────────────────
    # STEP 7 — 전략 + 자산 배분
    # ─────────────────────────────────────────────────────
    strat = strategy_compute(
        score_band=score_result["score_band"],
        integrated_score=score_result["score"],
        critical_count=critical_count_v,
        market_grade=risk_a.grade, volatility_grade=risk_b.grade,
        macro_grade=risk_e.grade, liquidity_grade=risk_c.grade,
        downside_grade=risk_d.grade,
    )

    # ─────────────────────────────────────────────────────
    # STEP 8 — 인사이트
    # ─────────────────────────────────────────────────────
    insights = insight_generate(
        market_grade=risk_a.grade, volatility_grade=risk_b.grade,
        liquidity_grade=risk_c.grade, downside_grade=risk_d.grade,
        macro_grade=risk_e.grade,
        integrated_score=score_result["score"],
        strategy=strat["strategy"],
        triggered_scenario=risk_e.details.flags.get("triggered_scenario"),
        fi_streak_sell=fi_streak_sell_v, vol_streak=vol_streak_v,
        var_95=var95, ma_bullish=ma_bullish_v,
        consecutive_days=state["consecutive_days"],
        active_alerts=active_alerts,
    )

    # ─────────────────────────────────────────────────────
    # STEP 9 — 알림 평가 + STATE 갱신
    # ─────────────────────────────────────────────────────
    up_count_v = len(risk_e.details.flags.get("active_up_events", []))
    additional = alert_mod.evaluate(
        state=state,
        integrated_score=score_result["score"],
        critical_count=critical_count_v,
        hv20=hv20, vol_ratio=vol_ratio_v,
        fi_streak_sell=fi_streak_sell_v, fi_5d_cum=fi_5d_cum_v,
        disp_ma20=disp20, disp_ma60=disp60,
        up_count=up_count_v, mdd_60=mdd60,
        triggered_scenario=risk_e.details.flags.get("triggered_scenario"),
    )
    for a in additional:
        if a not in active_alerts:
            active_alerts.append(a)

    # EOD STATE
    state_mod.update_eod(
        state,
        score_band=score_result["score_band"],
        integrated_score=score_result["score"],
        hv20_history=hv20_s.dropna().tolist(),
        generated_insight_ids=[i["id"] for i in insights],
    )
    if save:
        state_mod.save_state(state)

    # ─────────────────────────────────────────────────────
    # 결과 dict
    # ─────────────────────────────────────────────────────
    return {
        "timestamp":      timestamp,
        "phase":          phase,
        "weights":        weights,
        "score":          score_result["score"],
        "score_band":     score_result["score_band"],
        "contributions":  score_result["contributions"],
        "critical_count": critical_count_v,
        "system_critical_escalation": step4["system_critical_escalation"],
        "risks":          {k: r.model_dump() for k, r in risks.items()},
        "strategy":       strat,
        "insights":       insights,
        "alerts":         active_alerts,
        # 시계열 (시각화용)
        "series": {
            "close":  close,
            "ma20":   ma20_s, "ma60": ma60_s, "ma120": ma120_s,
            "hv20":   hv20_s,
            "mdd60":  mdd60_s,              # legacy window min/max (참고용)
            "mdd60_mc_p50": mdd60_mc_p50_s, # MC 기반 forward-looking p50 (UI 기본)
            "var95":  var95_s,
            "vol_ratio": vol_ratio_s,
        },
    }

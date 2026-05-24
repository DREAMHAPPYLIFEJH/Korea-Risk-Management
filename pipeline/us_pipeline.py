"""S&P500 리스크 분석 파이프라인 — Phase 3.

run_us_snapshot(end_date) → Phase 1 run_snapshot()과 동일 구조 dict 반환.

레이어 재사용:
  Layer 2 지표 계산    : 기존 layer2_indicator/* 전부 재사용 (동일 수식)
  Layer 3 Risk A~D    : 기존 risk_market / volatility / liquidity / downside 재사용
                        (VIX → vkospi 파라미터로 직접 전달)
  Layer 3 Risk E      : layer3_risk.us_macro (신규 — US 지표 기반)
  Layer 4~6 / Rules   : 기존 scoring / strategy / insight / override / alert 전부 재사용

FRED 키 미설정 시:
  fed_rate·cpi·m2 = None → US 매크로는 DXY 단독 평가
  경고 없이 정상 동작 (Phase 1 VKOSPI 보류와 동일 패턴)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

# Layer 1 — US 전용
from layer1_data.us_fetcher import get_sp500_ohlcv, get_vix, get_dxy
from layer1_data.fred_fetcher import FredClient
from layer1_data.cleaner import clean_dataframe, align_to_business_days

# Layer 2 — 재사용
from layer2_indicator import price as p_ind
from layer2_indicator import volatility as v_ind
from layer2_indicator import liquidity as l_ind
from layer2_indicator import downside as d_ind
from layer2_indicator import derived as derived_ind
from layer2_indicator.monte_carlo import simulate_paths, mc_mdd_p50_series

# Layer 3 — A~D 재사용, E 신규
from layer3_risk import market as risk_market
from layer3_risk import volatility as risk_volatility
from layer3_risk import liquidity as risk_liquidity
from layer3_risk import downside as risk_downside
from layer3_risk import us_macro as risk_us_macro

# Layer 4~6, Rules — 전부 재사용
from layer4_scoring.phase import determine_phase, select_weights
from layer4_scoring.score import compute as score_compute
from layer5_strategy.strategy import compute as strategy_compute
from layer6_insight.insight import generate as insight_generate
from rules.override import apply_step4


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _at(s: pd.Series, default=None):
    """Series 마지막 유효값 추출 (orchestrator at() 동일 패턴)."""
    try:
        v = s.iloc[-1]
        return float(v) if pd.notna(v) else default
    except (IndexError, TypeError):
        return default


def run_us_snapshot(
    end_date: date,
    lookback_days: int = 400,
) -> dict[str, Any]:
    """S&P500 단일 영업일 종합 분석 → dict.

    Phase 1 run_snapshot()과 동일 키 구조 반환.
    "market": "us" 필드 추가로 구분.
    """
    end_dt   = end_date
    start_dt = end_dt - timedelta(days=lookback_days)
    end_str  = _yyyymmdd(end_dt)
    start_str = _yyyymmdd(start_dt)

    # ── STEP 1: 데이터 수집 ──────────────────────────────────
    sp500_raw = get_sp500_ohlcv(start_str, end_str)
    if sp500_raw.empty:
        raise RuntimeError("US STEP 1: S&P500 OHLCV empty")

    vix_raw = get_vix(start_str, end_str)
    dxy_raw = get_dxy(start_str, end_str)

    fred = FredClient()
    yoy_start = _yyyymmdd(end_dt - timedelta(days=lookback_days + 400))
    fed_raw = fred.get_fed_rate(yoy_start, end_str)
    cpi_raw = fred.get_us_cpi(yoy_start, end_str)
    m2_raw  = fred.get_us_m2(yoy_start, end_str)

    # ── STEP 2: 정제 + 지표 계산 ─────────────────────────────
    sp500, _ = clean_dataframe(sp500_raw, start_str, end_str)
    dxy      = align_to_business_days(dxy_raw, start_str, end_str) if not dxy_raw.empty else dxy_raw

    close = sp500["close"]
    high  = sp500["high"]
    low   = sp500["low"]
    vol   = sp500["volume"]
    val   = sp500.get("value", sp500["volume"])   # S&P500은 value 없음 → volume 대체

    # Layer 2 시리즈
    ma20_s  = p_ind.moving_average(close, 20)
    ma60_s  = p_ind.moving_average(close, 60)
    ma120_s = p_ind.moving_average(close, 120)
    disp20_s = p_ind.disparity(close, 20)
    disp60_s = p_ind.disparity(close, 60)
    adx_s    = p_ind.adx(high, low, close, 14)
    cdec_s   = p_ind.consec_decline(close)

    hv20_s = v_ind.historical_volatility(close, 20)
    hv60_s = v_ind.historical_volatility(close, 60)

    vol_ratio_s  = l_ind.vol_ratio(vol, 20)
    vol_streak_s = l_ind.vol_streak(vol, 20)
    val_ratio_s  = l_ind.val_ratio(val, 20)

    mdd60_s  = d_ind.mdd(close, 60)
    mdd252_s = d_ind.mdd(close, 252)
    var95_s  = d_ind.var_95(close, 252)
    cvar95_s = d_ind.cvar_95(close, 252)

    # MC forward-looking 메트릭 — Risk-D 등급 산정 입력 (orchestrator.py와 동일)
    paths_60  = simulate_paths(close, horizon=60)
    paths_252 = simulate_paths(close, horizon=252)
    mdd_60_mc_dict  = d_ind.mc_mdd_percentiles(paths_60)
    mdd_252_mc_dict = d_ind.mc_mdd_percentiles(paths_252)
    var_cvar_mc     = d_ind.mc_var_cvar_1d(paths_60)
    mdd60_mc_p50_s  = mc_mdd_p50_series(close, horizon=60, n_paths=2_000)

    last      = sp500.index[-1]
    timestamp = last.strftime("%Y-%m-%d")

    ma20, ma60, ma120       = _at(ma20_s), _at(ma60_s), _at(ma120_s)
    disp20, disp60          = _at(disp20_s), _at(disp60_s)
    adx_v                   = _at(adx_s)
    consec_decline_v        = int(_at(cdec_s, 0))
    hv20, hv60              = _at(hv20_s), _at(hv60_s)
    vol_ratio_hv_v          = (hv20 / hv60) if (hv20 and hv60) else 1.0
    vol_ratio_v             = _at(vol_ratio_s)
    val_ratio_v             = _at(val_ratio_s)
    vol_streak_v            = int(_at(vol_streak_s, 0))
    mdd60, mdd252           = _at(mdd60_s), _at(mdd252_s)
    var95, cvar95           = _at(var95_s), _at(cvar95_s)
    mdd_recovery_v          = derived_ind.mdd_recovery_months(close.tail(252))

    # VIX (VKOSPI 대응) — 마지막 공통 날짜 기준
    vix_today: float | None = None
    if not vix_raw.empty:
        common = vix_raw.index.intersection(sp500.index)
        if len(common):
            vix_today = float(vix_raw.reindex(common).iloc[-1])

    # DXY 파생
    dxy_today:         float | None = _at(dxy) if not dxy.empty else None
    dxy_weekly_change: float | None = None
    if not dxy.empty and len(dxy) >= 6:
        wc = derived_ind.fx_change(dxy, 5).iloc[-1]
        dxy_weekly_change = float(wc) if pd.notna(wc) else None

    # FRED 파생
    fed_today: float | None = None
    fed_delta: float | None = None
    if fed_raw is not None and not fed_raw.empty:
        fed_aligned = align_to_business_days(fed_raw, start_str, end_str)
        fed_today   = _at(fed_aligned)
        if len(fed_aligned) >= 22:
            fed_delta = float((fed_today or 0) - fed_aligned.iloc[-22])

    # CPI 월별 절대 지수(CPIAUCSL) → YoY % 변환. risk_us_macro의 CPI_YOY_* 임계값은 % 단위.
    cpi_yoy: float | None = None
    cpi_delta: float | None = None
    if cpi_raw is not None and len(cpi_raw) >= 13:
        cpi_yoy_series = ((cpi_raw / cpi_raw.shift(12) - 1.0) * 100.0).dropna()
        if not cpi_yoy_series.empty:
            cpi_yoy = float(cpi_yoy_series.iloc[-1])
            if len(cpi_yoy_series) >= 2:
                cpi_delta = float(cpi_yoy_series.iloc[-1] - cpi_yoy_series.iloc[-2])

    # M2 월별 절대 통화량(M2SL) → YoY 성장률 % → 전월 대비 %p 차이로 contraction 판정
    m2_contraction_v = False
    if m2_raw is not None and len(m2_raw) >= 14:
        m2_yoy_series = ((m2_raw / m2_raw.shift(12) - 1.0) * 100.0).dropna()
        if len(m2_yoy_series) >= 2:
            m2_yoy_now  = float(m2_yoy_series.iloc[-1])
            m2_yoy_prev = float(m2_yoy_series.iloc[-2])
            m2_contraction_v = bool((m2_yoy_now - m2_yoy_prev) <= M2_CONTRACTION_DROP)

    # MA flags
    ma_bullish_v      = (ma20 or 0) > (ma60 or 0) > (ma120 or 0)
    ma_bearish_full_v = (ma20 or 0) < (ma60 or 0) < (ma120 or 0)
    ma_converging_v   = bool(
        derived_ind.ma_converging(pd.Series([ma20]), pd.Series([ma60])).iloc[-1]
    )

    # ── STEP 3: 5개 리스크 등급 ─────────────────────────────
    risk_a = risk_market.evaluate(
        ma20=ma20, ma60=ma60, ma120=ma120,
        disp_ma20=disp20, disp_ma60=disp60,
        adx=adx_v, consec_decline=consec_decline_v,
        timestamp=timestamp,
    )
    risk_b = risk_volatility.evaluate(
        hv20=hv20, hv60=hv60, vol_ratio_hv=vol_ratio_hv_v,
        vkospi=vix_today,   # VIX → vkospi 직접 대응
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
    risk_e = risk_us_macro.evaluate(
        fed_rate=fed_today,
        fed_rate_delta=fed_delta,
        cpi_yoy=cpi_yoy,
        cpi_delta=cpi_delta,
        dxy_level=dxy_today,
        dxy_weekly_change=dxy_weekly_change,
        m2_contraction=m2_contraction_v,
        timestamp=timestamp,
    )
    risks = {
        "market":     risk_a,
        "volatility": risk_b,
        "liquidity":  risk_c,
        "downside":   risk_d,
        "macro":      risk_e,
    }

    # ── STEP 4~9: 기존 레이어 그대로 재사용 ─────────────────
    active_alerts: list[str] = []
    step4 = apply_step4(risks, active_alerts)
    critical_count_v = step4["critical_count"]

    phase   = determine_phase(
        ma_bullish=ma_bullish_v, ma_bearish_full=ma_bearish_full_v,
        ma_converging=ma_converging_v, adx=adx_v,
        consec_decline=consec_decline_v,
    )
    weights = select_weights(phase)
    score_result = score_compute(
        market_grade=risk_a.grade, volatility_grade=risk_b.grade,
        macro_grade=risk_e.grade, liquidity_grade=risk_c.grade,
        downside_grade=risk_d.grade, weights=weights, scn04_flag=False,
    )
    strat = strategy_compute(
        score_band=score_result["score_band"],
        integrated_score=score_result["score"],
        critical_count=critical_count_v,
        market_grade=risk_a.grade, volatility_grade=risk_b.grade,
        macro_grade=risk_e.grade, liquidity_grade=risk_c.grade,
        downside_grade=risk_d.grade,
    )

    # STATE 없이 실행 (US는 별도 STATE 미관리)
    dummy_state = {"consecutive_days": {f"INS-0{i}": 0 for i in range(1, 12)}}
    insights = insight_generate(
        market_grade=risk_a.grade, volatility_grade=risk_b.grade,
        liquidity_grade=risk_c.grade, downside_grade=risk_d.grade,
        macro_grade=risk_e.grade,
        integrated_score=score_result["score"],
        strategy=strat["strategy"],
        triggered_scenario=risk_e.details.flags.get("triggered_scenario"),
        fi_streak_sell=0, vol_streak=vol_streak_v,
        var_95=var95 or 0.0, ma_bullish=ma_bullish_v,
        consecutive_days=dummy_state["consecutive_days"],
        active_alerts=active_alerts,
    )

    return {
        "market":         "us",
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
        "fred_available": risk_e.details.flags.get("fred_available", False),
        "series": {
            "close":     close,
            "ma20":      ma20_s,
            "ma60":      ma60_s,
            "ma120":     ma120_s,
            "hv20":      hv20_s,
            "mdd60":     mdd60_s,
            "mdd60_mc_p50": mdd60_mc_p50_s,
            "var95":     var95_s,
            "vol_ratio": vol_ratio_s,
        },
    }


# M2 임계값 (thresholds.py에서 재사용)
from config.thresholds import M2_CONTRACTION_DROP  # noqa: E402

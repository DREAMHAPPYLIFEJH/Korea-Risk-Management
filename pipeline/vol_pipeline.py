"""변동성 리스크 프레임워크 파이프라인 — Phase 5.

run_vol_analysis(kospi_result, us_result): Phase 1(run_snapshot) + Phase 3(run_us_snapshot)
결과를 받아 한미 변동성 관계지표(RI-01~05)·5분류 레짐·핵심 신호를 산출.
표시 전용 — 통합 점수·5리스크·Override·Alert에 영향 없음 (sector_pipeline 패턴).

신규 변동성 데이터(VIX·VVIX·SKEW·V-KOSPI)는 본 파이프라인이 직접 수집하고,
가격·HV 시계열은 두 result에서 추출한다.

Skills.md 참조: Phase 5 §P5-6(출력 스키마), §P5-7(통합 위치)
"""

from __future__ import annotations

from typing import Any

import pandas as pd

import layer2_indicator.cross_market as cm
from layer1_data.us_fetcher import get_vix, get_vvix, get_skew
from layer1_data.vkospi_fetcher import get_vkospi


def _last(s: pd.Series | None) -> float | None:
    """시계열 마지막 유효값 (없으면 None). orchestrator at() 패턴 변형."""
    if s is None or len(s) == 0:
        return None
    s = s.dropna()
    return float(s.iloc[-1]) if len(s) else None


def _round(v: float | None, n: int = 2) -> float | None:
    return round(v, n) if v is not None else None


def run_vol_analysis(
    kospi_result: dict[str, Any], us_result: dict[str, Any]
) -> dict[str, Any]:
    """한미 변동성 관계 분석. 두 시장 스냅샷 dict 입력 → 표시용 dict 반환."""
    kospi_close = kospi_result["series"]["close"]
    sp_close    = us_result["series"]["close"]
    kospi_hv20  = _last(kospi_result["series"]["hv20"])
    sp_hv20     = _last(us_result["series"]["hv20"])

    # 수집 기간 — 두 종가 인덱스의 합집합 범위
    idx = kospi_close.index.union(sp_close.index)
    start = idx.min().strftime("%Y%m%d")
    end   = idx.max().strftime("%Y%m%d")

    # 신규 변동성 데이터 직접 수집
    vix_s    = get_vix(start, end)
    vvix_s   = get_vvix(start, end)
    skew_s   = get_skew(start, end)
    vkospi_s = get_vkospi(start, end)

    vix    = _last(vix_s)
    vvix   = _last(vvix_s)
    skew   = _last(skew_s)
    vkospi = _last(vkospi_s)

    # RI-01~03
    spread      = cm.vix_vkospi_spread(vix, vkospi)
    hvr         = cm.hv_ratio(kospi_hv20, sp_hv20)
    us_vrp      = cm.vrp(vix, sp_hv20)
    kr_vrp      = cm.vrp(vkospi, kospi_hv20)
    vrp_div     = cm.vrp_divergence(us_vrp, kr_vrp)
    # RI-05 — 동시점 상관·베타 + 미국 선행 시차 상관
    corr_60d, kospi_beta = cm.correlation_beta(kospi_close, sp_close)
    lagged_corr = cm.lead_lag_correlation(kospi_close, sp_close)

    # TRG-01 입력 — KOSPI result에서 환율 시계열·외국인 연속 순매도 추출
    # (orchestrator가 노출. 구 데모 pkl엔 없을 수 있어 graceful .get())
    fx_series = kospi_result["series"].get("fx_rate")
    fx_spike = cm.fx_vol_spike(fx_series) if fx_series is not None else False
    streak_sell = kospi_result.get("foreign", {}).get("streak_sell", 0)
    foreign_net_sell_5d = streak_sell >= 5

    # 레짐 + 트리거
    regime_id, regime_label = cm.classify_regime(vix, vkospi, vix_s, vkospi_s)
    triggers = cm.evaluate_triggers(
        vix=vix, vkospi=vkospi, corr_60d=corr_60d, vvix=vvix,
        fx_spike=fx_spike, foreign_net_sell_5d=foreign_net_sell_5d,
    )

    return {
        "regime":       regime_id,
        "regime_label": regime_label,
        "us": {"vix": _round(vix), "vvix": _round(vvix), "skew": _round(skew),
               "us_vrp": _round(us_vrp)},
        "kr": {"vkospi": _round(vkospi), "kospi_hv20": _round(kospi_hv20),
               "kr_vrp": _round(kr_vrp)},
        "relationship": {
            "vix_vkospi_spread": _round(spread),
            "hv_ratio":          _round(hvr),
            "vrp_divergence":    _round(vrp_div),
            "corr_60d":          _round(corr_60d, 3),
            "lagged_corr_60d":   _round(lagged_corr, 3),  # 미국 1일 선행 전이 상관
            "kospi_beta":        _round(kospi_beta, 3),
        },
        "triggers": triggers,
        "data_available": {
            "vkospi":    len(vkospi_s) > 0,
            "vvix":      len(vvix_s) > 0,
            "skew":      len(skew_s) > 0,
        },
        # 시계열 (시각화용)
        "series": {
            "vix":    vix_s,
            "vkospi": vkospi_s,
            "spread": (vix_s - vkospi_s).dropna() if len(vkospi_s) else pd.Series(dtype=float),
            "garch_kospi": cm.garch_conditional_vol(kospi_close),  # GARCH 조건부 변동성(연율%)
            "garch_sp":    cm.garch_conditional_vol(sp_close),
        },
    }

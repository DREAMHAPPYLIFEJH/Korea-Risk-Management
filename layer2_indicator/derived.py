"""파생 지표 — Skills.md §3 Derived Indicator Definitions.

Layer 1 / Layer 2 원시 지표를 받아 의사결정에 직접 쓰이는 신호로 가공.

- fx_change(fx_rate, periods): 환율 N영업일 변화율 (일간/주간)
- rate_spread(kr_rate, us_rate): 한미 금리차
- ma_flags(ma20, ma60, ma120): bullish / bearish_part / bearish_full 불리언
- ma_gap_ratio(ma20, ma60), ma_converging(ma20, ma60)
- m2_contraction / m2_growth_slowdown / m2_expansion (Skills.md §3 IF/ELIF/ELSE 그대로)
- mdd_recovery_months(close_window): 최근 252일 내 trough → peak 회복 월수

`all_risk_grades`, `critical_count` 같은 등급 집계 변수는 파이프라인 단계에서 산출
(Layer 3 결과가 있어야 산출 가능) → 본 모듈 미포함.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.thresholds import (
    M2_CONTRACTION_DROP,
    M2_SLOWDOWN_DROP,
    M2_EXPANSION_RISE,
    MA_CONVERGING_RATIO,
    MDD_RECOVERY_UNFINISHED,
)


# ── 환율 변화율 ────────────────────────────────────────────
def fx_change(fx_rate: pd.Series, periods: int) -> pd.Series:
    """환율 N영업일 변화율 (Skills.md §3).

    fx_daily_change = fx_change(fx_rate, 1)
    fx_weekly_change = fx_change(fx_rate, 5)
    """
    return fx_rate.pct_change(periods=periods)


# ── 금리차 ────────────────────────────────────────────────
def rate_spread(kr_base_rate: pd.Series, us_base_rate: pd.Series) -> pd.Series:
    """한미 금리차 (Skills.md §3: kr - us).

    rate_spread_curr = .iloc[-1], rate_spread_prev = .iloc[-2].
    두 시리즈는 동일 인덱스(영업일)로 정합되어 있어야 함.
    """
    return (kr_base_rate - us_base_rate).rename("rate_spread")


# ── MA 배열 ────────────────────────────────────────────────
def ma_bullish(ma20: pd.Series, ma60: pd.Series, ma120: pd.Series) -> pd.Series:
    """정배열: MA20 > MA60 > MA120."""
    return ((ma20 > ma60) & (ma60 > ma120)).rename("ma_bullish")


def ma_bearish_full(ma20: pd.Series, ma60: pd.Series, ma120: pd.Series) -> pd.Series:
    """완전 역배열: MA20 < MA60 < MA120."""
    return ((ma20 < ma60) & (ma60 < ma120)).rename("ma_bearish_full")


def ma_bearish_part(ma20: pd.Series, ma60: pd.Series) -> pd.Series:
    """부분 역배열: MA20 < MA60 (완전 역배열 포함)."""
    return (ma20 < ma60).rename("ma_bearish_part")


def ma_gap_ratio(ma20: pd.Series, ma60: pd.Series) -> pd.Series:
    """MA20-MA60 절대 갭 / MA60 (Skills.md §3)."""
    return ((ma20 - ma60).abs() / ma60).rename("ma_gap_ratio")


def ma_converging(ma20: pd.Series, ma60: pd.Series) -> pd.Series:
    """MA 수렴 여부 — gap_ratio < 0.02."""
    return (ma_gap_ratio(ma20, ma60) < MA_CONVERGING_RATIO).rename("ma_converging")


# ── M2 신호 ────────────────────────────────────────────────
def m2_contraction(m2_growth: pd.Series) -> pd.Series:
    """M2 축소: 전월 대비 1.0%p 이상 감소 OR 양수 → 0 이하 전환 (Skills.md §3)."""
    prev = m2_growth.shift(1)
    delta = m2_growth - prev
    threshold_drop = delta <= M2_CONTRACTION_DROP
    sign_flip = (m2_growth <= 0) & (prev > 0)
    return (threshold_drop | sign_flip).rename("m2_contraction")


def m2_growth_slowdown(m2_growth: pd.Series) -> pd.Series:
    """M2 증가율 둔화: 전월 대비 0.5%p 이상 감소, 단 축소 미달 (Skills.md §3)."""
    prev = m2_growth.shift(1)
    drop = (prev - m2_growth) >= M2_SLOWDOWN_DROP
    not_contract = ~m2_contraction(m2_growth)
    return (drop & not_contract).rename("m2_growth_slowdown")


def m2_expansion(m2_growth: pd.Series) -> pd.Series:
    """M2 확대: 전월 대비 1.0%p 이상 증가 (Skills.md §3)."""
    prev = m2_growth.shift(1)
    return ((m2_growth - prev) >= M2_EXPANSION_RISE).rename("m2_expansion")


# ── MDD 회복 기간 ──────────────────────────────────────────
def mdd_recovery_months(close_window: pd.Series) -> float:
    """최근 252일 내 최저점 이후 peak 회복 소요 월수 (Skills.md §3).

    21영업일 ≈ 1개월. 회복 미완료 시 MDD_RECOVERY_UNFINISHED(=99) 반환.
    close_window: 최근 252영업일 close 시리즈 (또는 그보다 짧아도 무방).
    """
    arr = np.asarray(close_window.values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < 2:
        return float(MDD_RECOVERY_UNFINISHED)

    trough_idx = int(np.argmin(arr))
    if trough_idx == 0:
        return float(MDD_RECOVERY_UNFINISHED)

    peak_before_trough = float(np.max(arr[:trough_idx]))

    for i in range(trough_idx + 1, arr.size):
        if arr[i] >= peak_before_trough:
            return (i - trough_idx) / 21.0
    return float(MDD_RECOVERY_UNFINISHED)

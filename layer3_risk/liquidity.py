"""Risk-C 유동성 리스크 — Skills.md §7 Risk-C.

기본 가중치 15%.
- 기본 등급: vol_ratio + vol_streak 조합
- 보조 보정: val_ratio < 0.6 OR conc_ratio > 0.4 → 최소 Medium 보장
- conc_ratio는 Phase 1 미수집 (KOSPI 종목별 상위10 거래대금 별도 호출 필요)
"""

from __future__ import annotations

from config.thresholds import (
    VOL_RATIO_NORMAL, VOL_RATIO_REDUCED, VOL_RATIO_SEVERE,
    VOL_STREAK_HIGH, VOL_STREAK_CRITICAL,
    VAL_RATIO_WARNING, CONC_RATIO_HEAVY,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-C"
WEIGHT_DEFAULT = 0.15
CONFLICT_RULE = "none"
CONDITION_CANDIDATES = [
    "vol_ratio_gte_1.0", "vol_ratio_0.7_to_1.0",
    "vol_ratio_0.5_to_0.7", "vol_ratio_lt_0.5",
    "vol_streak_gte_3", "vol_streak_gte_5",
    "val_ratio_lt_0.6", "conc_ratio_gt_0.4",
]


def evaluate(
    *,
    vol_ratio: float,
    vol_streak: int,
    val_ratio: float | None = None,
    conc_ratio: float | None = None,
    timestamp: str,
) -> RiskOutput:
    """Risk-C 등급 산정.

    conc_ratio=None: Phase 1 미수집 (보정 미적용).
    """
    # ── 기본 등급 ─────────────────────────────────────────
    if vol_ratio < VOL_RATIO_SEVERE and vol_streak >= VOL_STREAK_CRITICAL:
        liquidity_grade = 4
    elif (VOL_RATIO_SEVERE <= vol_ratio < VOL_RATIO_REDUCED
          and vol_streak >= VOL_STREAK_HIGH):
        liquidity_grade = 3
    elif VOL_RATIO_REDUCED <= vol_ratio < VOL_RATIO_NORMAL:
        liquidity_grade = 2
    elif vol_ratio >= VOL_RATIO_NORMAL:
        liquidity_grade = 1
    else:
        liquidity_grade = 2

    # ── 보조 지표 보정 ────────────────────────────────────
    val_ratio_warning = (val_ratio is not None) and (val_ratio < VAL_RATIO_WARNING)
    if val_ratio_warning and liquidity_grade < 2:
        liquidity_grade = 2

    concentration_high = (conc_ratio is not None) and (conc_ratio > CONC_RATIO_HEAVY)
    if concentration_high and liquidity_grade < 2:
        liquidity_grade = 2

    # ── triggered_conditions ─────────────────────────────
    triggered: list[str] = []
    if vol_ratio < VOL_RATIO_SEVERE:
        triggered.append("vol_ratio_lt_0.5")
    elif vol_ratio < VOL_RATIO_REDUCED:
        triggered.append("vol_ratio_0.5_to_0.7")
    elif vol_ratio < VOL_RATIO_NORMAL:
        triggered.append("vol_ratio_0.7_to_1.0")
    else:
        triggered.append("vol_ratio_gte_1.0")

    if vol_streak >= VOL_STREAK_CRITICAL:
        triggered.append("vol_streak_gte_5")
    elif vol_streak >= VOL_STREAK_HIGH:
        triggered.append("vol_streak_gte_3")

    if val_ratio_warning:
        triggered.append("val_ratio_lt_0.6")
    if concentration_high:
        triggered.append("conc_ratio_gt_0.4")

    return RiskOutput(
        risk_id=RISK_ID,
        grade=liquidity_grade,
        score=liquidity_grade,
        triggered_conditions=triggered,
        reason=f"liquidity_risk grade={liquidity_grade} based on " + ", ".join(triggered),
        details=RiskDetails(
            risk_type="liquidity",
            grade_label=grade_label(liquidity_grade),
            weight_default=WEIGHT_DEFAULT,
            timestamp=timestamp,
            indicators={
                "vol_ratio":  vol_ratio,
                "val_ratio":  val_ratio,
                "conc_ratio": conc_ratio,
                "vol_streak": vol_streak,
            },
            sub_grades={},
            flags={
                "concentration_high": concentration_high,
                "val_ratio_warning":  val_ratio_warning,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

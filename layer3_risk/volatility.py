"""Risk-B 변동성 리스크 — Skills.md §7 Risk-B.

기본 가중치 25%.
- HV20 등급 (4단계)
- VKOSPI 등급 (Phase 1 보류 — Skills.md §5 구현 노트)
- CR-01 충돌 해소: MAX(hv_grade, vkospi_grade); VKOSPI 없으면 hv_grade
- 보조 플래그: vol_spike (>1.2), vol_contraction (<0.8)
"""

from __future__ import annotations

from config.thresholds import (
    HV20_CRITICAL, HV20_HIGH, HV20_MEDIUM,
    VKOSPI_CRITICAL, VKOSPI_HIGH, VKOSPI_MEDIUM,
    VOL_RATIO_HV_SPIKE, VOL_RATIO_HV_CONTRACTION,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-B"
WEIGHT_DEFAULT = 0.25
CONFLICT_RULE = "MAX(hv_grade, vkospi_grade)"
CONDITION_CANDIDATES = [
    "hv20_lt_12", "hv20_gte_12", "hv20_gte_20", "hv20_gte_30",
    "vkospi_lt_15", "vkospi_gte_15", "vkospi_gte_25", "vkospi_gte_35",
    "cr01_max_applied",
]


def _hv20_grade(hv20: float) -> int:
    if hv20 >= HV20_CRITICAL: return 4
    if hv20 >= HV20_HIGH:     return 3
    if hv20 >= HV20_MEDIUM:   return 2
    return 1


def _vkospi_grade(vkospi: float) -> int:
    if vkospi >= VKOSPI_CRITICAL: return 4
    if vkospi >= VKOSPI_HIGH:     return 3
    if vkospi >= VKOSPI_MEDIUM:   return 2
    return 1


def evaluate(
    *,
    hv20: float,
    hv60: float,
    vol_ratio_hv: float,
    vkospi: float | None = None,
    timestamp: str,
) -> RiskOutput:
    """Risk-B 등급 산정.

    vkospi=None이면 VKOSPI 보류 (Phase 1) — volatility_grade = hv_grade.
    """
    hv_grade = _hv20_grade(hv20)

    if vkospi is not None:
        vkospi_grade = _vkospi_grade(vkospi)
        if hv_grade != vkospi_grade:
            volatility_grade = max(hv_grade, vkospi_grade)
            cr01_applied = True
        else:
            volatility_grade = hv_grade
            cr01_applied = False
    else:
        vkospi_grade = None
        volatility_grade = hv_grade
        cr01_applied = False

    vol_spike = vol_ratio_hv > VOL_RATIO_HV_SPIKE
    vol_contraction = vol_ratio_hv < VOL_RATIO_HV_CONTRACTION

    triggered: list[str] = []
    if hv20 >= HV20_CRITICAL:    triggered.append("hv20_gte_30")
    elif hv20 >= HV20_HIGH:      triggered.append("hv20_gte_20")
    elif hv20 >= HV20_MEDIUM:    triggered.append("hv20_gte_12")
    else:                        triggered.append("hv20_lt_12")

    if vkospi is not None:
        if vkospi >= VKOSPI_CRITICAL:    triggered.append("vkospi_gte_35")
        elif vkospi >= VKOSPI_HIGH:      triggered.append("vkospi_gte_25")
        elif vkospi >= VKOSPI_MEDIUM:    triggered.append("vkospi_gte_15")
        else:                            triggered.append("vkospi_lt_15")

    if cr01_applied:
        triggered.append("cr01_max_applied")

    return RiskOutput(
        risk_id=RISK_ID,
        grade=volatility_grade,
        score=volatility_grade,
        triggered_conditions=triggered,
        reason=f"volatility_risk grade={volatility_grade} based on " + ", ".join(triggered),
        details=RiskDetails(
            risk_type="volatility",
            grade_label=grade_label(volatility_grade),
            weight_default=WEIGHT_DEFAULT,
            timestamp=timestamp,
            indicators={
                "hv20":         hv20,
                "hv60":         hv60,
                "vol_ratio_hv": vol_ratio_hv,
                "vkospi":       vkospi,
            },
            sub_grades={
                "hv_grade":     hv_grade,
                "vkospi_grade": vkospi_grade,
            },
            flags={
                "vol_spike":       vol_spike,
                "vol_contraction": vol_contraction,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

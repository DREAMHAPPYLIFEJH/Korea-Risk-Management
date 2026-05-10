"""Risk-D 하방 리스크 — Skills.md §7 Risk-D.

기본 가중치 10%.
- mdd_grade (MDD_60 기반 4단계)
- var_grade (VaR_95 기반 4단계)
- CR-02 충돌 해소: MAX(mdd_grade, var_grade)
- recovery_signal: mdd_recovery_months 기반 fast/slow/unknown

OVR-06 (단독 Critical 시스템 격상 예외)는 본 모듈에서 평가하지 않음 →
Layer 4/Override 단계에서 5개 등급 모두 확정 후 평가.
"""

from __future__ import annotations

from config.thresholds import (
    MDD_60_CRITICAL, MDD_60_HIGH, MDD_60_MEDIUM,
    VAR_95_CRITICAL, VAR_95_HIGH, VAR_95_MEDIUM,
    MDD_RECOVERY_FAST, MDD_RECOVERY_SLOW,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-D"
WEIGHT_DEFAULT = 0.10
CONFLICT_RULE = "MAX(mdd_grade, var_grade)"
CONDITION_CANDIDATES = [
    "mdd_60_gt_minus5", "mdd_60_lte_minus5",
    "mdd_60_lte_minus10", "mdd_60_lte_minus20",
    "var_95_gt_minus1.5", "var_95_lte_minus1.5",
    "var_95_lte_minus2.5", "var_95_lte_minus3.5",
    "cr02_max_applied", "ovr06_single_critical_exception",
]


def _mdd_grade(mdd_60: float) -> int:
    if mdd_60 <= MDD_60_CRITICAL: return 4
    if mdd_60 <= MDD_60_HIGH:     return 3
    if mdd_60 <= MDD_60_MEDIUM:   return 2
    return 1


def _var_grade(var_95: float) -> int:
    if var_95 <= VAR_95_CRITICAL: return 4
    if var_95 <= VAR_95_HIGH:     return 3
    if var_95 <= VAR_95_MEDIUM:   return 2
    return 1


def _recovery_signal(months: float) -> str:
    if months < MDD_RECOVERY_FAST: return "fast"
    if months > MDD_RECOVERY_SLOW: return "slow"
    return "unknown"


def evaluate(
    *,
    mdd_60: float,
    mdd_252: float,
    var_95: float,
    cvar: float,
    mdd_recovery_months: float,
    timestamp: str,
) -> RiskOutput:
    """Risk-D 등급 산정."""
    mdd_g = _mdd_grade(mdd_60)
    var_g = _var_grade(var_95)

    if mdd_g != var_g:
        downside_grade = max(mdd_g, var_g)
        cr02_applied = True
    else:
        downside_grade = mdd_g
        cr02_applied = False

    rec = _recovery_signal(mdd_recovery_months)

    triggered: list[str] = []
    if mdd_60 <= MDD_60_CRITICAL:    triggered.append("mdd_60_lte_minus20")
    elif mdd_60 <= MDD_60_HIGH:      triggered.append("mdd_60_lte_minus10")
    elif mdd_60 <= MDD_60_MEDIUM:    triggered.append("mdd_60_lte_minus5")
    else:                            triggered.append("mdd_60_gt_minus5")

    if var_95 <= VAR_95_CRITICAL:    triggered.append("var_95_lte_minus3.5")
    elif var_95 <= VAR_95_HIGH:      triggered.append("var_95_lte_minus2.5")
    elif var_95 <= VAR_95_MEDIUM:    triggered.append("var_95_lte_minus1.5")
    else:                            triggered.append("var_95_gt_minus1.5")

    if cr02_applied:
        triggered.append("cr02_max_applied")
    # ovr06_single_critical_exception은 STEP 4 (Override)에서 추가

    return RiskOutput(
        risk_id=RISK_ID,
        grade=downside_grade,
        score=downside_grade,
        triggered_conditions=triggered,
        reason=f"downside_risk grade={downside_grade} based on " + ", ".join(triggered),
        details=RiskDetails(
            risk_type="downside",
            grade_label=grade_label(downside_grade),
            weight_default=WEIGHT_DEFAULT,
            timestamp=timestamp,
            indicators={
                "mdd_60":  mdd_60,
                "mdd_252": mdd_252,
                "var_95":  var_95,
                "cvar":    cvar,
            },
            sub_grades={
                "mdd_grade": mdd_g,
                "var_grade": var_g,
            },
            flags={
                "recovery_signal": rec,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

"""Risk-D 하방 리스크 — Skills.md §7 Risk-D.

기본 가중치 10%.

등급 산정 (MC 기반 — 신 정의, Skills.md §9 갱신 예정):
  - mc_p50_grade: 60일 forward MDD 분포의 중위값 (MDD_60_MC_P50_* 임계값)
  - mc_p5_grade:  60일 forward MDD 분포의 worst 5% (MDD_60_MC_P5_* 임계값)
  - var_mc_grade: MC 1일 VaR (VAR_95_* 임계값 재사용)
  - CR-02 충돌 해소: MAX(mc_p50_grade, mc_p5_grade, var_mc_grade)

Legacy 지표 (Skills.md §6 historical — indicators dict에 참고용으로 보존):
  - mdd_60 / mdd_252: 윈도우 min/max 비율 (우상향장에서 -67% 같은 spurious 값 발생)
  - var_95 / cvar:    Historical Simulation 분위수

OVR-06 (단독 Critical 시스템 격상 예외)는 Layer 4/Override에서 평가.
"""

from __future__ import annotations

from config.thresholds import (
    MDD_60_CRITICAL, MDD_60_HIGH, MDD_60_MEDIUM,
    MDD_60_MC_P50_CRITICAL, MDD_60_MC_P50_HIGH, MDD_60_MC_P50_MEDIUM,
    MDD_60_MC_P5_CRITICAL, MDD_60_MC_P5_HIGH, MDD_60_MC_P5_MEDIUM,
    VAR_95_CRITICAL, VAR_95_HIGH, VAR_95_MEDIUM,
    MDD_RECOVERY_FAST, MDD_RECOVERY_SLOW,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-D"
WEIGHT_DEFAULT = 0.10
CONFLICT_RULE = "MAX(mc_p50_grade, mc_p5_grade, var_mc_grade)"
CONDITION_CANDIDATES = [
    # Legacy (참고용)
    "mdd_60_gt_minus5", "mdd_60_lte_minus5",
    "mdd_60_lte_minus10", "mdd_60_lte_minus20",
    "var_95_gt_minus1.5", "var_95_lte_minus1.5",
    "var_95_lte_minus2.5", "var_95_lte_minus3.5",
    # MC p50
    "mc_p50_low", "mc_p50_medium", "mc_p50_high", "mc_p50_critical",
    # MC p5
    "mc_p5_low", "mc_p5_medium", "mc_p5_high", "mc_p5_critical",
    # MC VaR
    "var_mc_low", "var_mc_medium", "var_mc_high", "var_mc_critical",
    "cr02_max_applied", "ovr06_single_critical_exception",
    "mc_fallback_to_legacy",
]


def _mdd_grade_legacy(mdd_60: float) -> int:
    """Legacy MDD 등급 — 참고용, grade에는 미반영."""
    if mdd_60 <= MDD_60_CRITICAL: return 4
    if mdd_60 <= MDD_60_HIGH:     return 3
    if mdd_60 <= MDD_60_MEDIUM:   return 2
    return 1


def _mc_p50_grade(p50: float) -> int:
    if p50 <= MDD_60_MC_P50_CRITICAL: return 4
    if p50 <= MDD_60_MC_P50_HIGH:     return 3
    if p50 <= MDD_60_MC_P50_MEDIUM:   return 2
    return 1


def _mc_p5_grade(p5: float) -> int:
    if p5 <= MDD_60_MC_P5_CRITICAL: return 4
    if p5 <= MDD_60_MC_P5_HIGH:     return 3
    if p5 <= MDD_60_MC_P5_MEDIUM:   return 2
    return 1


def _var_grade(var_95: float) -> int:
    if var_95 <= VAR_95_CRITICAL: return 4
    if var_95 <= VAR_95_HIGH:     return 3
    if var_95 <= VAR_95_MEDIUM:   return 2
    return 1


def _p50_condition(g: int) -> str:
    return {1: "mc_p50_low", 2: "mc_p50_medium", 3: "mc_p50_high", 4: "mc_p50_critical"}[g]


def _p5_condition(g: int) -> str:
    return {1: "mc_p5_low", 2: "mc_p5_medium", 3: "mc_p5_high", 4: "mc_p5_critical"}[g]


def _var_mc_condition(g: int) -> str:
    return {1: "var_mc_low", 2: "var_mc_medium", 3: "var_mc_high", 4: "var_mc_critical"}[g]


def _recovery_signal(months: float) -> str:
    if months < MDD_RECOVERY_FAST: return "fast"
    if months > MDD_RECOVERY_SLOW: return "slow"
    return "unknown"


def evaluate(
    *,
    # Legacy historical (참고용 — indicators dict에만 보존)
    mdd_60: float,
    mdd_252: float,
    var_95: float,
    cvar: float,
    mdd_recovery_months: float,
    # MC forward-looking (등급 산정 입력)
    mdd_60_mc: dict[str, float] | None = None,
    mdd_252_mc: dict[str, float] | None = None,
    var_95_mc: float | None = None,
    cvar_mc: float | None = None,
    timestamp: str,
) -> RiskOutput:
    """Risk-D 등급 산정.

    MC 입력이 None이면 legacy 식 (CR-02 MAX(mdd_grade, var_grade))으로 fallback.
    MC 입력이 있으면 MAX(mc_p50_grade, mc_p5_grade, var_mc_grade) 적용.
    """
    # Legacy 등급 (indicators 표시 + fallback용)
    mdd_g_legacy = _mdd_grade_legacy(mdd_60)
    var_g_legacy = _var_grade(var_95)

    triggered: list[str] = []
    sub_grades: dict[str, int | None] = {
        "mdd_grade_legacy": mdd_g_legacy,
        "var_grade_legacy": var_g_legacy,
    }
    mc_used = mdd_60_mc is not None and var_95_mc is not None

    if mc_used:
        p50_g = _mc_p50_grade(mdd_60_mc["p50"])
        p5_g  = _mc_p5_grade(mdd_60_mc["p5"])
        vmc_g = _var_grade(var_95_mc)

        downside_grade = max(p50_g, p5_g, vmc_g)
        sub_grades["mc_p50_grade"] = p50_g
        sub_grades["mc_p5_grade"]  = p5_g
        sub_grades["var_mc_grade"] = vmc_g

        triggered.append(_p50_condition(p50_g))
        triggered.append(_p5_condition(p5_g))
        triggered.append(_var_mc_condition(vmc_g))

        # CR-02 적용 여부: 세 sub-grade가 모두 같지 않으면 적용된 것
        if len({p50_g, p5_g, vmc_g}) > 1:
            triggered.append("cr02_max_applied")
    else:
        # Legacy fallback — Skills.md §6 원래 공식
        downside_grade = max(mdd_g_legacy, var_g_legacy)
        sub_grades["mc_p50_grade"] = None
        sub_grades["mc_p5_grade"]  = None
        sub_grades["var_mc_grade"] = None
        triggered.append("mc_fallback_to_legacy")

        if mdd_60 <= MDD_60_CRITICAL:    triggered.append("mdd_60_lte_minus20")
        elif mdd_60 <= MDD_60_HIGH:      triggered.append("mdd_60_lte_minus10")
        elif mdd_60 <= MDD_60_MEDIUM:    triggered.append("mdd_60_lte_minus5")
        else:                            triggered.append("mdd_60_gt_minus5")

        if var_95 <= VAR_95_CRITICAL:    triggered.append("var_95_lte_minus3.5")
        elif var_95 <= VAR_95_HIGH:      triggered.append("var_95_lte_minus2.5")
        elif var_95 <= VAR_95_MEDIUM:    triggered.append("var_95_lte_minus1.5")
        else:                            triggered.append("var_95_gt_minus1.5")

        if mdd_g_legacy != var_g_legacy:
            triggered.append("cr02_max_applied")

    rec = _recovery_signal(mdd_recovery_months)

    indicators: dict[str, float | dict[str, float] | None] = {
        # Legacy 원본 (참고용)
        "mdd_60":  mdd_60,
        "mdd_252": mdd_252,
        "var_95":  var_95,
        "cvar":    cvar,
        # MC forward-looking
        "mdd_60_mc":  mdd_60_mc,
        "mdd_252_mc": mdd_252_mc,
        "var_95_mc":  var_95_mc,
        "cvar_mc":    cvar_mc,
    }

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
            indicators=indicators,
            sub_grades=sub_grades,
            flags={
                "recovery_signal": rec,
                "mc_used":         mc_used,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

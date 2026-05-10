"""Override Rules — Skills.md §13 (OVR-01 ~ OVR-06).

적용 순서:
  STEP 4 (등급 확정 후): OVR-01 → OVR-06 → OVR-02
  STEP 7 (전략):           OVR-03 → OVR-04
  STEP 8 (인사이트):        OVR-05

OVR-01: 시나리오 발동 → macro_grade=4 강제 (Risk-E 내부에서 이미 적용 — 검증만)
OVR-02: critical_count >= 1 → ALT-02 강제 (alerts 리스트에 추가)
OVR-03: critical_count >= 1 → 최소 Moderate_Defensive 강제 (전략 단계)
OVR-04: critical >= 2 + score > 2.5 → Defensive 강제 (전략 단계)
OVR-05: 인사이트 마지막 = 전략 권고 강제 (인사이트 단계)
OVR-06: 하방 단독 Critical → 시스템 자동 격상 없음 (Risk-D triggered에 표식)
"""

from __future__ import annotations

from typing import Any

from config.constants import STRATEGY_LEVEL, STRATEGY_INSIGHT_TEMPLATE
from layer3_risk.schema import RiskOutput


# ── 공통 유틸 ──────────────────────────────────────────────
def count_critical(risks: dict[str, RiskOutput]) -> int:
    """전체 5개 리스크 중 grade==4 개수."""
    return sum(1 for r in risks.values() if r.grade == 4)


def all_risk_grades(risks: dict[str, RiskOutput]) -> list[int]:
    """[market, volatility, liquidity, downside, macro] 순서 등급 리스트."""
    return [risks[k].grade for k in ("market", "volatility", "liquidity", "downside", "macro")]


# ── OVR-01: 매크로 시나리오 → Critical 강제 ───────────────
def verify_ovr01(risks: dict[str, RiskOutput]) -> bool:
    """OVR-01 검증 — Risk-E 내부에서 이미 적용됐는지 확인 (사후 무결성).

    triggered_scenario != None이면 macro_grade == 4 이어야 함.
    """
    macro = risks["macro"]
    triggered_scn = macro.details.flags.get("triggered_scenario")
    if triggered_scn is not None and macro.grade != 4:
        return False
    return True


# ── OVR-06: 하방 단독 Critical 예외 ───────────────────────
def is_ovr06_active(risks: dict[str, RiskOutput]) -> bool:
    """하방 Critical AND 나머지 4개 모두 ≤ 3."""
    if risks["downside"].grade != 4:
        return False
    return all(
        risks[k].grade <= 3
        for k in ("market", "volatility", "liquidity", "macro")
    )


def apply_ovr06(risks: dict[str, RiskOutput]) -> bool:
    """OVR-06 적용 — Risk-D triggered_conditions에 표식 추가, system_critical_escalation 반환.

    Returns True if system 격상 정상 (OVR-06 미발동), False면 격상 차단.
    """
    if is_ovr06_active(risks):
        # Risk-D triggered_conditions에 누락된 경우만 추가
        td = risks["downside"].triggered_conditions
        if "ovr06_single_critical_exception" not in td:
            td.append("ovr06_single_critical_exception")
        return False  # system_critical_escalation = False
    return True


# ── OVR-02: 단일 Critical → ALT-02 강제 ───────────────────
def apply_ovr02(critical_count: int, active_alerts: list[str]) -> None:
    """ALT-02를 active_alerts에 추가 (이미 있으면 무시). In-place 수정."""
    if critical_count >= 1 and "ALT-02" not in active_alerts:
        active_alerts.append("ALT-02")


# ── STEP 4 통합 ───────────────────────────────────────────
def apply_step4(
    risks: dict[str, RiskOutput],
    active_alerts: list[str],
) -> dict[str, Any]:
    """STEP 4 Override 일괄 적용 — Skills.md §4.

    순서: OVR-01 검증 → OVR-06 → OVR-02.

    Returns:
        {
            "critical_count": int,
            "system_critical_escalation": bool,
            "ovr01_consistent": bool,
        }
    """
    cnt = count_critical(risks)
    consistent = verify_ovr01(risks)
    system_esc = apply_ovr06(risks)
    apply_ovr02(cnt, active_alerts)
    return {
        "critical_count":             cnt,
        "system_critical_escalation": system_esc,
        "ovr01_consistent":           consistent,
    }


# ── OVR-03: 단일 Critical → 최소 Moderate_Defensive ───────
def apply_ovr03(
    strategy: str,
    equity_ceiling: int,
    critical_count: int,
) -> tuple[str, int]:
    """전략 단계 (STEP 7 Step 2)."""
    if critical_count >= 1:
        if STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Moderate_Defensive"]:
            return "Moderate_Defensive", 50
    return strategy, equity_ceiling


# ── OVR-04: Critical>=2 + score>2.5 → Defensive ──────────
def apply_ovr04(
    strategy: str,
    equity_ceiling: int,
    critical_count: int,
    integrated_score: float,
) -> tuple[str, int]:
    """전략 단계 (STEP 7 Step 3, OVR-03 이후)."""
    if critical_count >= 2 and integrated_score > 2.5:
        if STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Defensive"]:
            return "Defensive", 30
    return strategy, equity_ceiling


# ── OVR-05: 인사이트 종결 강제 ────────────────────────────
def apply_ovr05(
    insights: list[dict[str, Any]],
    strategy: str,
    integrated_score: float,
) -> list[dict[str, Any]]:
    """인사이트 단계 (STEP 8 종료 직전).

    마지막에 strategy_recommendation 타입이 없거나 리스트가 비어있으면
    STRATEGY_INSIGHT_TEMPLATE 기반 종결 인사이트를 추가. R4 반복 억제 무시.
    """
    has_strategy_rec = any(i.get("type") == "strategy_recommendation" for i in insights)
    if not has_strategy_rec or len(insights) == 0:
        insights.append({
            "id":       "INS-STRATEGY",
            "type":     "strategy_recommendation",
            "priority": "terminal",
            "text":     STRATEGY_INSIGHT_TEMPLATE[strategy],
            "score":    integrated_score,
            "strategy": strategy,
        })
    return insights

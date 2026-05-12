"""Override 규칙 테스트 — Skills.md §13.

OVR-01 ~ OVR-06 각각의 트리거 조건 + 적용 결과 검증.
적용 순서(STEP 4/7/8) 의존성 테스트 포함.
"""

from __future__ import annotations

from layer3_risk.schema import RiskOutput, RiskDetails, grade_label
from rules.override import (
    apply_ovr02, apply_ovr03, apply_ovr04, apply_ovr05,
    apply_ovr06, apply_step4, is_ovr06_active, verify_ovr01,
)

TS = "2026-04-30"


def _make_risk(
    risk_id: str, grade: int, risk_type: str, weight: float, **flags
) -> RiskOutput:
    return RiskOutput(
        risk_id=risk_id, grade=grade, score=grade,
        triggered_conditions=[], reason="test",
        details=RiskDetails(
            risk_type=risk_type, grade_label=grade_label(grade),
            weight_default=weight, timestamp=TS,
            indicators={}, sub_grades={}, flags=flags,
            conflict_rule="none", condition_candidates=[],
        ),
    )


def _make_risks(
    market=1, volatility=1, liquidity=1, downside=1, macro=1,
    macro_flags: dict | None = None,
) -> dict:
    return {
        "market":     _make_risk("RISK-A", market,     "market",     0.30),
        "volatility": _make_risk("RISK-B", volatility, "volatility", 0.25),
        "liquidity":  _make_risk("RISK-C", liquidity,  "liquidity",  0.15),
        "downside":   _make_risk("RISK-D", downside,   "downside",   0.10),
        "macro":      _make_risk("RISK-E", macro,      "macro",      0.20,
                                 **(macro_flags or {})),
    }


# ── OVR-01 ───────────────────────────────────────────────────

def test_ovr01_시나리오_발동_macro_grade_4_일치():
    """triggered_scenario 있고 macro_grade=4 → 검증 통과."""
    risks = _make_risks(macro=4, macro_flags={"triggered_scenario": "SCN-01"})
    assert verify_ovr01(risks) is True

def test_ovr01_시나리오_발동_macro_grade_불일치():
    """triggered_scenario 있는데 macro_grade != 4 → 검증 실패."""
    risks = _make_risks(macro=3, macro_flags={"triggered_scenario": "SCN-01"})
    assert verify_ovr01(risks) is False

def test_ovr01_시나리오_없으면_통과():
    risks = _make_risks(macro=2, macro_flags={"triggered_scenario": None})
    assert verify_ovr01(risks) is True


# ── OVR-02 ───────────────────────────────────────────────────

def test_ovr02_critical_없으면_alt02_미추가():
    alerts: list[str] = []
    apply_ovr02(critical_count=0, active_alerts=alerts)
    assert "ALT-02" not in alerts

def test_ovr02_critical_1개_이상_alt02_추가():
    alerts: list[str] = []
    apply_ovr02(critical_count=1, active_alerts=alerts)
    assert "ALT-02" in alerts

def test_ovr02_중복_추가_방지():
    alerts = ["ALT-02"]
    apply_ovr02(critical_count=1, active_alerts=alerts)
    assert alerts.count("ALT-02") == 1


# ── OVR-03 ───────────────────────────────────────────────────

def test_ovr03_critical_없으면_전략_유지():
    strategy, ceiling = apply_ovr03("Aggressive", 100, critical_count=0)
    assert strategy == "Aggressive"
    assert ceiling == 100

def test_ovr03_critical_1개_최소_moderate_defensive():
    strategy, ceiling = apply_ovr03("Aggressive", 100, critical_count=1)
    assert strategy == "Moderate_Defensive"
    assert ceiling == 50

def test_ovr03_moderate_aggressive_도_상향():
    strategy, ceiling = apply_ovr03("Moderate_Aggressive", 80, critical_count=1)
    assert strategy == "Moderate_Defensive"

def test_ovr03_이미_defensive_이상이면_유지():
    strategy, ceiling = apply_ovr03("Defensive", 30, critical_count=1)
    assert strategy == "Defensive"
    assert ceiling == 30


# ── OVR-04 ───────────────────────────────────────────────────

def test_ovr04_critical_1개면_변화없음():
    strategy, ceiling = apply_ovr04(
        "Moderate_Defensive", 50, critical_count=1, integrated_score=2.6
    )
    assert strategy == "Moderate_Defensive"

def test_ovr04_critical_2개_score_2점5초과_defensive():
    strategy, ceiling = apply_ovr04(
        "Moderate_Defensive", 50, critical_count=2, integrated_score=2.6
    )
    assert strategy == "Defensive"
    assert ceiling == 30

def test_ovr04_score_정확히_2점5_미발동():
    """integrated_score > 2.5 조건 — 2.5는 포함 안됨."""
    strategy, ceiling = apply_ovr04(
        "Moderate_Defensive", 50, critical_count=2, integrated_score=2.5
    )
    assert strategy == "Moderate_Defensive"

def test_ovr04_이미_defensive_이상이면_유지():
    strategy, ceiling = apply_ovr04(
        "Defensive", 30, critical_count=2, integrated_score=2.6
    )
    assert strategy == "Defensive"


# ── OVR-05 ───────────────────────────────────────────────────

def test_ovr05_strategy_recommendation_없으면_추가():
    insights = [{"id": "INS-01", "type": "composite", "priority": "high", "text": "test"}]
    result = apply_ovr05(insights, strategy="Defensive", integrated_score=2.75)
    assert result[-1]["type"] == "strategy_recommendation"

def test_ovr05_이미_있으면_중복_미추가():
    insights = [
        {"id": "INS-03", "type": "strategy_recommendation", "priority": "medium", "text": "t"}
    ]
    result = apply_ovr05(insights, strategy="Defensive", integrated_score=2.75)
    assert sum(1 for i in result if i["type"] == "strategy_recommendation") == 1

def test_ovr05_빈_리스트에도_추가():
    result = apply_ovr05([], strategy="Aggressive", integrated_score=1.2)
    assert len(result) == 1
    assert result[0]["type"] == "strategy_recommendation"


# ── OVR-06 ───────────────────────────────────────────────────

def test_ovr06_하방_단독_critical_격상_차단():
    """하방만 Critical, 나머지 ≤3 → system_critical_escalation=False."""
    risks = _make_risks(downside=4)
    assert is_ovr06_active(risks) is True
    result = apply_step4(risks, active_alerts=[])
    assert result["system_critical_escalation"] is False

def test_ovr06_하방_외_critical_있으면_미발동():
    """하방 Critical + 시장 Critical → OVR-06 미발동 → system_critical_escalation=True."""
    risks = _make_risks(downside=4, market=4)
    assert is_ovr06_active(risks) is False
    result = apply_step4(risks, active_alerts=[])
    assert result["system_critical_escalation"] is True

def test_ovr06_발동시_triggered_conditions_표식():
    """OVR-06 발동 → downside triggered_conditions에 표식 추가."""
    risks = _make_risks(downside=4)
    apply_ovr06(risks)
    assert "ovr06_single_critical_exception" in risks["downside"].triggered_conditions


# ── STEP 4 통합 순서 검증 ────────────────────────────────────

def test_step4_반환_구조():
    """apply_step4 결과에 critical_count, system_critical_escalation, ovr01_consistent 포함."""
    risks = _make_risks()
    result = apply_step4(risks, active_alerts=[])
    assert "critical_count" in result
    assert "system_critical_escalation" in result
    assert "ovr01_consistent" in result

def test_step4_critical_count_집계():
    """Critical 2개 → critical_count=2."""
    risks = _make_risks(volatility=4, downside=4)
    result = apply_step4(risks, active_alerts=[])
    assert result["critical_count"] == 2

def test_step4_alt02_자동_추가():
    """Critical >= 1 → ALT-02 자동 추가 (OVR-02 연동)."""
    risks = _make_risks(macro=4, macro_flags={"triggered_scenario": "SCN-01"})
    alerts: list[str] = []
    apply_step4(risks, alerts)
    assert "ALT-02" in alerts

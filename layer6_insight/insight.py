"""인사이트 생성 — Skills.md §10 Layer 6.

11종 인사이트 (INS-01 ~ INS-11):
  1순위 시나리오 긴급 (INS-08~11): SCN-01~04
  2순위 복합 (INS-01, 05, 07)
  3순위 단일 / 전략권고 (INS-02, 03, 04)
  4순위 긍정 (INS-06)

규칙:
  R1 복합 조건 ≥ 2 우선 (자연스럽게 priority 순서로 보장)
  R2 수치 명시 (각 메시지 템플릿에 반영 가능)
  R3 마지막 = 전략 권고 (OVR-05로 강제)
  R4 동일 INS-ID 3일 이상 연속 금지 (consecutive_days 검사)
  R5 Critical_Alert 활성 시 critical priority 최상단 재정렬

OVR-05 적용은 rules.override.apply_ovr05 호출.
"""

from __future__ import annotations

from typing import Any

from rules.alert import has_critical_alert
from rules.override import apply_ovr05


# ── 메시지 템플릿 ──────────────────────────────────────────
INSIGHT_TEXTS: dict[str, str] = {
    "INS-01": "변동성 증가와 하락 추세가 동시에 나타나며 시장 리스크가 확대되고 있습니다.",
    "INS-02": "외국인 순매도가 지속되며 추가 하락 압력이 존재합니다.",
    "INS-03": "현재 구간에서는 방어적인 자산 배분 전략이 권장됩니다.",
    "INS-04": "거래량이 지속 감소하고 있어 시장 참여도가 약화되고 있습니다.",
    "INS-05": "금리 인상 및 환율 상승이 동시에 진행되며 거시 리스크가 극단 수준에 도달했습니다.",
    "INS-06": "전반적인 리스크 수준이 낮고 상승 추세가 유지되고 있습니다. 공격적 전략이 유효한 구간입니다.",
    "INS-07": "최대 손실 가능성이 임계 수준을 초과했습니다. 포지션 규모 축소를 권장합니다.",
    "INS-08": "환율 급등과 외국인 이탈이 동시에 감지되었습니다. 자본 유출 압력이 구조화되고 있습니다.",
    "INS-09": "금리 인상과 CPI 상승이 중첩되며 긴축 압력이 확대되고 있습니다. 성장주 비중 축소를 권장합니다.",
    "INS-10": "물가 급등·외국인 이탈·금리 인상이 동시 진행 중입니다. 전면 방어 전환이 필요합니다.",
    "INS-11": "환율 급등·금리 인상·외국인 이탈이 동시 발생했습니다. 모든 위험자산 비중 최소화를 권장합니다.",
}


def _make(ins_id: str, type_: str, priority: str) -> dict[str, Any]:
    return {
        "id":       ins_id,
        "type":     type_,
        "priority": priority,
        "text":     INSIGHT_TEXTS[ins_id],
    }


def generate(
    *,
    # Risk grades
    market_grade: int,
    volatility_grade: int,
    liquidity_grade: int,
    downside_grade: int,
    macro_grade: int,
    # Scoring + Strategy
    integrated_score: float,
    strategy: str,
    # Indicators / signals
    triggered_scenario: str | None,
    fi_streak_sell: int,
    vol_streak: int,
    var_95: float,
    ma_bullish: bool,
    # State
    consecutive_days: dict[str, int],
    active_alerts: list[str],
) -> list[dict[str, Any]]:
    """인사이트 리스트 생성. Skills.md §10 우선순위 순서.

    R4 반복 억제 → OVR-05 종결 강제 → R5 Critical 재정렬.
    """
    insights: list[dict[str, Any]] = []

    # ── 1순위: 시나리오 긴급 (PREPEND 효과 = 첫 번째에 배치) ──
    if triggered_scenario == "SCN-04":
        insights.append(_make("INS-11", "emergency", "critical"))
    elif triggered_scenario == "SCN-03":
        insights.append(_make("INS-10", "emergency", "critical"))
    elif triggered_scenario == "SCN-02":
        insights.append(_make("INS-09", "emergency", "critical"))
    elif triggered_scenario == "SCN-01":
        insights.append(_make("INS-08", "emergency", "critical"))

    # ── 2순위: 복합 조건 ─────────────────────────────────────
    if volatility_grade >= 3 and market_grade >= 3:
        insights.append(_make("INS-01", "composite", "high"))
    if downside_grade == 4 and var_95 <= -3.5:
        insights.append(_make("INS-07", "composite", "high"))
    if macro_grade == 4 and triggered_scenario is None:
        insights.append(_make("INS-05", "composite", "high"))

    # ── 3순위: 단일 + 전략권고 ───────────────────────────────
    if fi_streak_sell >= 5:
        insights.append(_make("INS-02", "single", "medium"))
    if vol_streak >= 5:
        insights.append(_make("INS-04", "single", "medium"))
    if integrated_score >= 2.5:
        insights.append(_make("INS-03", "strategy_recommendation", "medium"))

    # ── 4순위: 긍정 시장 요약 ────────────────────────────────
    if integrated_score < 1.5 and ma_bullish:
        insights.append(_make("INS-06", "positive", "low"))

    # ── R4: 동일 INS-ID 3일 이상 연속 생성 금지 ──────────────
    insights = [
        item for item in insights
        if consecutive_days.get(item["id"], 0) < 3
    ]

    # ── OVR-05: 전략 권고 종결 강제 (R3 최우선) ──────────────
    insights = apply_ovr05(insights, strategy=strategy, integrated_score=integrated_score)

    # ── R5: Critical_Alert 활성 시 critical priority 최상단 ──
    if has_critical_alert(active_alerts):
        critical_items = [i for i in insights if i["priority"] == "critical"]
        other_items    = [i for i in insights if i["priority"] != "critical"]
        insights = critical_items + other_items

    return insights

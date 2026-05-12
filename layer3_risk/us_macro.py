"""Risk-E (US) 미국 매크로 리스크 — Phase 3.

기본 가중치 20% (한국 매크로와 동일).
FRED 키 미설정 시 fed_rate·cpi·m2 입력이 None → 가능한 지표만으로 등급 산출.

3단계 직렬 (한국 Risk-E 구조 동일):
  US-E-1 수준 판정 → us_level_grade (1~3)
  US-E-2 이벤트 탐지 → us_event_grade (1~4)
  US-E-3 시나리오 → us_macro_grade (SCN-US-01: Tightening, SCN-US-02: Dollar Surge)
"""

from __future__ import annotations

from config.constants import CLAMP
from config.thresholds import (
    US_FED_RATE_DANGER, US_FED_RATE_CAUTION,
    US_FED_RATE_DELTA_HIKE, US_FED_RATE_DELTA_CUT,
    US_DXY_DANGER, US_DXY_CAUTION,
    US_DXY_WEEKLY_SPIKE, US_DXY_WEEKLY_DROP,
    CPI_YOY_CAUTION, CPI_YOY_DANGER,
    CPI_DELTA_SURGE,
    M2_CONTRACTION_DROP,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-E"
WEIGHT_DEFAULT = 0.20
CONFLICT_RULE = "US-E-3_scenario_override"
CONDITION_CANDIDATES = [
    "US_E1_danger_gte_2", "US_E1_caution_gte_1", "US_E1_all_stable",
    "EVT_US_01", "EVT_US_02", "EVT_US_03", "EVT_US_04", "EVT_US_05",
    "SCN_US_01", "SCN_US_02",
]


# ── US-E-1 수준 판정 ──────────────────────────────────────────
def _level_assessment(
    fed_rate: float | None,
    cpi_yoy: float | None,
    dxy_level: float | None,
    m2_contraction: bool,
) -> tuple[int, int, int]:
    """가용 지표 기반 수준 판정 → (level_grade, danger_count, caution_count)."""
    danger, caution = 0, 0

    if fed_rate is not None:
        if fed_rate > US_FED_RATE_DANGER:    danger  += 1
        elif fed_rate > US_FED_RATE_CAUTION: caution += 1

    if cpi_yoy is not None:
        if cpi_yoy > CPI_YOY_DANGER:    danger  += 1
        elif cpi_yoy >= CPI_YOY_CAUTION: caution += 1

    if dxy_level is not None:
        if dxy_level > US_DXY_DANGER:    danger  += 1
        elif dxy_level > US_DXY_CAUTION: caution += 1

    if m2_contraction:
        danger += 1

    if danger >= 2:    level_grade = 3
    elif caution >= 1: level_grade = 2
    else:              level_grade = 1
    return level_grade, danger, caution


# ── US-E-2 이벤트 탐지 ────────────────────────────────────────
def _event_detection(
    level_grade: int,
    fed_rate_delta: float | None,
    cpi_delta: float | None,
    dxy_weekly_change: float | None,
) -> tuple[int, dict]:
    """이벤트 평가 → (event_grade, evt_dict)."""
    evt = {
        "EVT_US_01": (fed_rate_delta is not None and fed_rate_delta >= US_FED_RATE_DELTA_HIKE),
        "EVT_US_02": (cpi_delta is not None and cpi_delta >= CPI_DELTA_SURGE),
        "EVT_US_03": (dxy_weekly_change is not None and dxy_weekly_change > US_DXY_WEEKLY_SPIKE),
        "EVT_US_04": (fed_rate_delta is not None and fed_rate_delta <= US_FED_RATE_DELTA_CUT),
        "EVT_US_05": (dxy_weekly_change is not None and dxy_weekly_change < US_DXY_WEEKLY_DROP),
    }

    up_count   = sum(evt[k] for k in ("EVT_US_01", "EVT_US_02", "EVT_US_03"))
    down_count = sum(evt[k] for k in ("EVT_US_04", "EVT_US_05"))
    net_delta  = up_count - down_count

    if up_count >= 2:
        net_delta += 1

    event_grade = int(CLAMP(level_grade + net_delta, 1, 4))
    return event_grade, evt


# ── US-E-3 시나리오 ────────────────────────────────────────────
def _scenario_check(evt: dict, event_grade: int) -> tuple[int, str | None]:
    """시나리오 발동 → (macro_grade, triggered_scenario).

    SCN-US-01: Tightening Squeeze (Fed hike + CPI surge)
    SCN-US-02: Dollar Surge (DXY 급등)
    """
    if evt["EVT_US_01"] and evt["EVT_US_02"]:
        return 4, "SCN-US-01"
    if evt["EVT_US_03"]:
        return 4, "SCN-US-02"
    return event_grade, None


def evaluate(
    *,
    fed_rate: float | None,
    fed_rate_delta: float | None,
    cpi_yoy: float | None,
    cpi_delta: float | None,
    dxy_level: float | None,
    dxy_weekly_change: float | None,
    m2_contraction: bool,
    timestamp: str,
) -> RiskOutput:
    """US 매크로 리스크 등급 산정 — US-E-1 → US-E-2 → US-E-3 직렬.

    FRED 키 미설정 시 fed_rate·cpi·m2 = None으로 호출.
    DXY(yfinance)는 항상 가용 → 최소한의 매크로 평가 유지.
    """
    level_g, danger_count, caution_count = _level_assessment(
        fed_rate, cpi_yoy, dxy_level, m2_contraction
    )
    event_g, evt = _event_detection(level_g, fed_rate_delta, cpi_delta, dxy_weekly_change)
    macro_grade, triggered_scenario = _scenario_check(evt, event_g)

    triggered: list[str] = []
    if danger_count >= 2:    triggered.append("US_E1_danger_gte_2")
    elif caution_count >= 1: triggered.append("US_E1_caution_gte_1")
    else:                    triggered.append("US_E1_all_stable")
    for code, active in evt.items():
        if active:
            triggered.append(code)
    if triggered_scenario:
        triggered.append(triggered_scenario)

    fred_available = any(v is not None for v in (fed_rate, cpi_yoy))

    return RiskOutput(
        risk_id=RISK_ID,
        grade=macro_grade,
        score=macro_grade,
        triggered_conditions=triggered,
        reason=f"us_macro grade={macro_grade} based on " + ", ".join(triggered),
        details=RiskDetails(
            risk_type="macro",
            grade_label=grade_label(macro_grade),
            weight_default=WEIGHT_DEFAULT,
            timestamp=timestamp,
            indicators={
                "fed_rate":         fed_rate,
                "cpi_yoy":          cpi_yoy,
                "dxy_level":        dxy_level,
                "dxy_weekly_change": dxy_weekly_change,
            },
            sub_grades={
                "level_grade": level_g,
                "event_grade": event_g,
            },
            flags={
                "triggered_scenario": triggered_scenario,
                "fred_available":     fred_available,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

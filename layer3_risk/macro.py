"""Risk-E 매크로 리스크 — Skills.md §7 Risk-E (3단계 직렬).

기본 가중치 20%.

3E-1 수준 판정 (Level Assessment) → level_grade ∈ {1, 2, 3}
  6개 지표 stable/caution/danger 분류, danger>=2 → 3, caution>=1 → 2, else 1.

3E-2 이벤트 탐지 (Event Detection) → event_grade ∈ {1..4}
  EVT-01~10 평가, net_delta = up - down, up>=2 → +1 가산, CLAMP(level + net, 1, 4).

3E-3 복합 시나리오 (Composite Scenario) → macro_grade
  SCN-04 → SCN-03 → SCN-02 → SCN-01 순서 검사, 시나리오 발동 시 macro_grade=4 강제.
"""

from __future__ import annotations

from config.constants import CLAMP
from config.thresholds import (
    FX_RATE_CAUTION, FX_RATE_DANGER,
    BASE_RATE_DELTA_CAUTION, BASE_RATE_DELTA_DANGER,
    RATE_SPREAD_CAUTION, RATE_SPREAD_DANGER,
    CPI_YOY_CAUTION, CPI_YOY_DANGER,
    FI_MONTHLY_CAUTION, FI_MONTHLY_DANGER,
    FX_WEEKLY_SPIKE, FX_DAILY_SPIKE, FX_WEEKLY_DROP,
    FI_STREAK_SELL_TRIGGER, FI_5D_CUM_SELL,
    FI_STREAK_BUY_TRIGGER, FI_5D_CUM_BUY,
    RATE_HIKE_DELTA, RATE_CUT_DELTA,
    CPI_DELTA_SURGE,
    EVENT_OVERLAP_TRIGGER,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-E"
WEIGHT_DEFAULT = 0.20
CONFLICT_RULE = "3E-3_scenario_override"
CONDITION_CANDIDATES = [
    "3E1_danger_count_gte_2", "3E1_caution_count_gte_1", "3E1_all_stable",
    "EVT_01", "EVT_02", "EVT_03", "EVT_04", "EVT_05", "EVT_06",
    "EVT_08", "EVT_09", "EVT_10",
    "SCN-01", "SCN-02", "SCN-03", "SCN-04",
]


# ── 3E-1 수준 판정 ────────────────────────────────────────
def _level_assessment(
    fx_rate: float,
    base_rate_delta: float,
    rate_spread_curr: float,
    cpi_yoy: float,
    fi_monthly: float,
    m2_contraction: bool,
    m2_growth_slowdown: bool,
) -> tuple[int, int, int]:
    """6개 지표 → (level_grade, danger_count, caution_count)."""
    danger = 0
    caution = 0

    if fx_rate > FX_RATE_DANGER:               danger += 1
    elif fx_rate >= FX_RATE_CAUTION:           caution += 1

    if base_rate_delta >= BASE_RATE_DELTA_DANGER:   danger += 1
    elif base_rate_delta >= BASE_RATE_DELTA_CAUTION: caution += 1

    if rate_spread_curr < RATE_SPREAD_DANGER:       danger += 1
    elif rate_spread_curr <= RATE_SPREAD_CAUTION:   caution += 1

    if cpi_yoy > CPI_YOY_DANGER:                    danger += 1
    elif cpi_yoy >= CPI_YOY_CAUTION:                caution += 1

    if fi_monthly < FI_MONTHLY_DANGER:              danger += 1
    elif fi_monthly < FI_MONTHLY_CAUTION:           caution += 1

    if m2_contraction:                              danger += 1
    elif m2_growth_slowdown:                        caution += 1

    if danger >= 2:    level_grade = 3
    elif caution >= 1: level_grade = 2
    else:              level_grade = 1
    return level_grade, danger, caution


# ── 3E-2 이벤트 탐지 ──────────────────────────────────────
def _event_detection(
    level_grade: int, *,
    fx_weekly_change: float, fx_daily_change: float,
    fi_streak_sell: int, fi_5d_cum: float,
    base_rate_delta: float, cpi_delta: float,
    rate_spread_prev: float, rate_spread_curr: float,
    m2_contraction: bool, m2_expansion: bool,
    fi_streak_buy: int,
) -> tuple[int, dict]:
    """이벤트 평가 → (event_grade, evt_dict)."""
    evt = {
        "EVT_01": (fx_weekly_change > FX_WEEKLY_SPIKE) or (fx_daily_change > FX_DAILY_SPIKE),
        "EVT_02": (fi_streak_sell >= FI_STREAK_SELL_TRIGGER) and (fi_5d_cum < FI_5D_CUM_SELL),
        "EVT_03": (base_rate_delta >= RATE_HIKE_DELTA),
        "EVT_04": (cpi_delta >= CPI_DELTA_SURGE),
        "EVT_05": (rate_spread_prev > 0) and (rate_spread_curr <= 0),
        "EVT_06": bool(m2_contraction),
        "EVT_07": (fx_weekly_change < FX_WEEKLY_DROP),  # 탐지만, 등급 영향 없음
        "EVT_08": (fi_streak_buy >= FI_STREAK_BUY_TRIGGER) and (fi_5d_cum > FI_5D_CUM_BUY),
        "EVT_09": (base_rate_delta <= RATE_CUT_DELTA),
        "EVT_10": bool(m2_expansion),
    }

    up_count = sum(evt[k] for k in ("EVT_01", "EVT_02", "EVT_03", "EVT_04", "EVT_05", "EVT_06"))
    down_count = sum(evt[k] for k in ("EVT_08", "EVT_09", "EVT_10"))
    net_delta = up_count - down_count

    if up_count >= EVENT_OVERLAP_TRIGGER:   # 중첩 상향 +1
        net_delta += 1

    event_grade = int(CLAMP(level_grade + net_delta, 1, 4))
    return event_grade, evt


# ── 3E-3 복합 시나리오 ────────────────────────────────────
def _scenario_check(evt: dict, event_grade: int) -> tuple[int, str | None, bool]:
    """시나리오 평가 → (macro_grade, triggered_scenario, scn04_flag).

    검사 순서: SCN-04 → SCN-03 → SCN-02 → SCN-01 (강도 높은 것부터).
    """
    if evt["EVT_01"] and evt["EVT_03"] and evt["EVT_02"]:
        return 4, "SCN-04", True
    if evt["EVT_04"] and evt["EVT_02"] and evt["EVT_03"]:
        return 4, "SCN-03", False
    if evt["EVT_03"] and evt["EVT_04"]:
        return 4, "SCN-02", False
    if evt["EVT_01"] and evt["EVT_02"]:
        return 4, "SCN-01", False
    return event_grade, None, False


def evaluate(
    *,
    # 3E-1 inputs
    fx_rate: float,
    base_rate_delta: float,
    rate_spread_curr: float,
    cpi_yoy: float,
    fi_monthly: float,
    m2_growth_curr: float,
    m2_contraction: bool,
    m2_growth_slowdown: bool,
    # 3E-2 추가 inputs
    fx_daily_change: float,
    fx_weekly_change: float,
    fi_streak_sell: int,
    fi_streak_buy: int,
    fi_5d_cum: float,
    cpi_delta: float,
    rate_spread_prev: float,
    m2_expansion: bool,
    timestamp: str,
) -> RiskOutput:
    """Risk-E 등급 산정 — 3E-1 → 3E-2 → 3E-3 직렬."""
    # 3E-1
    level_g, danger_count, caution_count = _level_assessment(
        fx_rate, base_rate_delta, rate_spread_curr, cpi_yoy, fi_monthly,
        m2_contraction, m2_growth_slowdown,
    )

    # 3E-2
    event_g, evt = _event_detection(
        level_g,
        fx_weekly_change=fx_weekly_change, fx_daily_change=fx_daily_change,
        fi_streak_sell=fi_streak_sell, fi_5d_cum=fi_5d_cum,
        base_rate_delta=base_rate_delta, cpi_delta=cpi_delta,
        rate_spread_prev=rate_spread_prev, rate_spread_curr=rate_spread_curr,
        m2_contraction=m2_contraction, m2_expansion=m2_expansion,
        fi_streak_buy=fi_streak_buy,
    )

    # 3E-3
    macro_grade, triggered_scenario, scn04_flag = _scenario_check(evt, event_g)

    # ── triggered_conditions ─────────────────────────────
    triggered: list[str] = []
    if danger_count >= 2:    triggered.append("3E1_danger_count_gte_2")
    elif caution_count >= 1: triggered.append("3E1_caution_count_gte_1")
    else:                    triggered.append("3E1_all_stable")

    for code in ("EVT_01", "EVT_02", "EVT_03", "EVT_04", "EVT_05", "EVT_06",
                 "EVT_08", "EVT_09", "EVT_10"):
        if evt[code]:
            triggered.append(code)

    if triggered_scenario:
        triggered.append(triggered_scenario)

    # 활성 이벤트 목록 (Skills.md flags 출력용)
    active_up = [c for c in ("EVT-01", "EVT-02", "EVT-03", "EVT-04", "EVT-05", "EVT-06")
                 if evt[c.replace("-", "_")]]
    active_down = [c for c in ("EVT-08", "EVT-09", "EVT-10")
                   if evt[c.replace("-", "_")]]

    return RiskOutput(
        risk_id=RISK_ID,
        grade=macro_grade,
        score=macro_grade,
        triggered_conditions=triggered,
        reason=f"macro_risk grade={macro_grade} based on " + ", ".join(triggered),
        details=RiskDetails(
            risk_type="macro",
            grade_label=grade_label(macro_grade),
            weight_default=WEIGHT_DEFAULT,
            timestamp=timestamp,
            indicators={
                "fx_rate":          fx_rate,
                "base_rate_delta":  base_rate_delta,
                "rate_spread_curr": rate_spread_curr,
                "cpi_yoy":          cpi_yoy,
                "fi_monthly":       fi_monthly,
                "m2_growth_curr":   m2_growth_curr,
            },
            sub_grades={
                "level_grade": level_g,
                "event_grade": event_g,
            },
            flags={
                "triggered_scenario": triggered_scenario,
                "scn04_flag":         scn04_flag,
                "active_up_events":   active_up,
                "active_down_events": active_down,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

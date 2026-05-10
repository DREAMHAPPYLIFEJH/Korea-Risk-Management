"""Alert Rules — Skills.md §14 (ALT-01 ~ ALT-12).

알림 평가 STEP 9. 등급 변화와 독립적으로 작동하는 조기 경고 신호.

Watch(1): ALT-03 변동성 급등 / ALT-04 거래량 급감
Warning(2): ALT-01 점수 급등 / ALT-02 단일 Critical(OVR-02) / ALT-05 외국인 집중 매도 /
           ALT-06 이격도 임계 / ALT-08 매크로 이벤트 중첩
Critical_Alert(3): ALT-07 MDD 임계 / ALT-09~12 시나리오 발동
"""

from __future__ import annotations

from typing import Any

from config.constants import ALERT_LEVEL
from config.thresholds import (
    ALT_SCORE_DELTA, ALT_HV_SPIKE_RATIO,
    ALT_VOL_RATIO, ALT_VOL_DAYS,
    DISP_MA20_HIGH, DISP_MA60_ALERT,
    ALT_MDD_60,
    EVENT_OVERLAP_TRIGGER,
    FI_STREAK_SELL_TRIGGER, FI_5D_CUM_SELL,
)
from layer1_data.state import roll_vol_ratio_window


# ALT-ID → 등급 (Watch=1, Warning=2, Critical_Alert=3)
ALERT_LEVELS: dict[str, int] = {
    "ALT-01": ALERT_LEVEL["Warning"],
    "ALT-02": ALERT_LEVEL["Warning"],
    "ALT-03": ALERT_LEVEL["Watch"],
    "ALT-04": ALERT_LEVEL["Watch"],
    "ALT-05": ALERT_LEVEL["Warning"],
    "ALT-06": ALERT_LEVEL["Warning"],
    "ALT-07": ALERT_LEVEL["Critical_Alert"],
    "ALT-08": ALERT_LEVEL["Warning"],
    "ALT-09": ALERT_LEVEL["Critical_Alert"],
    "ALT-10": ALERT_LEVEL["Critical_Alert"],
    "ALT-11": ALERT_LEVEL["Critical_Alert"],
    "ALT-12": ALERT_LEVEL["Critical_Alert"],
}


def evaluate(
    *,
    state: dict[str, Any],          # STATE (vol_ratio_3d 갱신됨)
    integrated_score: float,
    critical_count: int,
    hv20: float,
    vol_ratio: float,
    fi_streak_sell: int,
    fi_5d_cum: float,
    disp_ma20: float,
    disp_ma60: float,
    up_count: int,
    mdd_60: float,
    triggered_scenario: str | None,
) -> list[str]:
    """알림 평가 (STEP 9). 발동된 ALT-ID 리스트 반환.

    내부에서 STATE.vol_ratio_3d 롤링 갱신 (ALT-04 평가).
    ALT-02는 OVR-02 단계에서 이미 추가될 수 있음 — 중복 방지.
    """
    alerts: list[str] = []

    # ── Watch ─────────────────────────────────────────────
    # ALT-03: 변동성 급등
    hv20_5d_ago = state.get("hv20_5d_ago")
    if hv20_5d_ago is not None and hv20 > hv20_5d_ago * ALT_HV_SPIKE_RATIO:
        alerts.append("ALT-03")

    # ALT-04: 거래량 급감 (vol_ratio_3d 모두 ≤ 0.6, 3일 연속)
    roll_vol_ratio_window(state, vol_ratio)
    vol_window = state["vol_ratio_3d"]
    if (len(vol_window) == ALT_VOL_DAYS
            and all(v <= ALT_VOL_RATIO for v in vol_window)):
        alerts.append("ALT-04")

    # ── Warning ───────────────────────────────────────────
    # ALT-01: 통합 점수 급등
    prev_score = state.get("prev_integrated_score")
    if prev_score is not None and integrated_score - prev_score >= ALT_SCORE_DELTA:
        alerts.append("ALT-01")

    # ALT-02: 단일 Critical (OVR-02 중복 방지)
    if critical_count >= 1 and "ALT-02" not in alerts:
        alerts.append("ALT-02")

    # ALT-05: 외국인 집중 순매도
    if fi_streak_sell >= FI_STREAK_SELL_TRIGGER and fi_5d_cum <= FI_5D_CUM_SELL:
        alerts.append("ALT-05")

    # ALT-06: 이격도 임계 이탈
    if disp_ma20 <= DISP_MA20_HIGH or disp_ma60 <= DISP_MA60_ALERT:
        alerts.append("ALT-06")

    # ALT-08: 매크로 이벤트 중첩
    if up_count >= EVENT_OVERLAP_TRIGGER:
        alerts.append("ALT-08")

    # ── Critical_Alert ────────────────────────────────────
    # ALT-07: MDD 임계 도달 (mdd_60은 % 단위, 음수)
    if mdd_60 <= ALT_MDD_60:
        alerts.append("ALT-07")

    # ALT-09 ~ ALT-12: 시나리오 발동
    scn_to_alert = {
        "SCN-01": "ALT-09",
        "SCN-02": "ALT-10",
        "SCN-03": "ALT-11",
        "SCN-04": "ALT-12",
    }
    if triggered_scenario in scn_to_alert:
        alerts.append(scn_to_alert[triggered_scenario])

    return alerts


def alert_level(alert_id: str) -> int:
    """ALT-ID → 등급(1/2/3)."""
    return ALERT_LEVELS[alert_id]


def has_critical_alert(alerts: list[str]) -> bool:
    """Critical_Alert(3) 등급 포함 여부 — Layer 6 R5 재정렬에 사용."""
    return any(ALERT_LEVELS.get(a) == ALERT_LEVEL["Critical_Alert"] for a in alerts)

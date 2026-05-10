"""알림 배너 — Skills.md §11 Layer 7 + §14 알림 전달.

Streamlit native components 사용 (st.error / st.warning / st.info).
"""

from __future__ import annotations

import streamlit as st

from rules.alert import alert_level


# ALT-ID → 한글 설명
ALERT_LABELS: dict[str, str] = {
    "ALT-01": "통합 점수 급등",
    "ALT-02": "단일 Critical 등급 발생",
    "ALT-03": "변동성 급등 (5일 전 대비 30%↑)",
    "ALT-04": "거래량 급감 3일 연속",
    "ALT-05": "외국인 집중 순매도",
    "ALT-06": "이격도 임계 이탈",
    "ALT-07": "MDD 임계 도달 (-15%)",
    "ALT-08": "매크로 이벤트 중첩 (2개 이상)",
    "ALT-09": "자본유출 경고 (SCN-01)",
    "ALT-10": "긴축 압력 경고 (SCN-02)",
    "ALT-11": "스태그플레이션 경고 (SCN-03)",
    "ALT-12": "유동성 위기 경고 (SCN-04)",
}


def render_alerts(alerts: list[str]) -> None:
    """등급별 색상 배너 렌더링."""
    if not alerts:
        return

    grouped: dict[int, list[str]] = {1: [], 2: [], 3: []}
    for a in alerts:
        try:
            grouped[alert_level(a)].append(a)
        except KeyError:
            pass

    def fmt(ids: list[str]) -> str:
        return " · ".join(f"**{i}** {ALERT_LABELS.get(i, '')}" for i in ids)

    if grouped[3]:
        st.error(f"🚨 위험 (Critical Alert) — {fmt(grouped[3])}")
    if grouped[2]:
        st.warning(f"⚠️ 경고 (Warning) — {fmt(grouped[2])}")
    if grouped[1]:
        st.info(f"👁 주의 (Watch) — {fmt(grouped[1])}")

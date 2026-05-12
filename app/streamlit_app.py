"""KOSPI Risk Intelligence Dashboard — Streamlit 진입점.

레이아웃 (기획서 §9.1):
  ┌─ [1] 통합 리스크 게이지   [2] 리스크 유형별 레이더 ─┐
  ├─ [3] 리스크 추이 시계열 ─────────────────────────┤
  └─ [4] 전략·자산 배분      [5] 인사이트 영역 ──────┘

실행:
  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (streamlit run 시 import 안정화)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from pipeline.orchestrator import run_snapshot
from layer7_visualization.gauge import make_gauge
from layer7_visualization.radar import make_radar
from layer7_visualization.trend import make_trend
from layer7_visualization.allocation import make_allocation
from layer7_visualization.alert_banner import render_alerts


st.set_page_config(
    page_title="KOSPI Risk Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_snapshot(end_date_iso: str, lookback_days: int = 400) -> dict:
    return run_snapshot(end_date=date.fromisoformat(end_date_iso), lookback_days=lookback_days)


# ── 헤더 ──────────────────────────────────────────────────
st.title("KOSPI Risk Intelligence Dashboard")
col_header_l, col_header_r = st.columns([3, 1])
with col_header_l:
    selected_date = st.date_input("분석 기준일", value=date(2026, 4, 30))
with col_header_r:
    st.write("")  # spacing
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── 데이터 로드 ────────────────────────────────────────────
try:
    with st.spinner("분석 중... (키움 API 일별 외국인 데이터 수집 약 30~60초)"):
        result = load_snapshot(selected_date.isoformat())
except Exception as e:
    st.error(f"파이프라인 오류: {type(e).__name__}: {e}")
    st.stop()

# 알림 배너
render_alerts(result["alerts"])

st.divider()

# ── [1] [2] 행 — 게이지 + 레이더 ──────────────────────────
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader("통합 리스크 점수")
    st.plotly_chart(make_gauge(result["score"], result["score_band"]),
                    use_container_width=True)
    st.markdown(
        f"**Phase**: `{result['phase']}` · "
        f"**Critical**: `{result['critical_count']}` · "
        f"**System Esc**: `{result['system_critical_escalation']}`"
    )

with c2:
    st.subheader("리스크 유형별")
    grades = {k: result["risks"][k]["grade"]
              for k in ("market", "volatility", "liquidity", "downside", "macro")}
    st.plotly_chart(make_radar(grades), use_container_width=True)

# ── [3] 시계열 추이 ──────────────────────────────────────
st.subheader("리스크 추이")
series = result["series"]
st.plotly_chart(
    make_trend(series["close"], series["hv20"], series["mdd60"],
               ma20=series["ma20"], ma60=series["ma60"]),
    use_container_width=True,
)

# ── [4] [5] 행 — 전략 + 인사이트 ──────────────────────────
c3, c4 = st.columns([1, 2])
with c3:
    st.subheader("전략 / 자산 배분")
    a = result["strategy"]["allocation"]
    st.plotly_chart(
        make_allocation(a["equity"], a["bond"], a["cash"],
                        result["strategy"]["strategy"]),
        use_container_width=True,
    )

with c4:
    st.subheader("인사이트")
    EMOJI = {"critical": "🚨", "high": "⚠️", "medium": "📊",
             "low": "ℹ️", "terminal": "🎯"}
    for ins in result["insights"]:
        emoji = EMOJI.get(ins["priority"], "•")
        st.markdown(f"{emoji} **[{ins['id']}]** {ins['text']}")

# ── 세부 정보 (Expanders) ─────────────────────────────────
st.divider()

with st.expander("📊 리스크 기여도"):
    st.bar_chart(result["contributions"])

with st.expander("🔍 5 리스크 세부 (JSON)"):
    for k, r in result["risks"].items():
        st.markdown(
            f"### {r['risk_id']} {k.upper()} — "
            f"**{r['details']['grade_label']}** (grade {r['grade']})"
        )
        st.caption(f"Reason: {r['reason']}")
        if r["triggered_conditions"]:
            st.caption("Triggered: " + " · ".join(f"`{t}`" for t in r["triggered_conditions"]))
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Indicators**")
            st.json(r["details"]["indicators"])
        with cols[1]:
            st.markdown("**Flags / Sub-grades**")
            st.json({
                "sub_grades": r["details"]["sub_grades"],
                "flags": r["details"]["flags"],
            })

with st.expander("⚙️ 동적 가중치"):
    st.json(result["weights"])

# ── Phase 2: 섹터 리스크 분석 ──────────────────────────────
st.divider()
st.subheader("섹터 리스크 분석 (Phase 2)")

try:
    from pipeline.sector_pipeline import run_sector_analysis
    from layer7_visualization.sector_chart import make_sector_table

    sector_results = run_sector_analysis(result)
    st.plotly_chart(make_sector_table(sector_results), use_container_width=True)

    pending = [r.sector for r in sector_results if not r.data_available]
    if pending:
        st.caption(
            f"⚠️ 업종 코드 미확보 섹터: {', '.join(pending)} — "
            "config/constants.py의 SECTOR_CODES에 키움 inds_cd 입력 후 활성화"
        )
except Exception as e:
    st.warning(f"섹터 분석 오류: {type(e).__name__}: {e}")

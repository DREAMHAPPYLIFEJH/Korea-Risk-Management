"""KOSPI Risk Intelligence Dashboard — Streamlit 진입점.

레이아웃 (기획서 §9.1 / UI 가이드 적용):
  ┌─ 헤더 (기준일 + 새로고침) ────────────────────────────┐
  ├─ 시장 선택 라디오 (KOSPI / S&P 500) ────────────────┤
  ├─ Alert 영역 (등급별 색상 border-left) ───────────────┤
  ├─ 메트릭 카드 4개 (점수 / Phase / Critical / Esc) ────┤
  ├─ 리스크 유형별 수평 바 차트 ─────────────────────────┤
  ├─ 리스크 추이 (Price / HV20 / MDD) ─────────────────┤
  ├─ 전략·자산 배분 / 인사이트 ──────────────────────────┤
  ├─ 세부 정보 (Expanders) ────────────────────────────┤
  ├─ Phase 2 섹터 분석 (KOSPI 한정) ───────────────────┤
  └─ Phase 3 시장 비교 (KOSPI vs S&P 500) ───────────┘

실행:
  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (streamlit run 시 import 안정화)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.orchestrator import run_snapshot
from layer7_visualization.trend import make_trend
from layer7_visualization.allocation import make_allocation
from rules.alert import alert_level


st.set_page_config(
    page_title="KOSPI Risk Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── 커스텀 CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #fafafa; }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    /* 메트릭 카드 */
    .metric-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px 24px;
        border: 1px solid #e8e8e8;
        height: 110px;
    }
    .metric-card .label {
        font-size: 13px;
        color: #888;
        margin-bottom: 4px;
        font-weight: 400;
    }
    .metric-card .value {
        font-size: 28px;
        font-weight: 600;
        margin: 0;
        line-height: 1.2;
    }
    .metric-card .sub {
        font-size: 12px;
        color: #999;
        margin-top: 6px;
    }

    /* Alert */
    .alert-critical {
        background: #FEF2F2;
        border-left: 4px solid #EF4444;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 14px;
        color: #7F1D1D;
    }
    .alert-warning {
        background: #FFFBEB;
        border-left: 4px solid #F59E0B;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 14px;
        color: #78350F;
    }
    .alert-info {
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 14px;
        color: #1E3A5F;
    }

    /* 인사이트 카드 */
    .insight-card {
        background: #ffffff;
        border-left: 3px solid #cbd5e1;
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin-bottom: 6px;
        font-size: 14px;
        color: #333;
    }
    .insight-card.p-critical { border-left-color: #EF4444; }
    .insight-card.p-high     { border-left-color: #F59E0B; }
    .insight-card.p-medium   { border-left-color: #3B82F6; }
    .insight-card.p-low      { border-left-color: #94A3B8; }
    .insight-card.p-terminal { border-left-color: #10B981; }
    .insight-card .id {
        font-size: 11px;
        color: #888;
        margin-right: 6px;
        font-family: ui-monospace, monospace;
    }

    /* 섹션 타이틀 */
    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin-bottom: 12px;
        margin-top: 24px;
    }

    /* 페이지 헤더 */
    .page-title {
        font-size: 24px;
        font-weight: 700;
        color: #111;
        margin: 0;
    }
    .page-sub {
        font-size: 13px;
        color: #888;
        margin-top: 2px;
    }

    /* Streamlit 기본 요소 정리 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { display: none; }
    div[data-testid="stToolbar"] { display: none; }

    /* 다크모드 대비 — Expander 라이트 톤 강제 */
    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stExpander"] [data-testid="stCaptionContainer"] {
        color: #222 !important;
    }
    [data-testid="stExpander"] [data-testid="stJson"] {
        background: #f8f9fa;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_snapshot(end_date_iso: str, lookback_days: int = 400) -> dict:
    return run_snapshot(end_date=date.fromisoformat(end_date_iso), lookback_days=lookback_days)


@st.cache_data(ttl=3600, show_spinner=False)
def load_us_snapshot(end_date_iso: str) -> dict:
    from pipeline.us_pipeline import run_us_snapshot
    return run_us_snapshot(end_date=date.fromisoformat(end_date_iso))


@st.cache_data(ttl=3600, show_spinner=False)
def load_kospi_fundamental(end_date_iso: str, lookback_days: int = 365):
    """KOSPI PER/PBR (Phase 4). 자격증명 없으면 None."""
    from layer1_data.krx_fetcher import get_kospi_fundamental
    end = date.fromisoformat(end_date_iso)
    start = end - timedelta(days=lookback_days)
    return get_kospi_fundamental(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))


@st.cache_data(ttl=3600, show_spinner=False)
def load_sp500_fundamental():
    """S&P 500 PER/PBR 현재값 (Phase 4, SPY ETF 근사). 실패 시 None."""
    from layer1_data.us_fetcher import get_sp500_fundamental
    return get_sp500_fundamental()


# ── Alert 라벨 ────────────────────────────────────────────
ALERT_LABELS: dict[str, str] = {
    "ALT-01": "통합 점수 급등",
    "ALT-02": "단일 Critical 등급 발생",
    "ALT-03": "변동성 급등 (5일 전 대비 30%↑)",
    "ALT-04": "거래량 급감 3일 연속",
    "ALT-05": "외국인 집중 순매도",
    "ALT-06": "이격도 임계 이탈",
    "ALT-07": "MDD 임계 도달 (-15%)",
    "ALT-08": "매크로 이벤트 중첩",
    "ALT-09": "자본유출 경고 (SCN-01)",
    "ALT-10": "긴축 압력 경고 (SCN-02)",
    "ALT-11": "스태그플레이션 경고 (SCN-03)",
    "ALT-12": "유동성 위기 경고 (SCN-04)",
}
_ALERT_STYLE = {
    3: ("alert-critical", "🔴", "Critical"),
    2: ("alert-warning",  "🟡", "Warning"),
    1: ("alert-info",     "🔵", "Watch"),
}

_RISK_LABEL = {
    "market":     "시장",
    "volatility": "변동성",
    "liquidity":  "유동성",
    "downside":   "하방",
    "macro":      "매크로",
}


def _bar_color(v: int) -> str:
    if v >= 4: return "#EF4444"
    if v >= 3: return "#F59E0B"
    if v >= 2: return "#FBBF24"
    return "#10B981"


def render_market_dashboard(result: dict, *, price_label: str = "KOSPI 종가",
                            fundamental=None) -> None:
    """선택된 시장(KOSPI 또는 S&P 500) 대시보드 본체 렌더링.

    fundamental: KOSPI PER/PBR DataFrame (KOSPI 한정, 리스크 추이 아래 표시). None이면 생략.
    """
    # ── Alert 영역 ─────────────────────────────────────────
    if result["alerts"]:
        for aid in result["alerts"]:
            try:
                lvl = alert_level(aid)
            except KeyError:
                continue
            css, icon, label = _ALERT_STYLE[lvl]
            desc = ALERT_LABELS.get(aid, "")
            st.markdown(
                f'<div class="{css}">{icon} <strong>{label}</strong> — '
                f'<code>{aid}</code> {desc}</div>',
                unsafe_allow_html=True,
            )

    # ── 메트릭 카드 4개 ────────────────────────────────────
    score      = result["score"]
    score_band = result["score_band"]
    phase      = result["phase"]
    crit_cnt   = result["critical_count"]
    sys_esc    = result["system_critical_escalation"]

    score_color = "#EF4444" if score >= 3.0 else "#F59E0B" if score >= 2.0 else "#10B981"
    phase_color = {"bullish": "#10B981", "bearish": "#EF4444", "sideways": "#F59E0B"}.get(phase, "#666")
    crit_color  = "#EF4444" if crit_cnt > 0 else "#10B981"
    esc_color   = "#EF4444" if sys_esc else "#10B981"
    esc_label   = "활성" if sys_esc else "비활성"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <p class="label">통합 리스크 점수</p>
            <p class="value" style="color: {score_color};">{score:.2f}</p>
            <p class="sub">{score_band} · 4.0 만점</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <p class="label">시장 국면 (Phase)</p>
            <p class="value" style="color: {phase_color};">{phase}</p>
            <p class="sub">동적 가중치 적용 중</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <p class="label">Critical 등급 리스크</p>
            <p class="value" style="color: {crit_color};">{crit_cnt} <span style="font-size:14px;color:#999;">/ 5</span></p>
            <p class="sub">5개 리스크 중</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <p class="label">긴급 탈출 (System Esc)</p>
            <p class="value" style="color: {esc_color};">{esc_label}</p>
            <p class="sub">{"즉시 대응 필요" if sys_esc else "정상 상태"}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── 리스크 유형별 수평 바 차트 ────────────────────────
    st.markdown('<p class="section-title">리스크 유형별 분석</p>', unsafe_allow_html=True)

    risk_items = [(_RISK_LABEL[k], result["risks"][k]["grade"])
                  for k in ("volatility", "downside", "macro", "market", "liquidity")]
    risk_items.sort(key=lambda x: x[1], reverse=True)
    bar_labels = [r[0] for r in risk_items]
    bar_values = [r[1] for r in risk_items]
    bar_colors = [_bar_color(v) for v in bar_values]

    fig_bar = go.Figure(go.Bar(
        x=bar_values,
        y=bar_labels,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v}" for v in bar_values],
        textposition="outside",
        textfont=dict(size=13, color="#333"),
        hovertemplate="%{y}: grade %{x}<extra></extra>",
    ))
    fig_bar.add_vline(x=3, line_dash="dash", line_color="#EF4444", line_width=1,
                      annotation_text="Critical", annotation_position="top",
                      annotation_font_size=11, annotation_font_color="#EF4444")
    fig_bar.add_vline(x=2, line_dash="dash", line_color="#F59E0B", line_width=1,
                      annotation_text="Warning", annotation_position="top",
                      annotation_font_size=11, annotation_font_color="#F59E0B")
    fig_bar.update_layout(
        height=260,
        margin=dict(l=0, r=60, t=20, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 4.6], showgrid=True, gridcolor="#f0f0f0",
                   zeroline=False, tickfont=dict(size=12, color="#999"),
                   dtick=1),
        yaxis=dict(tickfont=dict(size=13, color="#555"), autorange="reversed"),
        font=dict(family="sans-serif"),
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ── 리스크 추이 (Price / HV20 / MDD) ──────────────────
    st.markdown('<p class="section-title">리스크 추이</p>', unsafe_allow_html=True)
    series = result["series"]
    st.plotly_chart(
        make_trend(series["close"], series["hv20"], series["mdd60_mc_p50"],
                   ma20=series["ma20"], ma60=series["ma60"],
                   price_label=price_label),
        use_container_width=True,
    )

    # ── 밸류에이션 (PER/PBR) — 리스크 추이(MDD) 아래 (Phase 4) ──
    is_kospi = result.get("market") != "us"
    label = "KOSPI" if is_kospi else "S&P 500"
    st.markdown(f'<p class="section-title">{label} 밸류에이션 (PER/PBR)</p>',
                unsafe_allow_html=True)
    if is_kospi:
        # KOSPI: KRX 일별 시계열 → 메트릭 + 추이 차트
        if fundamental is not None and not getattr(fundamental, "empty", True):
            from layer7_visualization.fundamental_chart import make_fundamental_trend
            latest = fundamental.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("PER", f"{latest['per']:.2f}")
            c2.metric("PBR", f"{latest['pbr']:.2f}")
            if "div_yield" in fundamental.columns:
                c3.metric("배당수익률", f"{latest['div_yield']:.2f}%")
            st.plotly_chart(make_fundamental_trend(fundamental), use_container_width=True)
        else:
            st.caption("⚠️ KOSPI PER/PBR 미수집 — KRX_ID/KRX_PW 미설정 또는 조회 실패")
    else:
        # S&P 500: SPY ETF 현재값 근사 (yfinance .info — 시계열 미제공)
        if fundamental:
            c1, c2 = st.columns(2)
            c1.metric("PER", f"{fundamental['per']:.2f}" if fundamental.get("per") else "-")
            c2.metric("PBR", f"{fundamental['pbr']:.2f}" if fundamental.get("pbr") else "-")
            st.caption("ℹ️ SPY ETF 기준 현재값 (S&P 500 지수 PER/PBR 근사) — 시계열 미제공")
        else:
            st.caption("⚠️ S&P 500 PER/PBR 미수집")

    # ── 전략·자산 배분 / 인사이트 ──────────────────────────
    col_strat, col_ins = st.columns([1, 2])

    with col_strat:
        st.markdown('<p class="section-title">전략 / 자산 배분</p>', unsafe_allow_html=True)
        a = result["strategy"]["allocation"]
        st.plotly_chart(
            make_allocation(a["equity"], a["bond"], a["cash"],
                            result["strategy"]["strategy"]),
            use_container_width=True,
        )

    with col_ins:
        st.markdown('<p class="section-title">인사이트</p>', unsafe_allow_html=True)
        for ins in result["insights"]:
            priority = ins.get("priority", "low")
            st.markdown(
                f'<div class="insight-card p-{priority}">'
                f'<span class="id">[{ins["id"]}]</span>{ins["text"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 세부 정보 (Expanders) ──────────────────────────────
    st.markdown('<p class="section-title">세부 정보</p>', unsafe_allow_html=True)

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

            # Risk-D 전용: Legacy vs MC 비교 패널
            if k == "downside":
                ind = r["details"]["indicators"]
                sg  = r["details"]["sub_grades"]
                mc60  = ind.get("mdd_60_mc") or {}
                mc252 = ind.get("mdd_252_mc") or {}

                st.markdown("**Legacy(historical) vs MC(forward-looking) 비교**")

                comp = pd.DataFrame({
                    "Metric":  ["MDD_60 (%)", "MDD_252 (%)", "VaR_95 (%)", "CVaR (%)"],
                    "Legacy":  [
                        f'{ind["mdd_60"]:.2f}',
                        f'{ind["mdd_252"]:.2f}',
                        f'{ind["var_95"]:.2f}',
                        f'{ind["cvar"]:.2f}',
                    ],
                    "MC p5":   [
                        f'{mc60.get("p5", float("nan")):.2f}'  if mc60  else "—",
                        f'{mc252.get("p5", float("nan")):.2f}' if mc252 else "—",
                        f'{ind.get("var_95_mc", float("nan")):.2f}' if ind.get("var_95_mc") is not None else "—",
                        f'{ind.get("cvar_mc", float("nan")):.2f}'   if ind.get("cvar_mc")   is not None else "—",
                    ],
                    "MC p50":  [
                        f'{mc60.get("p50", float("nan")):.2f}'  if mc60  else "—",
                        f'{mc252.get("p50", float("nan")):.2f}' if mc252 else "—",
                        "—", "—",
                    ],
                    "MC p95":  [
                        f'{mc60.get("p95", float("nan")):.2f}'  if mc60  else "—",
                        f'{mc252.get("p95", float("nan")):.2f}' if mc252 else "—",
                        "—", "—",
                    ],
                })
                st.dataframe(comp, hide_index=True, use_container_width=True)

                grade_tbl = pd.DataFrame({
                    "Source":           ["Legacy MDD", "Legacy VaR", "MC p50", "MC p5", "MC VaR"],
                    "Sub-grade (1~4)":  [
                        sg.get("mdd_grade_legacy"),
                        sg.get("var_grade_legacy"),
                        sg.get("mc_p50_grade"),
                        sg.get("mc_p5_grade"),
                        sg.get("var_mc_grade"),
                    ],
                    "→ 최종 grade 기여": [
                        "참고용 (등급 미반영)",
                        "참고용 (등급 미반영)",
                        "MAX 후보",
                        "MAX 후보",
                        "MAX 후보",
                    ],
                })
                st.dataframe(grade_tbl, hide_index=True, use_container_width=True)
                st.caption(
                    f"최종 grade = MAX(mc_p50, mc_p5, var_mc) = "
                    f"**{r['grade']}** ({r['details']['grade_label']})"
                )

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


# ── 헤더 ──────────────────────────────────────────────────
col_title, col_date, col_btn = st.columns([5, 2, 1])
with col_title:
    st.markdown('<p class="page-title">KOSPI Risk Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">통합 리스크 모니터링 대시보드</p>', unsafe_allow_html=True)
with col_date:
    selected_date = st.date_input("분석 기준일", value=date.today(), label_visibility="collapsed")
with col_btn:
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── 시장 선택 라디오 ──────────────────────────────────────
market = st.radio(
    "분석 시장",
    options=["KOSPI", "S&P 500"],
    horizontal=True,
    label_visibility="collapsed",
)


# ── 선택된 시장 데이터 로드 + 본체 렌더링 ─────────────────
try:
    if market == "KOSPI":
        with st.spinner("KOSPI 분석 중... (키움 API 일별 외국인 데이터 수집 약 30~60초)"):
            current = load_snapshot(selected_date.isoformat())
    else:
        with st.spinner("S&P 500 분석 중..."):
            current = load_us_snapshot(selected_date.isoformat())
        if not current.get("fred_available", False):
            st.caption("⚠️ FRED API 키 미설정 — 연준금리·CPI·M2 제외, DXY 단독 매크로 평가")
except Exception as e:
    st.error(f"파이프라인 오류: {type(e).__name__}: {e}")
    st.stop()

fundamental = (load_kospi_fundamental(selected_date.isoformat())
               if market == "KOSPI" else load_sp500_fundamental())
render_market_dashboard(
    current,
    price_label="KOSPI 종가" if market == "KOSPI" else "S&P 500 종가",
    fundamental=fundamental,
)


# ── Phase 2: 섹터 리스크 분석 (KOSPI 한정) ────────────────
if market == "KOSPI":
    st.markdown('<p class="section-title">섹터 리스크 분석 (Phase 2)</p>', unsafe_allow_html=True)
    try:
        from pipeline.sector_pipeline import run_sector_analysis
        from layer7_visualization.sector_chart import make_sector_table

        sector_results = run_sector_analysis(current)
        st.plotly_chart(make_sector_table(sector_results), use_container_width=True)

        pending = [r.sector for r in sector_results if not r.data_available]
        if pending:
            st.caption(
                f"⚠️ 업종 코드 미확보 섹터: {', '.join(pending)} — "
                "config/constants.py의 SECTOR_CODES에 키움 inds_cd 입력 후 활성화"
            )
    except Exception as e:
        st.warning(f"섹터 분석 오류: {type(e).__name__}: {e}")


# ── Phase 3+5: KOSPI vs S&P 500 비교 + 변동성 관계 (양쪽 로드) ──
st.markdown('<p class="section-title">KOSPI vs S&P 500 비교</p>', unsafe_allow_html=True)

with st.expander("📊 시장 비교 + 변동성 관계 열기 (양쪽 데이터 로드)"):
    try:
        from layer7_visualization.comparison import (
            make_comparison_gauge, make_comparison_radar, make_comparison_table,
        )
        from pipeline.vol_pipeline import run_vol_analysis
        from layer7_visualization.vol_chart import (
            make_regime_matrix, make_relationship_table, make_spread_trend,
            make_garch_trend,
        )
        with st.spinner("두 시장 데이터 준비 중... (V-KOSPI KRX 조회 포함)"):
            kospi_result = load_snapshot(selected_date.isoformat())
            us_result    = load_us_snapshot(selected_date.isoformat())
            vol = run_vol_analysis(kospi_result, us_result)

        # ── 통합 리스크 비교 ──
        col_us1, col_us2 = st.columns([1, 1])
        with col_us1:
            st.markdown("##### 통합 리스크 점수 비교")
            st.plotly_chart(make_comparison_gauge(kospi_result, us_result),
                            use_container_width=True)
        with col_us2:
            st.markdown("##### 리스크 유형별 비교")
            st.plotly_chart(make_comparison_radar(kospi_result, us_result),
                            use_container_width=True)
        st.markdown("##### 등급 상세 비교")
        st.plotly_chart(make_comparison_table(kospi_result, us_result),
                        use_container_width=True)

        # ── 변동성 관계 분석 (Phase 5) ──
        st.divider()
        st.markdown("##### 🌐 변동성 관계 분석 (Phase 5)")
        col_v1, col_v2 = st.columns([1.1, 1])
        with col_v1:
            st.plotly_chart(make_regime_matrix(vol), use_container_width=True)
        with col_v2:
            st.plotly_chart(make_relationship_table(vol), use_container_width=True)

        # 미국 VRP 현재 해석 + VRP 읽는 법
        us_vrp = vol["us"].get("us_vrp")
        vix = vol["us"].get("vix")
        if us_vrp is not None and vix is not None:
            rv = vix - us_vrp   # = S&P 실현 HV20
            if us_vrp < 0:
                msg = "음수 — 실현변동성이 내재를 추월(패닉). 옵션 매도 전략 중단 신호"
            elif us_vrp >= 7:
                msg = "높음 — 옵션 시장이 실제(RV)보다 크게 경계 (헤지 수요↑)"
            else:
                msg = "정상 — 미국 평균(+4%p) 부근"
            st.caption(f"미국 VRP = 내재(IV·VIX) {vix:.1f} − 외재(RV·실현 HV20) {rv:.1f} = "
                       f"**{us_vrp:+.1f}%p** → {msg}")
        with st.expander("💡 VRP(변동성 위험 프리미엄) 읽는 법"):
            st.markdown(
                "변동성에는 **두 종류**가 있습니다:\n\n"
                "**🔵 내재 변동성 (IV) = VIX / V-KOSPI**  \n"
                "옵션 시장이 보는, **미래에 일어날 가능성이 있는** 변동성. "
                "*\"앞으로 이만큼 출렁일 것 같다\"*는 옵션 시장의 예상.\n\n"
                "**🟠 외재(실현) 변동성 (RV) = HV20**  \n"
                "**실제로 일어난** 변동성 (과거 20일 수익률의 표준편차). "
                "GARCH(1,1) 같은 모델을 적용하면 변동성 추이를 함수로 모델링·예측할 수 있음.\n\n"
                "**VRP = IV − RV**  \n"
                "옵션 시장이 **실제보다 얼마나 더 불안해하는지**를 나타냅니다.\n\n"
                "---\n"
                "**📕 케이스 1 — RV는 낮은데 IV만 오름**  \n"
                "RV 12%(안정) · IV(VIX) 22%(상승) → **VRP +10%p (높음)**  \n"
                "→ *실제로는 평온한데 옵션 시장이 경계를 시작* (조기경보 성격)\n\n"
                "**📗 케이스 2 — 둘 다 낮고 격차도 정상**  \n"
                "RV 10% · IV 14% → **VRP +4%p (정상)**  \n"
                "→ *진짜 안정*\n\n"
                "※ **음수 VRP**: 외재(실현)가 내재를 추월 = 패닉. 옵션 매도 전략 중단 신호."
            )

        spread_fig = make_spread_trend(vol)
        if spread_fig is not None:
            st.plotly_chart(spread_fig, use_container_width=True)

        garch_fig = make_garch_trend(vol)
        if garch_fig is not None:
            st.plotly_chart(garch_fig, use_container_width=True)
            st.caption("외재(실현) 변동성 RV을 GARCH(1,1)로 모델링한 추이 — "
                       "변동성 클러스터링 반영. 단순 HV20보다 매끄러운 시장 변동성 함수.")

        # 핵심 신호 (TRG-01~04)
        fired = [k for k, v in vol["triggers"].items() if v]
        if fired:
            st.error(f"🚨 발효 중인 핵심 신호: {', '.join(fired)}")
        else:
            st.success("✅ 발효 중인 핵심 신호 없음 (TRG-01~04)")

        # #7 — 한국 VRP 신뢰도 경고
        st.caption(
            "⚠️ 한국 VRP는 V-KOSPI 옵션 유동성 부족으로 노이즈가 큽니다 — 보조 참고용. "
            "미국 VRP를 1차 지표로 사용하세요."
        )
        if not vol["data_available"]["vkospi"]:
            st.caption("⚠️ V-KOSPI 미수집 (KRX_ID/KRX_PW 미설정 또는 조회 실패) — "
                       "한국측 지표는 미국 단독 판정으로 대체됩니다.")
    except Exception as e:
        st.warning(f"시장 비교 / 변동성 관계 오류: {type(e).__name__}: {e}")


st.divider()
st.caption("ℹ️ KOSPI Risk Intelligence Dashboard · 통합 리스크 모니터링 시스템")

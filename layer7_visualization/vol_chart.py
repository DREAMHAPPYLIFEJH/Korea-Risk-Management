"""변동성 리스크 프레임워크 시각화 — Phase 5.

- make_regime_matrix     : 5분류 통합 레짐 2×2 매트릭스 (현재 레짐 하이라이트)
- make_relationship_table: RI-01~05 + VRP 요약 테이블 (한국 VRP는 보조 참고용 라벨)
- make_spread_trend      : VIX − V-KOSPI 스프레드 추이 (임계선 포함)
- make_garch_trend       : 한미 GARCH(1,1) 조건부 변동성 추이 (외재/실현 변동성 모델링)

Skills.md 참조: Phase 5 §P5-7
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from config.thresholds import SPREAD_KR_STRESS, SPREAD_INVERT

_HDR_COLOR = "#2C3E50"
_NA = "-"

# 레짐별 심각도 색상 (안정 → 위기)
_REGIME_COLOR = {
    "REG-01": "#2ECC71",   # 글로벌 안정 — green
    "REG-04": "#5DADE2",   # 글로벌 회복 — blue
    "REG-05": "#F39C12",   # 미국 경계 — amber
    "REG-03": "#E67E22",   # 한국 단독 위기 — orange
    "REG-02": "#E74C3C",   # 동조화 위기 — red
}

# 2×2 격자 위치 — (col, row): col 0=VIX낮음 1=VIX높음 / row 0=VKOSPI낮음 1=VKOSPI높음
_CELL = {
    "REG-03": (0, 1), "REG-02": (1, 1),
    "REG-01": (0, 0), "REG-05": (1, 0),
}


def _fmt(v: float | None, suffix: str = "", n: int = 2) -> str:
    return f"{v:.{n}f}{suffix}" if v is not None else _NA


def make_regime_matrix(vol_result: dict[str, Any]) -> go.Figure:
    """5분류 통합 레짐 2×2 매트릭스. 현재 레짐 셀을 진하게, 나머지는 흐리게.

    REG-04(회복기)는 좌하단(글로벌 안정) 칸을 점유하되 라벨/색을 회복기로 표시.
    """
    cur = vol_result.get("regime", "REG-01")
    us, kr = vol_result.get("us", {}), vol_result.get("kr", {})

    # 셀 정의: (id, 라벨, col, row). cur가 REG-04면 좌하단을 회복기로 치환.
    cells = [
        ("REG-03", "③ 한국 단독 위기", 0, 1),
        ("REG-02", "② 동조화 위기", 1, 1),
        ("REG-01", "① 글로벌 안정", 0, 0),
        ("REG-05", "⑤ 미국 경계 (US Watch)", 1, 0),
    ]
    if cur == "REG-04":
        cells = [c if c[0] != "REG-01" else ("REG-04", "④ 글로벌 회복기", 0, 0)
                 for c in cells]

    fig = go.Figure()
    for reg_id, label, col, row in cells:
        active = (reg_id == cur)
        base = _REGIME_COLOR[reg_id]
        fig.add_shape(
            type="rect", x0=col, x1=col + 1, y0=row, y1=row + 1,
            line=dict(color="white", width=3),
            fillcolor=base, opacity=1.0 if active else 0.28,
            layer="below",
        )
        fig.add_annotation(
            x=col + 0.5, y=row + 0.5, text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=14 if active else 12,
                      color="white" if active else "#555"),
        )

    # 축 라벨
    fig.add_annotation(x=0.5, y=-0.12, text="VIX 낮음", showarrow=False,
                       font=dict(size=12, color="#888"), yref="y")
    fig.add_annotation(x=1.5, y=-0.12, text="VIX 높음", showarrow=False,
                       font=dict(size=12, color="#888"), yref="y")
    fig.add_annotation(x=-0.12, y=0.5, text="V-KOSPI<br>낮음", showarrow=False,
                       font=dict(size=12, color="#888"), textangle=-90)
    fig.add_annotation(x=-0.12, y=1.5, text="V-KOSPI<br>높음", showarrow=False,
                       font=dict(size=12, color="#888"), textangle=-90)

    title = (f"현재 레짐: <b>{vol_result.get('regime_label', '')}</b>"
             f"  (VIX {_fmt(us.get('vix'))} · V-KOSPI {_fmt(kr.get('vkospi'))})")
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(range=[-0.3, 2], visible=False),
        yaxis=dict(range=[-0.3, 2], visible=False),
        height=380, margin=dict(t=50, b=20, l=40, r=20),
        plot_bgcolor="white",
    )
    return fig


def make_relationship_table(vol_result: dict[str, Any]) -> go.Figure:
    """관계지표(RI-01~05) + VRP 요약. 한국 VRP는 '(보조 참고용)' 라벨 — 신뢰도 경고."""
    rel = vol_result.get("relationship", {})
    us, kr = vol_result.get("us", {}), vol_result.get("kr", {})

    rows = [
        ("VIX − V-KOSPI 스프레드 (RI-01)", _fmt(rel.get("vix_vkospi_spread"))),
        ("HV 비율 KOSPI/S&P (RI-02)",       _fmt(rel.get("hv_ratio"))),
        ("VRP 격차 US−KR (RI-03)",          _fmt(rel.get("vrp_divergence"))),
        ("한미 상관 60일 (RI-05)",          _fmt(rel.get("corr_60d"), n=3)),
        ("  └ 미국 선행 시차 상관",          _fmt(rel.get("lagged_corr_60d"), n=3)),
        ("코스피 베타 (RI-05)",             _fmt(rel.get("kospi_beta"), n=3)),
        ("미국 VRP",                        _fmt(us.get("us_vrp"))),
        ("한국 VRP (보조 참고용)",          _fmt(kr.get("kr_vrp"))),
        ("VVIX",                            _fmt(us.get("vvix"))),
        ("SKEW",                            _fmt(us.get("skew"))),
    ]
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    # 한국 VRP 행만 옅은 경고색으로 구분
    row_fill = ["#FFF6E5" if "보조 참고용" in lab else "white" for lab in labels]

    fig = go.Figure(data=[go.Table(
        columnwidth=[3, 1.4],
        header=dict(values=["지표", "값"], fill_color=_HDR_COLOR,
                    font=dict(color="white", size=13), align=["left", "center"]),
        cells=dict(values=[labels, values],
                   fill_color=[row_fill, row_fill],
                   align=["left", "center"], font=dict(color="#222", size=12),
                   height=26),
    )])
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=40 + 28 * len(rows))
    return fig


def make_spread_trend(vol_result: dict[str, Any]) -> go.Figure | None:
    """VIX − V-KOSPI 스프레드 시계열 + 임계선 (한국 단독 불안 / 역전)."""
    spread = vol_result.get("series", {}).get("spread")
    if spread is None or len(spread) == 0:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spread.index, y=spread.values, mode="lines",
        line=dict(color="#2C3E50", width=1.5), name="VIX − V-KOSPI",
    ))
    # 임계선: 한국 단독 불안(+8) / 역전(0). 평소 음수(한국 프리미엄)대를 감안.
    fig.add_hline(y=SPREAD_INVERT, line=dict(color="#E67E22", width=1, dash="dash"),
                  annotation_text="역전(0)", annotation_position="right")
    fig.add_hline(y=SPREAD_KR_STRESS, line=dict(color="#E74C3C", width=1, dash="dash"),
                  annotation_text=f"한국 단독 불안(+{SPREAD_KR_STRESS})",
                  annotation_position="right")
    fig.update_layout(
        title=dict(text="VIX − V-KOSPI 스프레드 추이", font=dict(size=14)),
        height=300, margin=dict(t=40, b=20, l=40, r=80),
        plot_bgcolor="white", yaxis=dict(gridcolor="#EEE"),
        showlegend=False,
    )
    return fig


def make_garch_trend(vol_result: dict[str, Any]) -> go.Figure | None:
    """한미 GARCH(1,1) 조건부 변동성 추이 (연율화 %).

    외재(실현) 변동성을 GARCH로 모델링한 추이 — KOSPI vs S&P 비교. 둘 다 없으면 None.
    """
    series = vol_result.get("series", {})
    gk = series.get("garch_kospi")
    gs = series.get("garch_sp")
    has_k = gk is not None and len(gk) > 0
    has_s = gs is not None and len(gs) > 0
    if not (has_k or has_s):
        return None

    fig = go.Figure()
    if has_k:
        fig.add_trace(go.Scatter(x=gk.index, y=gk.values, mode="lines", name="KOSPI",
                                 line=dict(color="#E67E22", width=1.6)))
    if has_s:
        fig.add_trace(go.Scatter(x=gs.index, y=gs.values, mode="lines", name="S&P 500",
                                 line=dict(color="#2C3E50", width=1.6)))
    fig.update_layout(
        title=dict(text="GARCH(1,1) 조건부 변동성 추이 — 외재(실현) 변동성 (연율화 %)",
                   font=dict(size=14)),
        height=300, margin=dict(t=40, b=20, l=45, r=20),
        plot_bgcolor="white", yaxis=dict(title="변동성 %", gridcolor="#EEE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )
    return fig

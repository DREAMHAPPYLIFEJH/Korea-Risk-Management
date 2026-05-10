"""5개 리스크 오각형 레이더 차트 — Skills.md §11 Layer 7."""

from __future__ import annotations

import plotly.graph_objects as go


CATEGORIES = ["시장", "변동성", "유동성", "하방", "매크로"]
KEYS = ["market", "volatility", "liquidity", "downside", "macro"]


def make_radar(
    grades: dict[str, int],
    prev_grades: dict[str, int] | None = None,
) -> go.Figure:
    """5축 레이더. 현재(실선 + 채움) + 지난주(점선)."""
    cats_closed = CATEGORIES + [CATEGORIES[0]]

    values = [grades[k] for k in KEYS] + [grades[KEYS[0]]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=cats_closed,
        fill="toself", name="현재",
        fillcolor="rgba(230, 126, 34, 0.25)",
        line=dict(color="#E67E22", width=2),
    ))

    if prev_grades is not None:
        prev_vals = [prev_grades[k] for k in KEYS] + [prev_grades[KEYS[0]]]
        fig.add_trace(go.Scatterpolar(
            r=prev_vals, theta=cats_closed, name="지난주",
            line=dict(color="#3498DB", width=2, dash="dot"),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 4], dtick=1, tickfont={"size": 10}),
            angularaxis=dict(tickfont={"size": 13}),
        ),
        showlegend=True,
        height=400,
        margin=dict(t=20, b=20, l=40, r=40),
    )
    return fig

"""자산 배분 파이/도넛 차트 — Skills.md §11 Layer 7."""

from __future__ import annotations

import plotly.graph_objects as go


def make_allocation(equity: int, bond: int, cash: int, strategy: str) -> go.Figure:
    """주식/채권/현금 도넛 차트 + 전략명 중앙 표시."""
    fig = go.Figure(data=[go.Pie(
        labels=["주식", "채권", "현금"],
        values=[equity, bond, cash],
        hole=0.55,
        marker=dict(colors=["#2ECC71", "#F1C40F", "#3498DB"]),
        textinfo="label+value+percent",
        texttemplate="%{label}<br>%{value}%",
        hovertemplate="%{label}: %{value}%<extra></extra>",
        sort=False,
    )])
    fig.update_layout(
        annotations=[dict(
            text=f"<b>{strategy}</b>", x=0.5, y=0.5,
            font_size=14, showarrow=False,
        )],
        height=360, margin=dict(t=30, b=20, l=20, r=20),
        showlegend=False,
    )
    return fig

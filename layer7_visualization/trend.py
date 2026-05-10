"""리스크 추이 시계열 라인 차트 — Skills.md §11 Layer 7."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def make_trend(
    close: pd.Series,
    hv20: pd.Series,
    mdd60: pd.Series,
    ma20: pd.Series | None = None,
    ma60: pd.Series | None = None,
) -> go.Figure:
    """3-pane 시계열: KOSPI close / HV20 / MDD_60.

    상단 차트에 MA20/60 오버레이 가능.
    """
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=("KOSPI 종가", "HV20 (연율 %)", "MDD_60 (%)"),
        vertical_spacing=0.07,
        row_heights=[0.45, 0.275, 0.275],
    )

    fig.add_trace(go.Scatter(
        x=close.index, y=close.values, name="Close",
        line=dict(color="#2C3E50", width=1.6),
    ), row=1, col=1)
    if ma20 is not None:
        fig.add_trace(go.Scatter(
            x=ma20.index, y=ma20.values, name="MA20",
            line=dict(color="#E67E22", width=1, dash="dot"),
        ), row=1, col=1)
    if ma60 is not None:
        fig.add_trace(go.Scatter(
            x=ma60.index, y=ma60.values, name="MA60",
            line=dict(color="#9B59B6", width=1, dash="dot"),
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=hv20.index, y=hv20.values, name="HV20",
        line=dict(color="#E67E22", width=1.5), showlegend=False,
    ), row=2, col=1)
    # 변동성 등급 경계선
    for thresh, label, dash in [(12, "Medium", "dot"), (20, "High", "dash"), (30, "Critical", "solid")]:
        fig.add_hline(y=thresh, line=dict(color="gray", width=0.5, dash=dash),
                      annotation_text=label, annotation_position="right",
                      row=2, col=1)

    fig.add_trace(go.Scatter(
        x=mdd60.index, y=mdd60.values, name="MDD60",
        line=dict(color="#E74C3C", width=1.5), showlegend=False,
    ), row=3, col=1)
    for thresh, label, dash in [(-5, "Medium", "dot"), (-10, "High", "dash"), (-20, "Critical", "solid")]:
        fig.add_hline(y=thresh, line=dict(color="gray", width=0.5, dash=dash),
                      annotation_text=label, annotation_position="right",
                      row=3, col=1)

    fig.update_layout(
        height=620, margin=dict(t=40, b=20, l=20, r=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig

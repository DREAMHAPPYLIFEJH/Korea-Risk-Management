"""KOSPI 펀더멘털 시각화 — Phase 4 (마켓 컨텍스트).

make_fundamental_trend: KOSPI 지수 PER/PBR 추이 (이중 y축 — PER ~수십, PBR ~수배).

Skills.md 참조: Phase 4 §P4-1
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def make_fundamental_trend(df: pd.DataFrame) -> go.Figure:
    """KOSPI PER(좌축)·PBR(우축) 추이. df: get_kospi_fundamental 결과."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["per"], mode="lines", name="PER",
        line=dict(color="#2C3E50", width=1.6), yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["pbr"], mode="lines", name="PBR",
        line=dict(color="#E67E22", width=1.6), yaxis="y2",
    ))
    fig.update_layout(
        title=dict(text="KOSPI PER / PBR 추이", font=dict(size=14)),
        height=300, margin=dict(t=40, b=20, l=50, r=50),
        plot_bgcolor="white",
        yaxis=dict(title=dict(text="PER", font=dict(color="#2C3E50")),
                   gridcolor="#EEE"),
        yaxis2=dict(title=dict(text="PBR", font=dict(color="#E67E22")),
                    overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )
    return fig

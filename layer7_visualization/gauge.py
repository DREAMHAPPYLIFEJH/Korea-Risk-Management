"""통합 점수 반원형 게이지 — Skills.md §11 Layer 7.

0~4 범위, 5개 구간 색상 (Safe ~ Extreme).
"""

from __future__ import annotations

import plotly.graph_objects as go

from config.constants import BAND_COLOR


def make_gauge(score: float, score_band: str) -> go.Figure:
    """통합 점수 게이지. score_band 라벨 + 5개 구간 색상."""
    color = BAND_COLOR[score_band]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"valueformat": ".2f", "font": {"size": 40}},
        gauge={
            "axis":  {"range": [1, 4], "tickvals": [1, 1.5, 2, 2.5, 3, 4]},
            "bar":   {"color": color, "thickness": 0.25},
            "borderwidth": 1,
            "steps": [
                {"range": [1.0, 1.5], "color": BAND_COLOR["Safe"]},
                {"range": [1.5, 2.0], "color": BAND_COLOR["Caution"]},
                {"range": [2.0, 2.5], "color": BAND_COLOR["Alert"]},
                {"range": [2.5, 3.0], "color": BAND_COLOR["Danger"]},
                {"range": [3.0, 4.0], "color": BAND_COLOR["Extreme"]},
            ],
        },
        title={"text": f"<b>{score_band}</b>", "font": {"size": 22, "color": color}},
    ))
    fig.update_layout(height=320, margin=dict(t=60, b=10, l=20, r=20))
    return fig

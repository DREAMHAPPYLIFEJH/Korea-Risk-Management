"""KOSPI vs S&P500 글로벌 비교 시각화 — Phase 3."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.constants import BAND_COLOR, GRADE_COLOR


def make_comparison_gauge(kospi_result: dict[str, Any], us_result: dict[str, Any]) -> go.Figure:
    """KOSPI / S&P500 통합 점수 나란히 비교 게이지."""
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=["KOSPI", "S&P 500"],
    )

    for col, result in enumerate([kospi_result, us_result], start=1):
        score = result["score"]
        band  = result["score_band"]
        color = BAND_COLOR.get(band, "#CCCCCC")
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 28}, "suffix": f"  {band}"},
            gauge={
                "axis":  {"range": [1, 4], "tickvals": [1, 1.5, 2, 2.5, 3, 4]},
                "bar":   {"color": color},
                "steps": [
                    {"range": [1.0, 1.5], "color": BAND_COLOR["Safe"]},
                    {"range": [1.5, 2.0], "color": BAND_COLOR["Caution"]},
                    {"range": [2.0, 2.5], "color": BAND_COLOR["Alert"]},
                    {"range": [2.5, 3.0], "color": BAND_COLOR["Danger"]},
                    {"range": [3.0, 4.0], "color": BAND_COLOR["Extreme"]},
                ],
            },
        ), row=1, col=col)

    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def make_comparison_radar(kospi_result: dict[str, Any], us_result: dict[str, Any]) -> go.Figure:
    """KOSPI / S&P500 리스크 유형별 레이더 비교."""
    categories = ["시장", "변동성", "유동성", "하방", "매크로"]
    keys       = ["market", "volatility", "liquidity", "downside", "macro"]

    fig = go.Figure()
    for result, name, color in [
        (kospi_result, "KOSPI",   "#3498DB"),
        (us_result,   "S&P 500", "#E74C3C"),
    ]:
        grades = [result["risks"][k]["grade"] for k in keys]
        fig.add_trace(go.Scatterpolar(
            r=grades + [grades[0]],
            theta=categories + [categories[0]],
            name=name,
            line=dict(color=color, width=2),
            fill="toself",
            opacity=0.3,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 4], tickvals=[1, 2, 3, 4])),
        legend=dict(orientation="h", y=-0.15),
        height=320,
        margin=dict(l=40, r=40, t=20, b=40),
    )
    return fig


def make_comparison_table(kospi_result: dict[str, Any], us_result: dict[str, Any]) -> go.Figure:
    """KOSPI vs S&P500 리스크 등급 비교 테이블."""
    labels = {"market": "시장", "volatility": "변동성",
              "liquidity": "유동성", "downside": "하방", "macro": "매크로"}
    risk_keys = ["market", "volatility", "liquidity", "downside", "macro"]

    rows_kospi = [kospi_result["risks"][k]["details"]["grade_label"] for k in risk_keys]
    rows_us    = [us_result["risks"][k]["details"]["grade_label"]    for k in risk_keys]
    row_names  = [labels[k] for k in risk_keys]

    def _colors(labels_list):
        return [GRADE_COLOR.get(g, "#CCCCCC") for g in labels_list]

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["리스크 유형", "KOSPI", "S&P 500"],
            fill_color="#2C3E50",
            font=dict(color="white", size=13),
            align="center",
        ),
        cells=dict(
            values=[row_names, rows_kospi, rows_us],
            fill_color=[
                ["white"] * len(row_names),
                _colors(rows_kospi),
                _colors(rows_us),
            ],
            align="center",
            font=dict(size=12),
            height=28,
        ),
    )])
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                      height=40 + 30 * len(risk_keys))
    return fig

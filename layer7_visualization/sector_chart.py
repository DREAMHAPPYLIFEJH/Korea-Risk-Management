"""섹터 리스크 시각화 — Phase 2 (PDF §9.1).

make_sector_table: 섹터별 리스크 등급 테이블 (Plotly).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go

from config.constants import GRADE_COLOR

if TYPE_CHECKING:
    from layer3_risk.sector import SectorOutput

_NA_COLOR  = "#EEEEEE"
_HDR_COLOR = "#2C3E50"

_INDICATOR_FMT: dict[str, str] = {
    "beta":              "{:.2f}",
    "hv20":              "{:.1f}%",
    "relative_strength": "{:.2f}",
    "mdd_60":            "{:.1f}%",
}


def _fmt(key: str, value: float | None) -> str:
    if value is None:
        return "-"
    try:
        return _INDICATOR_FMT[key].format(value)
    except (KeyError, ValueError):
        return str(value)


def make_sector_table(sector_results: list[SectorOutput]) -> go.Figure:
    """섹터별 리스크 등급 테이블.

    데이터 없는 섹터는 '-'로 표시.
    """
    sectors, grades, betas, hvs, rs_vals, mdds = [], [], [], [], [], []
    grade_colors: list[str] = []

    for r in sector_results:
        sectors.append(r.sector)
        if r.data_available and r.grade_label:
            grades.append(r.grade_label)
            grade_colors.append(GRADE_COLOR.get(r.grade_label, _NA_COLOR))
        else:
            grades.append("N/A")
            grade_colors.append(_NA_COLOR)

        ind = r.indicators
        betas.append(_fmt("beta", ind.get("beta")))
        hvs.append(_fmt("hv20", ind.get("hv20")))
        rs_vals.append(_fmt("relative_strength", ind.get("relative_strength")))
        mdds.append(_fmt("mdd_60", ind.get("mdd_60")))

    fig = go.Figure(data=[go.Table(
        columnwidth=[2, 1.5, 1, 1, 1, 1],
        header=dict(
            values=["섹터", "등급", "베타", "변동성(HV20)", "상대강도(RS)", "MDD60"],
            fill_color=_HDR_COLOR,
            font=dict(color="white", size=13),
            align="center",
        ),
        cells=dict(
            values=[sectors, grades, betas, hvs, rs_vals, mdds],
            fill_color=[
                ["white"] * len(sectors),
                grade_colors,
                ["white"] * len(sectors),
                ["white"] * len(sectors),
                ["white"] * len(sectors),
                ["white"] * len(sectors),
            ],
            align="center",
            font=dict(size=12),
            height=28,
        ),
    )])
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=40 + 30 * len(sector_results))
    return fig

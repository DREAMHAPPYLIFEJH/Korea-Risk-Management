"""섹터 리스크 — Phase 2 독립 분석 (PDF §4).

Phase 1 통합 점수에 포함되지 않음 — 대시보드 섹터 분석 섹션 전용.
sector_close=None이면 data_available=False, grade=None 반환 (업종 코드 미확보).

등급 기준 (PDF §4.4):
  Low:      beta < 1.0
  Medium:   1.0 <= beta < 1.3
  High:     beta >= 1.3
  Critical: beta >= 1.5 AND RS < 1.0 (시장 대비 약세)

베타 판정 후 HV20·MDD로 상향 보정 가능.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from config.thresholds import (
    SECTOR_BETA_CRITICAL, SECTOR_BETA_HIGH, SECTOR_BETA_MEDIUM,
    SECTOR_RS_DECLINE, SECTOR_MDD_HIGH, SECTOR_MDD_CRITICAL,
    SECTOR_HV_HIGH, SECTOR_HV_CRITICAL,
)
from layer2_indicator.sector_indicator import (
    sector_beta, sector_hv20, relative_strength, sector_mdd,
)


_GRADE_LABELS: dict[int, str] = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}


class SectorOutput(BaseModel):
    """섹터 리스크 출력 스키마 — Phase 2 전용.

    RiskOutput과 별도 스키마: grade=None(데이터 없음) 허용.
    """
    model_config = ConfigDict(extra="forbid")

    sector:         str
    grade:          int | None     = Field(None, ge=1, le=4)
    grade_label:    str | None     = None
    data_available: bool           = False
    indicators:     dict[str, Any] = Field(default_factory=dict)
    reason:         str            = ""


def _grade_from_indicators(
    beta: float | None,
    rs: float | None,
    hv20: float | None,
    mdd: float | None,
) -> tuple[int | None, str]:
    """베타 기반 등급 산정 + HV20·MDD 보정."""
    if beta is None:
        return None, "데이터 없음"

    # 베타 1순위 판정
    rs_weak = (rs is not None and rs < SECTOR_RS_DECLINE)

    if beta >= SECTOR_BETA_CRITICAL and rs_weak:
        grade = 4
        reason = f"beta={beta:.2f}(≥{SECTOR_BETA_CRITICAL}) + RS약세"
    elif beta >= SECTOR_BETA_HIGH:
        grade = 3
        reason = f"beta={beta:.2f}(≥{SECTOR_BETA_HIGH})"
    elif beta >= SECTOR_BETA_MEDIUM:
        grade = 2
        reason = f"beta={beta:.2f}(≥{SECTOR_BETA_MEDIUM})"
    else:
        grade = 1
        reason = f"beta={beta:.2f}(<{SECTOR_BETA_MEDIUM})"

    # HV20 보정 (상향만)
    if hv20 is not None:
        if hv20 >= SECTOR_HV_CRITICAL and grade < 4:
            grade = 4
            reason += f" + hv20={hv20:.1f}%(≥{SECTOR_HV_CRITICAL})"
        elif hv20 >= SECTOR_HV_HIGH and grade < 3:
            grade = 3
            reason += f" + hv20={hv20:.1f}%(≥{SECTOR_HV_HIGH})"

    # MDD 보정 (상향만)
    if mdd is not None:
        if mdd <= SECTOR_MDD_CRITICAL and grade < 4:
            grade = 4
            reason += f" + mdd={mdd:.1f}%(≤{SECTOR_MDD_CRITICAL})"
        elif mdd <= SECTOR_MDD_HIGH and grade < 3:
            grade = 3
            reason += f" + mdd={mdd:.1f}%(≤{SECTOR_MDD_HIGH})"

    return grade, reason


def evaluate(
    *,
    sector: str,
    sector_close: pd.Series | None,
    market_close: pd.Series,
) -> SectorOutput:
    """섹터 리스크 등급 산정.

    sector_close=None → 업종 코드 미확보, data_available=False 반환.
    """
    if sector_close is None:
        return SectorOutput(
            sector=sector,
            reason="업종 코드 미확보 (config/constants.py SECTOR_CODES 교체 필요)",
        )

    beta = sector_beta(sector_close, market_close)
    hv20 = sector_hv20(sector_close)
    rs   = relative_strength(sector_close, market_close)
    mdd  = sector_mdd(sector_close)

    grade, reason = _grade_from_indicators(beta, rs, hv20, mdd)

    return SectorOutput(
        sector=sector,
        grade=grade,
        grade_label=_GRADE_LABELS.get(grade) if grade else None,
        data_available=True,
        indicators={
            "beta":             beta,
            "hv20":             hv20,
            "relative_strength": rs,
            "mdd_60":           mdd,
        },
        reason=reason,
    )

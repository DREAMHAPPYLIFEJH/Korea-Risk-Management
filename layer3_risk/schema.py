"""공통 JSON Output Schema — Skills.md §7 Layer 3 공통 구조.

5개 리스크가 동일하게 따르는 최상위 6필드 + details 9필드 Pydantic 모델.
Skills.md "최상위 필드 정확히 6개": risk_id, grade, score, triggered_conditions, reason, details.

사용 예:
    from layer3_risk.schema import RiskOutput, RiskDetails, grade_label

    out = RiskOutput(
        risk_id="RISK-A",
        grade=3, score=3,
        triggered_conditions=["ma_bearish_full", "disp_ma20_lt_94"],
        reason="...",
        details=RiskDetails(
            risk_type="market",
            grade_label=grade_label(3),
            weight_default=0.30,
            timestamp="2026-04-30",
            indicators={...}, sub_grades={...}, flags={...},
            conflict_rule="none",
            condition_candidates=[...],
        ),
    )
    out.model_dump()       # dict
    out.model_dump_json()  # JSON string
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


GRADE_LABELS: dict[int, str] = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
LABEL_GRADES: dict[str, int] = {v: k for k, v in GRADE_LABELS.items()}

GradeLabel = Literal["Low", "Medium", "High", "Critical"]
RiskId = Literal["RISK-A", "RISK-B", "RISK-C", "RISK-D", "RISK-E"]


def grade_label(grade: int) -> GradeLabel:
    """1~4 정수 → 'Low'~'Critical' (Skills.md §1 GRADE_MAP 역매핑)."""
    return GRADE_LABELS[grade]   # type: ignore[return-value]


def label_to_grade(label: str) -> int:
    """'Low'~'Critical' → 1~4 (Skills.md §1)."""
    return LABEL_GRADES[label]


class RiskDetails(BaseModel):
    """details 객체 — Skills.md §7 details 내부 9필드."""

    model_config = ConfigDict(extra="forbid")

    risk_type:            str
    grade_label:          GradeLabel
    weight_default:       float
    timestamp:            str            # YYYY-MM-DD
    indicators:           dict[str, Any] = Field(default_factory=dict)
    sub_grades:           dict[str, Any] = Field(default_factory=dict)
    flags:                dict[str, Any] = Field(default_factory=dict)
    conflict_rule:        str            = "none"
    condition_candidates: list[str]      = Field(default_factory=list)


class RiskOutput(BaseModel):
    """최상위 6필드 — Skills.md §7 모든 리스크 공통."""

    model_config = ConfigDict(extra="forbid")

    risk_id:              RiskId
    grade:                int = Field(ge=1, le=4)
    score:                int = Field(ge=1, le=4)
    triggered_conditions: list[str] = Field(default_factory=list)
    reason:               str
    details:              RiskDetails

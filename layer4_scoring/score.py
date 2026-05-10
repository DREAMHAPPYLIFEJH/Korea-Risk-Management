"""통합 점수 계산 + 기여도 + 점수 구간 매핑 — Skills.md §8 Layer 4.

integrated_score = Σ(grade_i × W_i), 범위 1.0~4.0.
score_band 5구간 (Safe/Caution/Alert/Danger/Extreme), 경계값 상위 구간 적용.
SCN-04 + score >= 3.0 → score_band="Extreme" 명시 확인.
"""

from __future__ import annotations

from typing import Any


# 점수 구간 (Skills.md §1 SCORE_BAND_THRESHOLDS와 동일)
def score_to_band(integrated_score: float) -> str:
    """경계값 상위 구간 적용 (예: 2.5 → Danger)."""
    if integrated_score >= 3.0: return "Extreme"
    if integrated_score >= 2.5: return "Danger"
    if integrated_score >= 2.0: return "Alert"
    if integrated_score >= 1.5: return "Caution"
    return "Safe"


def integrated_score(
    *,
    market_grade: int,
    volatility_grade: int,
    macro_grade: int,
    liquidity_grade: int,
    downside_grade: int,
    weights: dict[str, float],
) -> float:
    """통합 점수 = Σ(grade × W). Skills.md §8."""
    return (
        market_grade     * weights["market"]
        + volatility_grade * weights["volatility"]
        + macro_grade      * weights["macro"]
        + liquidity_grade  * weights["liquidity"]
        + downside_grade   * weights["downside"]
    )


def contributions(
    *,
    market_grade: int,
    volatility_grade: int,
    macro_grade: int,
    liquidity_grade: int,
    downside_grade: int,
    weights: dict[str, float],
    score: float,
) -> dict[str, float]:
    """리스크별 기여도 (%) — 어떤 리스크가 통합 점수에 가장 크게 기여하는지."""
    if score == 0:
        return {k: 0.0 for k in ("market", "volatility", "macro", "liquidity", "downside")}
    return {
        "market":     (market_grade     * weights["market"])     / score * 100.0,
        "volatility": (volatility_grade * weights["volatility"]) / score * 100.0,
        "macro":      (macro_grade      * weights["macro"])      / score * 100.0,
        "liquidity":  (liquidity_grade  * weights["liquidity"])  / score * 100.0,
        "downside":   (downside_grade   * weights["downside"])   / score * 100.0,
    }


def compute(
    *,
    market_grade: int,
    volatility_grade: int,
    macro_grade: int,
    liquidity_grade: int,
    downside_grade: int,
    weights: dict[str, float],
    scn04_flag: bool = False,
) -> dict[str, Any]:
    """통합 점수 + 구간 + 기여도 일괄 산출.

    Returns: {score, score_band, contributions}.
    SCN-04 발동 + score >= 3.0 → "Extreme" 명시 보정.
    """
    score = integrated_score(
        market_grade=market_grade, volatility_grade=volatility_grade,
        macro_grade=macro_grade, liquidity_grade=liquidity_grade,
        downside_grade=downside_grade, weights=weights,
    )
    band = score_to_band(score)
    if scn04_flag and score >= 3.0:
        band = "Extreme"   # 명시 확인
    contrib = contributions(
        market_grade=market_grade, volatility_grade=volatility_grade,
        macro_grade=macro_grade, liquidity_grade=liquidity_grade,
        downside_grade=downside_grade, weights=weights, score=score,
    )
    return {
        "score":         score,
        "score_band":    band,
        "contributions": contrib,
    }

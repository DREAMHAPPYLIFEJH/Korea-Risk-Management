"""End-to-end 파이프라인 골든 테스트 — Skills.md §8 계산 예시.

기준 케이스: 시장 High(3)·변동성 High(3)·매크로 Medium(2)·유동성 Medium(2)·하방 High(3)
→ integrated_score = 2.65 → score_band = "Danger" → strategy = "Defensive"
"""

from __future__ import annotations

from layer4_scoring.phase import select_weights
from layer4_scoring.score import compute as score_compute
from layer5_strategy.strategy import compute as strategy_compute


# ── Skills.md §8 계산 예시 ────────────────────────────────────

def test_skills_md_s8_score():
    """시장3·변동성3·매크로2·유동성2·하방3, bullish → 2.65, Danger."""
    weights = select_weights("bullish")
    result = score_compute(
        market_grade=3, volatility_grade=3, macro_grade=2,
        liquidity_grade=2, downside_grade=3, weights=weights,
    )
    assert abs(result["score"] - 2.65) < 1e-9
    assert result["score_band"] == "Danger"


def test_skills_md_s8_strategy():
    """Danger + critical_count=0 → Defensive."""
    result = strategy_compute(
        score_band="Danger", integrated_score=2.65, critical_count=0,
        market_grade=3, volatility_grade=3, macro_grade=2,
        liquidity_grade=2, downside_grade=3,
    )
    assert result["strategy"] == "Defensive"


# ── 2026-04-30 라이브 검증 ────────────────────────────────────

def test_2026_04_30_score():
    """시장1·변동성3·매크로1·유동성2·하방4, bullish → 1.95, Caution."""
    weights = select_weights("bullish")
    result = score_compute(
        market_grade=1, volatility_grade=3, macro_grade=1,
        liquidity_grade=2, downside_grade=4, weights=weights,
    )
    assert abs(result["score"] - 1.95) < 1e-9
    assert result["score_band"] == "Caution"


def test_2026_04_30_strategy():
    """하방 Critical(1개) → OVR-03 → Moderate_Defensive."""
    result = strategy_compute(
        score_band="Caution", integrated_score=1.95, critical_count=1,
        market_grade=1, volatility_grade=3, macro_grade=1,
        liquidity_grade=2, downside_grade=4,
    )
    assert result["strategy"] == "Moderate_Defensive"


# ── 2026-03-31 라이브 검증 ────────────────────────────────────

def test_2026_03_31_score():
    """시장2·변동성4·매크로3·유동성1·하방4, bullish → 2.75, Danger."""
    weights = select_weights("bullish")
    result = score_compute(
        market_grade=2, volatility_grade=4, macro_grade=3,
        liquidity_grade=1, downside_grade=4, weights=weights,
    )
    assert abs(result["score"] - 2.75) < 1e-9
    assert result["score_band"] == "Danger"


def test_2026_03_31_strategy():
    """Critical 2개 + score > 2.5 → OVR-04 → Defensive."""
    result = strategy_compute(
        score_band="Danger", integrated_score=2.75, critical_count=2,
        market_grade=2, volatility_grade=4, macro_grade=3,
        liquidity_grade=1, downside_grade=4,
    )
    assert result["strategy"] == "Defensive"


def test_2026_03_31_allocation():
    """변동성·하방 양쪽 Critical → CR-03 → equity=0, 0/47/53."""
    result = strategy_compute(
        score_band="Danger", integrated_score=2.75, critical_count=2,
        market_grade=2, volatility_grade=4, macro_grade=3,
        liquidity_grade=1, downside_grade=4,
    )
    alloc = result["allocation"]
    assert alloc["equity"] == 0
    assert alloc["bond"] == 47
    assert alloc["cash"] == 53


# ── 점수 구간 경계값 ──────────────────────────────────────────

def test_score_band_경계값_상위_구간_적용():
    """2.5 → Danger (Alert 아님), 경계값은 상위 구간."""
    from layer4_scoring.score import score_to_band
    assert score_to_band(2.5) == "Danger"
    assert score_to_band(2.0) == "Alert"
    assert score_to_band(3.0) == "Extreme"
    assert score_to_band(1.5) == "Caution"
    assert score_to_band(1.0) == "Safe"

"""S&P500 파이프라인 테스트 — Phase 3.

API 호출 없이 us_macro 로직 + 점수 계산만 검증.
"""

from __future__ import annotations

import pytest

from layer3_risk.us_macro import evaluate as us_macro_evaluate
from layer4_scoring.score import compute as score_compute
from layer4_scoring.phase import select_weights


TS = "2026-04-30"


# ── US 매크로 기저 입력 ───────────────────────────────────────

_BASE_MACRO = dict(
    fed_rate=3.0, fed_rate_delta=0.0,
    cpi_yoy=2.0, cpi_delta=0.0,
    dxy_level=98.0, dxy_weekly_change=0.0,
    m2_contraction=False, timestamp=TS,
)


def _us_macro(**overrides):
    return us_macro_evaluate(**{**_BASE_MACRO, **overrides})


# ── US 매크로 수준 판정 ───────────────────────────────────────

def test_us_macro_안정_시_low():
    """모든 지표 안정 → grade=1."""
    out = _us_macro()
    assert out.grade == 1
    assert out.details.flags["triggered_scenario"] is None

def test_us_macro_fed_경계_caution():
    """Fed rate 경계(3.5~4.5%) → caution_count=1 → grade=2."""
    out = _us_macro(fed_rate=4.0)
    assert out.grade >= 2

def test_us_macro_fed_cpi_위험_high():
    """Fed > 4.5% + CPI > 4.0% → danger_count >= 2 → level=3."""
    out = _us_macro(fed_rate=5.0, cpi_yoy=4.5)
    assert out.grade >= 3

def test_us_macro_dxy_없으면_동작():
    """dxy_level=None (FRED 미설정 등) → 오류 없이 동작."""
    out = _us_macro(dxy_level=None, dxy_weekly_change=None)
    assert out.grade >= 1

def test_us_macro_fred_없어도_동작():
    """FRED 데이터 전부 None → DXY만으로 평가, 오류 없음."""
    out = _us_macro(
        fed_rate=None, fed_rate_delta=None,
        cpi_yoy=None, cpi_delta=None,
    )
    assert out.grade >= 1
    assert out.details.flags["fred_available"] is False


# ── 이벤트 탐지 ───────────────────────────────────────────────

def test_us_evt_fed_hike():
    """Fed hike 0.25%p → EVT_US_01 발동."""
    out = _us_macro(fed_rate_delta=0.25)
    assert "EVT_US_01" in out.triggered_conditions

def test_us_evt_cpi_surge():
    """CPI delta >= 0.5%p → EVT_US_02 발동."""
    out = _us_macro(cpi_delta=0.5)
    assert "EVT_US_02" in out.triggered_conditions

def test_us_evt_dxy_spike():
    """DXY 주간 +2% → EVT_US_03 발동."""
    out = _us_macro(dxy_weekly_change=0.025)
    assert "EVT_US_03" in out.triggered_conditions

def test_us_evt_fed_cut():
    """Fed cut -0.25%p → EVT_US_04 발동."""
    out = _us_macro(fed_rate_delta=-0.25)
    assert "EVT_US_04" in out.triggered_conditions


# ── 시나리오 ──────────────────────────────────────────────────

def test_us_scn01_tightening():
    """Fed hike + CPI surge → SCN-US-01, grade=4."""
    out = _us_macro(fed_rate_delta=0.25, cpi_delta=0.5)
    assert out.grade == 4
    assert out.details.flags["triggered_scenario"] == "SCN-US-01"

def test_us_scn02_dollar_surge():
    """DXY spike → SCN-US-02, grade=4."""
    out = _us_macro(dxy_weekly_change=0.025)
    assert out.grade == 4
    assert out.details.flags["triggered_scenario"] == "SCN-US-02"


# ── 점수 계산 (기존 score_compute 재사용 검증) ────────────────

def test_us_score_계산_bullish():
    """S&P500 bullish 국면 점수 계산 — Phase 1 score_compute 재사용 확인."""
    weights = select_weights("bullish")
    result  = score_compute(
        market_grade=1, volatility_grade=2, macro_grade=1,
        liquidity_grade=1, downside_grade=2, weights=weights,
    )
    assert 1.0 <= result["score"] <= 4.0
    assert result["score_band"] in ("Safe", "Caution", "Alert", "Danger", "Extreme")

def test_us_score_extreme_경계():
    """모든 등급 Critical → score=4.0, Extreme."""
    weights = select_weights("bearish")
    result  = score_compute(
        market_grade=4, volatility_grade=4, macro_grade=4,
        liquidity_grade=4, downside_grade=4, weights=weights,
    )
    assert result["score"] == pytest.approx(4.0)
    assert result["score_band"] == "Extreme"

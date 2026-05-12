"""5개 리스크 등급 판정 테스트 — Skills.md §7 Layer 3 등급 표 케이스.

각 리스크별 Low/Medium/High/Critical 경계값 케이스.
JSON 공통 6필드 스키마 검증 포함.
"""

from __future__ import annotations

import pytest

from layer3_risk import market as risk_market
from layer3_risk import volatility as risk_volatility
from layer3_risk import liquidity as risk_liquidity
from layer3_risk import downside as risk_downside
from layer3_risk.schema import RiskOutput, RiskDetails

TS = "2026-04-30"


# ── Risk-A 시장 ──────────────────────────────────────────────

def test_risk_a_low():
    """정배열 + 이격도 98~102 + ADX > 25 → Low(1)."""
    out = risk_market.evaluate(
        ma20=110, ma60=105, ma120=100,
        disp_ma20=100, disp_ma60=100,
        adx=30, consec_decline=0, timestamp=TS,
    )
    assert out.grade == 1

def test_risk_a_medium():
    """부분 역배열 + 이격도 94~98 → Medium(2)."""
    out = risk_market.evaluate(
        ma20=95, ma60=100, ma120=90,
        disp_ma20=95, disp_ma60=90,
        adx=25, consec_decline=0, timestamp=TS,
    )
    assert out.grade == 2

def test_risk_a_high():
    """완전 역배열 + 이격도 90~94 → High(3)."""
    out = risk_market.evaluate(
        ma20=80, ma60=90, ma120=100,
        disp_ma20=91, disp_ma60=88,
        adx=25, consec_decline=0, timestamp=TS,
    )
    assert out.grade == 3

def test_risk_a_critical():
    """완전 역배열 + 이격도 < 90 + 연속 하락 5일 이상 → Critical(4)."""
    out = risk_market.evaluate(
        ma20=80, ma60=90, ma120=100,
        disp_ma20=85, disp_ma60=82,
        adx=30, consec_decline=5, timestamp=TS,
    )
    assert out.grade == 4

def test_risk_a_schema_6필드():
    """RiskOutput 최상위 6필드 존재 확인."""
    out = risk_market.evaluate(
        ma20=110, ma60=105, ma120=100,
        disp_ma20=100, disp_ma60=100,
        adx=30, consec_decline=0, timestamp=TS,
    )
    d = out.model_dump()
    for field in ("risk_id", "grade", "score", "triggered_conditions", "reason", "details"):
        assert field in d

def test_risk_a_schema_details_9필드():
    """RiskDetails 내부 9필드 존재 확인."""
    out = risk_market.evaluate(
        ma20=110, ma60=105, ma120=100,
        disp_ma20=100, disp_ma60=100,
        adx=30, consec_decline=0, timestamp=TS,
    )
    det = out.model_dump()["details"]
    for field in ("risk_type", "grade_label", "weight_default", "timestamp",
                  "indicators", "sub_grades", "flags", "conflict_rule", "condition_candidates"):
        assert field in det


# ── Risk-B 변동성 ────────────────────────────────────────────

def test_risk_b_low():
    """HV20 < 12 → Low(1)."""
    out = risk_volatility.evaluate(hv20=10, hv60=15, vol_ratio_hv=0.9, timestamp=TS)
    assert out.grade == 1

def test_risk_b_medium():
    """12 <= HV20 < 20 → Medium(2)."""
    out = risk_volatility.evaluate(hv20=15, hv60=15, vol_ratio_hv=1.0, timestamp=TS)
    assert out.grade == 2

def test_risk_b_high():
    """20 <= HV20 < 30 → High(3)."""
    out = risk_volatility.evaluate(hv20=25, hv60=20, vol_ratio_hv=1.25, timestamp=TS)
    assert out.grade == 3

def test_risk_b_critical():
    """HV20 >= 30 → Critical(4)."""
    out = risk_volatility.evaluate(hv20=35, hv60=25, vol_ratio_hv=1.4, timestamp=TS)
    assert out.grade == 4

def test_risk_b_cr01_max_적용():
    """HV20 Low(1) + VKOSPI High(3) → CR-01 MAX → grade=3."""
    out = risk_volatility.evaluate(hv20=10, hv60=15, vol_ratio_hv=0.9, vkospi=28, timestamp=TS)
    assert out.grade == 3
    assert "cr01_max_applied" in out.triggered_conditions

def test_risk_b_vkospi_none_hv_단독():
    """VKOSPI=None(Phase 1 보류) → hv_grade만 사용."""
    out = risk_volatility.evaluate(hv20=25, hv60=20, vol_ratio_hv=1.2, vkospi=None, timestamp=TS)
    assert out.grade == 3
    assert "cr01_max_applied" not in out.triggered_conditions


# ── Risk-C 유동성 ────────────────────────────────────────────

def test_risk_c_low():
    """거래량 비율 >= 1.0 → Low(1)."""
    out = risk_liquidity.evaluate(vol_ratio=1.2, vol_streak=0, timestamp=TS)
    assert out.grade == 1

def test_risk_c_medium():
    """거래량 비율 0.7~1.0 → Medium(2)."""
    out = risk_liquidity.evaluate(vol_ratio=0.8, vol_streak=0, timestamp=TS)
    assert out.grade == 2

def test_risk_c_high():
    """거래량 비율 0.5~0.7 + 연속 감소 3일 → High(3)."""
    out = risk_liquidity.evaluate(vol_ratio=0.6, vol_streak=3, timestamp=TS)
    assert out.grade == 3

def test_risk_c_critical():
    """거래량 비율 < 0.5 + 연속 감소 5일 → Critical(4)."""
    out = risk_liquidity.evaluate(vol_ratio=0.4, vol_streak=5, timestamp=TS)
    assert out.grade == 4

def test_risk_c_val_ratio_보정():
    """vol_ratio 정상(Low) + val_ratio < 0.6 → 최소 Medium 보정."""
    out = risk_liquidity.evaluate(vol_ratio=1.0, vol_streak=0, val_ratio=0.5, timestamp=TS)
    assert out.grade == 2
    assert "val_ratio_lt_0.6" in out.triggered_conditions


# ── Risk-D 하방 ──────────────────────────────────────────────

def test_risk_d_low():
    """MDD_60 > -5, VaR > -1.5 → Low(1)."""
    out = risk_downside.evaluate(
        mdd_60=-3, mdd_252=-5, var_95=-1.0, cvar=-1.5, mdd_recovery_months=2, timestamp=TS,
    )
    assert out.grade == 1

def test_risk_d_medium():
    """MDD_60 -5~-10, VaR -1.5~-2.5 → Medium(2)."""
    out = risk_downside.evaluate(
        mdd_60=-7, mdd_252=-10, var_95=-2.0, cvar=-2.8, mdd_recovery_months=4, timestamp=TS,
    )
    assert out.grade == 2

def test_risk_d_high():
    """MDD_60 -10~-20, VaR -2.5~-3.5 → High(3)."""
    out = risk_downside.evaluate(
        mdd_60=-15, mdd_252=-20, var_95=-3.0, cvar=-4.0, mdd_recovery_months=5, timestamp=TS,
    )
    assert out.grade == 3

def test_risk_d_critical():
    """MDD_60 < -20, VaR < -3.5 → Critical(4)."""
    out = risk_downside.evaluate(
        mdd_60=-25, mdd_252=-30, var_95=-4.0, cvar=-5.5, mdd_recovery_months=99, timestamp=TS,
    )
    assert out.grade == 4

def test_risk_d_cr02_max_적용():
    """MDD Medium(2) + VaR Critical(4) → CR-02 MAX → grade=4."""
    out = risk_downside.evaluate(
        mdd_60=-7, mdd_252=-10, var_95=-4.0, cvar=-5.0, mdd_recovery_months=4, timestamp=TS,
    )
    assert out.grade == 4
    assert "cr02_max_applied" in out.triggered_conditions


# ── Pydantic 스키마 검증 ─────────────────────────────────────

def test_schema_extra_field_금지():
    """extra='forbid' — 정의되지 않은 필드 추가 시 ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RiskDetails(
            risk_type="test", grade_label="Low",
            weight_default=0.1, timestamp=TS,
            unknown_field="should_fail",  # type: ignore
        )

def test_schema_grade_범위_초과():
    """grade는 1~4만 허용 — 5 입력 시 ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RiskOutput(
            risk_id="RISK-A", grade=5, score=5,
            triggered_conditions=[], reason="test",
            details=RiskDetails(
                risk_type="market", grade_label="Low",
                weight_default=0.30, timestamp=TS,
            ),
        )

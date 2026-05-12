"""섹터 리스크 테스트 — Phase 2.

API 호출 없이 순수 계산 로직만 검증.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from layer2_indicator.sector_indicator import (
    sector_beta, sector_hv20, relative_strength, sector_mdd,
)
from layer3_risk.sector import evaluate, SectorOutput


# ── 헬퍼 ─────────────────────────────────────────────────────

def _series(values: list[float], start: str = "2025-01-01") -> pd.Series:
    dates = pd.bdate_range(start=start, periods=len(values))
    return pd.Series(values, index=dates, dtype=float)


def _market(n: int = 100, base: float = 100.0) -> pd.Series:
    """무작위성 없는 단조 상승 시장 시계열."""
    return _series([base + i * 0.5 for i in range(n)])


# ── sector_beta ───────────────────────────────────────────────

def test_beta_none_when_sector_none():
    assert sector_beta(None, _market()) is None

def test_beta_none_when_market_none():
    assert sector_beta(_market(), None) is None

def test_beta_none_when_insufficient_data():
    s = _series([100.0, 101.0])
    m = _series([100.0, 100.5])
    assert sector_beta(s, m) is None

def test_beta_1_when_identical_returns():
    """섹터 수익률 = 시장 수익률 → 베타 ≈ 1.0."""
    m = _market(80)
    result = sector_beta(m.copy(), m)
    assert result is not None
    assert abs(result - 1.0) < 0.01

def test_beta_2_when_double_returns():
    """섹터 수익률 = 시장 수익률 × 2 → 베타 ≈ 2.0."""
    # 수익률 기반으로 구성: sector_ret = 2 * market_ret → 베타 정확히 2.0
    m_rets = [0.01 if i % 2 == 0 else -0.008 for i in range(79)]
    m_vals = [100.0]
    for r in m_rets:
        m_vals.append(m_vals[-1] * (1 + r))
    s_vals = [100.0]
    for r in m_rets:
        s_vals.append(s_vals[-1] * (1 + 2 * r))
    m = _series(m_vals)
    s = _series(s_vals)
    result = sector_beta(s, m)
    assert result is not None
    assert abs(result - 2.0) < 0.01


# ── sector_hv20 ───────────────────────────────────────────────

def test_hv20_none_when_none():
    assert sector_hv20(None) is None

def test_hv20_none_when_insufficient():
    assert sector_hv20(_series([100.0] * 10)) is None

def test_hv20_zero_for_flat_series():
    """변동 없는 시계열 → HV20 = 0."""
    s = _series([100.0] * 30)
    result = sector_hv20(s)
    assert result is not None
    assert result == pytest.approx(0.0, abs=1e-8)

def test_hv20_positive_for_volatile_series():
    s = _series([100.0 * (1.0 + 0.02 * ((-1) ** i)) for i in range(30)])
    result = sector_hv20(s)
    assert result is not None
    assert result > 0


# ── relative_strength ─────────────────────────────────────────

def test_rs_none_when_none():
    assert relative_strength(None, _market()) is None

def test_rs_1_when_identical():
    """동일 시계열 → RS = 1.0."""
    m = _market(30)
    result = relative_strength(m.copy(), m)
    assert result is not None
    assert abs(result - 1.0) < 0.01

def test_rs_gt_1_when_sector_outperforms():
    """섹터가 시장보다 2배 상승 → RS > 1."""
    m = _series([100.0 + i for i in range(30)])
    s = _series([100.0 + i * 2 for i in range(30)])
    result = relative_strength(s, m)
    assert result is not None
    assert result > 1.0

def test_rs_lt_1_when_sector_underperforms():
    """섹터 수익률 0, 시장 상승 → RS < 1."""
    m = _series([100.0 + i for i in range(30)])
    s = _series([100.0] * 30)
    result = relative_strength(s, m)
    assert result is not None
    assert result < 1.0


# ── sector_mdd ────────────────────────────────────────────────

def test_mdd_none_when_none():
    assert sector_mdd(None) is None

def test_mdd_none_when_insufficient():
    assert sector_mdd(_series([100.0] * 30)) is None

def test_mdd_zero_for_monotone_up():
    """단조 상승 → MDD = 0."""
    s = _series([100.0 + i for i in range(70)])
    result = sector_mdd(s)
    assert result is not None
    assert result == pytest.approx(0.0, abs=1e-6)

def test_mdd_negative_for_declining():
    """고점 100 → 저점 80 → MDD = -20%."""
    vals = [100.0] * 10 + [80.0] * 50
    s = _series(vals)
    result = sector_mdd(s)
    assert result is not None
    assert result == pytest.approx(-20.0, abs=0.1)


# ── evaluate() ────────────────────────────────────────────────

def test_evaluate_no_data():
    """sector_close=None → data_available=False, grade=None."""
    out = evaluate(sector="반도체", sector_close=None, market_close=_market(100))
    assert isinstance(out, SectorOutput)
    assert out.data_available is False
    assert out.grade is None
    assert out.grade_label is None

def test_evaluate_low_beta():
    """베타 ≈ 0.5 (방어적) → Low(1)."""
    m = _series([100.0 + i for i in range(100)])
    s = _series([100.0 + i * 0.5 for i in range(100)])
    out = evaluate(sector="금융", sector_close=s, market_close=m)
    assert out.data_available is True
    assert out.grade == 1

def test_evaluate_medium_beta():
    """베타 ≈ 1.1 → Medium(2)."""
    m = _series([100.0 + i for i in range(100)])
    s = _series([100.0 + i * 1.1 for i in range(100)])
    out = evaluate(sector="자동차", sector_close=s, market_close=m)
    assert out.data_available is True
    assert out.grade == 2

def test_evaluate_high_beta():
    """베타 ≈ 1.4 → High(3)."""
    m = _series([100.0 + i for i in range(100)])
    s = _series([100.0 + i * 1.4 for i in range(100)])
    out = evaluate(sector="헬스케어", sector_close=s, market_close=m)
    assert out.data_available is True
    assert out.grade == 3

def test_evaluate_critical_beta_and_rs_weak():
    """베타 ≈ 1.6 + RS < 1.0 → Critical(4)."""
    # 수익률 기반 구성: sector_ret = 1.6 * market_ret - 0.005 (하락 편향)
    # → 베타 = 1.6 (공분산 불변), 섹터 누적 수익 < 시장 → RS < 1.0
    m_rets = [0.01 if i % 2 == 0 else -0.008 for i in range(99)]
    m_vals = [100.0]
    for r in m_rets:
        m_vals.append(m_vals[-1] * (1 + r))
    s_vals = [100.0]
    for r in m_rets:
        s_vals.append(s_vals[-1] * (1 + 1.6 * r - 0.005))
    m = _series(m_vals)
    s = _series(s_vals)
    out = evaluate(sector="에너지/화학", sector_close=s, market_close=m)
    assert out.data_available is True
    assert out.grade == 4

def test_evaluate_schema_no_extra_fields():
    """extra='forbid' — 정의되지 않은 필드 추가 시 ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SectorOutput(sector="테스트", unknown_field="fail")  # type: ignore

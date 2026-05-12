"""복합 시나리오 발동 테스트 — Skills.md §7 3E-3.

SCN-01 Capital Flight (EVT_01 + EVT_02)
SCN-02 Tightening Squeeze (EVT_03 + EVT_04)
SCN-03 Stagflation Alert (EVT_04 + EVT_02 + EVT_03)
SCN-04 Liquidity Crisis (EVT_01 + EVT_03 + EVT_02)

발동 시 macro_grade=4 강제 + scn04_flag 동작 검증.
"""

from __future__ import annotations

from layer3_risk.macro import evaluate

TS = "2026-04-30"

# 모든 이벤트 미발동 기저 입력값
_BASE: dict = dict(
    fx_rate=1200, base_rate_delta=0.0, rate_spread_curr=0.5,
    cpi_yoy=2.0, fi_monthly=1.0, m2_growth_curr=3.0,
    m2_contraction=False, m2_growth_slowdown=False,
    fx_daily_change=0.0, fx_weekly_change=0.0,
    fi_streak_sell=0, fi_streak_buy=0, fi_5d_cum=0.0,
    cpi_delta=0.0, rate_spread_prev=0.5, m2_expansion=False,
    timestamp=TS,
)


def _eval(**overrides):
    return evaluate(**{**_BASE, **overrides})


# ── 기저 상태 ────────────────────────────────────────────────

def test_기저_입력_안정():
    """모든 지표 안정 → macro_grade=1, 시나리오 없음."""
    out = _eval()
    assert out.grade == 1
    assert out.details.flags["triggered_scenario"] is None
    assert out.details.flags["scn04_flag"] is False


# ── SCN-01: Capital Flight ────────────────────────────────────

def test_scn01_자본유출_경고():
    """환율 급등(EVT_01) + 외국인 이탈(EVT_02) → SCN-01, grade=4."""
    out = _eval(
        fx_weekly_change=0.05,   # EVT_01: 주간 > 3%
        fi_streak_sell=6,        # EVT_02: 연속 순매도 >= 5일
        fi_5d_cum=-1.5,          # EVT_02: 5일 누적 < -1조
    )
    assert out.grade == 4
    assert out.details.flags["triggered_scenario"] == "SCN-01"
    assert out.details.flags["scn04_flag"] is False

def test_scn01_evt01_일간_급등():
    """일간 환율 급등(EVT_01 일간 조건) + 외국인 이탈 → SCN-01."""
    out = _eval(
        fx_daily_change=0.02,    # EVT_01: 일간 > 1.5%
        fi_streak_sell=6,
        fi_5d_cum=-1.5,
    )
    assert out.details.flags["triggered_scenario"] == "SCN-01"


# ── SCN-02: Tightening Squeeze ───────────────────────────────

def test_scn02_긴축_압력_경고():
    """금리 인상(EVT_03) + CPI 급등(EVT_04) → SCN-02, grade=4."""
    out = _eval(
        base_rate_delta=0.25,    # EVT_03: >= 0.25%p
        cpi_delta=0.5,           # EVT_04: >= 0.5%p
    )
    assert out.grade == 4
    assert out.details.flags["triggered_scenario"] == "SCN-02"
    assert out.details.flags["scn04_flag"] is False


# ── SCN-03: Stagflation Alert ────────────────────────────────

def test_scn03_스태그플레이션_경고():
    """CPI 급등(EVT_04) + 외국인 이탈(EVT_02) + 금리 인상(EVT_03) → SCN-03, grade=4."""
    out = _eval(
        cpi_delta=0.5,           # EVT_04
        fi_streak_sell=6,        # EVT_02
        fi_5d_cum=-1.5,          # EVT_02
        base_rate_delta=0.25,    # EVT_03
    )
    assert out.grade == 4
    assert out.details.flags["triggered_scenario"] == "SCN-03"
    assert out.details.flags["scn04_flag"] is False


# ── SCN-04: Liquidity Crisis ─────────────────────────────────

def test_scn04_유동성_위기_경고():
    """환율 급등(EVT_01) + 금리 인상(EVT_03) + 외국인 이탈(EVT_02) → SCN-04, grade=4."""
    out = _eval(
        fx_weekly_change=0.05,   # EVT_01
        base_rate_delta=0.25,    # EVT_03
        fi_streak_sell=6,        # EVT_02
        fi_5d_cum=-1.5,          # EVT_02
    )
    assert out.grade == 4
    assert out.details.flags["triggered_scenario"] == "SCN-04"
    assert out.details.flags["scn04_flag"] is True


# ── 우선순위 검증 ────────────────────────────────────────────

def test_우선순위_scn04_gt_scn01():
    """SCN-04 + SCN-01 동시 충족 → SCN-04 우선."""
    out = _eval(
        fx_weekly_change=0.05,   # EVT_01 (SCN-01, SCN-04 공통)
        fi_streak_sell=6,        # EVT_02 (SCN-01, SCN-04 공통)
        fi_5d_cum=-1.5,
        base_rate_delta=0.25,    # EVT_03 (SCN-04 추가 조건)
    )
    assert out.details.flags["triggered_scenario"] == "SCN-04"

def test_우선순위_scn03_gt_scn02():
    """SCN-03 + SCN-02 동시 충족 → SCN-03 우선."""
    out = _eval(
        base_rate_delta=0.25,    # EVT_03 (SCN-02, SCN-03 공통)
        cpi_delta=0.5,           # EVT_04 (SCN-02, SCN-03 공통)
        fi_streak_sell=6,        # EVT_02 (SCN-03 추가 조건)
        fi_5d_cum=-1.5,
    )
    assert out.details.flags["triggered_scenario"] == "SCN-03"

def test_우선순위_scn04_gt_scn03():
    """SCN-04 조건이 SCN-03보다 먼저 체크됨."""
    out = _eval(
        fx_weekly_change=0.05,   # EVT_01 (SCN-04)
        base_rate_delta=0.25,    # EVT_03 (SCN-04, SCN-03)
        fi_streak_sell=6,        # EVT_02 (SCN-04, SCN-03)
        fi_5d_cum=-1.5,
        cpi_delta=0.5,           # EVT_04 (SCN-03)
    )
    assert out.details.flags["triggered_scenario"] == "SCN-04"

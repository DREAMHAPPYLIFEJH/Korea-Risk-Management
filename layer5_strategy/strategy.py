"""전략 + 자산 배분 결정 — Skills.md §9 Layer 5.

6단계 결정 트리:
  Step 1: score_band → strategy + equity_ceiling 기본 매핑
  Step 2: OVR-03 — critical_count>=1 → 최소 Moderate_Defensive
  Step 3: OVR-04 — critical>=2 + score>2.5 → Defensive
  Step 4: OVR-02 연동 — critical>=1 → equity_ceiling -10%p
  Step 5: CR-03 — 하방+변동성 양쪽 Critical → 추가 -10%p / 양쪽 High 이상 → -5%p
  Step 6: prev_score_band 변경 시 → 전체 재산출 (호출자 책임)

자산 배분 (주식 / 채권 / 현금) 합계 100%. 본 모듈은 equity 결정 후 bond/cash 분배.
"""

from __future__ import annotations

from typing import Any

from config.constants import (
    EQUITY_CEILING_DEFAULT, EQUITY_MIN, STRATEGY_LEVEL,
)
from config.thresholds import (
    EQUITY_CEILING_CRITICAL_DROP,
    EQUITY_CEILING_DOUBLE_C_DROP,
    EQUITY_CEILING_DOUBLE_H_DROP,
)
from rules.override import apply_ovr03, apply_ovr04


# Skills.md §9 자산 배분 표 — bond/cash 중앙값 (equity 결정 후 분배)
BOND_CASH_MIDPOINTS = {
    "Aggressive":          (5,   5),     # 0-10 / 0-10 → mid 5/5
    "Moderate_Aggressive": (15,  15),
    "Moderate_Defensive":  (25,  30),
    "Defensive":           (35,  40),
    "Extreme_Defensive":   (25,  70),
}


def _band_to_strategy(score_band: str) -> tuple[str, int]:
    """Step 1 — score_band → 기본 strategy + equity_ceiling."""
    mapping = {
        "Safe":    "Aggressive",
        "Caution": "Moderate_Aggressive",
        "Alert":   "Moderate_Defensive",
        "Danger":  "Defensive",
        "Extreme": "Extreme_Defensive",
    }
    strategy = mapping[score_band]
    return strategy, EQUITY_CEILING_DEFAULT[strategy]


def _apply_cr03(
    strategy: str,
    equity_ceiling: int,
    downside_grade: int,
    volatility_grade: int,
) -> int:
    """Step 5 CR-03 — 하방+변동성 충돌 추가 조정."""
    if downside_grade == 4 and volatility_grade == 4:
        # 양쪽 Critical → 해당 전략 base_min에서 추가 -10%p
        equity_ceiling = EQUITY_MIN[strategy] - EQUITY_CEILING_DOUBLE_C_DROP
        equity_ceiling = max(equity_ceiling, 0)
    if volatility_grade >= 3 and downside_grade >= 3:
        equity_ceiling -= EQUITY_CEILING_DOUBLE_H_DROP
        equity_ceiling = max(equity_ceiling, 0)
    return equity_ceiling


def compute(
    *,
    score_band: str,
    integrated_score: float,
    critical_count: int,
    market_grade: int,
    volatility_grade: int,
    macro_grade: int,
    liquidity_grade: int,
    downside_grade: int,
) -> dict[str, Any]:
    """전략 + 자산 배분 결정 — Skills.md §9 Step 1~5 일괄 적용.

    Returns:
        {
            "strategy": str,
            "equity_ceiling": int,
            "allocation": {"equity": int, "bond": int, "cash": int},
        }
    """
    # Step 1: 기본 매핑
    strategy, equity_ceiling = _band_to_strategy(score_band)

    # Step 2: OVR-03
    strategy, equity_ceiling = apply_ovr03(strategy, equity_ceiling, critical_count)

    # Step 3: OVR-04
    strategy, equity_ceiling = apply_ovr04(
        strategy, equity_ceiling, critical_count, integrated_score
    )

    # Step 4: OVR-02 연동 — critical >= 1 → -10%p
    if critical_count >= 1:
        equity_ceiling -= EQUITY_CEILING_CRITICAL_DROP
        equity_ceiling = max(equity_ceiling, 0)

    # Step 5: CR-03
    equity_ceiling = _apply_cr03(strategy, equity_ceiling, downside_grade, volatility_grade)

    # 자산 배분 — bond/cash midpoint 기반
    bond_mid, cash_mid = BOND_CASH_MIDPOINTS[strategy]
    # equity가 결정됐으니 bond + cash = 100 - equity. midpoint 비율로 분배.
    remaining = 100 - equity_ceiling
    bond_cash_total = bond_mid + cash_mid
    if bond_cash_total > 0:
        bond = round(remaining * (bond_mid / bond_cash_total))
        cash = remaining - bond
    else:
        bond = 0
        cash = remaining

    return {
        "strategy":       strategy,
        "equity_ceiling": equity_ceiling,
        "allocation": {
            "equity": equity_ceiling,
            "bond":   bond,
            "cash":   cash,
        },
    }

"""Risk-A 시장 리스크 — Skills.md §7 Risk-A.

기본 가중치 30%.
4단계 명시적 IF/THEN + ELSE 복합 신호 집계 (sig_ma + sig_disp + sig_adx + sig_streak 최빈값).
- 1순위: ma_bearish_full + disp_ma20<90 + consec_decline>=5 → 4 Critical
- 2순위: ma_bearish_full + 90<=disp_ma20<94 → 3 High
- 3순위: ma_bearish_part + (94<=disp_ma20<98 OR adx<20) → 2 Medium
- 4순위: ma_bullish + 98<=disp_ma20<=102 + adx>25 → 1 Low
- ELSE: 4개 신호 등급 최빈값, 동점 시 MAX (보수적)
"""

from __future__ import annotations

from config.thresholds import (
    DISP_MA20_LOW_MIN, DISP_MA20_LOW_MAX, DISP_MA20_MEDIUM, DISP_MA20_HIGH,
    ADX_TREND, ADX_SIDEWAYS,
    CONSEC_DECLINE_CRITICAL, CONSEC_DECLINE_HIGH, CONSEC_DECLINE_MEDIUM,
)
from layer3_risk.schema import RiskOutput, RiskDetails, grade_label


RISK_ID = "RISK-A"
WEIGHT_DEFAULT = 0.30
CONFLICT_RULE = "none"
CONDITION_CANDIDATES = [
    "ma_bearish_full", "ma_bearish_part", "ma_bullish", "composite_signal",
    "disp_ma20_lt_90", "disp_ma20_lt_94", "disp_ma20_lt_98",
    "adx_lt_20", "adx_gte_25",
    "consec_decline_gte_5", "consec_decline_gte_10",
]


def _composite_signal(
    ma_bullish: bool, ma_bearish_full: bool, ma_bearish_part: bool,
    disp_ma20: float, adx: float, consec_decline: int,
) -> int:
    """ELSE 분기 — 4개 신호 등급의 최빈값, 동점 시 MAX."""
    # MA 배열
    if ma_bearish_full:   sig_ma = 4
    elif ma_bearish_part: sig_ma = 2
    elif ma_bullish:      sig_ma = 1
    else:                 sig_ma = 2

    # 이격도
    if disp_ma20 < DISP_MA20_HIGH:        sig_disp = 4
    elif disp_ma20 < DISP_MA20_MEDIUM:    sig_disp = 3
    elif disp_ma20 < DISP_MA20_LOW_MIN:   sig_disp = 2
    else:                                 sig_disp = 1

    # ADX (Skills.md: <20 횡보 / 20~25 전환 / >25 추세 확립)
    if adx < ADX_SIDEWAYS:    sig_adx = 2
    elif adx <= ADX_TREND:    sig_adx = 2
    else:                     sig_adx = 1

    # 연속 하락
    if consec_decline >= CONSEC_DECLINE_CRITICAL:  sig_streak = 4
    elif consec_decline >= CONSEC_DECLINE_HIGH:    sig_streak = 3
    elif consec_decline >= CONSEC_DECLINE_MEDIUM:  sig_streak = 2
    else:                                          sig_streak = 1

    # 최빈값 (동점 시 보수적 = MAX)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for g in (sig_ma, sig_disp, sig_adx, sig_streak):
        counts[g] += 1
    max_count = max(counts.values())
    candidates = [g for g, c in counts.items() if c == max_count]
    return max(candidates)


def evaluate(
    *,
    ma20: float, ma60: float, ma120: float,
    disp_ma20: float, disp_ma60: float,
    adx: float, consec_decline: int,
    timestamp: str,
) -> RiskOutput:
    """Risk-A 등급 산정."""
    ma_bullish = (ma20 > ma60) and (ma60 > ma120)
    ma_bearish_full = (ma20 < ma60) and (ma60 < ma120)
    ma_bearish_part = (ma20 < ma60)

    # ── 명시적 우선순위 평가 ──────────────────────────────
    if (ma_bearish_full and disp_ma20 < DISP_MA20_HIGH
            and consec_decline >= CONSEC_DECLINE_HIGH):
        market_grade = 4
    elif (ma_bearish_full
          and DISP_MA20_HIGH <= disp_ma20 < DISP_MA20_MEDIUM):
        market_grade = 3
    elif (ma_bearish_part
          and ((DISP_MA20_MEDIUM <= disp_ma20 < DISP_MA20_LOW_MIN)
               or adx < ADX_SIDEWAYS)):
        market_grade = 2
    elif (ma_bullish
          and DISP_MA20_LOW_MIN <= disp_ma20 <= DISP_MA20_LOW_MAX
          and adx > ADX_TREND):
        market_grade = 1
    else:
        market_grade = _composite_signal(
            ma_bullish, ma_bearish_full, ma_bearish_part,
            disp_ma20, adx, consec_decline,
        )

    # ── triggered_conditions ─────────────────────────────
    triggered: list[str] = []
    if ma_bearish_full:    triggered.append("ma_bearish_full")
    elif ma_bearish_part:  triggered.append("ma_bearish_part")
    elif ma_bullish:       triggered.append("ma_bullish")
    else:                  triggered.append("composite_signal")

    if disp_ma20 < DISP_MA20_HIGH:        triggered.append("disp_ma20_lt_90")
    elif disp_ma20 < DISP_MA20_MEDIUM:    triggered.append("disp_ma20_lt_94")
    elif disp_ma20 < DISP_MA20_LOW_MIN:   triggered.append("disp_ma20_lt_98")

    if adx < ADX_SIDEWAYS:   triggered.append("adx_lt_20")
    elif adx > ADX_TREND:    triggered.append("adx_gte_25")

    if consec_decline >= CONSEC_DECLINE_CRITICAL:  triggered.append("consec_decline_gte_10")
    elif consec_decline >= CONSEC_DECLINE_HIGH:    triggered.append("consec_decline_gte_5")

    return RiskOutput(
        risk_id=RISK_ID,
        grade=market_grade,
        score=market_grade,
        triggered_conditions=triggered,
        reason=f"market_risk grade={market_grade} based on " + ", ".join(triggered),
        details=RiskDetails(
            risk_type="market",
            grade_label=grade_label(market_grade),
            weight_default=WEIGHT_DEFAULT,
            timestamp=timestamp,
            indicators={
                "ma20":           ma20,
                "ma60":           ma60,
                "ma120":          ma120,
                "disp_ma20":      disp_ma20,
                "disp_ma60":      disp_ma60,
                "adx":            adx,
                "consec_decline": consec_decline,
            },
            sub_grades={},
            flags={
                "ma_bullish":      ma_bullish,
                "ma_bearish_part": ma_bearish_part,
                "ma_bearish_full": ma_bearish_full,
            },
            conflict_rule=CONFLICT_RULE,
            condition_candidates=CONDITION_CANDIDATES,
        ),
    )

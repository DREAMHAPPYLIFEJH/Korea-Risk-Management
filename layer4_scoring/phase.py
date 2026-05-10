"""시장 국면 판단 + 동적 가중치 — Skills.md §8 Layer 4.

bullish:  ma_bullish AND adx > 25            → 기본 가중치
bearish:  ma_bearish_full AND consec_decline >= 3 → 하락장 가중치
sideways: adx < 20 OR ma_converging          → 횡보장 가중치
ELSE: 기본 가중치(bullish) 적용

CR-05 (Skills.md §12): bearish + sideways 충돌 시 bearish 우선.
"""

from __future__ import annotations

from config.thresholds import (
    ADX_TREND, ADX_SIDEWAYS, BEARISH_CONSEC_DECLINE, WEIGHTS,
)


def determine_phase(
    *,
    ma_bullish: bool,
    ma_bearish_full: bool,
    ma_converging: bool,
    adx: float,
    consec_decline: int,
) -> str:
    """시장 국면 판단 → "bullish" / "bearish" / "sideways"."""
    bearish = ma_bearish_full and (consec_decline >= BEARISH_CONSEC_DECLINE)
    sideways = (adx < ADX_SIDEWAYS) or ma_converging
    bullish = ma_bullish and (adx > ADX_TREND)

    # CR-05: bearish + sideways 충돌 → bearish 우선
    if bearish:
        return "bearish"
    if bullish:
        return "bullish"
    if sideways:
        return "sideways"
    return "bullish"   # 기본값 (조건 미충족 시)


def select_weights(phase: str) -> dict[str, float]:
    """국면별 가중치 (Skills.md §8 가중치 테이블).

    Returns dict {market, volatility, macro, liquidity, downside}.
    """
    return dict(WEIGHTS[phase])

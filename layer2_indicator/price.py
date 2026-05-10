"""가격/추세 지표 — Skills.md §6 Layer 2.

- moving_average(close, window): MA20/60/120 단순 이동평균
- disparity(close, window): 이격도 = close / MA × 100
- consec_decline(close): close_t < close_{t-1} 연속 일수
- adx(high, low, close, period=14): Wilder 방식 ADX
- wilder_rma(series, period): Wilder 평활 (alpha = 1/period)

함수 시그니처는 모두 (Series, ...) → Series 형태로 통일.
NaN warm-up: rolling은 window 미충족 시 NaN, ewm은 첫 값부터 산출.
"""

from __future__ import annotations

import pandas as pd


def moving_average(close: pd.Series, window: int) -> pd.Series:
    """단순 이동평균 (Skills.md §6: MA = Σ(close_t) / N)."""
    return close.rolling(window=window, min_periods=window).mean()


def disparity(close: pd.Series, window: int) -> pd.Series:
    """이격도 (%) (Skills.md §6: (close / MA_n) × 100)."""
    ma = moving_average(close, window)
    return (close / ma) * 100.0


def consec_decline(close: pd.Series) -> pd.Series:
    """연속 하락 일수 (Skills.md §6: close_t < close_{t-1} 연속).

    당일이 상승·보합이면 0으로 리셋되는 streak 카운트.
    """
    diffs = close.diff()
    is_dec = (diffs < 0).astype(int)
    # 비하락 일을 그룹 경계로 사용 → 각 그룹 내에서 누적합 = 그 시점까지의 연속 하락 일수
    groups = (is_dec == 0).cumsum()
    return is_dec.groupby(groups).cumsum().astype(int)


def wilder_rma(s: pd.Series, period: int) -> pd.Series:
    """Wilder 평활 이동평균 (alpha = 1/period).

    재귀식: RMA_t = ((period-1) × RMA_{t-1} + value_t) / period.
    pandas ewm(alpha=1/p, adjust=False)와 동일.
    """
    return s.ewm(alpha=1.0 / period, adjust=False).mean()


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average Directional Index — Wilder 방식 (Skills.md §6).

    절차:
      1. True Range = max(H-L, |H - prev_C|, |L - prev_C|)
      2. +DM = up if (up > dn AND up > 0) else 0
         -DM = dn if (dn > up AND dn > 0) else 0
         (up = H - prev_H, dn = prev_L - L)
      3. ATR / +DM / -DM 각각 Wilder 평활 (period)
      4. +DI = 100 × smoothed(+DM) / ATR, -DI 동일
      5. DX = 100 × |+DI - -DI| / (+DI + -DI)
      6. ADX = Wilder 평활(DX, period)
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    up = high.diff()
    dn = -low.diff()  # = prev_low - low
    plus_dm = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)

    atr = wilder_rma(tr, period)
    plus_di = 100.0 * wilder_rma(plus_dm, period) / atr
    minus_di = 100.0 * wilder_rma(minus_dm, period) / atr

    di_sum = plus_di + minus_di
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum.where(di_sum != 0)
    return wilder_rma(dx, period).rename("adx")

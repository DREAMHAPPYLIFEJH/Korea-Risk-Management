"""유동성 지표 — Skills.md §6 Layer 2.

- vol_ratio(volume): 거래량 비율 = current / MA20
- val_ratio(value): 거래대금 비율 = current / MA20
- vol_streak(volume): vol_ratio < 1.0 연속 일수
- conc_ratio: top10 거래대금 / 전체 거래대금 — Phase 1 보류 (종목별 데이터 추가 수집 필요)

conc_ratio 보류 이유: KOSPI 지수 OHLCV(키움 ka20006)는 시장 전체 합산이라
종목별 비중 산출 불가. 추후 ka10032(거래대금상위) 등 추가 호출 시 산출 가능.
"""

from __future__ import annotations

import pandas as pd


def vol_ratio(volume: pd.Series, window: int = 20) -> pd.Series:
    """거래량 비율 (Skills.md §6: current_volume / MA20_volume).

    < 0.7: 유동성 축소 / < 0.5: 심각 / < 1.0: 평균 이하.
    """
    ma = volume.rolling(window=window, min_periods=window).mean()
    return (volume / ma).rename("vol_ratio")


def val_ratio(value: pd.Series, window: int = 20) -> pd.Series:
    """거래대금 비율 (Skills.md §6: current_value / MA20_value).

    < 0.6: 경계 (Risk-C 최소 Medium 보정 트리거).
    """
    ma = value.rolling(window=window, min_periods=window).mean()
    return (value / ma).rename("val_ratio")


def vol_streak(volume: pd.Series, window: int = 20) -> pd.Series:
    """vol_ratio < 1.0 연속 일수 (Skills.md §6).

    당일 vol_ratio ≥ 1.0이면 0으로 리셋되는 streak.
    Risk-C: 3일 이상 → High 트리거 / 5일 이상 → Critical 트리거.
    """
    vr = vol_ratio(volume, window)
    is_low = (vr < 1.0).astype(int)
    groups = (is_low == 0).cumsum()
    return is_low.groupby(groups).cumsum().astype(int).rename("vol_streak")

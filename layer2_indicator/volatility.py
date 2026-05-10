"""변동성 지표 — Skills.md §6 Layer 2.

- log_returns(close): 일별 로그 수익률 ln(close_t / close_{t-1})
- historical_volatility(close, window): σ × √252, 연율화 % 단위
- hv_ratio(hv_short, hv_long): HV20 / HV60 비율

VKOSPI는 외부 데이터 (Phase 1 보류) — 별도 fetcher 도입 후 합류.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


def log_returns(close: pd.Series) -> pd.Series:
    """일별 로그 수익률 (Skills.md §6: log(close_t / close_{t-1}))."""
    return np.log(close / close.shift(1))


def historical_volatility(close: pd.Series, window: int) -> pd.Series:
    """역사적 변동성 — 연율화 (%) (Skills.md §6).

    σ_annual = σ(log_returns, window) × √252 × 100.
    출력 단위: % (예: 15.5 = 연 15.5%).
    """
    r = log_returns(close)
    return r.rolling(window=window, min_periods=window).std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100.0


def hv_ratio(hv_short: pd.Series, hv_long: pd.Series) -> pd.Series:
    """HV 비율 (Skills.md §6: hv20 / hv60).

    > 1.2: 변동성 급등 / < 0.8: 변동성 축소.
    """
    return (hv_short / hv_long).rename("vol_ratio_hv")

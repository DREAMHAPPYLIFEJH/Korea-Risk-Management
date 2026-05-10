"""하방 리스크 지표 — Skills.md §6 Layer 2.

- mdd(close, window): 윈도우 내 최저-최고 비율 (단순 정의, Skills.md §6 그대로)
- var_95(close, window): 일별 수익률 5% 분위수 (Historical VaR)
- cvar_95(close, window): VaR 초과 손실의 조건부 평균

mdd 정의 주의: Skills.md §6은 (MIN(window) - MAX(window)) / MAX(window) × 100.
시간 순서를 고려한 peak-to-trough 정의가 아님 — 단순 윈도우 최저/최고 비율.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mdd(close: pd.Series, window: int) -> pd.Series:
    """Maximum Drawdown (%) — Skills.md §6 정의.

    (rolling_min − rolling_max) / rolling_max × 100.
    음수값 (예: -15.0 = 윈도우 내 최저점이 최고점 대비 15% 하락).
    """
    rolling_max = close.rolling(window=window, min_periods=window).max()
    rolling_min = close.rolling(window=window, min_periods=window).min()
    return ((rolling_min - rolling_max) / rolling_max * 100.0).rename(f"mdd_{window}")


def var_95(close: pd.Series, window: int = 252) -> pd.Series:
    """Value at Risk 95% (1일) — Historical Simulation 방식 (Skills.md §6).

    일별 simple return 분포의 5% 분위수 → %.
    예: -2.5 = "95% 확률로 1일 손실이 2.5% 이내".
    """
    returns = close.pct_change()
    return (
        returns.rolling(window=window, min_periods=window).quantile(0.05) * 100.0
    ).rename("var_95")


def cvar_95(close: pd.Series, window: int = 252) -> pd.Series:
    """Conditional VaR (Expected Shortfall) — Skills.md §6.

    VaR 초과 손실의 조건부 평균 → %.
    일반적으로 VaR의 1.3 ~ 1.5배 절댓값.
    """
    returns = close.pct_change()

    def _cond_mean(arr: np.ndarray) -> float:
        threshold = np.quantile(arr, 0.05)
        tail = arr[arr <= threshold]
        return float(np.mean(tail)) if tail.size > 0 else np.nan

    return (
        returns.rolling(window=window, min_periods=window).apply(_cond_mean, raw=True)
        * 100.0
    ).rename("cvar_95")

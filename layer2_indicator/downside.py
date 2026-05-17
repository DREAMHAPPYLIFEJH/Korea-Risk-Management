"""하방 리스크 지표 — Skills.md §6 Layer 2.

Legacy (historical, Skills.md §6):
- mdd(close, window): 윈도우 내 최저-최고 비율
- var_95(close, window): 일별 수익률 5% 분위수 (Historical VaR)
- cvar_95(close, window): VaR 초과 손실의 조건부 평균

MC 기반 (forward-looking, Skills.md 갱신 예정 task #9):
- mc_mdd_percentiles(paths): 각 경로의 peak-to-trough MDD 분포 → p5/p50/p95
- mc_var_cvar_1d(paths): MC 1일 수익률 분포에서 VaR95/CVaR95

mdd() 정의 주의: Skills.md §6은 (MIN(window) - MAX(window)) / MAX(window) × 100.
시간 순서를 고려한 peak-to-trough 정의가 아님 — 단순 윈도우 최저/최고 비율.
MC 기반은 정상적인 peak-to-trough MDD를 측정.
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


# ─────────────────────────────────────────────────────────────
# MC 기반 forward-looking 메트릭
# ─────────────────────────────────────────────────────────────


def mc_mdd_percentiles(paths: np.ndarray) -> dict[str, float]:
    """각 경로의 peak-to-trough MDD 분포 → percentile dict (%).

    paths: shape (n_paths, horizon+1), monte_carlo.simulate_paths() 출력.

    반환:
        {"p5": -X.X, "p50": -X.X, "p95": -X.X, "mean": -X.X}
        각 값은 음수 % (예: -8.5 = "60일 동안 고점 대비 평균 8.5% 하락").
    """
    if paths.ndim != 2 or paths.shape[1] < 2:
        raise ValueError(f"mc_mdd_percentiles: bad paths shape {paths.shape}")

    running_max = np.maximum.accumulate(paths, axis=1)
    drawdown = (paths - running_max) / running_max  # ≤ 0
    mdd_per_path = drawdown.min(axis=1) * 100.0     # 각 경로의 최저 drawdown (%)
    return {
        "p5":   float(np.percentile(mdd_per_path, 5)),
        "p50":  float(np.percentile(mdd_per_path, 50)),
        "p95":  float(np.percentile(mdd_per_path, 95)),
        "mean": float(mdd_per_path.mean()),
    }


def mc_var_cvar_1d(paths: np.ndarray, alpha: float = 0.05) -> dict[str, float]:
    """MC 1일 수익률 분포에서 VaR/CVaR (%).

    paths[:, 1] / paths[:, 0] - 1 → 1일 simple return 분포 → 하단 alpha 분위.

    반환:
        {"var": -X.X, "cvar": -X.X} (음수 %, 예: -2.5 = "95% 확률 1일 손실 ≤ 2.5%").
    """
    if paths.ndim != 2 or paths.shape[1] < 2:
        raise ValueError(f"mc_var_cvar_1d: bad paths shape {paths.shape}")

    day1_ret = (paths[:, 1] / paths[:, 0] - 1.0) * 100.0
    var = float(np.percentile(day1_ret, alpha * 100))
    tail = day1_ret[day1_ret <= var]
    cvar = float(tail.mean()) if tail.size > 0 else var
    return {"var": var, "cvar": cvar}

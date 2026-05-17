"""Monte Carlo 가격 경로 시뮬레이션 — Risk-D MC 기반 지표용.

simulate_paths(close, horizon, n_paths, method, seed) → ndarray(n_paths, horizon+1).
시작점은 close.iloc[-1], log-return 기반.

method:
  'bootstrap'  — 과거 일별 로그수익률을 비복원 없이 재샘플링 (모수 가정 0)
  'student_t'  — Student's t(df=auto)에서 IID 샘플링 (fat tail 보존)
  'garch'      — GARCH(1,1) 조건부 변동성 시뮬레이션 (volatility clustering 반영)

Phase 1 구현: 'bootstrap' 우선. 나머지는 task #7에서 추가.
Skills.md 갱신은 task #9에서 처리 — 현재는 코드 상 사양.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.constants import MC_LOOKBACK_DAYS, MC_METHOD, MC_N_PATHS, MC_SEED


def simulate_paths(
    close: pd.Series,
    horizon: int,
    n_paths: int = MC_N_PATHS,
    method: str = MC_METHOD,
    seed: int | None = MC_SEED,
    lookback: int = MC_LOOKBACK_DAYS,
) -> np.ndarray:
    """현재가에서 시작하는 n_paths개의 가격 경로 (horizon+1 길이) 생성.

    Returns:
        ndarray shape (n_paths, horizon+1). [:, 0] == close.iloc[-1].

    Raises:
        ValueError: close에 유효한 수익률이 부족하거나 method가 미지원일 때.
    """
    if len(close) < 2:
        raise ValueError(f"simulate_paths: close too short (n={len(close)})")

    start_price = float(close.iloc[-1])
    log_returns = np.log(close / close.shift(1)).dropna().to_numpy()
    if lookback and len(log_returns) > lookback:
        log_returns = log_returns[-lookback:]
    if len(log_returns) < 30:
        raise ValueError(
            f"simulate_paths: insufficient returns for MC (n={len(log_returns)})"
        )

    if method == "bootstrap":
        return _simulate_bootstrap(start_price, log_returns, horizon, n_paths, seed)
    if method == "student_t":
        return _simulate_student_t(start_price, log_returns, horizon, n_paths, seed)
    if method == "garch":
        return _simulate_garch(start_price, log_returns, horizon, n_paths, seed)
    raise ValueError(f"simulate_paths: unknown method '{method}'")


def _simulate_bootstrap(
    start_price: float,
    log_returns: np.ndarray,
    horizon: int,
    n_paths: int,
    seed: int | None,
) -> np.ndarray:
    """과거 로그수익률을 복원추출로 재샘플링 (Historical bootstrap).

    모수 가정 0 — 과거 분포 모양 (fat tail, skewness) 그대로 보존.
    한계: 과거에 없던 극단치는 생성 불가, 시계열 의존성 무시.
    """
    rng = np.random.default_rng(seed)
    sampled = rng.choice(log_returns, size=(n_paths, horizon), replace=True)
    cum_log = np.cumsum(sampled, axis=1)
    paths = np.empty((n_paths, horizon + 1), dtype=np.float64)
    paths[:, 0] = start_price
    paths[:, 1:] = start_price * np.exp(cum_log)
    return paths


def _simulate_student_t(
    start_price: float,
    log_returns: np.ndarray,
    horizon: int,
    n_paths: int,
    seed: int | None,
) -> np.ndarray:
    """Student's t 분포에서 IID 샘플링.

    scipy.stats.t.fit으로 (df, loc, scale) MLE 추정 후 동일 분포에서 재샘플링.
    KOSPI 일별 로그수익률은 경험적으로 df 4~6 정도 — fat tail 보존.
    한계: bootstrap과 마찬가지로 IID 가정 (volatility clustering 무시).
    """
    from scipy import stats

    df, loc, scale = stats.t.fit(log_returns)
    rng = np.random.default_rng(seed)
    samples = stats.t.rvs(
        df, loc=loc, scale=scale, size=(n_paths, horizon), random_state=rng
    )
    cum_log = np.cumsum(samples, axis=1)
    paths = np.empty((n_paths, horizon + 1), dtype=np.float64)
    paths[:, 0] = start_price
    paths[:, 1:] = start_price * np.exp(cum_log)
    return paths


def mc_mdd_p50_series(
    close: pd.Series,
    horizon: int = 60,
    n_paths: int = 2_000,
    method: str = "bootstrap",
    seed: int | None = MC_SEED,
    lookback: int = MC_LOOKBACK_DAYS,
    min_history: int = 60,
) -> pd.Series:
    """과거 매 영업일마다 MC p50 MDD를 계산한 시계열.

    시각화 전용 — n_paths 기본값을 2,000으로 낮춰 속도 최적화 (p50은 빠르게 수렴).
    각 시점 t에서 close[:t]까지의 데이터로 MC를 돌려 forward horizon MDD의 중위값 반환.

    min_history 영업일 미만은 NaN.
    """
    from layer2_indicator.downside import mc_mdd_percentiles

    out: dict = {}
    for i in range(len(close)):
        if i < min_history:
            out[close.index[i]] = float("nan")
            continue
        sub = close.iloc[: i + 1]
        try:
            paths = simulate_paths(
                sub, horizon=horizon, n_paths=n_paths,
                method=method, seed=seed, lookback=lookback,
            )
            out[close.index[i]] = mc_mdd_percentiles(paths)["p50"]
        except (ValueError, RuntimeError):
            out[close.index[i]] = float("nan")
    return pd.Series(out, name=f"mdd_{horizon}_mc_p50")


def _simulate_garch(
    start_price: float,
    log_returns: np.ndarray,
    horizon: int,
    n_paths: int,
    seed: int | None,
) -> np.ndarray:
    """GARCH(1,1) 조건부 변동성 시뮬레이션.

    σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}

    arch 패키지로 GARCH(1,1) 적합 (mean='Zero', dist='normal') 후
    추정된 (ω, α, β)와 최종 조건부 분산을 시작점으로 forward simulation.
    Volatility clustering 반영 — 큰 변동 다음 큰 변동이 나오는 패턴 모델링.
    """
    from arch import arch_model

    # arch는 % 단위 수익률 권장 → ×100 후 다시 환원
    returns_pct = log_returns * 100.0
    am = arch_model(returns_pct, vol="Garch", p=1, q=1, mean="Zero", dist="normal")
    res = am.fit(disp="off", show_warning=False)

    omega = float(res.params["omega"])
    alpha = float(res.params["alpha[1]"])
    beta  = float(res.params["beta[1]"])
    cv = res.conditional_volatility
    last_cv = cv.iloc[-1] if hasattr(cv, "iloc") else cv[-1]
    sigma2_init = float(last_cv ** 2)

    rng = np.random.default_rng(seed)
    paths = np.empty((n_paths, horizon + 1), dtype=np.float64)
    paths[:, 0] = start_price

    sigma2 = np.full(n_paths, sigma2_init, dtype=np.float64)
    log_price = np.full(n_paths, np.log(start_price), dtype=np.float64)

    for t in range(horizon):
        eps_pct = rng.standard_normal(n_paths) * np.sqrt(sigma2)  # % 단위 innovation
        log_price = log_price + eps_pct / 100.0                   # decimal 환원 후 누적
        paths[:, t + 1] = np.exp(log_price)
        sigma2 = omega + alpha * eps_pct**2 + beta * sigma2

    return paths

"""섹터 리스크 지표 계산 — Phase 2 (PDF §4.2).

sector_close / market_close가 None이거나 데이터 부족이면 None 반환.
모든 함수는 순수 계산 — 외부 의존성 없음.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from config.thresholds import SECTOR_BETA_WINDOW, SECTOR_RS_WINDOW


def sector_beta(
    sector_close: pd.Series,
    market_close: pd.Series,
    window: int = SECTOR_BETA_WINDOW,
) -> float | None:
    """업종 베타 — Cov(섹터 수익률, 시장 수익률) / Var(시장 수익률).

    최근 window 영업일 기준. 데이터 부족(< 20일) 시 None.
    """
    if sector_close is None or market_close is None:
        return None

    s_ret = sector_close.pct_change().dropna()
    m_ret = market_close.pct_change().dropna()
    aligned = pd.concat([s_ret, m_ret], axis=1).dropna().tail(window)

    if len(aligned) < 20:
        return None

    cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    var = aligned.iloc[:, 1].var()
    if var == 0 or np.isnan(var):
        return None
    return float(cov / var)


def sector_hv20(sector_close: pd.Series) -> float | None:
    """업종 역사적 변동성 HV20 (연율화 %).

    Phase 1 hv20과 동일 공식. 데이터 부족 시 None.
    """
    if sector_close is None or len(sector_close) < 21:
        return None
    returns = sector_close.pct_change().dropna().tail(20)
    return float(returns.std() * (252 ** 0.5) * 100)


def relative_strength(
    sector_close: pd.Series,
    market_close: pd.Series,
    window: int = SECTOR_RS_WINDOW,
) -> float | None:
    """상대 강도 — 섹터 누적 수익률 / 시장 누적 수익률 (최근 window일).

    RS > 1.0: 시장 대비 강세 / RS < 1.0: 시장 대비 약세.
    """
    if sector_close is None or market_close is None:
        return None

    common_idx = sector_close.index.intersection(market_close.index)
    if len(common_idx) < window + 1:
        return None

    s = sector_close.reindex(common_idx).tail(window + 1)
    m = market_close.reindex(common_idx).tail(window + 1)

    s_ret = (s.iloc[-1] / s.iloc[0]) - 1
    m_ret = (m.iloc[-1] / m.iloc[0]) - 1

    if abs(m_ret) < 1e-8:
        return None
    return float(s_ret / m_ret)


def sector_mdd(sector_close: pd.Series, window: int = 60) -> float | None:
    """업종 MDD (최근 window 영업일, %).

    Phase 1 mdd_60과 동일 공식.
    """
    if sector_close is None or len(sector_close) < window:
        return None
    s = sector_close.tail(window)
    peak = s.expanding().max()
    drawdown = (s - peak) / peak * 100
    return float(drawdown.min())

"""S&P500 시장 데이터 수집 — Phase 3 / Phase 5.

yfinance 기반:
- get_sp500_ohlcv : ^GSPC 일별 OHLCV
- get_vix         : ^VIX 일별 종가 (VKOSPI 대응)
- get_vvix        : ^VVIX 일별 종가 (Phase 5 — VIX의 변동성, 조기경보)
- get_skew        : ^SKEW 일별 종가 (Phase 5 — 꼬리 리스크)
- get_dxy         : DX-Y.NYB 일별 종가 (달러 인덱스)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from config.constants import (
    US_MARKET_TICKER, US_VIX_TICKER, US_VVIX_TICKER, US_SKEW_TICKER, US_DXY_TICKER,
)


def _download(ticker: str, start: str, end: str) -> pd.DataFrame:
    """yfinance 다운로드 공통 헬퍼. start/end: YYYYMMDD."""
    s = datetime.strptime(start, "%Y%m%d").strftime("%Y-%m-%d")
    e = datetime.strptime(end,   "%Y%m%d").strftime("%Y-%m-%d")
    df = yf.download(ticker, start=s, end=e, progress=False, auto_adjust=True)
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df


def get_sp500_ohlcv(start: str, end: str) -> pd.DataFrame:
    """S&P500 일별 OHLCV — yfinance ^GSPC.

    start, end: YYYYMMDD.
    Returns DataFrame(open, high, low, close, volume) indexed by date.
    """
    df = _download(US_MARKET_TICKER, start, end)
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                  for c in df.columns]
    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    return df[cols]


def get_vix(start: str, end: str) -> pd.Series:
    """VIX 일별 종가 — yfinance ^VIX.

    Returns Series indexed by date, or empty Series on failure.
    """
    df = _download(US_VIX_TICKER, start, end)
    if df.empty:
        return pd.Series(name="vix", dtype=float)
    close_col = [c for c in df.columns if "close" in str(c).lower()]
    if not close_col:
        return pd.Series(name="vix", dtype=float)
    return df[close_col[0]].rename("vix")


def get_vvix(start: str, end: str) -> pd.Series:
    """VVIX 일별 종가 — yfinance ^VVIX (Phase 5).

    Returns Series indexed by date, or empty Series on failure.
    """
    df = _download(US_VVIX_TICKER, start, end)
    if df.empty:
        return pd.Series(name="vvix", dtype=float)
    close_col = [c for c in df.columns if "close" in str(c).lower()]
    if not close_col:
        return pd.Series(name="vvix", dtype=float)
    return df[close_col[0]].rename("vvix")


def get_skew(start: str, end: str) -> pd.Series:
    """SKEW 일별 종가 — yfinance ^SKEW (Phase 5).

    Returns Series indexed by date, or empty Series on failure.
    """
    df = _download(US_SKEW_TICKER, start, end)
    if df.empty:
        return pd.Series(name="skew", dtype=float)
    close_col = [c for c in df.columns if "close" in str(c).lower()]
    if not close_col:
        return pd.Series(name="skew", dtype=float)
    return df[close_col[0]].rename("skew")


def get_dxy(start: str, end: str) -> pd.Series:
    """달러 인덱스 일별 종가 — yfinance DX-Y.NYB.

    Returns Series indexed by date, or empty Series on failure.
    """
    df = _download(US_DXY_TICKER, start, end)
    if df.empty:
        return pd.Series(name="dxy", dtype=float)
    close_col = [c for c in df.columns if "close" in str(c).lower()]
    if not close_col:
        return pd.Series(name="dxy", dtype=float)
    return df[close_col[0]].rename("dxy")


def get_sp500_fundamental() -> dict | None:
    """S&P 500 PER/PBR 현재값 — SPY ETF 근사 (Phase 4, 표시 전용).

    지수(^GSPC)는 yfinance에 PE/PB가 없어 SPY ETF info로 근사. 시계열 미제공 — 현재값만.
    Returns {"per", "pbr"} 또는 조회 실패 시 None.
    """
    try:
        info = yf.Ticker("SPY").info
        per = info.get("trailingPE")
        pbr = info.get("priceToBook")
    except Exception:
        return None
    if per is None and pbr is None:
        return None
    return {"per": per, "pbr": pbr}

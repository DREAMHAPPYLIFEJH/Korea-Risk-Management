"""
데이터 정제 — Skills.md §5 Layer 1 정제 로직.

- Forward Fill (공휴일/비영업일/API 실패 시 전일 값 유지)
- 3σ 이상값 탐지 + rolling mean 대체 + outlier_flag
- 영업일 캘린더 정합 (이종 데이터 → 일별 인덱스 통일, 월별→일별 ffill)
- Min-Max 정규화 (점수 비교 시 선택적 적용)

API 실패 케이스: fetcher가 NaN 또는 결측을 반환하면 forward_fill로 자동 처리.
"""

from __future__ import annotations

import pandas as pd

from config.thresholds import OUTLIER_SIGMA


def forward_fill(s: pd.Series) -> pd.Series:
    """결측값 forward fill — 공휴일/비영업일/API 실패 처리."""
    return s.ffill()


def detect_and_replace_outliers(
    s: pd.Series,
    window: int = 20,
    sigma: float = OUTLIER_SIGMA,
) -> tuple[pd.Series, pd.Series]:
    """3σ 이상값 탐지 + rolling mean 대체.

    조건: ABS(value − rolling_mean) > sigma × rolling_std (Skills.md §5).
    초기 window 미만 구간은 rolling_std가 NaN/0이 되어 false로 처리됨.

    Returns (cleaned_series, outlier_flag_series).
    """
    rolling_mean = s.rolling(window=window, min_periods=1).mean()
    rolling_std = s.rolling(window=window, min_periods=2).std()

    deviation = (s - rolling_mean).abs()
    is_outlier = (deviation > sigma * rolling_std).fillna(False)

    cleaned = s.where(~is_outlier, rolling_mean)
    return cleaned, is_outlier


def align_to_business_days(
    s: pd.Series,
    start: str,
    end: str,
    method: str | None = "ffill",
) -> pd.Series:
    """영업일 캘린더(Mon–Fri)에 정합. 결측은 ffill.

    월별 시리즈(CPI/M2 등)도 같은 인덱스로 확장 — 해당 월 동안 동일 값 유지.
    한국 공휴일은 별도 처리하지 않음 (입력 데이터에 이미 반영되어 있다고 가정).
    """
    business_days = pd.bdate_range(start=start, end=end)
    aligned = s.reindex(business_days, method=method)
    aligned.index.name = "date"
    return aligned


def min_max_normalize(s: pd.Series) -> pd.Series:
    """Min-Max 정규화 → [0, 1]. 점수 비교 시 선택적 사용."""
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mn == mx:
        return pd.Series(0.0, index=s.index, name=s.name)
    return (s - mn) / (mx - mn)


def clean_series(
    s: pd.Series,
    start: str | None = None,
    end: str | None = None,
    window: int = 20,
    sigma: float = OUTLIER_SIGMA,
) -> tuple[pd.Series, pd.Series]:
    """단일 시리즈 전체 정제 파이프라인.

    1. Forward Fill
    2. 3σ 이상값 → rolling mean 대체 + flag
    3. (start, end 지정 시) 영업일 캘린더 정합

    Returns (cleaned, outlier_flag).
    """
    s = forward_fill(s)
    cleaned, flag = detect_and_replace_outliers(s, window=window, sigma=sigma)
    if start and end:
        cleaned = align_to_business_days(cleaned, start, end)
        flag = align_to_business_days(flag.astype(int), start, end).fillna(0).astype(bool)
    return cleaned, flag


def clean_dataframe(
    df: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
    window: int = 20,
    sigma: float = OUTLIER_SIGMA,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """DataFrame 전체 정제 (각 컬럼에 clean_series 적용).

    KOSPI OHLCV 같은 다중 컬럼 정제용.

    Returns (cleaned_df, outlier_flag_df).
    """
    cleaned_cols = {}
    flag_cols = {}
    for col in df.columns:
        c, f = clean_series(df[col], start=start, end=end, window=window, sigma=sigma)
        cleaned_cols[col] = c
        flag_cols[col] = f
    cleaned = pd.DataFrame(cleaned_cols)
    flags = pd.DataFrame(flag_cols)
    return cleaned, flags

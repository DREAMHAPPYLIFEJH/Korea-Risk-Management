"""FRED (Federal Reserve Economic Data) 매크로 데이터 수집 — Phase 3.

FRED_API_KEY 미설정 시 모든 메서드가 None 반환 (VKOSPI 보류와 동일 패턴).
API키 설정 후 자동 활성화.

발급: https://fred.stlouisfed.org/docs/api/api_key.html (무료)
"""

from __future__ import annotations

import os

import pandas as pd
import requests
from dotenv import load_dotenv
from pathlib import Path

from config.constants import FRED_SERIES

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


class FredClient:
    """FRED REST API 클라이언트.

    API키 없으면 get_* 메서드 전부 None 반환.
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("FRED_API_KEY")

    def _available(self) -> bool:
        return bool(self.api_key)

    def _fetch(self, series_id: str, start: str, end: str) -> pd.Series | None:
        """FRED 시리즈 조회. start/end: YYYYMMDD → YYYY-MM-DD 변환."""
        if not self._available():
            return None
        s = f"{start[:4]}-{start[4:6]}-{start[6:]}"
        e = f"{end[:4]}-{end[4:6]}-{end[6:]}"
        params = {
            "series_id":         series_id,
            "api_key":           self.api_key,
            "observation_start": s,
            "observation_end":   e,
            "file_type":         "json",
        }
        try:
            r = requests.get(_FRED_BASE, params=params, timeout=15)
            r.raise_for_status()
            obs = r.json().get("observations", [])
        except Exception:
            return None

        records = {}
        for o in obs:
            try:
                val = float(o["value"])
                records[pd.Timestamp(o["date"])] = val
            except (ValueError, KeyError):
                continue

        if not records:
            return None
        s_out = pd.Series(records, name=series_id)
        s_out.index.name = "date"
        return s_out.sort_index()

    def get_fed_rate(self, start: str, end: str) -> pd.Series | None:
        """연준 기준금리 (FEDFUNDS, 월별 %)."""
        return self._fetch(FRED_SERIES["fed_rate"], start, end)

    def get_us_cpi(self, start: str, end: str) -> pd.Series | None:
        """미국 CPI 전수 지수 (CPIAUCSL, 월별). YoY는 파이프라인에서 계산."""
        return self._fetch(FRED_SERIES["cpi"], start, end)

    def get_us_m2(self, start: str, end: str) -> pd.Series | None:
        """미국 M2 통화량 (M2SL, 월별, 십억달러)."""
        return self._fetch(FRED_SERIES["m2"], start, end)

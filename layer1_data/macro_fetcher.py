"""
매크로 데이터 수집 — Skills.md §5 Layer 1.

한국은행 ECOS API 기반:
- fx_rate (원/달러 환율, 731Y001 / 0000001, 일별)
- base_rate (한국 기준금리, 722Y001 / 0101000, 일별)
- cpi_yoy (소비자물가지수 전년 동월 대비, 901Y009 / 0 → YoY 자체 계산, 월별)
- m2_growth (M2 평잔 원계열 → 전년 동월 대비, 161Y006 / BBHA00, 월별)
- us_base_rate (미국 정책금리, 902Y006 / US, 월별)

ECOS API URL: /StatisticSearch/{key}/json/kr/{start}/{end}/{stat_code}/{cycle}/{from}/{to}/{item}
cycle 코드: "D" 일별 / "M" 월별 / "Q" 분기 / "A" 연 (단일 문자, "DD" 아님).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class EcosError(RuntimeError):
    """ECOS API 호출 오류."""


class EcosClient:
    """한국은행 ECOS Open API 클라이언트.

    공식 문서: https://ecos.bok.or.kr/api/
    """

    BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
    DEFAULT_TIMEOUT = 30

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ECOS_API_KEY")
        if not self.api_key:
            raise EcosError("ECOS_API_KEY 환경 변수가 설정되지 않았습니다.")

    # ── 저수준 API ────────────────────────────────────────────
    def fetch(
        self,
        stat_code: str,
        cycle: str,
        start: str,
        end: str,
        *item_codes: str,
        max_rows: int = 10000,
    ) -> pd.DataFrame:
        """ECOS StatisticSearch 호출.

        cycle: "D"(일) / "M"(월) / "Q"(분기) / "A"(연).
        start/end: cycle 형식 (D=YYYYMMDD, M=YYYYMM, A=YYYY).
        """
        parts = [
            self.api_key, "json", "kr",
            "1", str(max_rows),
            stat_code, cycle, start, end,
            *item_codes,
        ]
        url = f"{self.BASE_URL}/" + "/".join(parts)

        r = requests.get(url, timeout=self.DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        if "StatisticSearch" not in data:
            result = data.get("RESULT", {})
            raise EcosError(
                f"ECOS API 오류 [{result.get('CODE', '?')}]: {result.get('MESSAGE', data)}"
            )

        rows = data["StatisticSearch"].get("row", [])
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df["TIME"] = pd.to_datetime(df["TIME"], format=self._date_format(cycle))
        df["DATA_VALUE"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
        return df.set_index("TIME").sort_index()

    @staticmethod
    def _date_format(cycle: str) -> str:
        return {"D": "%Y%m%d", "M": "%Y%m", "A": "%Y"}[cycle]

    # ── 지표별 메서드 (원시값) ─────────────────────────────────
    def get_fx_rate(self, start: str, end: str) -> pd.Series:
        """원/달러 매매기준율 (일별)."""
        df = self.fetch("731Y001", "D", start, end, "0000001")
        return df["DATA_VALUE"].rename("fx_rate")

    def get_base_rate(self, start: str, end: str) -> pd.Series:
        """한국은행 기준금리 (일별, 변경일 기준)."""
        df = self.fetch("722Y001", "D", start, end, "0101000")
        return df["DATA_VALUE"].rename("base_rate")

    def get_cpi(self, start: str, end: str) -> pd.Series:
        """소비자물가지수 총지수 (월별, 2020=100)."""
        df = self.fetch("901Y009", "M", start, end, "0")
        return df["DATA_VALUE"].rename("cpi")

    def get_m2(self, start: str, end: str) -> pd.Series:
        """M2 통화량 평잔 원계열 (월별, 십억원)."""
        df = self.fetch("161Y006", "M", start, end, "BBHA00")
        return df["DATA_VALUE"].rename("m2")

    def get_us_base_rate(self, start: str, end: str) -> pd.Series:
        """미국 정책금리 (월별)."""
        df = self.fetch("902Y006", "M", start, end, "US")
        return df["DATA_VALUE"].rename("us_base_rate")

    # ── 지표별 메서드 (파생: 전년 동월 대비) ──────────────────
    def get_cpi_yoy(self, start: str, end: str) -> pd.Series:
        """소비자물가지수 전년 동월 대비 등락률 (%, 월별).

        Skills.md cpi_yoy. CPI 지수에서 12개월 차분 → %.
        start보다 12개월 일찍 fetch 후 YoY 계산하여 [start:end] 반환.
        """
        from_dt = (pd.to_datetime(start, format="%Y%m") - pd.DateOffset(months=12)).strftime("%Y%m")
        cpi = self.get_cpi(from_dt, end)
        yoy = (cpi / cpi.shift(12) - 1) * 100
        return yoy.dropna().loc[pd.to_datetime(start, format="%Y%m"):].rename("cpi_yoy")

    def get_m2_growth(self, start: str, end: str) -> pd.Series:
        """M2 통화량 전년 동월 대비 증가율 (%, 월별).

        Skills.md m2_growth_curr. M2 평잔에서 12개월 차분 → %.
        """
        from_dt = (pd.to_datetime(start, format="%Y%m") - pd.DateOffset(months=12)).strftime("%Y%m")
        m2 = self.get_m2(from_dt, end)
        yoy = (m2 / m2.shift(12) - 1) * 100
        return yoy.dropna().loc[pd.to_datetime(start, format="%Y%m"):].rename("m2_growth")

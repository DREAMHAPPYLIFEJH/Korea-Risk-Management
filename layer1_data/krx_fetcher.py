"""KRX 펀더멘털 데이터 수집 — Phase 4 (마켓 컨텍스트).

KOSPI 지수 전체 PER/PBR/배당수익률 — pykrx `get_index_fundamental_by_date`.
파생/펀더멘털 데이터는 KRX 회원 로그인 게이트 뒤 → pykrx가 KRX_ID/KRX_PW로 자동 로그인.

자격증명 미설정 또는 조회 실패 시 None 반환 (vkospi_fetcher / FRED와 동일 graceful 패턴).
표시 전용 — 등급·점수에 영향 없음 (Skills.md §P4-0 옵션 A).

Skills.md 참조: Phase 4 §P4-1
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from config.constants import KOSPI_INDEX_CODE

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_kospi_fundamental(start: str, end: str) -> pd.DataFrame | None:
    """KOSPI 지수 PER/PBR/배당수익률 일별. start/end: YYYYMMDD.

    Returns DataFrame(per, pbr, div_yield) indexed by date, 또는
    자격증명 없음·조회 실패 시 None.
    """
    if not (os.environ.get("KRX_ID") and os.environ.get("KRX_PW")):
        return None
    try:
        from pykrx import stock
        df = stock.get_index_fundamental_by_date(start, end, KOSPI_INDEX_CODE)
    except Exception:
        return None
    if df is None or df.empty:
        return None

    out = df.rename(columns={"PER": "per", "PBR": "pbr", "배당수익률": "div_yield"})
    cols = [c for c in ["per", "pbr", "div_yield"] if c in out.columns]
    if not cols:
        return None
    out = out[cols]
    out.index = pd.to_datetime(out.index)
    out.index.name = "date"
    return out

"""섹터(업종) 데이터 수집 — Phase 2.

ka20006 업종일봉조회를 섹터별 inds_cd로 호출.
SECTOR_CODES에 "???"가 있으면 API 호출 없이 None 반환 (업종 코드 미확보).
코드 확보 후 config/constants.py의 SECTOR_CODES만 교체하면 자동 활성화.
"""

from __future__ import annotations

import pandas as pd

from config.constants import SECTOR_CODES
from .kiwoom_client import KiwoomClient


def get_sector_ohlcv(
    sector: str,
    start: str,
    end: str,
    client: KiwoomClient | None = None,
) -> pd.DataFrame | None:
    """섹터 일별 OHLCV — ka20006.

    sector: SECTOR_NAMES의 섹터명.
    start, end: YYYYMMDD.
    inds_cd에 "?"가 포함되면 None 반환 (업종 코드 미확보).

    Returns DataFrame(open, high, low, close) indexed by date, or None.
    """
    inds_cd = SECTOR_CODES.get(sector, "???")
    if "?" in inds_cd:
        return None

    client = client or KiwoomClient()
    rows: list[dict] = []
    cont_yn, next_key = "N", ""
    body = {"inds_cd": inds_cd, "base_dt": end}

    while True:
        data, headers = client.request_tr(
            "ka20006", "/api/dostk/chart", body, cont_yn=cont_yn, next_key=next_key
        )
        page = data.get("inds_dt_pole_qry", [])
        if not page:
            break
        rows.extend(page)

        oldest = page[-1]["dt"]
        if oldest <= start:
            break

        cont_yn = headers.get("cont-yn", "N")
        next_key = headers.get("next-key", "")
        if cont_yn != "Y":
            break

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["dt"], format="%Y%m%d")
    for col in ["open_pric", "high_pric", "low_pric", "cur_prc"]:
        df[col] = pd.to_numeric(df[col]) / 100.0
    df = df.rename(columns={
        "open_pric": "open",
        "high_pric": "high",
        "low_pric":  "low",
        "cur_prc":   "close",
    })
    df = df.set_index("date").sort_index()
    return df.loc[start:end, ["open", "high", "low", "close"]]

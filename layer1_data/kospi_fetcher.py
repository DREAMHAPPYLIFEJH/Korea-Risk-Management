"""KOSPI 시장 데이터 수집 — Skills.md §5 Layer 1.

키움 REST API 기반:
- get_kospi_ohlcv: ka20006 업종일봉조회 (inds_cd=001 종합 KOSPI)
- get_foreign_net_buying: ka10051 업종별투자자순매수 (일별 스냅샷, 날짜 루프)

VKOSPI는 키움 REST API 미지원 (별도 처리 필요).
"""

from __future__ import annotations

import pandas as pd

from .kiwoom_client import KiwoomClient


def get_kospi_ohlcv(
    start: str,
    end: str,
    client: KiwoomClient | None = None,
) -> pd.DataFrame:
    """KOSPI 종합지수 일별 OHLCV — ka20006.

    start, end: YYYYMMDD.
    응답에서 지수 값은 100배로 반환되므로 100으로 나눠 실제값 복원.
    페이징(cont-yn=Y) 자동 처리: 가장 오래된 날짜가 start 이전이 될 때까지 반복.

    Returns DataFrame indexed by date, columns: open, high, low, close, volume, value.
    """
    client = client or KiwoomClient()

    rows: list[dict] = []
    cont_yn, next_key = "N", ""
    body = {"inds_cd": "001", "base_dt": end}

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
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "value"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["dt"], format="%Y%m%d")
    for col in ["open_pric", "high_pric", "low_pric", "cur_prc"]:
        df[col] = pd.to_numeric(df[col]) / 100.0
    df["trde_qty"] = pd.to_numeric(df["trde_qty"])
    df["trde_prica"] = pd.to_numeric(df["trde_prica"])

    df = df.rename(columns={
        "open_pric":  "open",
        "high_pric":  "high",
        "low_pric":   "low",
        "cur_prc":    "close",
        "trde_qty":   "volume",
        "trde_prica": "value",
    })
    df = df.set_index("date").sort_index()
    return df.loc[start:end, ["open", "high", "low", "close", "volume", "value"]]


def get_foreign_net_buying(
    start: str,
    end: str,
    client: KiwoomClient | None = None,
    on_progress=None,
) -> pd.Series:
    """KOSPI 시장 전체 외국인 순매수 시계열 — ka10051.

    ka10051은 일별 스냅샷이므로 영업일마다 호출하여 시계열 구성.
    inds_cd=001_AL (종합 KOSPI) 행의 frgnr_netprps 추출.

    응답 단위: 응답 원본은 백만원 추정 (Skills.md fi_monthly는 조원 → Layer 2에서 환산).
    실패 일자는 SKIP하고 경고 로그.

    Returns Series indexed by date, values: 외국인 순매수 (백만원 추정).
    """
    client = client or KiwoomClient()
    dates = pd.bdate_range(start=start, end=end)

    results: dict[pd.Timestamp, float] = {}
    for i, dt in enumerate(dates):
        d = dt.strftime("%Y%m%d")
        body = {"mrkt_tp": "0", "amt_qty_tp": "0", "base_dt": d, "stex_tp": "3"}
        try:
            data, _ = client.request_tr("ka10051", "/api/dostk/sect", body)
        except Exception as e:
            print(f"[fi_net] {d} skip: {e}")
            continue

        for item in data.get("inds_netprps", []):
            if item.get("inds_cd") == "001_AL":
                raw = item.get("frgnr_netprps", "0").replace("+", "")
                try:
                    results[dt] = float(raw)
                except ValueError:
                    pass
                break

        if on_progress is not None:
            on_progress(i + 1, len(dates), d)

    s = pd.Series(results, name="fi_net").sort_index()
    s.index.name = "date"
    return s

"""V-KOSPI (코스피200 변동성지수) 현물 데이터 수집 — Phase 5.

KRX 정보데이터시스템(data.krx.co.kr) `MDCSTAT01402` 직접 호출.
V-KOSPI는 파생시장 지수라 pykrx `get_index_*` 미지원 → 회원 로그인 게이트 뒤에 있음.
pykrx 내장 로그인(KRX_ID/KRX_PW)으로 인증 세션을 확보한 뒤 getJsonData를 호출한다.

KRX_ID/KRX_PW 미설정 또는 로그인 실패 시 빈 Series 반환 (FRED/VKOSPI 보류와 동일
graceful degradation 패턴). 호출부는 empty 여부로 data_available을 판정한다.

Skills.md 참조: Phase 5 §P5-1
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from config.constants import KRX_GETJSON_URL, VKOSPI_BLD, VKOSPI_IDX_CD

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _authenticated_session():
    """pykrx 인증 세션(KRXSession) 확보. 실패 시 None.

    이미 로그인된 전역 세션이 유효하면 재사용, 아니면 KRX_ID/KRX_PW로 재로그인.
    """
    krx_id = os.environ.get("KRX_ID")
    krx_pw = os.environ.get("KRX_PW")
    if not (krx_id and krx_pw):
        return None
    try:
        from pykrx.website.comm import auth
    except Exception:
        return None

    sess = auth._auth_session
    if sess is not None and sess.is_valid():
        return sess
    try:
        sess = sess or auth.KRXSession()
        if sess.refresh(krx_id, krx_pw):
            auth.set_auth_session(sess)
            return sess
    except Exception:
        return None
    return None


def get_vkospi(start: str, end: str) -> pd.Series:
    """V-KOSPI 일별 종가. start/end: YYYYMMDD.

    Returns Series(name="vkospi") indexed by date, 또는 인증/조회 실패 시 빈 Series.
    """
    empty = pd.Series(name="vkospi", dtype=float)
    sess = _authenticated_session()
    if sess is None:
        return empty

    payload = {
        "bld":      VKOSPI_BLD,
        "locale":   "ko_KR",
        "indTpCd":  "1",
        "idxIndCd": VKOSPI_IDX_CD,
        "idxCd":    "1",
        "idxCd2":   VKOSPI_IDX_CD,
        "strtDd":   start,
        "endDd":    end,
        "csvxls_isNo": "false",
    }
    try:
        r = sess.post(KRX_GETJSON_URL, data=payload, timeout=20)
        rows = r.json().get("output", [])
    except Exception:
        return empty

    records: dict[pd.Timestamp, float] = {}
    for row in rows:
        date_raw = row.get("TRD_DD", "")
        close_raw = str(row.get("CLSPRC_IDX", "")).replace(",", "").strip()
        if "/" not in date_raw or not close_raw:
            continue
        try:
            records[pd.Timestamp(date_raw.replace("/", "-"))] = float(close_raw)
        except ValueError:
            continue

    if not records:
        return empty
    out = pd.Series(records, name="vkospi")
    out.index.name = "date"
    return out.sort_index()

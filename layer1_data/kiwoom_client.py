"""
키움 REST API 저수준 클라이언트 — Skills.md §5 Layer 1.

OAuth2 토큰 발급(au10001) + 공통 TR 요청 헬퍼.
TR 호출은 POST + JSON, 헤더에 api-id / authorization / cont-yn / next-key 필수.
운영 도메인: https://api.kiwoom.com
모의투자 도메인: https://mockapi.kiwoom.com
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class KiwoomError(RuntimeError):
    """키움 API 호출 오류."""


class KiwoomClient:
    """키움 REST API 클라이언트.

    토큰은 자동 발급/재사용. 만료 23시간 보수적 처리.
    페이징(cont-yn/next-key)은 호출자가 응답 헤더로 직접 처리.
    """

    BASE_URL = "https://api.kiwoom.com"
    DEFAULT_TIMEOUT = 30
    TOKEN_LIFETIME_HOURS = 23

    def __init__(
        self,
        appkey: str | None = None,
        secretkey: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.appkey = appkey or os.environ.get("KIWOOM_APPKEY")
        self.secretkey = secretkey or os.environ.get("KIWOOM_SECRETKEY")
        if not self.appkey or not self.secretkey:
            raise KiwoomError("KIWOOM_APPKEY / KIWOOM_SECRETKEY 환경 변수가 설정되지 않았습니다.")
        self.base_url = base_url or self.BASE_URL
        self._token: str | None = None
        self._token_expiry: datetime | None = None

    # ── 토큰 ──────────────────────────────────────────────────
    def _ensure_token(self) -> None:
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return
        self._fetch_token()

    def _fetch_token(self) -> None:
        url = f"{self.base_url}/oauth2/token"
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "secretkey": self.secretkey,
        }
        r = requests.post(url, headers=headers, json=body, timeout=self.DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("return_code", 0) != 0 or "token" not in data:
            raise KiwoomError(f"토큰 발급 실패: {data}")
        self._token = data["token"]
        self._token_expiry = datetime.now() + timedelta(hours=self.TOKEN_LIFETIME_HOURS)

    # ── 공통 TR 요청 ──────────────────────────────────────────
    def request_tr(
        self,
        api_id: str,
        url_path: str,
        body: dict,
        cont_yn: str = "N",
        next_key: str = "",
    ) -> tuple[dict, dict]:
        """
        TR 호출. (응답 body, 응답 헤더 dict) 반환.

        cont_yn / next_key — 페이징은 호출자에서 응답 헤더 보고 다음 호출에 전달.
        """
        self._ensure_token()
        url = f"{self.base_url}{url_path}"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {self._token}",
            "api-id": api_id,
            "cont-yn": cont_yn,
            "next-key": next_key,
        }
        r = requests.post(url, headers=headers, json=body, timeout=self.DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("return_code", 0) != 0:
            raise KiwoomError(
                f"TR {api_id} 실패 [{data.get('return_code')}]: {data.get('return_msg', data)}"
            )
        return data, dict(r.headers)

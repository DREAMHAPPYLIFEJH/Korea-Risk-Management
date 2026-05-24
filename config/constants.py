"""전역 상수 — Skills.md §1 Global Constants & Type Definitions.

GRADE_MAP, STRATEGY_LEVEL, EQUITY_CEILING_DEFAULT, EQUITY_MIN,
STRATEGY_INSIGHT_TEMPLATE, SCORE_BAND_THRESHOLDS, ALERT_LEVEL,
GRADE_COLOR, BAND_COLOR, CLAMP.
"""

# ── 등급 수치 매핑 ─────────────────────────────────────────
GRADE_MAP = {
    "Low":      1,
    "Medium":   2,
    "High":     3,
    "Critical": 4,
}

# ── 전략 레벨 (숫자 클수록 방어적) ───────────────────────
STRATEGY_LEVEL = {
    "Aggressive":          1,
    "Moderate_Aggressive": 2,
    "Moderate_Defensive":  3,
    "Defensive":           4,
    "Extreme_Defensive":   5,
}

# ── 전략별 주식 비중 상한 (기본값, %) ─────────────────────
EQUITY_CEILING_DEFAULT = {
    "Aggressive":          100,
    "Moderate_Aggressive":  80,
    "Moderate_Defensive":   50,
    "Defensive":            30,
    "Extreme_Defensive":    10,
}

# ── 전략별 주식 비중 최솟값 (%) ───────────────────────────
EQUITY_MIN = {
    "Aggressive":           80,
    "Moderate_Aggressive":  60,
    "Moderate_Defensive":   30,
    "Defensive":            10,
    "Extreme_Defensive":     0,
}

# ── 전략 권고 인사이트 템플릿 ─────────────────────────────
STRATEGY_INSIGHT_TEMPLATE = {
    "Aggressive":
        "현재 리스크 수준이 낮아 공격적 투자 전략이 유효합니다. 성장주 비중 확대를 권장합니다.",
    "Moderate_Aggressive":
        "시장 리스크가 일부 존재합니다. 우량주 중심 포트폴리오를 유지하되 채권을 일부 편입하십시오.",
    "Moderate_Defensive":
        "복합 리스크가 감지됩니다. 저변동 섹터로 이동하고 채권 비중 확대를 권장합니다.",
    "Defensive":
        "방어적 자산 배분이 필요합니다. 고배당주 및 채권 중심으로 포트폴리오를 재편하십시오.",
    "Extreme_Defensive":
        "극단적 리스크 수준입니다. 포지션을 최소화하고 현금·금·단기채 위주로 전환하십시오.",
}

# ── 통합 점수 구간 (경계값 상위 구간 적용) ────────────────
# 예: integrated_score == 2.5 → "Danger" (Alert 아님)
SCORE_BAND_THRESHOLDS = [
    (3.0, 4.0, "Extreme"),
    (2.5, 3.0, "Danger"),
    (2.0, 2.5, "Alert"),
    (1.5, 2.0, "Caution"),
    (1.0, 1.5, "Safe"),
]

# ── 알림 등급 ────────────────────────────────────────────
ALERT_LEVEL = {
    "Watch":          1,
    "Warning":        2,
    "Critical_Alert": 3,
}

# ── 색상 코드 ────────────────────────────────────────────
GRADE_COLOR = {
    "Low":      "#2ECC71",
    "Medium":   "#F1C40F",
    "High":     "#E67E22",
    "Critical": "#E74C3C",
}

BAND_COLOR = {
    "Safe":    "#2ECC71",
    "Caution": "#A8D8A8",
    "Alert":   "#F1C40F",
    "Danger":  "#E67E22",
    "Extreme": "#E74C3C",
}


def CLAMP(value, min_val, max_val):
    """값을 [min_val, max_val] 범위로 제한 — Skills.md §1."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


# ── Phase 3 — S&P500 설정 ────────────────────────────────────

# yfinance 티커
US_MARKET_TICKER = "^GSPC"   # S&P500
US_VIX_TICKER    = "^VIX"    # VIX (VKOSPI 대응)
US_VVIX_TICKER   = "^VVIX"   # VVIX — VIX의 변동성 (Phase 5, 조기경보)
US_SKEW_TICKER   = "^SKEW"   # SKEW — 꼬리 리스크 (Phase 5)
US_DXY_TICKER    = "DX-Y.NYB" # Dollar Index

# FRED 시리즈 ID
FRED_SERIES = {
    "fed_rate":  "FEDFUNDS",      # 연준 기준금리
    "cpi":       "CPIAUCSL",      # CPI (전수 지수)
    "m2":        "M2SL",          # M2 통화량
    "hy_spread": "BAMLH0A0HYM2",  # 하이일드 회사채 OAS (Phase 5, 5계층 보조)
}

# ── Phase 5 — V-KOSPI (KRX 정보데이터시스템) ─────────────────
# 코스피200 변동성지수 현물. KRX MDCSTAT01402 / idxIndCd=300.
# 파생시장 지수라 pykrx get_index_* 미지원 → KRX 로그인(KRX_ID/KRX_PW) 후 직접 호출.
KRX_GETJSON_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
VKOSPI_BLD      = "dbms/MDC/STAT/standard/MDCSTAT01402"
VKOSPI_IDX_CD   = "300"

# KOSPI 지수 코드 (Phase 4 — PER/PBR 펀더멘털 조회)
KOSPI_INDEX_CODE = "1001"

# ── Monte Carlo 설정 — Risk-D MC 기반 지표 ──────────────────

MC_N_PATHS = 10_000           # 시뮬레이션 경로 수
MC_METHOD = "bootstrap"       # 'bootstrap' | 'student_t' | 'garch'
MC_SEED = 42                  # 재현성용 시드 (None이면 매번 다른 결과)
MC_LOOKBACK_DAYS = 252        # 수익률 분포 추정에 사용할 과거 윈도우


# ── Phase 2 — 섹터 정의 ──────────────────────────────────────

# 분석 대상 섹터 목록
SECTOR_NAMES: list[str] = ["반도체", "금융", "에너지/화학", "자동차", "헬스케어"]

# 키움 ka20006 업종 코드 (inds_cd) — ka10051 응답 기준 확인 완료
SECTOR_CODES: dict[str, str] = {
    "반도체":     "013",  # 전기/전자
    "금융":       "021",  # 금융
    "에너지/화학": "008",  # 화학
    "자동차":     "015",  # 운송장비/부품
    "헬스케어":   "009",  # 제약
}

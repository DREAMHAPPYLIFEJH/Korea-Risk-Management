"""지표별 임계값 — Skills.md §6 Layer 2, §7 Layer 3, §8 Layer 4, §14 Alert.

시장 확장(S&P500, 암호화폐 등) 시 본 파일만 교체.
모든 임계값은 등급 경계 또는 이벤트 트리거 기준.
"""

# ─────────────────────────────────────────────────────────────
# Risk-A 시장 — Skills.md §6, §7 Risk-A
# ─────────────────────────────────────────────────────────────

# 이격도 (disp_ma20)
DISP_MA20_LOW_MIN = 98          # Low 정상 구간 [98, 102]
DISP_MA20_LOW_MAX = 102
DISP_MA20_MEDIUM = 94           # [94, 98) 하락 신호
DISP_MA20_HIGH = 90             # [90, 94) 강한 하락
# < 90 → Critical / ALT-06 트리거

# 이격도 (disp_ma60)
DISP_MA60_WEAK = 90             # < 90 하락 추세 강화
DISP_MA60_ALERT = 85            # ≤ 85 ALT-06 트리거

# ADX 추세 강도
ADX_TREND = 25                  # > 25 추세 확립
ADX_SIDEWAYS = 20               # < 20 횡보장

# 연속 하락 일수 (consec_decline)
CONSEC_DECLINE_CRITICAL = 10
CONSEC_DECLINE_HIGH = 5
CONSEC_DECLINE_MEDIUM = 3       # bearish_phase 판정에도 사용

# ─────────────────────────────────────────────────────────────
# Risk-B 변동성 — Skills.md §6, §7 Risk-B
# ─────────────────────────────────────────────────────────────

# 역사적 변동성 (HV20, 연율화 %)
HV20_CRITICAL = 30
HV20_HIGH = 20
HV20_MEDIUM = 12

# VKOSPI 내재 변동성
VKOSPI_CRITICAL = 35
VKOSPI_HIGH = 25
VKOSPI_MEDIUM = 15

# HV20 / HV60 비율
VOL_RATIO_HV_SPIKE = 1.2        # > 1.2 변동성 급등
VOL_RATIO_HV_CONTRACTION = 0.8  # < 0.8 변동성 축소

# ─────────────────────────────────────────────────────────────
# Risk-C 유동성 — Skills.md §6, §7 Risk-C
# ─────────────────────────────────────────────────────────────

# 거래량 비율 (vol_ratio)
VOL_RATIO_NORMAL = 1.0          # ≥ 1.0 정상
VOL_RATIO_REDUCED = 0.7         # [0.7, 1.0) 축소
VOL_RATIO_SEVERE = 0.5          # [0.5, 0.7) 심각, < 0.5 위험

# 연속 거래량 감소 일수
VOL_STREAK_HIGH = 3
VOL_STREAK_CRITICAL = 5

# 거래대금 비율 / 편중도
VAL_RATIO_WARNING = 0.6         # < 0.6 경계, 최소 Medium 보정
CONC_RATIO_HEAVY = 0.4          # > 0.4 쏠림, 최소 Medium 보정

# ─────────────────────────────────────────────────────────────
# Risk-D 하방 — Skills.md §6, §7 Risk-D
# ─────────────────────────────────────────────────────────────

# MDD_60 (Maximum Drawdown, %)
MDD_60_CRITICAL = -20
MDD_60_HIGH = -10
MDD_60_MEDIUM = -5

# VaR_95 (Value at Risk, 1일, %)
VAR_95_CRITICAL = -3.5
VAR_95_HIGH = -2.5
VAR_95_MEDIUM = -1.5

# MDD 회복 기간 (월)
MDD_RECOVERY_FAST = 3           # < 3 빠른 회복
MDD_RECOVERY_SLOW = 6           # > 6 장기 침체

# ─────────────────────────────────────────────────────────────
# Risk-D MC 기반 임계값 — Monte Carlo 분포 percentile별
# ─────────────────────────────────────────────────────────────
# 의미: simulate_paths(close, horizon=60, n_paths=10000)로 생성한 경로들의
#   peak-to-trough MDD 분포에서
#     p50 = 중위 시나리오 ("일반적으로 예상되는 60일 최대 낙폭")
#     p5  = 워스트 5% 시나리오 ("나쁜 경우의 60일 최대 낙폭")
# 두 percentile을 각각 4단계 등급화 후 MAX 적용 (Risk-D evaluate에서).
# 초기 임계값은 1차 추정 — task #6 검증 단계에서 실측 분포 기반으로 보정 예정.

# 60일 forward MDD - p50 (typical case)
MDD_60_MC_P50_CRITICAL = -10
MDD_60_MC_P50_HIGH     = -7
MDD_60_MC_P50_MEDIUM   = -4

# 60일 forward MDD - p5 (worst case)
MDD_60_MC_P5_CRITICAL = -25
MDD_60_MC_P5_HIGH     = -18
MDD_60_MC_P5_MEDIUM   = -10

# 252일 forward MDD - p50
MDD_252_MC_P50_CRITICAL = -18
MDD_252_MC_P50_HIGH     = -12
MDD_252_MC_P50_MEDIUM   = -7

# 252일 forward MDD - p5
MDD_252_MC_P5_CRITICAL = -40
MDD_252_MC_P5_HIGH     = -28
MDD_252_MC_P5_MEDIUM   = -15

# MC 기반 1일 VaR — 기존 VAR_95_CRITICAL/HIGH/MEDIUM 재사용 (분포만 다르고 의미 동일)

# ─────────────────────────────────────────────────────────────
# Risk-E 매크로 3E-1 수준 판정 — Skills.md §7 Risk-E 3E-1
# ─────────────────────────────────────────────────────────────

# 원/달러 환율
FX_RATE_CAUTION = 1300          # ≥ 1300 경계
FX_RATE_DANGER = 1400           # > 1400 위험

# 기준금리 전월 대비 변화 (%p)
BASE_RATE_DELTA_CAUTION = 0.25  # +0.25%p 경계 (인상)
BASE_RATE_DELTA_DANGER = 0.50   # ≥ +0.50%p 위험 (빅스텝)

# 한미 금리차 (%p)
RATE_SPREAD_CAUTION = 0         # ≤ 0 경계 (역전)
RATE_SPREAD_DANGER = -0.5       # < -0.5 위험 (역전 심화)

# CPI 전년 동월 대비 (%)
CPI_YOY_CAUTION = 2.5           # ≥ 2.5 경계
CPI_YOY_DANGER = 4.0            # > 4.0 위험

# 외국인 월간 순매수 (조원)
FI_MONTHLY_CAUTION = 0          # < 0 경계 (-1조 ~ 0)
FI_MONTHLY_DANGER = -2.0        # < -2 위험

# ─────────────────────────────────────────────────────────────
# Risk-E 매크로 3E-2 이벤트 — Skills.md §7 Risk-E 3E-2
# ─────────────────────────────────────────────────────────────

# EVT-01 FX Spike
FX_WEEKLY_SPIKE = 0.03          # 주간 +3%
FX_DAILY_SPIKE = 0.015          # 일간 +1.5%

# EVT-07 FX Drop (등급 하향 없음, 섹터 연동 검토만)
FX_WEEKLY_DROP = -0.03          # 주간 -3%

# EVT-02 Foreign Exodus
FI_STREAK_SELL_TRIGGER = 5      # 5일 연속 순매도
FI_5D_CUM_SELL = -1.0           # 5일 누적 -1조

# EVT-08 Foreign Return
FI_STREAK_BUY_TRIGGER = 5
FI_5D_CUM_BUY = 0.5             # 5일 누적 +5,000억

# EVT-03 Rate Hike / EVT-09 Rate Cut
RATE_HIKE_DELTA = 0.25          # +0.25%p 이상
RATE_CUT_DELTA = -0.25          # -0.25%p 이상

# EVT-04 CPI Surge
CPI_DELTA_SURGE = 0.5           # 전월 대비 +0.5%p

# EVT-05 Yield Inversion
# rate_spread_prev > 0 AND rate_spread_curr <= 0 (임계값 RATE_SPREAD_CAUTION 사용)

# 매크로 이벤트 중첩 상향
EVENT_OVERLAP_TRIGGER = 2       # up_count >= 2 → net_delta +1, ALT-08 발동

# ─────────────────────────────────────────────────────────────
# Derived 신호 — Skills.md §3 Derived Indicator Definitions
# ─────────────────────────────────────────────────────────────

# M2 신호 (전월 대비 %p 변화)
M2_CONTRACTION_DROP = -1.0      # ≤ -1.0%p 또는 음수 전환 → m2_contraction
M2_SLOWDOWN_DROP = 0.5          # ≥ 0.5%p 감소 → m2_growth_slowdown
M2_EXPANSION_RISE = 1.0         # ≥ +1.0%p 증가 → m2_expansion

# MA 수렴 (ma_converging)
MA_CONVERGING_RATIO = 0.02      # ABS(ma20 - ma60) / ma60 < 0.02

# MDD 회복 미완료 표시값
MDD_RECOVERY_UNFINISHED = 99    # 회복 안된 경우 → 장기 침체 처리

# ─────────────────────────────────────────────────────────────
# Layer 4 국면 + 동적 가중치 — Skills.md §8
# ─────────────────────────────────────────────────────────────

# 국면 판단 임계값 (ADX는 위 ADX_TREND/ADX_SIDEWAYS 재사용)
BEARISH_CONSEC_DECLINE = 3      # ma_bearish_full + consec_decline >= 3 → bearish

# 동적 가중치 (시장/변동성/매크로/유동성/하방)
WEIGHTS = {
    "bullish":  {"market": 0.30, "volatility": 0.25, "macro": 0.20, "liquidity": 0.15, "downside": 0.10},
    "bearish":  {"market": 0.30, "volatility": 0.25, "macro": 0.20, "liquidity": 0.10, "downside": 0.15},
    "sideways": {"market": 0.20, "volatility": 0.25, "macro": 0.20, "liquidity": 0.20, "downside": 0.15},
}

# ─────────────────────────────────────────────────────────────
# Alert — Skills.md §14 (지표 의존 임계값만; 등급 의존은 rules/alert.py)
# ─────────────────────────────────────────────────────────────

# ALT-01 통합 점수 급등
ALT_SCORE_DELTA = 0.5           # integrated_score - prev >= 0.5

# ALT-03 변동성 급등
ALT_HV_SPIKE_RATIO = 1.3        # hv20 > hv20_5d_ago * 1.3

# ALT-04 거래량 급감
ALT_VOL_RATIO = 0.6             # vol_ratio ≤ 0.6
ALT_VOL_DAYS = 3                # 연속 일수

# ALT-06 이격도 임계 이탈 (DISP_MA20_HIGH=90, DISP_MA60_ALERT=85 재사용)

# ALT-07 MDD 임계 도달
ALT_MDD_60 = -15                # mdd_60 ≤ -15% (Skills.md = -0.15 비율 → -15% 정수 일관)

# ─────────────────────────────────────────────────────────────
# 데이터 정제 — Skills.md §5 Layer 1
# ─────────────────────────────────────────────────────────────

OUTLIER_SIGMA = 3               # |x - rolling_mean| > 3σ → 이상값 플래그

# ─────────────────────────────────────────────────────────────
# Strategy 자산 배분 추가 조정 — Skills.md §9 / §12 CR-03
# ─────────────────────────────────────────────────────────────

EQUITY_CEILING_CRITICAL_DROP = 10   # OVR-02: critical >= 1 시 -10%p
EQUITY_CEILING_DOUBLE_C_DROP = 10   # CR-03: 하방+변동성 양쪽 Critical → 추가 -10%p
EQUITY_CEILING_DOUBLE_H_DROP = 5    # CR-03: 하방+변동성 양쪽 High 이상 → -5%p

# ─────────────────────────────────────────────────────────────
# Phase 3 — S&P500 (기획서 §13.2)
# ─────────────────────────────────────────────────────────────

# S&P500 변동성 — VIX 임계값 (VKOSPI 동일 사용 가능, 참고용)
US_HV20_MEDIUM   = 10    # KOSPI: 12
US_HV20_HIGH     = 18    # KOSPI: 20 (기획서 §13.2)
US_HV20_CRITICAL = 28    # KOSPI: 30

# 연준 기준금리
US_FED_RATE_DANGER  = 4.5    # > 4.5% 위험
US_FED_RATE_CAUTION = 3.5    # 3.5~4.5% 경계
US_FED_RATE_DELTA_HIKE = 0.25  # >= 0.25%p 인상 이벤트
US_FED_RATE_DELTA_CUT  = -0.25 # <= -0.25%p 인하 이벤트

# 달러 인덱스 (DXY) — 강달러 = S&P500 다국적기업 역풍
US_DXY_DANGER      = 105    # > 105 위험
US_DXY_CAUTION     = 100    # 100~105 경계
US_DXY_WEEKLY_SPIKE = 0.02  # 주간 +2% 급등 이벤트
US_DXY_WEEKLY_DROP  = -0.02 # 주간 -2% 급락 이벤트

# 미국 CPI — 한국과 동일 임계값 재사용 (CPI_YOY_CAUTION=2.5, CPI_YOY_DANGER=4.0)
# 미국 M2 — 한국과 동일 임계값 재사용 (M2_CONTRACTION_DROP, M2_SLOWDOWN_DROP)

# ─────────────────────────────────────────────────────────────
# Phase 2 — 섹터 리스크 (PDF §4.4)
# ─────────────────────────────────────────────────────────────

# 업종 베타 등급 경계
SECTOR_BETA_CRITICAL = 1.5   # >= 1.5 AND RS 약세 → Critical
SECTOR_BETA_HIGH     = 1.3   # >= 1.3 → High
SECTOR_BETA_MEDIUM   = 1.0   # >= 1.0 → Medium, < 1.0 → Low

# 상대 강도 (RS) 기준
SECTOR_RS_DECLINE    = 1.0   # < 1.0 → 시장 대비 약세 (Critical 판정 보조 조건)

# 섹터 MDD 경계 (%)
SECTOR_MDD_HIGH      = -15   # <= -15% → High 보정
SECTOR_MDD_CRITICAL  = -25   # <= -25% → Critical 보정

# 섹터 HV20 경계 (연율화 %)
SECTOR_HV_HIGH       = 30    # >= 30% → High 보정
SECTOR_HV_CRITICAL   = 45    # >= 45% → Critical 보정

# 베타 산출 롤링 윈도우 (영업일)
SECTOR_BETA_WINDOW   = 60
SECTOR_RS_WINDOW     = 20

# ─────────────────────────────────────────────────────────────
# Phase 5 — 변동성 리스크 프레임워크 (Skills.md §P5-3)
# 표시 전용. 등급 영향 없음. line 번호는 volatility_risk_v2_kospi_sp500.pdf 근거.
# ─────────────────────────────────────────────────────────────

# 내재변동성 절대값 — 레짐 높음/낮음 (line 281~288)
VIX_HIGH_ABS    = 22
VIX_LOW_ABS     = 15
VKOSPI_HIGH_ABS = 25
VKOSPI_LOW_ABS  = 18

# 1년 백분위 기준 (데이터 252일 이상일 때 활성화, 아니면 절대값 fallback)
VIX_PCTL_HIGH    = 70
VIX_PCTL_LOW     = 30
VKOSPI_PCTL_HIGH = 70
VKOSPI_PCTL_LOW  = 30

# 2차 지표 조기경보 (line 69~70)
VVIX_WARNING = 120   # VVIX 120+ 조기경보
SKEW_TAIL    = 140   # SKEW 140+ 꼬리 리스크

# RI-01 VIX − V-KOSPI 스프레드 (line 88~89)
SPREAD_KR_STRESS = 8     # >= +8%p → 한국 단독 불안
SPREAD_INVERT    = 0     # <= 0 → 역전 (이례적)

# RI-02 HV 비율 KOSPI/S&P (line 122~124)
HVRATIO_KR_SHOCK  = 1.5  # >= 1.5 → 한국 충격 진행
HVRATIO_KR_CRISIS = 2.0  # >= 2.0 → 한국 단독 위기
HVRATIO_US_CRISIS = 1.0  # <= 1.0 → 미국발 위기

# RI-03 VRP 격차 US−KR (line 154~155)
VRPDIV_US_WATCH = 5      # >= +5%p → 미국 경계 강화
VRPDIV_INVERT   = 0      # <= 0 → 한국 단독 경계

# RI-05 한미 상관계수·베타 (line 55~57, 236~238)
CORR_NORMAL_HIGH = 0.5   # > 0.5 경계 시작
CORR_SYSTEMIC    = 0.7   # > 0.7 위기 동조화 (TRG-03)
BETA_VULNERABLE  = 1.2   # >= 1.2 취약성 확대
BETA_DECOUPLE    = 0.7   # < 0.7 탈동조화

# HY 신용 스프레드 (line 209~210)
HY_SPREAD_WIDEN_BP = 50  # 1개월 50bp+ 확대 → 스트레스

# 롤링 윈도우 (영업일)
CORR_WINDOW = 60
BETA_WINDOW = 60
VOL_PCTL_WINDOW = 252    # 1년 백분위 산출 윈도우
VKOSPI_PEAK_WINDOW = 60  # REG-04 회복 판별 lookback. V-KOSPI AR(1) 반감기 ~50일(φ≈0.99)의
                         # 약 1.2배 — 위기 후 하락 글라이드 구간 커버 (GARCH 평균회귀 근거)

# 핵심 신호 (Action Triggers, line 349~353, 384~388)
VIX_TRIGGER     = 25     # TRG-01/02 VIX 기준
VKOSPI_SYNC     = 30     # TRG-02 동조화 위기 V-KOSPI 기준
VIX_NIGHT_SPIKE = 0.30   # VIX 야간 30%+ 급등
FX_TRIGGER      = 1400   # 원/달러 1차 방어선

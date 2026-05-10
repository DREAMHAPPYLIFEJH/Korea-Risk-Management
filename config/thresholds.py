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

# Skills.md — KOSPI Risk Intelligence Dashboard
## Production-Ready Execution Specification v6.0

**기준**: 금융_투자_대시보드_서비스_기획서 v2.0
**버전**: v6.0 (Normalized JSON Schema — Identical Structure Across All 5 Risks)
**범위**: Layer 1–7 · 5 Risks · 10 Events · 4 Scenarios · 5 Conflict Rules · 6 Override Rules · 12 Alerts

---

## 목차

1. [Global Constants & Type Definitions](#1-global-constants--type-definitions)
2. [State Variables](#2-state-variables)
3. [Derived Indicator Definitions](#3-derived-indicator-definitions)
4. [실행 순서 및 GUARD](#4-실행-순서-및-guard)
5. [Layer 1 — Data](#5-layer-1--data)
6. [Layer 2 — Indicator](#6-layer-2--indicator)
7. [Layer 3 — Risk (5종 + JSON Schema)](#7-layer-3--risk)
   - [Risk-A: 시장 리스크](#risk-a-시장-리스크-market-risk)
   - [Risk-B: 변동성 리스크](#risk-b-변동성-리스크-volatility-risk)
   - [Risk-C: 유동성 리스크](#risk-c-유동성-리스크-liquidity-risk)
   - [Risk-D: 하방 리스크](#risk-d-하방-리스크-downside-risk)
   - [Risk-E: 매크로 리스크 (3-Step Chain)](#risk-e-매크로-리스크-macro-risk)
8. [Layer 4 — Scoring](#8-layer-4--scoring)
9. [Layer 5 — Strategy](#9-layer-5--strategy)
10. [Layer 6 — Insight](#10-layer-6--insight)
11. [Layer 7 — Visualization](#11-layer-7--visualization)
12. [Conflict Rules (IF/THEN)](#12-conflict-rules)
13. [Override Rules (IF/THEN)](#13-override-rules)
14. [Alert Rules (IF/THEN)](#14-alert-rules)
15. [Final Validation Checklist](#15-final-validation-checklist)

---

## 1. Global Constants & Type Definitions

```python
# ── 등급 수치 매핑 ─────────────────────────────────────────
GRADE_MAP = {
    "Low":      1,
    "Medium":   2,
    "High":     3,
    "Critical": 4
}

# ── 전략 레벨 (숫자 클수록 방어적) ───────────────────────
STRATEGY_LEVEL = {
    "Aggressive":          1,
    "Moderate_Aggressive": 2,
    "Moderate_Defensive":  3,
    "Defensive":           4,
    "Extreme_Defensive":   5
}

# ── 전략별 주식 비중 상한 (기본값, %) ─────────────────────
EQUITY_CEILING_DEFAULT = {
    "Aggressive":          100,
    "Moderate_Aggressive":  80,
    "Moderate_Defensive":   50,
    "Defensive":            30,
    "Extreme_Defensive":    10
}

# ── 전략별 주식 비중 최솟값 (%) ───────────────────────────
EQUITY_MIN = {
    "Aggressive":           80,
    "Moderate_Aggressive":  60,
    "Moderate_Defensive":   30,
    "Defensive":            10,
    "Extreme_Defensive":     0
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
        "극단적 리스크 수준입니다. 포지션을 최소화하고 현금·금·단기채 위주로 전환하십시오."
}

# ── 통합 점수 구간 (경계값 상위 구간 적용) ────────────────
# 예: integrated_score == 2.5 → "Danger" (Alert 아님)
SCORE_BAND_THRESHOLDS = [
    (3.0, 4.0, "Extreme"),
    (2.5, 3.0, "Danger"),
    (2.0, 2.5, "Alert"),
    (1.5, 2.0, "Caution"),
    (1.0, 1.5, "Safe")
]

# ── 알림 등급 ────────────────────────────────────────────
ALERT_LEVEL = {
    "Watch":          1,
    "Warning":        2,
    "Critical_Alert": 3
}

# ── 색상 코드 ────────────────────────────────────────────
GRADE_COLOR = {
    "Low":      "#2ECC71",
    "Medium":   "#F1C40F",
    "High":     "#E67E22",
    "Critical": "#E74C3C"
}
BAND_COLOR = {
    "Safe":    "#2ECC71",
    "Caution": "#A8D8A8",
    "Alert":   "#F1C40F",
    "Danger":  "#E67E22",
    "Extreme": "#E74C3C"
}

# ── CLAMP 함수 정의 (인라인 사용) ────────────────────────
# CLAMP(value, min_val, max_val):
#   IF value < min_val → RETURN min_val
#   ELIF value > max_val → RETURN max_val
#   ELSE → RETURN value
```

### 정규화 변수명 (Normalized Variable Names)

| 범주 | 변수명 | 설명 |
|------|--------|------|
| 지표 | `ma20`, `ma60`, `ma120` | 이동평균 |
| 지표 | `disp_ma20`, `disp_ma60` | 이격도 |
| 지표 | `hv20`, `hv60` | 역사적 변동성 |
| 지표 | `vol_ratio_hv` | HV20/HV60 비율 |
| 지표 | `vkospi` | 내재 변동성 |
| 지표 | `adx` | 추세 강도 |
| 지표 | `consec_decline` | 연속 하락 일수 |
| 지표 | `vol_ratio` | 거래량 비율 |
| 지표 | `val_ratio` | 거래대금 비율 |
| 지표 | `conc_ratio` | 거래대금 편중도 |
| 지표 | `vol_streak` | 연속 거래량 감소 일수 |
| 지표 | `mdd_60`, `mdd_252` | 최대 낙폭 |
| 지표 | `var_95` | Value at Risk (1일, 95%) |
| 지표 | `cvar` | Conditional VaR |
| 지표 | `fx_rate` | 원/달러 환율 (당일) |
| 지표 | `fx_rate_prev` | 원/달러 환율 (전일) |
| 지표 | `fx_rate_5d_ago` | 원/달러 환율 (5영업일 전) |
| 지표 | `fx_daily_change` | 환율 일간 변화율 |
| 지표 | `fx_weekly_change` | 환율 주간 변화율 |
| 지표 | `base_rate_delta` | 기준금리 전월 대비 변화 |
| 지표 | `rate_spread_curr` | 한미 금리차 (당일) |
| 지표 | `rate_spread_prev` | 한미 금리차 (전일) |
| 지표 | `cpi_yoy` | CPI 전년 동월 대비 |
| 지표 | `cpi_delta` | CPI 전월 대비 변화 |
| 지표 | `fi_monthly` | 외국인 월간 순매수 |
| 지표 | `fi_5d_cum` | 외국인 5일 누적 순매수 |
| 지표 | `fi_streak_sell` | 외국인 연속 순매도 일수 |
| 지표 | `fi_streak_buy` | 외국인 연속 순매수 일수 |
| 지표 | `m2_growth_curr` | M2 증가율 (당월) |
| 지표 | `m2_growth_prev` | M2 증가율 (전월) |
| 지표 | `mdd_recovery_months` | MDD 최저점 이후 회복 소요 월수 |
| 불리언 | `m2_contraction` | M2 축소 이벤트 발동 여부 |
| 불리언 | `m2_expansion` | M2 확대 이벤트 발동 여부 |
| 불리언 | `m2_growth_slowdown` | M2 증가율 둔화 여부 |
| 불리언 | `ma_bullish` | MA 정배열 여부 |
| 불리언 | `ma_bearish_full` | MA 완전 역배열 여부 |
| 불리언 | `ma_bearish_part` | MA 부분 역배열 여부 |
| 불리언 | `ma_converging` | MA 수렴 여부 |
| 등급 | `market_grade` | 시장 리스크 등급 (1~4) |
| 등급 | `volatility_grade` | 변동성 리스크 등급 (1~4) |
| 등급 | `liquidity_grade` | 유동성 리스크 등급 (1~4) |
| 등급 | `downside_grade` | 하방 리스크 등급 (1~4) |
| 등급 | `macro_grade` | 매크로 리스크 등급 (1~4) |
| 등급 | `hv_grade` | HV20 기반 변동성 등급 |
| 등급 | `vkospi_grade` | VKOSPI 기반 변동성 등급 |
| 등급 | `mdd_grade` | MDD_60 기반 하방 등급 |
| 등급 | `var_grade` | VaR_95 기반 하방 등급 |
| 등급 | `level_grade` | 매크로 1단계 임시 등급 |
| 등급 | `event_grade` | 매크로 2단계 조정 등급 |
| 점수 | `integrated_score` | 통합 리스크 점수 (1.0~4.0) |
| 국면 | `market_phase` | "bullish" / "bearish" / "sideways" |
| 가중치 | `W1`~`W5` | 각 리스크별 가중치 |
| 전략 | `strategy` | 현재 투자 전략 문자열 |
| 전략 | `equity_ceiling` | 주식 비중 상한 (%) |
| 점수 구간 | `score_band` | "Safe" / "Caution" / "Alert" / "Danger" / "Extreme" |
| 시나리오 | `triggered_scenario` | "SCN-01"~"SCN-04" or None |
| 플래그 | `scn04_flag` | SCN-04 발동 여부 (boolean) |
| 집합 | `all_risk_grades` | [market, volatility, liquidity, downside, macro] |
| 집합 | `active_alerts` | 발동된 알림 ID 목록 |
| 정수 | `critical_count` | Critical(4) 등급 리스크 수 |
| 불리언 | `any_critical_alert_active` | Critical_Alert 발동 여부 |

---

## 2. State Variables

> 영업일 간 유지되는 상태 변수. 매 영업일 장 마감 후 업데이트.

```python
STATE = {
    "prev_score_band":       None,    # 전일 score_band (문자열 or None)
    "prev_integrated_score": None,    # 전일 integrated_score (float or None)
    "hv20_5d_ago":           None,    # 5영업일 전 hv20 값 (ALT-03 계산용)
    "vol_ratio_3d":          [],      # 최근 3영업일 vol_ratio 값 리스트 (ALT-04용)
    "vol_ratio_streak_count": 0,      # 거래량 비율 ≤ 0.6 연속 일수
    "consecutive_days": {             # 인사이트 ID별 연속 생성 일수
        "INS-01": 0, "INS-02": 0, "INS-03": 0, "INS-04": 0,
        "INS-05": 0, "INS-06": 0, "INS-07": 0, "INS-08": 0,
        "INS-09": 0, "INS-10": 0, "INS-11": 0
    }
}

# 매 영업일 종료 시 STATE 업데이트 규칙
# STATE["prev_score_band"]       ← 당일 score_band
# STATE["prev_integrated_score"] ← 당일 integrated_score
# STATE["hv20_5d_ago"]           ← 5영업일 전 hv20 (롤링 업데이트)
# STATE["consecutive_days"][id]  ← 해당 인사이트 생성 시 +1, 미생성 시 0으로 초기화
```

---

## 3. Derived Indicator Definitions

> 모든 파생 지표의 계산 규칙을 명시적으로 정의한다.

```python
# ── 환율 변화율 ────────────────────────────────────────────
fx_daily_change  = (fx_rate - fx_rate_prev) / fx_rate_prev
fx_weekly_change = (fx_rate - fx_rate_5d_ago) / fx_rate_5d_ago

# ── 금리차 ────────────────────────────────────────────────
rate_spread_curr = kr_base_rate - us_base_rate          # 당일
rate_spread_prev = kr_base_rate_prev - us_base_rate_prev  # 전일

# ── MA 배열 불리언 ─────────────────────────────────────────
ma_bullish      = (ma20 > ma60) AND (ma60 > ma120)
ma_bearish_full = (ma20 < ma60) AND (ma60 < ma120)
ma_bearish_part = (ma20 < ma60)                         # 완전 역배열 아닌 부분 역배열

# ── MA 수렴 여부 ───────────────────────────────────────────
# MA20과 MA60의 차이가 MA60의 2% 미만일 때 수렴으로 판단
ma_gap_ratio  = ABS(ma20 - ma60) / ma60
ma_converging = (ma_gap_ratio < 0.02)

# ── M2 신호 ───────────────────────────────────────────────
# M2 축소: 전월 대비 1.0%p 이상 감소 OR 0 이하로 전환
IF (m2_growth_curr - m2_growth_prev) <= -1.0:
    m2_contraction = True
ELIF m2_growth_curr <= 0 AND m2_growth_prev > 0:
    m2_contraction = True
ELSE:
    m2_contraction = False

# M2 둔화: 전월 대비 0.5%p 이상 감소 (축소 미달)
IF (m2_growth_prev - m2_growth_curr) >= 0.5 AND NOT m2_contraction:
    m2_growth_slowdown = True
ELSE:
    m2_growth_slowdown = False

# M2 확대: 전월 대비 1.0%p 이상 증가
IF (m2_growth_curr - m2_growth_prev) >= 1.0:
    m2_expansion = True
ELSE:
    m2_expansion = False

# ── MDD 회복 기간 ──────────────────────────────────────────
# 최근 252일 내 최저점 이후 원점 회복까지 소요 영업일 → 월 환산
mdd_trough_price = MIN(close_252d)
mdd_trough_idx   = INDEX_OF(mdd_trough_price, close_252d)
peak_before_trough = MAX(close_252d[0 : mdd_trough_idx])

recovery_idx = None
FOR i IN RANGE(mdd_trough_idx + 1, LEN(close_252d)):
    IF close_252d[i] >= peak_before_trough:
        recovery_idx = i
        BREAK

IF recovery_idx IS NOT None:
    mdd_recovery_months = (recovery_idx - mdd_trough_idx) / 21.0
    # 21영업일 ≈ 1개월
ELSE:
    mdd_recovery_months = 99    # 회복 미완료 → 장기 침체 처리

# ── 집합 변수 ─────────────────────────────────────────────
all_risk_grades = [market_grade, volatility_grade, liquidity_grade,
                   downside_grade, macro_grade]
critical_count  = LEN([g FOR g IN all_risk_grades IF g == 4])

# ── 알림 상태 ─────────────────────────────────────────────
any_critical_alert_active = ("Critical_Alert" IN active_alerts)
```

---

## 4. 실행 순서 및 GUARD

> **절대 순서** — GUARD 조건 미충족 시 해당 STEP 진입 차단, 폴백 실행

```
STEP 1  ── 데이터 수집                        [Layer 1]
  GUARD : 없음 (시작점)

STEP 2  ── 데이터 정제 + 지표 계산            [Layer 2]
  GUARD : STEP 1 완료 AND 필수 데이터 전체 수집 성공

STEP 3  ── 5개 리스크 등급 산출               [Layer 3]
  GUARD : STEP 2 완료 AND 전체 지표 계산 성공
  ├─ 3A  market_grade      ┐
  ├─ 3B  volatility_grade  │ 병렬 처리 가능
  ├─ 3C  liquidity_grade   │ (단, STEP 4 전 전부 완료 필수)
  ├─ 3D  downside_grade    ┘
  └─ 3E  macro_grade       ← 내부 직렬 처리 필수
           3E-1  level_grade    (GUARD: STEP 2 완료)
           3E-2  event_grade    (GUARD: 3E-1 완료)
           3E-3  macro_grade    (GUARD: 3E-2 완료)

STEP 4  ── Override 적용                      [Override Rules]
  GUARD : 3A·3B·3C·3D·3E 전부 완료
  순서  : OVR-01 → OVR-06 → OVR-02 → OVR-03 → OVR-04

STEP 5  ── 시장 국면 판단 + 가중치 선택       [Layer 4]
  GUARD : STEP 4 완료

STEP 6  ── 통합 점수 계산                     [Layer 4]
  GUARD : STEP 5 완료 (가중치 확정)

STEP 7  ── 전략 + 자산 배분 결정              [Layer 5]
  GUARD : STEP 6 완료 (integrated_score 확정)

STEP 8  ── 인사이트 생성                      [Layer 6]
  GUARD : STEP 7 완료

STEP 9  ── 알림 트리거 평가
  GUARD : STEP 6 AND STEP 7 AND STEP 8 완료

STEP 10 ── 시각화 출력                        [Layer 7]
  GUARD : STEP 9 완료
```

**GUARD 위반 시 공통 폴백**

```python
IF guard_condition == False:
    BLOCK current_step()
    SET error_flag = True
    IF STATE["prev_integrated_score"] IS NOT None:
        USE prev_day_data AS fallback
    DISPLAY "데이터 지연 알림" TO user
    LOG error_detail
```

---

## 5. Layer 1 — Data

### 수집 대상

| 변수 | 설명 | 소스 / 엔드포인트 | 주기 | 비고 |
|------|------|------------------|------|------|
| `kospi_ohlcv` | KOSPI 종합지수 OHLCV | 키움 REST API `ka20006` (inds_cd=`001`) | 일별 | 응답 지수값은 100배 → /100 보정 |
| `vol`, `val` | 거래량, 거래대금 | 키움 `ka20006` (`trde_qty`, `trde_prica`) | 일별 | OHLCV와 동일 응답에 포함 |
| `fi_net` | 외국인 순매수/매도 (시장 전체) | 키움 `ka10051` (inds_cd=`001_AL`, `frgnr_netprps`) | 일별 | 일별 스냅샷 → 영업일 루프, 단위 백만원 추정 |
| `vkospi` | VKOSPI 변동성 지수 | **Phase 1 보류** — 외부 소스(키움/ECOS/FDR/yfinance) 모두 미확보 | 일별 | Risk-B는 HV20 단독 산정 (아래 구현 노트 참조) |
| `fx_rate` | 원/달러 환율 (매매기준율) | ECOS `731Y001` / 항목 `0000001` | 일별 | |
| `base_rate` | 한국은행 기준금리 | ECOS `722Y001` / 항목 `0101000` | 일별 | 변경일 기준 step function |
| `cpi_yoy` | CPI 전년 동월 대비 (%) | ECOS `901Y009` / 항목 `0` (총지수) | 월별 | YoY는 12개월 차분 자체 계산 |
| `m2_growth_curr` | M2 통화량 전년 동월 대비 증가율 (%) | ECOS `161Y006` / 항목 `BBHA00` (M2 평잔 원계열) | 월별 | YoY는 12개월 차분 자체 계산 |
| `us_base_rate` | 미국 정책금리 | ECOS `902Y006` / 항목 `US` | 월별 | FRED 미사용 (ECOS 대체) |
| `bond_rate` | 국채금리 | 미사용 (Skills.md 본문에서 참조 없음) | — | `rate_spread`는 `base_rate − us_base_rate`로 산출 |

### 구현 노트 — VKOSPI 보류 처리 (Phase 1)

> **VKOSPI 외부 데이터 소스 미확보**로 Phase 1 구현에서는 Risk-B를 **HV20 단독**으로 등급 산정.
> CR-01의 `MAX(hv_grade, vkospi_grade)` 충돌 해소는 사실상 `volatility_grade = hv_grade`로 동작.
> Risk-B JSON 출력에서 `vkospi`, `vkospi_grade` 필드는 `null`로 직렬화.
> VKOSPI 데이터 소스 확보 시 fetcher 추가만으로 자동 활성화되도록 등급 산정 로직은 분기 처리 (HV20 단독 vs 둘 다 사용).

### 정제 로직

```python
FOR each data_source IN required_sources:
    IF data_source.date IS holiday OR non_business_day:
        data_source.value = prev_day.value          # Forward Fill

    IF ABS(data_source.value - rolling_mean) > 3 * rolling_std:
        SET data_source.outlier_flag = True
        data_source.value = rolling_mean            # 이상값 → 이동평균으로 대체

    IF api_call_failed:
        data_source.value = prev_day.value
        SET warning_flag = True
        DISPLAY "API 수집 실패 경고"

ALIGN all dates TO business_day_calendar
# 이종 데이터 간 날짜 인덱스 정합: 영업일 기준 캘린더 통일
IF score_comparison_needed:
    APPLY min_max_normalization TO comparison_set
```

---

## 6. Layer 2 — Indicator

### 계산 공식

| 변수명 | 계산식 | 단위 |
|--------|--------|------|
| `ma20` | Σ(close_t) / 20, t=최근 20영업일 | 가격 |
| `ma60` | Σ(close_t) / 60, t=최근 60영업일 | 가격 |
| `ma120` | Σ(close_t) / 120, t=최근 120영업일 | 가격 |
| `disp_ma20` | (close / ma20) × 100 | % |
| `disp_ma60` | (close / ma60) × 100 | % |
| `hv20` | σ(log(close_t / close_{t-1}), 최근20일) × √252 | 연율화 % |
| `hv60` | σ(log(close_t / close_{t-1}), 최근60일) × √252 | 연율화 % |
| `vol_ratio_hv` | hv20 / hv60 | 배수 |
| `mdd_60` | (MIN(close_60d) − MAX(close_60d)) / MAX(close_60d) × 100 | % |
| `mdd_252` | (MIN(close_252d) − MAX(close_252d)) / MAX(close_252d) × 100 | % |
| `var_95` | percentile(daily_returns_252d, 5) | % |
| `cvar` | MEAN(r FOR r IN daily_returns_252d IF r < var_95) | % |
| `vol_ratio` | current_volume / MA20_volume | 배수 |
| `val_ratio` | current_value / MA20_value | 배수 |
| `conc_ratio` | top10_stocks_value / total_market_value | % |
| `fi_5d_cum` | Σ(fi_net_t, t=최근 5영업일) | 조원 |
| `fi_monthly` | Σ(fi_net_t, t=당월 전체) | 조원 |
| `fi_streak_sell` | 연속 (fi_net_t < 0) 일수 카운트 | 일 |
| `fi_streak_buy` | 연속 (fi_net_t > 0) 일수 카운트 | 일 |
| `adx` | Wilder DI+·DI− 기반 ADX (14일 기준) | 수치 |
| `consec_decline` | 연속 (close_t < close_{t-1}) 일수 카운트 | 일 |
| `base_rate_delta` | base_rate_curr − base_rate_prev_month | %p |
| `cpi_delta` | cpi_yoy_curr − cpi_yoy_prev_month | %p |
| `rate_spread_curr` | kr_base_rate − us_base_rate | %p |
| `vol_streak` | 연속 (vol_ratio < 1.0) 일수 카운트 | 일 |

### 임계값 참조 테이블

| 변수 | 구간 | 분류 |
|------|------|------|
| `disp_ma20` | ≥ 98 AND ≤ 102 | 정상 |
| `disp_ma20` | [94, 98) | 하락 신호 |
| `disp_ma20` | [90, 94) | 강한 하락 |
| `disp_ma20` | < 90 | 극단 하락 (ALT-06 트리거) |
| `disp_ma60` | < 90 | 하락 추세 강화 |
| `disp_ma60` | ≤ 85 | 경고 임계 (ALT-06 트리거) |
| `hv20` | < 12% | Low |
| `hv20` | [12%, 20%) | Medium |
| `hv20` | [20%, 30%) | High |
| `hv20` | ≥ 30% | Critical |
| `vkospi` | < 15 | Low |
| `vkospi` | [15, 25) | Medium |
| `vkospi` | [25, 35) | High |
| `vkospi` | ≥ 35 | Critical |
| `vol_ratio_hv` | > 1.2 | 변동성 급등 |
| `vol_ratio_hv` | < 0.8 | 변동성 축소 |
| `vol_ratio` | ≥ 1.0 | 정상 |
| `vol_ratio` | [0.7, 1.0) | 축소 |
| `vol_ratio` | [0.5, 0.7) | 심각 |
| `vol_ratio` | < 0.5 | 위험 |
| `val_ratio` | < 0.6 | 경계 |
| `conc_ratio` | > 0.4 | 쏠림 |
| `adx` | > 25 | 추세 확립 |
| `adx` | [20, 25] | 전환 구간 |
| `adx` | < 20 | 횡보장 |
| `mdd_60` | > −5% | Low |
| `mdd_60` | [−10%, −5%] | Medium |
| `mdd_60` | (−20%, −10%) | High |
| `mdd_60` | ≤ −20% | Critical |
| `var_95` | > −1.5% | Low |
| `var_95` | [−2.5%, −1.5%] | Medium |
| `var_95` | (−3.5%, −2.5%) | High |
| `var_95` | ≤ −3.5% | Critical |

---

## 7. Layer 3 — Risk

> **공통 규칙**
> - 5개 리스크는 독립 실행 (상호 참조 금지)
> - 출력: integer 1~4
> - 2개 이상 지표가 동일 등급 지시 → 해당 등급 확정
> - 단일 Critical 지표 → Critical 가능 (Risk-D 제외 → OVR-06)

### 공통 JSON Output Schema 구조

> **모든 5개 리스크는 아래 최상위 구조를 동일하게 따른다. 예외 없음.**
> **최상위 필드는 정확히 6개**: `risk_id` · `grade` · `score` · `triggered_conditions` · `reason` · `details`

```json
{
  "risk_id":              "RISK-A | RISK-B | RISK-C | RISK-D | RISK-E",
  "grade":                1,
  "score":                1,
  "triggered_conditions": [],
  "reason":               "string",
  "details": {
    "risk_type":           "string",
    "grade_label":         "Low | Medium | High | Critical",
    "weight_default":      0.00,
    "timestamp":           "YYYY-MM-DD",
    "indicators":          {},
    "sub_grades":          {},
    "flags":               {},
    "conflict_rule":       "string | none",
    "condition_candidates": []
  }
}
```

**최상위 필드 정의** (정확히 6개):

| 필드 | 타입 | 설명 |
|------|------|------|
| `risk_id` | string | 리스크 식별자 (RISK-A~E, 불변) |
| `grade` | integer | 등급 수치 (1=Low, 2=Medium, 3=High, 4=Critical) |
| `score` | integer | `grade`와 동일값 — 외부 시스템 연동용 별칭 |
| `triggered_conditions` | array[string] | 런타임에 실제 발동된 조건 ID 목록 (기본값 `[]`) |
| `reason` | string | 등급 산출 근거 자연어 설명 |
| `details` | object | 모든 원본 데이터 (하위 필드 참조) |

**details 내부 필드 정의**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `details.risk_type` | string | 리스크 유형명 소문자 |
| `details.grade_label` | string | 등급 레이블 (Low/Medium/High/Critical) |
| `details.weight_default` | float | 기본 가중치 (국면 조정 미반영) |
| `details.timestamp` | string | 산출 기준 영업일 (YYYY-MM-DD) |
| `details.indicators` | object | 입력 지표 현재값 |
| `details.sub_grades` | object | 중간 등급값 (없으면 `{}`) |
| `details.flags` | object | 불리언 신호 플래그 |
| `details.conflict_rule` | string | 적용된 충돌 해소 규칙 |
| `details.condition_candidates` | array[string] | 이 리스크에서 발동 가능한 조건 ID 후보 전체 목록 |

---

### Risk-A: 시장 리스크 (Market Risk)

**기본 가중치**: 30%

#### JSON Output Schema

```json
{
  "risk_id": "RISK-A",
  "grade": 1,
  "score": 1,
  "triggered_conditions": [],
  "reason": "MA 배열 상태 + 이격도_MA20 + ADX + 연속 하락 일수 조합으로 등급 결정",
  "details": {
    "risk_type":      "market",
    "grade_label":    "Low | Medium | High | Critical",
    "weight_default": 0.30,
    "timestamp":      "YYYY-MM-DD",
    "indicators": {
      "ma20":           0.0,
      "ma60":           0.0,
      "ma120":          0.0,
      "disp_ma20":      0.0,
      "disp_ma60":      0.0,
      "adx":            0.0,
      "consec_decline": 0
    },
    "sub_grades": {},
    "flags": {
      "ma_bullish":      false,
      "ma_bearish_part": false,
      "ma_bearish_full": false
    },
    "conflict_rule": "none",
    "condition_candidates": [
      "ma_bearish_full",
      "ma_bearish_part",
      "ma_bullish",
      "composite_signal",
      "disp_ma20_lt_90",
      "disp_ma20_lt_94",
      "disp_ma20_lt_98",
      "adx_lt_20",
      "adx_gte_25",
      "consec_decline_gte_5",
      "consec_decline_gte_10"
    ]
  }
}
```

#### Grade Logic (IF/THEN — 미정의 함수 없음)

```python
output = {
    "risk_id": "RISK-A",
    "grade":   None,
    "score":   None,
    "triggered_conditions": [],
    "reason":  "",
    "details": {
        "risk_type":      "market",
        "grade_label":    "",
        "weight_default": 0.30,
        "timestamp":      "YYYY-MM-DD",
        "indicators": {
            "ma20":           ma20,
            "ma60":           ma60,
            "ma120":          ma120,
            "disp_ma20":      disp_ma20,
            "disp_ma60":      disp_ma60,
            "adx":            adx,
            "consec_decline": consec_decline
        },
        "sub_grades": {},
        "flags": {
            "ma_bullish":      ma_bullish,
            "ma_bearish_part": ma_bearish_part,
            "ma_bearish_full": ma_bearish_full
        },
        "conflict_rule": "none",
        "condition_candidates": [
            "ma_bearish_full", "ma_bearish_part", "ma_bullish", "composite_signal",
            "disp_ma20_lt_90", "disp_ma20_lt_94", "disp_ma20_lt_98",
            "adx_lt_20", "adx_gte_25", "consec_decline_gte_5", "consec_decline_gte_10"
        ]
    }
}

# ── 전제 계산 (Section 3에서 이미 산출) ────────────────────
# ma_bullish, ma_bearish_full, ma_bearish_part — Section 3 참조

# ── 1순위: Critical 조건 ──────────────────────────────────
IF ma_bearish_full AND disp_ma20 < 90 AND consec_decline >= 5:
    market_grade = 4    # Critical

# ── 2순위: High 조건 ──────────────────────────────────────
ELIF ma_bearish_full AND disp_ma20 >= 90 AND disp_ma20 < 94:
    market_grade = 3    # High

# ── 3순위: Medium 조건 ────────────────────────────────────
ELIF ma_bearish_part AND (
        (disp_ma20 >= 94 AND disp_ma20 < 98) OR adx < 20
     ):
    market_grade = 2    # Medium

# ── 4순위: Low 조건 ───────────────────────────────────────
ELIF ma_bullish AND disp_ma20 >= 98 AND disp_ma20 <= 102 AND adx > 25:
    market_grade = 1    # Low

# ── ELSE: 복합 신호 집계 (모든 함수 인라인 정의) ──────────
ELSE:
    # MA 배열 등급
    IF ma_bearish_full:   sig_ma = 4
    ELIF ma_bearish_part: sig_ma = 2
    ELIF ma_bullish:      sig_ma = 1
    ELSE:                 sig_ma = 2    # 중립

    # 이격도 등급
    IF disp_ma20 < 90:              sig_disp = 4
    ELIF disp_ma20 < 94:            sig_disp = 3
    ELIF disp_ma20 < 98:            sig_disp = 2
    ELSE:                           sig_disp = 1

    # ADX 등급
    IF adx < 20:                    sig_adx = 2    # 횡보
    ELIF adx <= 25:                 sig_adx = 2    # 전환
    ELSE:                           sig_adx = 1    # 추세 확립

    # 연속 하락 등급
    IF consec_decline >= 10:        sig_streak = 4
    ELIF consec_decline >= 5:       sig_streak = 3
    ELIF consec_decline >= 3:       sig_streak = 2
    ELSE:                           sig_streak = 1

    signal_grades = [sig_ma, sig_disp, sig_adx, sig_streak]

    # 최빈값 계산 (MODE 인라인)
    grade_count = {1: 0, 2: 0, 3: 0, 4: 0}
    FOR g IN signal_grades:
        grade_count[g] = grade_count[g] + 1

    max_count = MAX(grade_count[1], grade_count[2],
                    grade_count[3], grade_count[4])

    candidates = []
    IF grade_count[4] == max_count: candidates.APPEND(4)
    IF grade_count[3] == max_count: candidates.APPEND(3)
    IF grade_count[2] == max_count: candidates.APPEND(2)
    IF grade_count[1] == max_count: candidates.APPEND(1)

    IF LEN(candidates) == 1:
        market_grade = candidates[0]
    ELSE:
        market_grade = MAX(candidates)    # 동점 시 보수적 적용

# ── triggered_conditions 수집 ────────────────────────────
triggered_conditions = []

IF ma_bearish_full:               triggered_conditions.APPEND("ma_bearish_full")
ELIF ma_bearish_part:             triggered_conditions.APPEND("ma_bearish_part")
ELIF ma_bullish:                  triggered_conditions.APPEND("ma_bullish")
ELSE:                             triggered_conditions.APPEND("composite_signal")

IF disp_ma20 < 90:               triggered_conditions.APPEND("disp_ma20_lt_90")
ELIF disp_ma20 < 94:             triggered_conditions.APPEND("disp_ma20_lt_94")
ELIF disp_ma20 < 98:             triggered_conditions.APPEND("disp_ma20_lt_98")

IF adx < 20:                     triggered_conditions.APPEND("adx_lt_20")
ELIF adx > 25:                   triggered_conditions.APPEND("adx_gte_25")

IF consec_decline >= 10:         triggered_conditions.APPEND("consec_decline_gte_10")
ELIF consec_decline >= 5:        triggered_conditions.APPEND("consec_decline_gte_5")

# ── JSON 출력 연결 ────────────────────────────────────────
output["triggered_conditions"] = triggered_conditions
output["reason"] = "market_risk grade=" + STRING(market_grade) + " based on " + JOIN(triggered_conditions, ", ")
output["grade"] = market_grade
output["score"] = market_grade

RETURN output
```

---

### Risk-B: 변동성 리스크 (Volatility Risk)

**기본 가중치**: 25%

#### JSON Output Schema

```json
{
  "risk_id": "RISK-B",
  "grade": 1,
  "score": 1,
  "triggered_conditions": [],
  "reason": "HV20 등급과 VKOSPI 등급 중 CR-01(MAX) 적용 결과로 최종 등급 결정",
  "details": {
    "risk_type":      "volatility",
    "grade_label":    "Low | Medium | High | Critical",
    "weight_default": 0.25,
    "timestamp":      "YYYY-MM-DD",
    "indicators": {
      "hv20":         0.0,
      "hv60":         0.0,
      "vol_ratio_hv": 0.0,
      "vkospi":       0.0
    },
    "sub_grades": {
      "hv_grade":     1,
      "vkospi_grade": 1
    },
    "flags": {
      "vol_spike":       false,
      "vol_contraction": false
    },
    "conflict_rule": "MAX(hv_grade, vkospi_grade)",
    "condition_candidates": [
      "hv20_lt_12",
      "hv20_gte_12",
      "hv20_gte_20",
      "hv20_gte_30",
      "vkospi_lt_15",
      "vkospi_gte_15",
      "vkospi_gte_25",
      "vkospi_gte_35",
      "cr01_max_applied"
    ]
  }
}
```

#### Grade Logic (IF/THEN)

```python
output = {
    "risk_id": "RISK-B",
    "grade":   None,
    "score":   None,
    "triggered_conditions": [],
    "reason":  "",
    "details": {
        "risk_type":      "volatility",
        "grade_label":    "",
        "weight_default": 0.25,
        "timestamp":      "YYYY-MM-DD",
        "indicators": {
            "hv20":         hv20,
            "hv60":         hv60,
            "vol_ratio_hv": vol_ratio_hv,
            "vkospi":       vkospi
        },
        "sub_grades": {
            "hv_grade":     None,
            "vkospi_grade": None
        },
        "flags": {
            "vol_spike":       False,
            "vol_contraction": False
        },
        "conflict_rule": "MAX(hv_grade, vkospi_grade)",
        "condition_candidates": [
            "hv20_lt_12", "hv20_gte_12", "hv20_gte_20", "hv20_gte_30",
            "vkospi_lt_15", "vkospi_gte_15", "vkospi_gte_25", "vkospi_gte_35",
            "cr01_max_applied"
        ]
    }
}

# ── HV20 등급 ────────────────────────────────────────────
IF hv20 >= 30:    hv_grade = 4    # Critical
ELIF hv20 >= 20:  hv_grade = 3    # High
ELIF hv20 >= 12:  hv_grade = 2    # Medium
ELSE:             hv_grade = 1    # Low

# ── VKOSPI 등급 ──────────────────────────────────────────
IF vkospi >= 35:   vkospi_grade = 4    # Critical
ELIF vkospi >= 25: vkospi_grade = 3    # High
ELIF vkospi >= 15: vkospi_grade = 2    # Medium
ELSE:              vkospi_grade = 1    # Low

# ── CR-01 충돌 해소 (IF/THEN) ────────────────────────────
IF hv_grade != vkospi_grade:
    volatility_grade = MAX(hv_grade, vkospi_grade)
ELSE:
    volatility_grade = hv_grade

# ── 보조 플래그 ───────────────────────────────────────────
IF vol_ratio_hv > 1.2:
    vol_spike = True
ELSE:
    vol_spike = False

IF vol_ratio_hv < 0.8:
    vol_contraction = True
ELSE:
    vol_contraction = False

# ── triggered_conditions 수집 ────────────────────────────
triggered_conditions = []

IF hv20 >= 30:    triggered_conditions.APPEND("hv20_gte_30")
ELIF hv20 >= 20:  triggered_conditions.APPEND("hv20_gte_20")
ELIF hv20 >= 12:  triggered_conditions.APPEND("hv20_gte_12")
ELSE:             triggered_conditions.APPEND("hv20_lt_12")

IF vkospi >= 35:   triggered_conditions.APPEND("vkospi_gte_35")
ELIF vkospi >= 25: triggered_conditions.APPEND("vkospi_gte_25")
ELIF vkospi >= 15: triggered_conditions.APPEND("vkospi_gte_15")
ELSE:              triggered_conditions.APPEND("vkospi_lt_15")

IF hv_grade != vkospi_grade:
    triggered_conditions.APPEND("cr01_max_applied")

# ── JSON 출력 연결 ────────────────────────────────────────
output["triggered_conditions"] = triggered_conditions
output["reason"] = "volatility_risk grade=" + STRING(volatility_grade) + " based on " + JOIN(triggered_conditions, ", ")
output["grade"] = volatility_grade
output["score"] = volatility_grade

RETURN output
```

---

### Risk-C: 유동성 리스크 (Liquidity Risk)

**기본 가중치**: 15%

#### JSON Output Schema

```json
{
  "risk_id": "RISK-C",
  "grade": 1,
  "score": 1,
  "triggered_conditions": [],
  "reason": "거래량 비율 + 연속 감소 일수 기준 기본 등급 결정; val_ratio·conc_ratio로 최솟값 Medium 보정 적용",
  "details": {
    "risk_type":      "liquidity",
    "grade_label":    "Low | Medium | High | Critical",
    "weight_default": 0.15,
    "timestamp":      "YYYY-MM-DD",
    "indicators": {
      "vol_ratio":  0.0,
      "val_ratio":  0.0,
      "conc_ratio": 0.0,
      "vol_streak": 0
    },
    "sub_grades": {},
    "flags": {
      "concentration_high": false,
      "val_ratio_warning":  false
    },
    "conflict_rule": "none",
    "condition_candidates": [
      "vol_ratio_gte_1.0",
      "vol_ratio_0.7_to_1.0",
      "vol_ratio_0.5_to_0.7",
      "vol_ratio_lt_0.5",
      "vol_streak_gte_3",
      "vol_streak_gte_5",
      "val_ratio_lt_0.6",
      "conc_ratio_gt_0.4"
    ]
  }
}
```

#### Grade Logic (IF/THEN)

```python
output = {
    "risk_id": "RISK-C",
    "grade":   None,
    "score":   None,
    "triggered_conditions": [],
    "reason":  "",
    "details": {
        "risk_type":      "liquidity",
        "grade_label":    "",
        "weight_default": 0.15,
        "timestamp":      "YYYY-MM-DD",
        "indicators": {
            "vol_ratio":  vol_ratio,
            "val_ratio":  val_ratio,
            "conc_ratio": conc_ratio,
            "vol_streak": vol_streak
        },
        "sub_grades": {},
        "flags": {
            "concentration_high": False,
            "val_ratio_warning":  False
        },
        "conflict_rule": "none",
        "condition_candidates": [
            "vol_ratio_gte_1.0", "vol_ratio_0.7_to_1.0",
            "vol_ratio_0.5_to_0.7", "vol_ratio_lt_0.5",
            "vol_streak_gte_3", "vol_streak_gte_5",
            "val_ratio_lt_0.6", "conc_ratio_gt_0.4"
        ]
    }
}

# ── 기본 등급: vol_ratio + vol_streak 기준 ────────────────
IF vol_ratio < 0.5 AND vol_streak >= 5:
    liquidity_grade = 4    # Critical

ELIF vol_ratio >= 0.5 AND vol_ratio < 0.7 AND vol_streak >= 3:
    liquidity_grade = 3    # High

ELIF vol_ratio >= 0.7 AND vol_ratio < 1.0:
    liquidity_grade = 2    # Medium

ELIF vol_ratio >= 1.0:
    liquidity_grade = 1    # Low

ELSE:
    liquidity_grade = 2    # 기본 Medium (예외 케이스 처리)

# ── 보조 지표 최솟값 보정 ────────────────────────────────
IF val_ratio < 0.6:
    val_ratio_warning = True
    IF liquidity_grade < 2:
        liquidity_grade = 2    # 최소 Medium 보장
ELSE:
    val_ratio_warning = False

IF conc_ratio > 0.4:
    concentration_high = True
    IF liquidity_grade < 2:
        liquidity_grade = 2    # 최소 Medium 보장
ELSE:
    concentration_high = False

# ── triggered_conditions 수집 ────────────────────────────
triggered_conditions = []

IF vol_ratio < 0.5:   triggered_conditions.APPEND("vol_ratio_lt_0.5")
ELIF vol_ratio < 0.7: triggered_conditions.APPEND("vol_ratio_0.5_to_0.7")
ELIF vol_ratio < 1.0: triggered_conditions.APPEND("vol_ratio_0.7_to_1.0")
ELSE:                 triggered_conditions.APPEND("vol_ratio_gte_1.0")

IF vol_streak >= 5:   triggered_conditions.APPEND("vol_streak_gte_5")
ELIF vol_streak >= 3: triggered_conditions.APPEND("vol_streak_gte_3")

IF val_ratio < 0.6:   triggered_conditions.APPEND("val_ratio_lt_0.6")
IF conc_ratio > 0.4:  triggered_conditions.APPEND("conc_ratio_gt_0.4")

# ── JSON 출력 연결 ────────────────────────────────────────
output["triggered_conditions"] = triggered_conditions
output["reason"] = "liquidity_risk grade=" + STRING(liquidity_grade) + " based on " + JOIN(triggered_conditions, ", ")
output["grade"] = liquidity_grade
output["score"] = liquidity_grade

RETURN output
```

---

### Risk-D: 하방 리스크 (Downside Risk)

**기본 가중치**: 10%

> **단일 Critical 예외**: Risk-D만 단독 Critical → 전체 시스템 자동 격상 없음 (OVR-06)

#### JSON Output Schema

```json
{
  "risk_id": "RISK-D",
  "grade": 1,
  "score": 1,
  "triggered_conditions": [],
  "reason": "MDD_60 등급과 VaR_95 등급 중 CR-02(MAX) 적용; 하방 단독 Critical 시 OVR-06 예외 처리",
  "details": {
    "risk_type":      "downside",
    "grade_label":    "Low | Medium | High | Critical",
    "weight_default": 0.10,
    "timestamp":      "YYYY-MM-DD",
    "indicators": {
      "mdd_60":  0.0,
      "mdd_252": 0.0,
      "var_95":  0.0,
      "cvar":    0.0
    },
    "sub_grades": {
      "mdd_grade": 1,
      "var_grade": 1
    },
    "flags": {
      "recovery_signal": "fast | slow | unknown"
    },
    "conflict_rule": "MAX(mdd_grade, var_grade)",
    "condition_candidates": [
      "mdd_60_gt_minus5",
      "mdd_60_lte_minus5",
      "mdd_60_lte_minus10",
      "mdd_60_lte_minus20",
      "var_95_gt_minus1.5",
      "var_95_lte_minus1.5",
      "var_95_lte_minus2.5",
      "var_95_lte_minus3.5",
      "cr02_max_applied",
      "ovr06_single_critical_exception"
    ]
  }
}
```

#### Grade Logic (IF/THEN)

```python
output = {
    "risk_id": "RISK-D",
    "grade":   None,
    "score":   None,
    "triggered_conditions": [],
    "reason":  "",
    "details": {
        "risk_type":      "downside",
        "grade_label":    "",
        "weight_default": 0.10,
        "timestamp":      "YYYY-MM-DD",
        "indicators": {
            "mdd_60":  mdd_60,
            "mdd_252": mdd_252,
            "var_95":  var_95,
            "cvar":    cvar
        },
        "sub_grades": {
            "mdd_grade": None,
            "var_grade": None
        },
        "flags": {
            "recovery_signal": None
        },
        "conflict_rule": "MAX(mdd_grade, var_grade)",
        "condition_candidates": [
            "mdd_60_gt_minus5", "mdd_60_lte_minus5",
            "mdd_60_lte_minus10", "mdd_60_lte_minus20",
            "var_95_gt_minus1.5", "var_95_lte_minus1.5",
            "var_95_lte_minus2.5", "var_95_lte_minus3.5",
            "cr02_max_applied", "ovr06_single_critical_exception"
        ]
    }
}

# ── MDD_60 등급 ───────────────────────────────────────────
IF mdd_60 <= -20:         mdd_grade = 4    # Critical
ELIF mdd_60 <= -10:       mdd_grade = 3    # High
ELIF mdd_60 <= -5:        mdd_grade = 2    # Medium
ELSE:                     mdd_grade = 1    # Low

# ── VaR_95 등급 ───────────────────────────────────────────
IF var_95 <= -3.5:        var_grade = 4    # Critical
ELIF var_95 <= -2.5:      var_grade = 3    # High
ELIF var_95 <= -1.5:      var_grade = 2    # Medium
ELSE:                     var_grade = 1    # Low

# ── CR-02 충돌 해소 (IF/THEN) ────────────────────────────
IF mdd_grade != var_grade:
    downside_grade = MAX(mdd_grade, var_grade)
ELSE:
    downside_grade = mdd_grade

# ── 회복 기간 플래그 (Section 3에서 산출된 mdd_recovery_months 사용)
IF mdd_recovery_months < 3:
    recovery_signal = "fast"
ELIF mdd_recovery_months > 6:
    recovery_signal = "slow"
ELSE:
    recovery_signal = "unknown"

# ── triggered_conditions 수집 ────────────────────────────
triggered_conditions = []

IF mdd_60 <= -20:    triggered_conditions.APPEND("mdd_60_lte_minus20")
ELIF mdd_60 <= -10:  triggered_conditions.APPEND("mdd_60_lte_minus10")
ELIF mdd_60 <= -5:   triggered_conditions.APPEND("mdd_60_lte_minus5")
ELSE:                triggered_conditions.APPEND("mdd_60_gt_minus5")

IF var_95 <= -3.5:   triggered_conditions.APPEND("var_95_lte_minus3.5")
ELIF var_95 <= -2.5: triggered_conditions.APPEND("var_95_lte_minus2.5")
ELIF var_95 <= -1.5: triggered_conditions.APPEND("var_95_lte_minus1.5")
ELSE:                triggered_conditions.APPEND("var_95_gt_minus1.5")

IF mdd_grade != var_grade:
    triggered_conditions.APPEND("cr02_max_applied")
# ovr06_single_critical_exception: STEP 4에서 타 등급 확정 후 평가

# ── JSON 출력 연결 ────────────────────────────────────────
output["triggered_conditions"] = triggered_conditions
output["reason"] = "downside_risk grade=" + STRING(downside_grade) + " based on " + JOIN(triggered_conditions, ", ")
output["grade"] = downside_grade
output["score"] = downside_grade

RETURN output
```

---

### Risk-E: 매크로 리스크 (Macro Risk)

**기본 가중치**: 20%

> **처리 규칙**: 3E-1 → 3E-2 → 3E-3 직렬 처리 필수.
> 이전 단계 완료 전 다음 단계 진입 BLOCK.

#### JSON Output Schema

```json
{
  "risk_id": "RISK-E",
  "grade": 1,
  "score": 1,
  "triggered_conditions": [],
  "reason": "3E-1 수준 판정 → 3E-2 이벤트 조정(net_delta) → 3E-3 시나리오 발동 시 Critical 강제 격상",
  "details": {
    "risk_type":      "macro",
    "grade_label":    "Low | Medium | High | Critical",
    "weight_default": 0.20,
    "timestamp":      "YYYY-MM-DD",
    "indicators": {
      "fx_rate":          0.0,
      "base_rate_delta":  0.0,
      "rate_spread_curr": 0.0,
      "cpi_yoy":          0.0,
      "fi_monthly":       0.0,
      "m2_growth_curr":   0.0
    },
    "sub_grades": {
      "level_grade": 1,
      "event_grade": 1
    },
    "flags": {
      "triggered_scenario": null,
      "scn04_flag":         false,
      "active_up_events":   [],
      "active_down_events": []
    },
    "conflict_rule": "3E-3_scenario_override",
    "condition_candidates": [
      "3E1_danger_count_gte_2",
      "3E1_caution_count_gte_1",
      "3E1_all_stable",
      "EVT_01",
      "EVT_02",
      "EVT_03",
      "EVT_04",
      "EVT_05",
      "EVT_06",
      "EVT_08",
      "EVT_09",
      "EVT_10",
      "SCN-01",
      "SCN-02",
      "SCN-03",
      "SCN-04"
    ]
  }
}
```

---

#### 3E-1. 수준 판정 (Level Assessment)

**출력**: `level_grade` (임시 등급, 최대 3 — Critical 도달 불가)

##### 지표 구간 분류

| 변수 | stable | caution | danger |
|------|--------|---------|--------|
| `fx_rate` | < 1,300원 | 1,300~1,400원 | > 1,400원 |
| `base_rate_delta` | ≤ 0 (동결·인하) | +0.25%p | ≥ +0.50%p |
| `rate_spread_curr` | > 0 (양수) | 0 ~ −0.5%p | < −0.5%p |
| `cpi_yoy` | < 2.5% | 2.5~4.0% | > 4.0% |
| `fi_monthly` | > 0 (양수) | −1조 ~ 0 | < −2조 |
| `m2_growth_curr` | 정상 증가 | 둔화 | 급감 or 음수 |

##### Grade Logic (IF/THEN — COUNT 인라인 전개)

```python
output = {
    "risk_id": "RISK-E",
    "grade":   None,
    "score":   None,
    "triggered_conditions": [],
    "reason":  "",
    "details": {
        "risk_type":      "macro",
        "grade_label":    "",
        "weight_default": 0.20,
        "timestamp":      "YYYY-MM-DD",
        "indicators": {
            "fx_rate":          fx_rate,
            "base_rate_delta":  base_rate_delta,
            "rate_spread_curr": rate_spread_curr,
            "cpi_yoy":          cpi_yoy,
            "fi_monthly":       fi_monthly,
            "m2_growth_curr":   m2_growth_curr
        },
        "sub_grades": {
            "level_grade": None,
            "event_grade": None
        },
        "flags": {
            "triggered_scenario": None,
            "scn04_flag":         False,
            "active_up_events":   [],
            "active_down_events": []
        },
        "conflict_rule": "3E-3_scenario_override",
        "condition_candidates": [
            "3E1_danger_count_gte_2", "3E1_caution_count_gte_1", "3E1_all_stable",
            "EVT_01", "EVT_02", "EVT_03", "EVT_04", "EVT_05", "EVT_06",
            "EVT_08", "EVT_09", "EVT_10",
            "SCN-01", "SCN-02", "SCN-03", "SCN-04"
        ]
    }
}

# ── 지표별 구간 판단 → danger_count / caution_count 집계 ──
danger_count  = 0
caution_count = 0

# fx_rate
IF fx_rate > 1400:
    danger_count = danger_count + 1
ELIF fx_rate >= 1300:
    caution_count = caution_count + 1

# base_rate_delta
IF base_rate_delta >= 0.50:
    danger_count = danger_count + 1
ELIF base_rate_delta >= 0.25:
    caution_count = caution_count + 1

# rate_spread_curr
IF rate_spread_curr < -0.5:
    danger_count = danger_count + 1
ELIF rate_spread_curr <= 0:
    caution_count = caution_count + 1

# cpi_yoy
IF cpi_yoy > 4.0:
    danger_count = danger_count + 1
ELIF cpi_yoy >= 2.5:
    caution_count = caution_count + 1

# fi_monthly
IF fi_monthly < -2.0:
    danger_count = danger_count + 1
ELIF fi_monthly < 0:
    caution_count = caution_count + 1

# m2_growth_curr
IF m2_contraction:                 # Section 3에서 산출
    danger_count = danger_count + 1
ELIF m2_growth_slowdown:           # Section 3에서 산출
    caution_count = caution_count + 1

# ── 임시 등급 산출 ────────────────────────────────────────
IF danger_count >= 2:
    level_grade = 3    # High  (1단계 최대: 3, Critical 불가)
ELIF caution_count >= 1:
    level_grade = 2    # Medium
ELSE:
    level_grade = 1    # Low

RETURN level_grade
```

---

#### 3E-2. 이벤트 탐지 (Event Detection)

**선행 조건**: `level_grade` 확정
**출력**: `event_grade`

##### 이벤트 정의

| ID | 이벤트명 | 탐지 조건 | 방향 |
|----|---------|-----------|------|
| EVT-01 | FX Spike | `fx_weekly_change > 0.03` OR `fx_daily_change > 0.015` | 상향 +1 |
| EVT-02 | Foreign Exodus | `fi_streak_sell >= 5` AND `fi_5d_cum < -1.0` | 상향 +1 |
| EVT-03 | Rate Hike | `base_rate_delta >= 0.25` | 상향 +1 |
| EVT-04 | CPI Surge | `cpi_delta >= 0.5` | 상향 +1 |
| EVT-05 | Yield Inversion | `rate_spread_prev > 0` AND `rate_spread_curr <= 0` | 상향 +1 |
| EVT-06 | Liquidity Contraction | `m2_contraction == True` | 상향 +1 |
| EVT-07 | FX Drop | `fx_weekly_change < -0.03` | **등급 하향 없음** (섹터 연동 검토만) |
| EVT-08 | Foreign Return | `fi_streak_buy >= 5` AND `fi_5d_cum > 0.5` | 하향 −1 |
| EVT-09 | Rate Cut | `base_rate_delta <= -0.25` | 하향 −1 |
| EVT-10 | Liquidity Expansion | `m2_expansion == True` | 하향 −1 |

##### Grade Logic (IF/THEN)

```python
# ── 이벤트 활성화 탐지 (모든 변수 Section 3에서 정의됨) ──
EVT_01 = (fx_weekly_change > 0.03) OR (fx_daily_change > 0.015)
EVT_02 = (fi_streak_sell >= 5) AND (fi_5d_cum < -1.0)
EVT_03 = (base_rate_delta >= 0.25)
EVT_04 = (cpi_delta >= 0.5)
EVT_05 = (rate_spread_prev > 0) AND (rate_spread_curr <= 0)
EVT_06 = (m2_contraction == True)
EVT_07 = (fx_weekly_change < -0.03)      # 탐지만, down_count 미포함
EVT_08 = (fi_streak_buy >= 5) AND (fi_5d_cum > 0.5)
EVT_09 = (base_rate_delta <= -0.25)
EVT_10 = (m2_expansion == True)

# ── 집계 ─────────────────────────────────────────────────
up_count   = 0
down_count = 0

IF EVT_01: up_count   = up_count + 1
IF EVT_02: up_count   = up_count + 1
IF EVT_03: up_count   = up_count + 1
IF EVT_04: up_count   = up_count + 1
IF EVT_05: up_count   = up_count + 1
IF EVT_06: up_count   = up_count + 1
# EVT_07: down_count에 포함하지 않음
IF EVT_08: down_count = down_count + 1
IF EVT_09: down_count = down_count + 1
IF EVT_10: down_count = down_count + 1

net_delta = up_count - down_count

# ── 중첩 상향 규칙 ────────────────────────────────────────
IF up_count >= 2:
    net_delta = net_delta + 1    # 추가 +1

# ── 조정 등급 산출 (CLAMP 인라인) ────────────────────────
raw_event_grade = level_grade + net_delta
IF raw_event_grade < 1:   event_grade = 1
ELIF raw_event_grade > 4: event_grade = 4
ELSE:                     event_grade = raw_event_grade

# ── 활성 이벤트 목록 기록 (JSON 출력용) ──────────────────
active_up_events   = []
active_down_events = []
IF EVT_01: active_up_events.APPEND("EVT-01")
IF EVT_02: active_up_events.APPEND("EVT-02")
IF EVT_03: active_up_events.APPEND("EVT-03")
IF EVT_04: active_up_events.APPEND("EVT-04")
IF EVT_05: active_up_events.APPEND("EVT-05")
IF EVT_06: active_up_events.APPEND("EVT-06")
IF EVT_08: active_down_events.APPEND("EVT-08")
IF EVT_09: active_down_events.APPEND("EVT-09")
IF EVT_10: active_down_events.APPEND("EVT-10")

RETURN event_grade
```

---

#### 3E-3. 복합 시나리오 판별 (Composite Scenario)

**선행 조건**: `event_grade` 확정
**출력**: `macro_grade`, `triggered_scenario`, `scn04_flag`

##### 시나리오 정의

| ID | 시나리오명 | 트리거 조건 (AND) | 시장 영향 |
|----|-----------|-----------------|-----------|
| SCN-01 | Capital Flight | EVT_01 AND EVT_02 | 외국인 매도 가속, 환율·주가 동반 악화 |
| SCN-02 | Tightening Squeeze | EVT_03 AND EVT_04 | 추가 긴축 불가피, 성장주·중소형주 타격 |
| SCN-03 | Stagflation Alert | EVT_04 AND EVT_02 AND EVT_03 | 경기 둔화 + 물가 상승 동시 |
| SCN-04 | Liquidity Crisis | EVT_01 AND EVT_03 AND EVT_02 | 유동성 급감, 신용경색 가능성 |

##### 시나리오별 긴급 대응

| ID | 긴급 대응 |
|----|-----------|
| SCN-01 | 주식 비중 최소화, 달러 헤지 실행 |
| SCN-02 | 성장주 축소, 가치주·배당주 전환, 채권 듀레이션 축소 |
| SCN-03 | 전면 방어 전환, 금 비중 확대, 현금 극대화 |
| SCN-04 | 모든 위험자산 포지션 청산 권장 |

##### Grade Logic (IF/THEN)

```python
# ── 검사 순서: 강도 높은 시나리오 먼저 ──────────────────
# SCN-04: 3개 이벤트 (가장 강함)
IF EVT_01 AND EVT_03 AND EVT_02:
    triggered_scenario = "SCN-04"
    macro_grade        = 4          # Critical 강제 (1·2단계 무시)
    scn04_flag         = True

# SCN-03: 3개 이벤트
ELIF EVT_04 AND EVT_02 AND EVT_03:
    triggered_scenario = "SCN-03"
    macro_grade        = 4          # Critical 강제
    scn04_flag         = False

# SCN-02: 2개 이벤트
ELIF EVT_03 AND EVT_04:
    triggered_scenario = "SCN-02"
    macro_grade        = 4          # Critical 강제
    scn04_flag         = False

# SCN-01: 2개 이벤트
ELIF EVT_01 AND EVT_02:
    triggered_scenario = "SCN-01"
    macro_grade        = 4          # Critical 강제
    scn04_flag         = False

# 미발동
ELSE:
    triggered_scenario = None
    macro_grade        = event_grade    # 3E-2 결과 그대로
    scn04_flag         = False

# ── triggered_conditions 수집 (3E-1 + 3E-2 + 3E-3 통합) ─
triggered_conditions = []

# 3E-1: 수준 판정 결과
IF danger_count >= 2:    triggered_conditions.APPEND("3E1_danger_count_gte_2")
ELIF caution_count >= 1: triggered_conditions.APPEND("3E1_caution_count_gte_1")
ELSE:                    triggered_conditions.APPEND("3E1_all_stable")

# 3E-2: 활성 이벤트
IF EVT_01: triggered_conditions.APPEND("EVT_01")
IF EVT_02: triggered_conditions.APPEND("EVT_02")
IF EVT_03: triggered_conditions.APPEND("EVT_03")
IF EVT_04: triggered_conditions.APPEND("EVT_04")
IF EVT_05: triggered_conditions.APPEND("EVT_05")
IF EVT_06: triggered_conditions.APPEND("EVT_06")
IF EVT_08: triggered_conditions.APPEND("EVT_08")
IF EVT_09: triggered_conditions.APPEND("EVT_09")
IF EVT_10: triggered_conditions.APPEND("EVT_10")

# 3E-3: 발동 시나리오
IF triggered_scenario == "SCN-04": triggered_conditions.APPEND("SCN-04")
ELIF triggered_scenario == "SCN-03": triggered_conditions.APPEND("SCN-03")
ELIF triggered_scenario == "SCN-02": triggered_conditions.APPEND("SCN-02")
ELIF triggered_scenario == "SCN-01": triggered_conditions.APPEND("SCN-01")

# ── JSON 출력 연결 ────────────────────────────────────────
output["triggered_conditions"] = triggered_conditions
output["reason"] = "macro_risk grade=" + STRING(macro_grade) + " based on " + JOIN(triggered_conditions, ", ")
output["grade"] = macro_grade
output["score"] = macro_grade

RETURN output
```

> **SCN-04 Extreme 해석**: `macro_grade` 자체는 4(Critical)가 최댓값.
> `scn04_flag == True`일 때 Scoring Layer에서 `integrated_score >= 3.0`이면 `score_band = "Extreme"`.

#### 매크로 최종 등급 흐름 요약

```
3E-1 → level_grade  ∈ {1, 2, 3}          (임시 등급, Critical 불가)
  ↓
3E-2 → event_grade  = CLAMP(level_grade + net_delta, 1, 4)
  ↓
3E-3 → IF scenario triggered:
            macro_grade = 4  (Critical, 1·2단계 무시)
        ELSE:
            macro_grade = event_grade
```

**최종 등급 기준표**

| 등급 | 조건 |
|------|------|
| Low (1) | 전 지표 안정 + 이벤트 없음 + 시나리오 미발동 |
| Medium (2) | 경계 지표 1~2개 + 이벤트 ≤ 1개 |
| High (3) | 위험 지표 ≥ 2개 + 이벤트 ≥ 2개 동시 발생 |
| Critical (4) | 시나리오 발동 (1·2단계 결과 전부 무시) |

---

## 8. Layer 4 — Scoring

**선행 조건**: STEP 4 (Override) 완료

### 시장 국면 판단 (IF/THEN)

```python
# ── 전제 계산 (Section 3에서 산출됨) ─────────────────────
# ma_bullish, ma_bearish_full, ma_converging — Section 3 참조

bullish_phase  = ma_bullish AND (adx > 25)
bearish_phase  = ma_bearish_full AND (consec_decline >= 3)
sideways_phase = (adx < 20) OR ma_converging

# ── 국면 선택 (CR-05: 충돌 시 하락장 우선) ───────────────
IF bearish_phase:
    market_phase = "bearish"
    W1, W2, W3, W4, W5 = 0.30, 0.25, 0.20, 0.10, 0.15

ELIF bullish_phase:
    market_phase = "bullish"
    W1, W2, W3, W4, W5 = 0.30, 0.25, 0.20, 0.15, 0.10

ELIF sideways_phase:
    market_phase = "sideways"
    W1, W2, W3, W4, W5 = 0.20, 0.25, 0.20, 0.20, 0.15

ELSE:
    market_phase = "bullish"    # 기본값 (조건 미충족 시)
    W1, W2, W3, W4, W5 = 0.30, 0.25, 0.20, 0.15, 0.10
```

### 동적 가중치 테이블

| 리스크 | W_bullish | W_bearish | W_sideways |
|--------|-----------|-----------|------------|
| 시장 (W1) | 0.30 | 0.30 | 0.20 |
| 변동성 (W2) | 0.25 | 0.25 | 0.25 |
| 매크로 (W3) | 0.20 | 0.20 | 0.20 |
| 유동성 (W4) | 0.15 | 0.10 | 0.20 |
| 하방 (W5) | 0.10 | 0.15 | 0.15 |
| 합계 | 1.00 | 1.00 | 1.00 |

### 통합 점수 계산

```python
integrated_score = (
    market_grade     * W1 +
    volatility_grade * W2 +
    macro_grade      * W3 +
    liquidity_grade  * W4 +
    downside_grade   * W5
)
# 범위: 1.0 (전체 Low) ~ 4.0 (전체 Critical)

# ── 점수 구간 매핑 (IF/THEN, 경계값 상위 구간 적용) ───────
IF integrated_score >= 3.0:   score_band = "Extreme"
ELIF integrated_score >= 2.5: score_band = "Danger"
ELIF integrated_score >= 2.0: score_band = "Alert"
ELIF integrated_score >= 1.5: score_band = "Caution"
ELSE:                         score_band = "Safe"

# ── SCN-04 Extreme 명시 확인 ─────────────────────────────
IF scn04_flag AND integrated_score >= 3.0:
    score_band = "Extreme"

# ── 리스크 기여도 ─────────────────────────────────────────
contribution_market     = (market_grade     * W1) / integrated_score * 100
contribution_volatility = (volatility_grade * W2) / integrated_score * 100
contribution_macro      = (macro_grade      * W3) / integrated_score * 100
contribution_liquidity  = (liquidity_grade  * W4) / integrated_score * 100
contribution_downside   = (downside_grade   * W5) / integrated_score * 100
```

### 계산 예시

| 리스크 | 등급 | 점수 | 가중치 | 기여 |
|--------|------|------|--------|------|
| 시장 | High(3) | 3 | 0.30 | 0.90 |
| 변동성 | High(3) | 3 | 0.25 | 0.75 |
| 매크로 | Medium(2) | 2 | 0.20 | 0.40 |
| 유동성 | Medium(2) | 2 | 0.15 | 0.30 |
| 하방 | High(3) | 3 | 0.10 | 0.30 |
| **통합** | | | | **2.65 → Danger** |

---

## 9. Layer 5 — Strategy

**선행 조건**: `integrated_score` 확정

### 기본 전략 매핑

| score_band | strategy | 주식 | 채권 | 현금 | 핵심 행동 |
|-----------|---------|------|------|------|-----------|
| Safe | Aggressive (1) | 80~100% | 0~10% | 0~10% | 성장주 확대, 레버리지 가능 |
| Caution | Moderate_Aggressive (2) | 60~80% | 10~20% | 10~20% | 우량주 중심, 채권 일부 편입 |
| Alert | Moderate_Defensive (3) | 30~50% | 20~30% | 20~40% | 저변동 섹터, 채권 확대 |
| Danger | Defensive (4) | 10~30% | 30~40% | 30~50% | 고배당·채권 집중, 현금 확대 |
| Extreme | Extreme_Defensive (5) | 0~10% | 20~30% | 60~80% | 포지션 최소화, 현금·금·단기채 |

### 전략 결정 로직 (IF/THEN 완전 결정 트리)

```python
# ── Step 1: score_band 기반 기본 전략 ──────────────────
IF score_band == "Safe":
    strategy = "Aggressive"
ELIF score_band == "Caution":
    strategy = "Moderate_Aggressive"
ELIF score_band == "Alert":
    strategy = "Moderate_Defensive"
ELIF score_band == "Danger":
    strategy = "Defensive"
ELSE:    # "Extreme"
    strategy = "Extreme_Defensive"

# EQUITY_CEILING_DEFAULT 딕셔너리에서 상한 조회 (Section 1에서 정의)
IF strategy == "Aggressive":          equity_ceiling = 100
ELIF strategy == "Moderate_Aggressive": equity_ceiling = 80
ELIF strategy == "Moderate_Defensive":  equity_ceiling = 50
ELIF strategy == "Defensive":           equity_ceiling = 30
ELSE:                                   equity_ceiling = 10

# ── Step 2: OVR-03 — 단일 Critical → 최소 방어 보장 ────
# critical_count는 Section 3에서 산출됨
IF critical_count >= 1:
    IF STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Moderate_Defensive"]:
        strategy = "Moderate_Defensive"
        equity_ceiling = 50

# ── Step 3: OVR-04 — Critical ≥ 2 + score > 2.5 ────────
IF critical_count >= 2 AND integrated_score > 2.5:
    IF STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Defensive"]:
        strategy = "Defensive"
        equity_ceiling = 30

# ── Step 4: OVR-02 연동 — 주식 상한 -10%p ───────────────
IF critical_count >= 1:
    equity_ceiling = equity_ceiling - 10
    IF equity_ceiling < 0:
        equity_ceiling = 0

# ── Step 5: CR-03 — 리스크 충돌 추가 조정 ──────────────
IF downside_grade == 4 AND volatility_grade == 4:
    # 해당 전략의 최솟값에서 추가 -10%p
    IF strategy == "Aggressive":          base_min = 80
    ELIF strategy == "Moderate_Aggressive": base_min = 60
    ELIF strategy == "Moderate_Defensive":  base_min = 30
    ELIF strategy == "Defensive":           base_min = 10
    ELSE:                                   base_min = 0
    equity_ceiling = base_min - 10
    IF equity_ceiling < 0:
        equity_ceiling = 0

IF volatility_grade >= 3 AND downside_grade >= 3:
    equity_ceiling = equity_ceiling - 5
    IF equity_ceiling < 0:
        equity_ceiling = 0

# ── Step 6: 구간 이동 감지 → 전체 재산출 ───────────────
recompute_strategy = False
IF STATE["prev_score_band"] IS NOT None:
    IF STATE["prev_score_band"] != score_band:
        recompute_strategy = True

IF recompute_strategy:
    # Step 1 ~ Step 5 재실행
    IF score_band == "Safe":
        strategy = "Aggressive"
    ELIF score_band == "Caution":
        strategy = "Moderate_Aggressive"
    ELIF score_band == "Alert":
        strategy = "Moderate_Defensive"
    ELIF score_band == "Danger":
        strategy = "Defensive"
    ELSE:
        strategy = "Extreme_Defensive"

    IF strategy == "Aggressive":            equity_ceiling = 100
    ELIF strategy == "Moderate_Aggressive": equity_ceiling = 80
    ELIF strategy == "Moderate_Defensive":  equity_ceiling = 50
    ELIF strategy == "Defensive":           equity_ceiling = 30
    ELSE:                                   equity_ceiling = 10

    IF critical_count >= 1:
        IF STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Moderate_Defensive"]:
            strategy = "Moderate_Defensive"
            equity_ceiling = 50

    IF critical_count >= 2 AND integrated_score > 2.5:
        IF STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Defensive"]:
            strategy = "Defensive"
            equity_ceiling = 30

    IF critical_count >= 1:
        equity_ceiling = equity_ceiling - 10
        IF equity_ceiling < 0:
            equity_ceiling = 0

    IF downside_grade == 4 AND volatility_grade == 4:
        IF strategy == "Aggressive":            base_min = 80
        ELIF strategy == "Moderate_Aggressive": base_min = 60
        ELIF strategy == "Moderate_Defensive":  base_min = 30
        ELIF strategy == "Defensive":           base_min = 10
        ELSE:                                   base_min = 0
        equity_ceiling = base_min - 10
        IF equity_ceiling < 0:
            equity_ceiling = 0

    IF volatility_grade >= 3 AND downside_grade >= 3:
        equity_ceiling = equity_ceiling - 5
        IF equity_ceiling < 0:
            equity_ceiling = 0

RETURN strategy, equity_ceiling
```

---

## 10. Layer 6 — Insight

**선행 조건**: `strategy` 확정

### 인사이트 생성 로직 (IF/THEN)

```python
insights = []

# ── 1순위: 시나리오 긴급 인사이트 ───────────────────────
IF triggered_scenario == "SCN-04":
    insights.PREPEND({
        "id":       "INS-11",
        "type":     "emergency",
        "priority": "critical",
        "text":     "환율 급등·금리 인상·외국인 이탈이 동시 발생했습니다. 모든 위험자산 비중 최소화를 권장합니다."
    })

ELIF triggered_scenario == "SCN-03":
    insights.PREPEND({
        "id":       "INS-10",
        "type":     "emergency",
        "priority": "critical",
        "text":     "물가 급등·외국인 이탈·금리 인상이 동시 진행 중입니다. 전면 방어 전환이 필요합니다."
    })

ELIF triggered_scenario == "SCN-02":
    insights.PREPEND({
        "id":       "INS-09",
        "type":     "emergency",
        "priority": "critical",
        "text":     "금리 인상과 CPI 상승이 중첩되며 긴축 압력이 확대되고 있습니다. 성장주 비중 축소를 권장합니다."
    })

ELIF triggered_scenario == "SCN-01":
    insights.PREPEND({
        "id":       "INS-08",
        "type":     "emergency",
        "priority": "critical",
        "text":     "환율 급등과 외국인 이탈이 동시에 감지되었습니다. 자본 유출 압력이 구조화되고 있습니다."
    })

# ── 2순위: 복합 조건 인사이트 ────────────────────────────
IF volatility_grade >= 3 AND market_grade >= 3:
    insights.APPEND({
        "id":       "INS-01",
        "type":     "composite",
        "priority": "high",
        "text":     "변동성 증가와 하락 추세가 동시에 나타나며 시장 리스크가 확대되고 있습니다."
    })

IF downside_grade == 4 AND var_95 <= -3.5:
    insights.APPEND({
        "id":       "INS-07",
        "type":     "composite",
        "priority": "high",
        "text":     "최대 손실 가능성이 임계 수준을 초과했습니다. 포지션 규모 축소를 권장합니다."
    })

IF macro_grade == 4 AND triggered_scenario IS None:
    insights.APPEND({
        "id":       "INS-05",
        "type":     "composite",
        "priority": "high",
        "text":     "금리 인상 및 환율 상승이 동시에 진행되며 거시 리스크가 극단 수준에 도달했습니다."
    })

# ── 3순위: 단일 조건 인사이트 ────────────────────────────
IF fi_streak_sell >= 5:
    insights.APPEND({
        "id":       "INS-02",
        "type":     "single",
        "priority": "medium",
        "text":     "외국인 순매도가 지속되며 추가 하락 압력이 존재합니다."
    })

IF vol_streak >= 5:
    insights.APPEND({
        "id":       "INS-04",
        "type":     "single",
        "priority": "medium",
        "text":     "거래량이 지속 감소하고 있어 시장 참여도가 약화되고 있습니다."
    })

IF integrated_score >= 2.5:
    insights.APPEND({
        "id":       "INS-03",
        "type":     "strategy_recommendation",
        "priority": "medium",
        "text":     "현재 구간에서는 방어적인 자산 배분 전략이 권장됩니다."
    })

# ── 4순위: 긍정 시장 요약 ─────────────────────────────────
IF integrated_score < 1.5 AND ma_bullish:
    insights.APPEND({
        "id":       "INS-06",
        "type":     "positive",
        "priority": "low",
        "text":     "전반적인 리스크 수준이 낮고 상승 추세가 유지되고 있습니다. 공격적 전략이 유효한 구간입니다."
    })

# ── R4 반복 억제 (STATE에서 조회) ─────────────────────────
filtered_insights = []
FOR item IN insights:
    ins_id = item["id"]
    IF STATE["consecutive_days"][ins_id] < 3:
        filtered_insights.APPEND(item)
insights = filtered_insights

# ── OVR-05: 전략 권고 종결 강제 (R3, R4 우선) ────────────
has_strategy_rec = False
FOR item IN insights:
    IF item["type"] == "strategy_recommendation":
        has_strategy_rec = True
        BREAK

IF NOT has_strategy_rec OR LEN(insights) == 0:
    forced = {
        "id":       "INS-STRATEGY",
        "type":     "strategy_recommendation",
        "priority": "terminal",
        "text":     STRATEGY_INSIGHT_TEMPLATE[strategy],
        "score":    integrated_score,
        "strategy": strategy
    }
    insights.APPEND(forced)
    # R4 반복 억제 무시 — 무조건 추가

# ── R5: Critical 알림 활성 시 최상단 재정렬 ──────────────
any_critical_alert_active = ("Critical_Alert" IN active_alerts)

IF any_critical_alert_active:
    critical_items = [i FOR i IN insights IF i["priority"] == "critical"]
    other_items    = [i FOR i IN insights IF i["priority"] != "critical"]
    insights = critical_items + other_items

# ── STATE 업데이트: 생성된 인사이트 연속 일수 갱신 ────────
generated_ids = [item["id"] FOR item IN insights]
FOR ins_id IN STATE["consecutive_days"]:
    IF ins_id IN generated_ids:
        STATE["consecutive_days"][ins_id] = STATE["consecutive_days"][ins_id] + 1
    ELSE:
        STATE["consecutive_days"][ins_id] = 0

RETURN insights
```

### 인사이트 조건-메시지 매핑 (11종)

| ID | 트리거 조건 | 우선순위 | 유형 |
|----|------------|---------|------|
| INS-01 | `volatility_grade >= 3` AND `market_grade >= 3` | 2순위 | 복합 |
| INS-02 | `fi_streak_sell >= 5` | 3순위 | 단일 |
| INS-03 | `integrated_score >= 2.5` | 3순위 | 전략권고 |
| INS-04 | `vol_streak >= 5` | 3순위 | 단일 |
| INS-05 | `macro_grade == 4` AND `triggered_scenario IS None` | 2순위 | 복합 |
| INS-06 | `integrated_score < 1.5` AND `ma_bullish == True` | 4순위 | 긍정 |
| INS-07 | `downside_grade == 4` AND `var_95 <= -3.5` | 2순위 | 복합 |
| INS-08 | `triggered_scenario == "SCN-01"` | 1순위 | 긴급+전략 |
| INS-09 | `triggered_scenario == "SCN-02"` | 1순위 | 긴급+전략 |
| INS-10 | `triggered_scenario == "SCN-03"` | 1순위 | 긴급+전략 |
| INS-11 | `triggered_scenario == "SCN-04"` | 1순위 | 긴급+전략 |

### 필수 생성 규칙

| 규칙 | 조건 | 처리 | 우선순위 |
|------|------|------|---------|
| R1 | 복합 조건 ≥ 2개 | 복합 인사이트 우선 생성 | 높음 |
| R2 | 수치 포함 시 | 구체적 수치 명시 | 중간 |
| R3 | 항상 | 마지막 = 전략 권고 문장 | **최고** |
| R4 | 동일 INS-ID | 연속 3일 이상 반복 금지 | 중간 (R3에 종속) |
| R5 | Critical 알림 활성 | 인사이트 최상단 강조 | 높음 |

---

## 11. Layer 7 — Visualization

### 컴포넌트 매핑

| 목적 | 차트 | 규격 |
|------|------|------|
| 통합 점수 요약 | 반원형 게이지 | 0°~180°, 소수점 2자리, 구간 색상 |
| 리스크 유형 비교 | 오각형 레이더 차트 | 현재(실선) + 지난주(점선) |
| 시간 변화 | 시계열 라인 차트 | 최근 252일, 구간별 배경색 |
| 자산 배분 | 파이 / 수평 바 | 주식·채권·현금 3분할 |
| 지표 비교 | 테이블 | 현재값 + 기준값 병렬 |
| 알림 | 배너 / 팝업 / 푸시 | 등급별 색상 |

### 갱신 트리거 (IF/THEN)

```python
IF business_day_market_closed:
    REFRESH gauge_chart
    REFRESH radar_chart
    REFRESH trend_chart

IF STATE["prev_score_band"] != score_band:
    REFRESH strategy_chart
    REFRESH allocation_chart

IF LEN(active_alerts) > 0:
    FOR alert_id IN active_alerts:
        IF ALERT_LEVEL[alert_type(alert_id)] == 3:    # Critical_Alert
            DISPLAY immediate_popup(alert_id)
            SEND email(alert_id)
            SEND push_notification(alert_id)
        ELIF ALERT_LEVEL[alert_type(alert_id)] == 2:  # Warning
            DISPLAY popup(alert_id)
            SEND email(alert_id)
        ELIF ALERT_LEVEL[alert_type(alert_id)] == 1:  # Watch
            DISPLAY banner(alert_id)
```

---

## 12. Conflict Rules

> **모든 규칙 IF/THEN 형식 — 암시적 로직 없음**

### CR-01: 변동성 리스크 내부 (HV vs VKOSPI)

```python
IF hv_grade != vkospi_grade:
    volatility_grade = MAX(hv_grade, vkospi_grade)
ELSE:
    volatility_grade = hv_grade
```

### CR-02: 하방 리스크 내부 (MDD vs VaR)

```python
IF mdd_grade != var_grade:
    downside_grade = MAX(mdd_grade, var_grade)
ELSE:
    downside_grade = mdd_grade
```

### CR-03: 전략 리스크 충돌 우선순위

```python
# 우선순위: 하방+변동성 > 매크로 > 시장 > 유동성
IF downside_grade == 4 AND volatility_grade == 4:
    IF strategy == "Aggressive":          base_min = 80
    ELIF strategy == "Moderate_Aggressive": base_min = 60
    ELIF strategy == "Moderate_Defensive":  base_min = 30
    ELIF strategy == "Defensive":           base_min = 10
    ELSE:                                   base_min = 0
    equity_ceiling = base_min - 10
    IF equity_ceiling < 0:
        equity_ceiling = 0

IF volatility_grade >= 3 AND downside_grade >= 3:
    equity_ceiling = equity_ceiling - 5
    IF equity_ceiling < 0:
        equity_ceiling = 0
```

### CR-04: 매크로 이벤트 방향 충돌

```python
# 상향·하향 이벤트 동시 발생 시 순 방향으로 계산
# (이미 3E-2 Grade Logic 내에서 net_delta로 처리됨)
# 시나리오 발동(3E-3)은 이 계산과 무관하게 macro_grade = 4 강제
IF triggered_scenario IS NOT None:
    macro_grade = 4    # net_delta 계산 결과 무시
```

### CR-05: 시장 국면 충돌

```python
IF bearish_phase AND sideways_phase:
    market_phase = "bearish"
    W1, W2, W3, W4, W5 = 0.30, 0.25, 0.20, 0.10, 0.15
    # 하락장 가중치 우선 적용 (보수적 리스크 관리)
```

---

## 13. Override Rules

> **적용 순서 (STEP 4)**: OVR-01 → OVR-06 → OVR-02 (등급 확정)
> **전략 적용 순서 (STEP 7)**: OVR-03 → OVR-04
> **인사이트 적용 (STEP 8)**: OVR-05

### OVR-01: 시나리오 발동 → 매크로 Critical 강제

```python
IF triggered_scenario == "SCN-01" OR \
   triggered_scenario == "SCN-02" OR \
   triggered_scenario == "SCN-03" OR \
   triggered_scenario == "SCN-04":
    macro_grade = 4
    # level_grade, event_grade 결과 전부 무시
    # 적용 시점: STEP 4 (1번째)
```

### OVR-02: 단일 Critical → 경고 알림 강제 + 주식 상한 하향

```python
critical_count = 0
IF market_grade    == 4: critical_count = critical_count + 1
IF volatility_grade == 4: critical_count = critical_count + 1
IF liquidity_grade == 4: critical_count = critical_count + 1
IF downside_grade  == 4: critical_count = critical_count + 1
IF macro_grade     == 4: critical_count = critical_count + 1

IF critical_count >= 1:
    active_alerts.APPEND("ALT-02")    # Warning 강제 (통합 점수 무관)
    # equity_ceiling 하향은 STEP 7 Step 4에서 처리
    # 적용 시점: STEP 4 (3번째)
```

### OVR-03: 단일 Critical → 최소 방어 전략 강제

```python
IF critical_count >= 1:
    IF STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Moderate_Defensive"]:
        strategy = "Moderate_Defensive"
        equity_ceiling = 50
# 예: integrated_score=1.8(Caution→Moderate_Aggressive), macro_grade=4
#     → strategy = "Moderate_Defensive" 강제
# 적용 시점: STEP 7 (Step 2)
```

### OVR-04: Critical ≥ 2 + 점수 > 2.5 → Defensive 강제

```python
IF critical_count >= 2 AND integrated_score > 2.5:
    IF STRATEGY_LEVEL[strategy] < STRATEGY_LEVEL["Defensive"]:
        strategy = "Defensive"
        equity_ceiling = 30
# 적용 시점: STEP 7 (Step 3, OVR-03 이후)
```

### OVR-05: 인사이트 전략 권고 종결 강제

```python
has_strategy_rec = False
FOR item IN insights:
    IF item["type"] == "strategy_recommendation":
        has_strategy_rec = True
        BREAK

IF NOT has_strategy_rec OR LEN(insights) == 0:
    forced = {
        "id":       "INS-STRATEGY",
        "type":     "strategy_recommendation",
        "priority": "terminal",
        "text":     STRATEGY_INSIGHT_TEMPLATE[strategy],
        "score":    integrated_score,
        "strategy": strategy
    }
    insights.APPEND(forced)
    # R4 반복 억제보다 우선 — 무조건 추가
# 적용 시점: STEP 8 종료 직전
```

### OVR-06: 하방 리스크 단일 Critical 예외

```python
IF downside_grade == 4:
    all_others_le3 = (
        market_grade     <= 3 AND
        volatility_grade <= 3 AND
        liquidity_grade  <= 3 AND
        macro_grade      <= 3
    )
    IF all_others_le3:
        system_critical_escalation = False
        # 전체 시스템 Critical 자동 격상 없음
        # 단, ALT-02는 OVR-02에 의해 정상 발생
        IF "ALT-02" NOT IN active_alerts:
            active_alerts.APPEND("ALT-02")
# 적용 시점: STEP 4 (2번째, OVR-01 직후)
```

---

## 14. Alert Rules

> 알림은 등급 변화와 독립적으로 작동하는 조기 경고 신호

### 알림 평가 로직 (STEP 9, IF/THEN)

```python
active_alerts = []

# ── Watch (주의) ──────────────────────────────────────────
# ALT-03: 변동성 급등
IF STATE["hv20_5d_ago"] IS NOT None:
    hv20_5d_ago = STATE["hv20_5d_ago"]
    IF hv20 > hv20_5d_ago * 1.3:
        active_alerts.APPEND("ALT-03")
ELSE:
    SKIP ALT-03    # 5영업일 데이터 미확보

# ALT-04: 거래량 급감 (3일 연속 vol_ratio ≤ 0.6)
STATE["vol_ratio_3d"].APPEND(vol_ratio)
IF LEN(STATE["vol_ratio_3d"]) > 3:
    STATE["vol_ratio_3d"].REMOVE_FIRST()

IF LEN(STATE["vol_ratio_3d"]) == 3:
    IF STATE["vol_ratio_3d"][0] <= 0.6 AND \
       STATE["vol_ratio_3d"][1] <= 0.6 AND \
       STATE["vol_ratio_3d"][2] <= 0.6:
        active_alerts.APPEND("ALT-04")

# ── Warning (경고) ────────────────────────────────────────
# ALT-01: 통합 점수 급등
IF STATE["prev_integrated_score"] IS NOT None:
    IF integrated_score - STATE["prev_integrated_score"] >= 0.5:
        active_alerts.APPEND("ALT-01")

# ALT-02: 단일 Critical (OVR-02에서 이미 추가됨 — 중복 방지)
IF critical_count >= 1:
    IF "ALT-02" NOT IN active_alerts:
        active_alerts.APPEND("ALT-02")

# ALT-05: 외국인 집중 순매도
IF fi_streak_sell >= 5 AND fi_5d_cum <= -1.0:
    active_alerts.APPEND("ALT-05")

# ALT-06: 이격도 임계 이탈
IF disp_ma20 <= 90 OR disp_ma60 <= 85:
    active_alerts.APPEND("ALT-06")

# ALT-08: 매크로 이벤트 중첩
IF up_count >= 2:
    active_alerts.APPEND("ALT-08")

# ── Critical Alert (위험) ─────────────────────────────────
# ALT-07: MDD 임계 도달
IF mdd_60 <= -0.15:
    active_alerts.APPEND("ALT-07")

# ALT-09 ~ ALT-12: 시나리오 발동
IF triggered_scenario == "SCN-01":
    active_alerts.APPEND("ALT-09")

IF triggered_scenario == "SCN-02":
    active_alerts.APPEND("ALT-10")

IF triggered_scenario == "SCN-03":
    active_alerts.APPEND("ALT-11")

IF triggered_scenario == "SCN-04":
    active_alerts.APPEND("ALT-12")

RETURN active_alerts
```

### 알림 참조 테이블

| ID | 유형 | 트리거 조건 | 등급 |
|----|------|------------|------|
| ALT-01 | 통합 점수 급등 | `integrated_score - prev >= 0.5` | Warning |
| ALT-02 | 단일 Critical | `critical_count >= 1` | Warning |
| ALT-03 | 변동성 급등 | `hv20 > hv20_5d_ago * 1.3` | Watch |
| ALT-04 | 거래량 급감 | `vol_ratio <= 0.6`, 3일 연속 | Watch |
| ALT-05 | 외국인 집중 순매도 | `fi_streak_sell >= 5 AND fi_5d_cum <= -1.0` | Warning |
| ALT-06 | 이격도 임계 이탈 | `disp_ma20 <= 90 OR disp_ma60 <= 85` | Warning |
| ALT-07 | MDD 임계 도달 | `mdd_60 <= -0.15` | Critical_Alert |
| ALT-08 | 매크로 이벤트 중첩 | `up_count >= 2` | Warning |
| ALT-09 | SCN-01 발동 | `triggered_scenario == "SCN-01"` | Critical_Alert |
| ALT-10 | SCN-02 발동 | `triggered_scenario == "SCN-02"` | Critical_Alert |
| ALT-11 | SCN-03 발동 | `triggered_scenario == "SCN-03"` | Critical_Alert |
| ALT-12 | SCN-04 발동 | `triggered_scenario == "SCN-04"` | Critical_Alert |

### 전달 방식

| 등급 | 채널 | 메시지 형태 |
|------|------|------------|
| Watch (1) | 대시보드 배너 | 노란색 배너 + 요약 1줄 |
| Warning (2) | 팝업 + 이메일 | 원인 + 권고 전략 |
| Critical_Alert (3) | 즉시 팝업 + 이메일 + 앱 푸시 | 긴급 메시지 + 자산 배분 조정 요청 |

---

## 15. Final Validation Checklist

### ✅ 모든 5개 리스크 동일 JSON Schema 구조

> **최상위 필드 정확히 6개**: `risk_id` · `grade` · `score` · `triggered_conditions` · `reason` · `details`
> `details` 내부: `risk_type` · `grade_label` · `weight_default` · `timestamp` · `indicators` · `sub_grades` · `flags` · `conflict_rule`

| 리스크 | risk_id | grade | score | triggered_conditions | reason | details | 최상위 6개만 | 상태 |
|--------|---------|-------|-------|----------------------|--------|---------|------------|------|
| 시장 (A) | RISK-A | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 변동성 (B) | RISK-B | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 유동성 (C) | RISK-C | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 하방 (D) | RISK-D | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 매크로 (E) | RISK-E | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**최상위에서 제거된 필드 (details 내부로 이동)**:

| 제거된 필드 | 이동 위치 | 상태 |
|------------|----------|------|
| `risk_type` | `details.risk_type` | ✅ |
| `grade_label` | `details.grade_label` | ✅ |
| `weight_default` | `details.weight_default` | ✅ |
| `timestamp` | `details.timestamp` | ✅ |

### ✅ 모든 변수 정규화 (중복 없음)

| 범주 | 정규화 | 상태 |
|------|--------|------|
| 지표 변수 (snake_case) | Section 1 테이블 | ✅ |
| 파생 지표 | Section 3에서 완전 정의 | ✅ |
| 상태 변수 | Section 2 STATE 딕셔너리 | ✅ |
| 등급/점수/전략 변수 | Section 1 테이블 | ✅ |
| 중복 변수 없음 | `m2_growth` → `m2_growth_curr`로 통일 | ✅ |

### ✅ 미정의 함수 호출 없음

| 이전 미정의 함수 | v5.0 처리 |
|----------------|----------|
| `grade_from_ma_alignment()` | Risk-A ELSE 블록 인라인 IF/THEN | ✅ |
| `grade_from_disp()` | Risk-A ELSE 블록 인라인 IF/THEN | ✅ |
| `grade_from_adx()` | Risk-A ELSE 블록 인라인 IF/THEN | ✅ |
| `grade_from_streak()` | Risk-A ELSE 블록 인라인 IF/THEN | ✅ |
| `MODE(signal_grades)` | grade_count 딕셔너리 + MAX 인라인 | ✅ |
| `m2_contraction_detected()` | Section 3에서 `m2_contraction` 불리언으로 | ✅ |
| `m2_expansion_detected()` | Section 3에서 `m2_expansion` 불리언으로 | ✅ |
| `ma_converging` | Section 3에서 `ma_gap_ratio < 0.02`로 | ✅ |
| `mdd_recovery_months` | Section 3에서 252일 종가 배열로 계산 | ✅ |
| `generate_strategy_insight()` | Layer 6 + OVR-05에서 인라인 객체 생성으로 대체 (함수 의존성 제거) | ✅ |
| `EQUITY_CEILING_DEFAULT[strategy]` | Section 1 상수 + Strategy IF/THEN | ✅ |
| `EQUITY_MIN[strategy]` | Section 1 상수 + CR-03 IF/THEN | ✅ |
| `consecutive_days[i.id]` | Section 2 STATE["consecutive_days"] | ✅ |
| `any_critical_alert_active` | Section 3에서 명시적 불리언 | ✅ |
| `COUNT(indicator IN danger_zone)` | 3E-1에서 지표별 IF/THEN 전개 | ✅ |
| `prev_score_band`, `prev_integrated_score` | Section 2 STATE | ✅ |
| `hv20_5d_ago` (prev_week_hv20) | Section 2 STATE | ✅ |
| `fx_weekly_change`, `fx_daily_change` | Section 3에서 계산식 정의 | ✅ |
| `rate_spread_prev`, `rate_spread_curr` | Section 3에서 계산식 정의 | ✅ |
| `CLAMP()` | Section 1에서 인라인 정의 + 3E-2 IF/THEN | ✅ |
| `all_risk_grades` | Section 3에서 리스트로 정의 | ✅ |

### ✅ 모든 로직 IF/THEN 형식

| 섹션 | 상태 |
|------|------|
| Risk-A 등급 판정 (ELSE 복합 신호 포함) | ✅ |
| Risk-B 등급 판정 + CR-01 | ✅ |
| Risk-C 등급 판정 + 보조 지표 보정 | ✅ |
| Risk-D 등급 판정 + CR-02 | ✅ |
| Risk-E 3E-1 (6개 지표 개별 IF/THEN) | ✅ |
| Risk-E 3E-2 이벤트 탐지 + 집계 | ✅ |
| Risk-E 3E-3 시나리오 판별 | ✅ |
| 시장 국면 판단 | ✅ |
| 통합 점수 구간 매핑 | ✅ |
| 전략 결정 트리 (6단계) | ✅ |
| 인사이트 생성 (STATE 업데이트 포함) | ✅ |
| 알림 평가 (vol_ratio_3d 롤링 포함) | ✅ |
| CR-01~CR-05 | ✅ |
| OVR-01~OVR-06 | ✅ |
| 시각화 갱신 트리거 | ✅ |

### ✅ 매크로 Level → Event → Scenario 체인

| 단계 | 입력 | 출력 | GUARD | 상태 |
|------|------|------|-------|------|
| 3E-1 수준 판정 | 6개 지표 (개별 IF/THEN) | `level_grade` ∈ {1,2,3} | STEP 2 완료 | ✅ |
| 3E-2 이벤트 탐지 | `level_grade` + EVT_01~10 | `event_grade` ∈ {1,2,3,4} | 3E-1 완료 | ✅ |
| 3E-3 시나리오 판별 | `event_grade` + 이벤트 불리언 | `macro_grade`, `triggered_scenario`, `scn04_flag` | 3E-2 완료 | ✅ |
| CLAMP 인라인 | `raw_event_grade` | min=1, max=4 보장 | — | ✅ |
| EVT-07 예외 | `fx_weekly_change < -0.03` | down_count 미포함 | — | ✅ |
| SCN-04 분리 | `scn04_flag = True` | Scoring에서 Extreme 해석 | — | ✅ |
| 중첩 상향 | `up_count >= 2` | `net_delta +1` | — | ✅ |

### ✅ 원본 로직 보존 여부

| 항목 | 보존 |
|------|------|
| 5가지 리스크 가중치 (30/25/20/15/10%) | ✅ |
| 동적 가중치 3세트 (상승/하락/횡보) | ✅ |
| 통합 점수 공식 | ✅ |
| 점수 구간 5개 (Safe~Extreme) | ✅ |
| 이벤트 10종 (EVT-01~EVT-10) | ✅ |
| 시나리오 4종 (SCN-01~SCN-04) | ✅ |
| Override 6종 (OVR-01~OVR-06) | ✅ |
| Conflict 5종 (CR-01~CR-05) | ✅ |
| Alert 12종 (ALT-01~ALT-12) | ✅ |
| Insight 11종 (INS-01~INS-11) | ✅ |
| 인사이트 규칙 5종 (R1~R5) | ✅ |
| 매크로 3단계 흐름 | ✅ |
| SCN-04 Extreme 특이 처리 | ✅ |
| 하방 리스크 단일 Critical 예외 | ✅ |
| EVT-07 직접 하향 없음 규칙 | ✅ |

---

*기준: 금융_투자_대시보드_서비스_기획서 v2.0 — Skills.md v6.0 Normalized JSON Schema · Fully Executable*

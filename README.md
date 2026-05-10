# KOSPI Risk Intelligence Dashboard

> KOSPI 시장의 리스크를 5가지 유형으로 구조화하고, 가중 통합 점수 기반으로
> 투자 전략과 자산 배분 방향을 자동 제시하는 분석 대시보드.

**기준 스펙**: [`Skills.md`](./Skills.md) v6.0 / [기획서 v2.0](./금융_투자_대시보드_서비스_기획서.md)
**진행률**: Phase 1 핵심 기능 100% (분석 엔진 + 대시보드)

---

## 목차

1. [개요](#1-개요)
2. [핵심 기능](#2-핵심-기능)
3. [빠른 시작](#3-빠른-시작)
4. [시스템 구조](#4-시스템-구조)
5. [데이터 소스](#5-데이터-소스)
6. [분석 파이프라인](#6-분석-파이프라인)
7. [디렉토리 구조](#7-디렉토리-구조)
8. [라이브 검증 결과](#8-라이브-검증-결과)
9. [Skills.md 매핑](#9-skillsmd-매핑)
10. [알려진 제한 / 향후 작업](#10-알려진-제한--향후-작업)
11. [기여 / 라이선스](#11-기여--라이선스)

---

## 1. 개요

### 핵심 차별화

| # | 차별화 포인트 | 설명 |
|---|-------------|------|
| 1 | 리스크 → 전략 자동 연결 | 분석 결과가 투자 전략으로 직결되는 일관된 흐름 |
| 2 | 이벤트 기반 매크로 분석 | 수준 판정 + 이벤트 탐지 + 복합 시나리오 3단계 구조 |
| 3 | 시나리오 기반 리스크 격상 | 복합 시나리오 발동 시 Critical 자동 격상 |
| 4 | 동적 가중치 시스템 | 시장 국면(상승/하락/횡보)별 리스크 가중치 자동 조정 |

### 5가지 리스크 유형

| 유형 | 가중치 | 핵심 지표 |
|------|--------|----------|
| 시장 (Market) | 30% | MA 배열 / 이격도 / ADX / 연속 하락 |
| 변동성 (Volatility) | 25% | HV20 / HV60 (VKOSPI 보류) |
| 매크로 (Macro) | 20% | 환율 / 금리 / CPI / 외국인 / M2 — 3단계 평가 |
| 유동성 (Liquidity) | 15% | 거래량 비율 / 거래대금 / 연속 감소 |
| 하방 (Downside) | 10% | MDD / VaR / CVaR / 회복 기간 |

### 통합 점수 → 전략 매핑

| 점수 구간 | 등급 | 전략 | 주식 / 채권 / 현금 |
|-----------|------|------|---------------------|
| 1.0 ~ 1.5 | Safe | Aggressive | 80~100 / 0~10 / 0~10 |
| 1.5 ~ 2.0 | Caution | Moderate Aggressive | 60~80 / 10~20 / 10~20 |
| 2.0 ~ 2.5 | Alert | Moderate Defensive | 30~50 / 20~30 / 20~40 |
| 2.5 ~ 3.0 | Danger | Defensive | 10~30 / 30~40 / 30~50 |
| 3.0 ~ | Extreme | Extreme Defensive | 0~10 / 20~30 / 60~80 |

---

## 2. 핵심 기능

- **5개 리스크 독립 등급 산정** (Low / Medium / High / Critical 4단계)
- **시장 국면별 동적 가중치** — bullish / bearish / sideways 3 세트
- **매크로 3단계 분석** — 수준 판정(6 지표) → 이벤트 탐지(10종) → 복합 시나리오(4종)
- **OVR 6종 + CR 5종** — 단일 Critical 시 최소 방어 강제, 시나리오 발동 시 자동 격상
- **인사이트 11종 + R1~R5** — 복합 조건 우선 / 반복 억제 / 전략 권고 종결 강제
- **알림 12종** — Watch / Warning / Critical_Alert 3등급
- **Pydantic 강제 검증** — 5개 리스크 출력 JSON 6+9 필드 무결성

---

## 3. 빠른 시작

### 사전 요구사항

- Python 3.10 ~ 3.12 (Anaconda 권장)
- 한국은행 ECOS API 키 — [발급](https://ecos.bok.or.kr/api/)
- 키움증권 REST API 앱키 / 시크릿키 — [발급](https://openapi.kiwoom.com)

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/DREAMHAPPYLIFEJH/Korea-Risk-Management.git
cd Korea-Risk-Management

# 2. Conda 환경 생성
conda create -n kospi_risk python=3.10 -y
conda activate kospi_risk

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 다음 키들을 입력:
#   ECOS_API_KEY=...
#   KIWOOM_APPKEY=...
#   KIWOOM_SECRETKEY=...
```

### 실행

```bash
# Streamlit 대시보드
streamlit run app/streamlit_app.py
```

브라우저가 자동으로 http://localhost:8501 을 엽니다. 분석 기준일을 선택하면 30~60초 후 결과 표시 (키움 외국인 데이터 일별 수집 시간).

### 헤드리스 분석 (코드에서 호출)

```python
from datetime import date
from pipeline.orchestrator import run_snapshot

result = run_snapshot(end_date=date(2026, 4, 30), lookback_days=400)

print(f"score: {result['score']:.2f} → {result['score_band']}")
print(f"strategy: {result['strategy']['strategy']}")
print(f"allocation: {result['strategy']['allocation']}")
```

---

## 4. 시스템 구조

### 7 Layer 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 7: Visualization                                          │
│  └── gauge / radar / trend / allocation / alert_banner           │
├──────────────────────────────────────────────────────────────────┤
│  Layer 6: Insight              (11종 + R1~R5 + OVR-05)           │
├──────────────────────────────────────────────────────────────────┤
│  Layer 5: Strategy             (6단계 결정 트리 + OVR-03/04)      │
├──────────────────────────────────────────────────────────────────┤
│  Layer 4: Scoring              (phase + integrated_score)         │
├──────────────────────────────────────────────────────────────────┤
│  Layer 3: Risk                 (5 risks + Pydantic schema)        │
├──────────────────────────────────────────────────────────────────┤
│  Layer 2: Indicator            (price/vol/liq/dn/derived)         │
├──────────────────────────────────────────────────────────────────┤
│  Layer 1: Data                 (kiwoom + ECOS + cleaner + state)  │
└──────────────────────────────────────────────────────────────────┘
                ↑                              ↑
                │                              │
        ┌───────┴───────┐              ┌──────┴───────┐
        │ Conflict Rules│              │ Override Rules│
        │  (CR-01~05)   │              │  (OVR-01~06)  │
        └───────────────┘              └───────────────┘
                                            ┌───────────┐
                                            │  Alerts   │
                                            │ (ALT-01~12)│
                                            └───────────┘
```

**원칙**:
- Layer N은 Layer N-1만 import (단방향 의존성)
- Pipeline orchestrator가 모든 Layer를 조립
- 모든 임계값은 `config/thresholds.py`에 분리 → 시장 확장 시 본 파일만 교체

---

## 5. 데이터 소스

| 변수 | 설명 | 소스 / 엔드포인트 | 주기 |
|------|------|------------------|------|
| `kospi_ohlcv` | KOSPI 종합지수 OHLCV | 키움 `ka20006` (inds_cd=`001`) | 일별 |
| `vol`, `val` | 거래량, 거래대금 | 키움 `ka20006` (응답 포함) | 일별 |
| `fi_net` | 외국인 시장 전체 순매수 | 키움 `ka10051` (inds_cd=`001_AL`) | 일별 |
| `vkospi` | VKOSPI 변동성 지수 | **Phase 1 보류** (외부 소스 미확보) | — |
| `fx_rate` | 원/달러 매매기준율 | ECOS `731Y001` / `0000001` | 일별 |
| `base_rate` | 한국은행 기준금리 | ECOS `722Y001` / `0101000` | 일별 |
| `cpi_yoy` | CPI 전년 동월 대비 (%) | ECOS `901Y009` / `0` (자체 YoY 계산) | 월별 |
| `m2_growth_curr` | M2 통화량 전년 동월 대비 (%) | ECOS `161Y006` / `BBHA00` (자체 YoY 계산) | 월별 |
| `us_base_rate` | 미국 정책금리 | ECOS `902Y006` / `US` | 월별 |

**API 키 관리**: `.env` 파일에 보관 → `.gitignore`로 차단됨.

---

## 6. 분석 파이프라인

`pipeline/orchestrator.py`의 `run_snapshot()`이 STEP 1~9를 직렬 실행:

```
STEP 1  데이터 수집           [Layer 1]
   ↓
STEP 2  정제 + 지표 계산        [Layer 2]
   ↓
STEP 3  5개 리스크 등급          [Layer 3]
        ├ 3A market_grade
        ├ 3B volatility_grade
        ├ 3C liquidity_grade
        ├ 3D downside_grade
        └ 3E macro_grade  (3E-1 → 3E-2 → 3E-3 직렬)
   ↓
STEP 4  Override 적용           [rules.override]
        OVR-01 → OVR-06 → OVR-02
   ↓
STEP 5  시장 국면 + 가중치 선택  [Layer 4]
   ↓
STEP 6  통합 점수 계산           [Layer 4]
   ↓
STEP 7  전략 + 자산 배분 결정    [Layer 5]
        OVR-03 → OVR-04
   ↓
STEP 8  인사이트 생성            [Layer 6]
        OVR-05
   ↓
STEP 9  알림 트리거 평가          [rules.alert]
   ↓
EOD     STATE 저장               [Layer 1]
```

각 STEP은 GUARD 조건 충족 시에만 진입. 위반 시 `prev_day_data` 폴백 + 경고.

---

## 7. 디렉토리 구조

```
Korea-Risk-Management/
├── .env.example                   # API 키 템플릿
├── .gitignore                     # 비밀키·저작권 자료 제외
├── CLAUDE.md                      # 협업 행동 지침
├── README.md                      # 본 문서
├── Skills.md                      # 실행 스펙 v6.0 (계약 문서)
├── 금융_투자_대시보드_서비스_기획서.md  # 기획서 v2.0
├── preceed.md                     # 진행 내역 로그
├── requirements.txt
│
├── config/
│   ├── constants.py               # GRADE_MAP / STRATEGY_LEVEL / EQUITY_*
│   └── thresholds.py              # 9 섹션 임계값 (시장 교체용 분리)
│
├── layer1_data/
│   ├── kiwoom_client.py           # OAuth + TR 헬퍼
│   ├── kospi_fetcher.py           # ka20006 + ka10051
│   ├── macro_fetcher.py           # ECOS 5종
│   ├── cleaner.py                 # ffill + 3σ + 영업일 정합
│   └── state.py                   # JSON 영속화 + EOD 갱신
│
├── layer2_indicator/
│   ├── price.py                   # MA / 이격도 / ADX / consec_decline
│   ├── volatility.py              # HV20/60 / vol_ratio_hv
│   ├── liquidity.py               # vol_ratio / val_ratio / vol_streak
│   ├── downside.py                # MDD / VaR / CVaR
│   └── derived.py                 # fx_change / MA flags / M2 / MDD 회복
│
├── layer3_risk/
│   ├── schema.py                  # Pydantic RiskOutput / RiskDetails
│   ├── market.py                  # Risk-A
│   ├── volatility.py              # Risk-B (HV20 단독, VKOSPI 보류)
│   ├── liquidity.py               # Risk-C
│   ├── downside.py                # Risk-D (CR-02 + recovery_signal)
│   └── macro.py                   # Risk-E (3E-1 → 3E-2 → 3E-3)
│
├── layer4_scoring/
│   ├── phase.py                   # bullish / bearish / sideways
│   └── score.py                   # integrated_score + score_band
│
├── layer5_strategy/
│   └── strategy.py                # 6단계 결정 트리 (OVR-03/04 + CR-03)
│
├── layer6_insight/
│   └── insight.py                 # 11종 + R1~R5 + OVR-05
│
├── layer7_visualization/
│   ├── gauge.py                   # 반원 통합 점수
│   ├── radar.py                   # 5축 오각형
│   ├── trend.py                   # 3-pane 시계열
│   ├── allocation.py              # 도넛 + 전략 라벨
│   └── alert_banner.py            # 3등급 배너
│
├── rules/
│   ├── conflict.py                # CR-01~05 (각 모듈 분산 적용 — docstring 참조)
│   ├── override.py                # OVR-01~06 + apply_step4 통합
│   └── alert.py                   # ALT-01~12 + alert_level
│
├── pipeline/
│   └── orchestrator.py            # STEP 1~9 end-to-end + STATE 갱신
│
├── app/
│   └── streamlit_app.py           # 대시보드 진입점
│
├── tests/                         # stub (인라인 검증으로 대체 중)
└── data/cache/                    # API 캐시 (gitignored)
```

---

## 8. 라이브 검증 결과

### 2026-04-30 KOSPI 분석

| 항목 | 값 |
|------|-----|
| Phase | bullish (정배열) |
| 통합 점수 | 1.95 → **Caution** |
| 시장 (A) | Low (1) — 강한 상승 추세 |
| 변동성 (B) | High (3) — HV20 = 29.27% |
| 유동성 (C) | Medium (2) — vol_ratio = 0.74 |
| 하방 (D) | **Critical (4)** — MDD_60 = -26%, VaR = -3.08% |
| 매크로 (E) | (산출 가능) |
| 전략 | Moderate Defensive (OVR-03 강제) |
| 자산 배분 | 35% / 30% / 35% |
| 핵심 기여 | 변동성 38.5%, 하방 20.5% |

### 2026-03-31 KOSPI 분석

| 항목 | 값 |
|------|-----|
| 통합 점수 | 2.75 → **Danger** |
| Critical 개수 | 2 (변동성 + 하방) |
| 전략 | Defensive (OVR-04 강제) |
| 자산 배분 | **0% / 47% / 53%** (CR-03 양쪽 Critical → equity 극단 축소) |
| 알림 | ALT-02 (단일 Critical) + ALT-07 (MDD 임계) |
| 인사이트 | INS-02 (외국인 매도 지속) + INS-03 (방어 권고) |

### Skills.md §8 계산 예시 검증

> 시장 High(3) + 변동성 High(3) + 매크로 Medium(2) + 유동성 Medium(2) + 하방 High(3)
> = 0.90 + 0.75 + 0.40 + 0.30 + 0.30 = **2.65 → Danger** ✓

---

## 9. Skills.md 매핑

| 섹션 | 구현 |
|------|------|
| §1 Constants | `config/constants.py` |
| §2 STATE | `layer1_data/state.py` |
| §3 Derived | `layer2_indicator/derived.py` |
| §4 STEP 1~10 | `pipeline/orchestrator.py` (STEP 10 = `app/streamlit_app.py`) |
| §5 Layer 1 | `layer1_data/*` (VKOSPI 보류 노트 §5에 명시) |
| §6 Layer 2 | `layer2_indicator/*` |
| §7 Risk-A~E | `layer3_risk/*` (공통 `schema.py` 6+9 필드) |
| §8 Scoring | `layer4_scoring/*` |
| §9 Strategy | `layer5_strategy/strategy.py` |
| §10 Insight | `layer6_insight/insight.py` |
| §11 Visualization | `layer7_visualization/*` |
| §12 Conflict (CR-01~05) | Risk-B/D 내부 + phase/strategy 분산 |
| §13 Override (OVR-01~06) | `rules/override.py` |
| §14 Alert (ALT-01~12) | `rules/alert.py` |
| §15 Validation Checklist | Pydantic 모델로 6+9 필드 강제 |

---

## 10. 알려진 제한 / 향후 작업

| 항목 | 영향 | 우선순위 |
|------|------|---------|
| **VKOSPI 미수집** | Risk-B를 HV20 단독으로 산정 (정확도 일부 손실) | 데이터 소스 확보 시 |
| ka10051 일별 루프 + 429 rate limit | 30~60초 소요, 일부 일자 skip | 캐싱 레이어 도입 시 해소 |
| 한국 공휴일 캘린더 미반영 | `pd.bdate_range`가 5/1·5/5 등 포함 → ffill로 흡수 | `exchange_calendars` 추가 시 |
| pytest 자동 회귀 테스트 미작성 | 인라인 검증으로 대체 중 | 운영 배포 전 |
| 등급 시계열 차트 (252일 grade 추이) | 현재는 close/HV20/MDD60 raw 차트만 | 일별 grade 백테스트 시 |
| 멀티 사용자 STATE 격리 | 단일 JSON 파일 (단일 사용자 가정) | 멀티 인스턴스 배포 시 |

### VKOSPI 보류 처리 (Phase 1)

외부 데이터 소스(키움 / ECOS / FinanceDataReader / yfinance) 모두 VKOSPI 미지원으로
Phase 1에서는 **Risk-B를 HV20 단독으로 등급 산정**합니다.

- CR-01의 `MAX(hv_grade, vkospi_grade)` 충돌 해소는 사실상 `volatility_grade = hv_grade`로 동작
- Risk-B JSON 출력에서 `vkospi`, `vkospi_grade` 필드는 `null` 직렬화
- VKOSPI 데이터 소스 확보 시 fetcher 추가만으로 자동 활성화 (분기 처리 완료)

---

## 11. 기여 / 라이선스

### 기여 가이드

기여는 환영합니다. 단, 다음 원칙을 따라주세요:

- **Skills.md를 계약 문서로 취급** — 모든 새 코드의 docstring에 해당 섹션 ID(`Risk-A`, `OVR-03` 등) 명시
- **시장 확장 시 `config/thresholds.py`만 교체** — 레이어 구조·등급 체계·점수 공식·알림 규칙은 불변
- **Pydantic 출력 검증** — 5개 리스크는 6+9 필드 구조 유지
- **단방향 의존성** — Layer N은 N-1만 import

### 보안

- **API 키는 절대 커밋 금지** — `.env`, `*appkey*.txt`, `*secretkey*.txt` 모두 `.gitignore`로 차단됨
- **저작권 자료 제외** — 키움 공식 PDF/XLS는 `.gitignore`로 차단됨
- 발견 시 즉시 [Issue](https://github.com/DREAMHAPPYLIFEJH/Korea-Risk-Management/issues) 또는 PR로 알려주세요

### 라이선스

본 프로젝트는 Skills.md 사양 기반 학습·연구용으로 작성되었습니다.
실제 투자 의사결정 도구로 사용 시 별도 검증 및 면책 조항을 명시해주세요.

---

## 부록: 주요 용어

| 용어 | 정의 |
|------|------|
| MDD | Maximum Drawdown — 특정 기간 내 고점 대비 최대 하락 비율 |
| VaR | Value at Risk — 일정 신뢰구간 내 최대 예상 손실 (95% 분위수) |
| CVaR | Conditional VaR — VaR 초과 손실 발생 시 조건부 평균 |
| ADX | Average Directional Index — 추세의 강도 (방향 무관, 14일 기준) |
| VKOSPI | 코스피200 옵션 가격 기반 내재 변동성 지수 |
| HV | Historical Volatility — 과거 일별 수익률 표준편차의 연율화 값 |
| 정배열 | MA20 > MA60 > MA120 (상승 추세) |
| 역배열 | MA20 < MA60 < MA120 (하락 추세) |
| Forward Fill | 결측값을 이전 영업일 값으로 채움 |

---

*본 프로젝트는 [Skills.md](./Skills.md) v6.0의 모든 IF/THEN 분기, 임계값,
규칙 ID(CR / OVR / ALT / INS)를 1:1로 매핑하여 구현했습니다. 시장 확장 시
`config/thresholds.py`만 교체하면 다른 시장(S&P500, 암호화폐 등)에도 동일 구조로 적용 가능합니다.*

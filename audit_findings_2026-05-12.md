# 논리 오류 검토 결과 (2026-05-12)

검토 범위: 오케스트레이터 + 5개 리스크 모듈(market/volatility/liquidity/downside/macro) + override/alert/insight/score/strategy/cleaner/state.

---

## 🔴 진짜 버그 (수정 필요)

### 1. `_apply_cr03`의 두 if가 비배타 — 더블 Critical 시 과조정
**위치**: `layer5_strategy/strategy.py:52-66`

```python
def _apply_cr03(...):
    if downside_grade == 4 and volatility_grade == 4:
        equity_ceiling = EQUITY_MIN[strategy] - EQUITY_CEILING_DOUBLE_C_DROP   # -10
        equity_ceiling = max(equity_ceiling, 0)
    if volatility_grade >= 3 and downside_grade >= 3:        # ← elif 아님
        equity_ceiling -= EQUITY_CEILING_DOUBLE_H_DROP       # 또 -5
```

`downside==4 AND volatility==4`일 때 두 번째 if (`>=3 and >=3`)도 True → 추가 -5%p.
- 예: `strategy=Moderate_Defensive` 더블 Critical → `EQUITY_MIN[MD]=30 → -10 → 20 → -5 → 15`.
- CR-03 docstring("양쪽 Critical → -10%p / 양쪽 High → -5%p") OR 의도면 `elif`로 변경.
- Defensive는 `EQUITY_MIN=10-10=0` 클램프로 결과 동일하나 strategy에 따라 결과가 갈리는 잠재 결함.

### 2. OVR-03/04 안에 equity ceiling 하드코딩
**위치**: `rules/override.py:115-116, 130`

```python
return "Moderate_Defensive", 50    # ← config.EQUITY_CEILING_DEFAULT 와 우연히 일치
return "Defensive", 30
```

- `EQUITY_CEILING_DEFAULT["Moderate_Defensive"]=50`, `["Defensive"]=30`이라 현재는 일치.
- CLAUDE.md 원칙 "임계값은 `config/thresholds.py`에" 위배. 시장 확장 시 깨짐.
- 수정: `EQUITY_CEILING_DEFAULT[strategy]` 참조.

### 3. R3 "마지막 = 전략 권고" 부분 enforcement
**위치**: `rules/override.py:apply_ovr05` (145-155)

- 기존 strategy_recommendation이 있으면 append만 skip할 뿐, 순서를 끝으로 옮기지 않음.
- 현재 generate 순서상 INS-03이 우연히 마지막에 위치. 향후 인사이트 추가 시 R3 위반 가능.
- 수정: 기존 strategy_recommendation을 pop → end에 append.

---

## 🟡 데이터 무결성 위험 (검토 필요)

### 4. `or 0` 트릭이 결측을 0으로 silently 치환
**위치**: `pipeline/orchestrator.py:174, 177, 182-184, 204-205`

```python
base_today = at(base_kr)             # None 가능
rate_spread_curr_v = (base_today or 0) - (us_today or 0)
cpi_delta_v = float((cpi_yoy_v or 0) - (cpi_prev or 0))
ma_bullish_v = (ma20 or 0) > (ma60 or 0) > (ma120 or 0)
```

- None을 0으로 치환 → 데이터 부재가 "정상=0%"으로 둔갑.
- 특히 `rate_spread_curr=0`은 RATE_SPREAD_CAUTION(0) 임계에 걸려 caution 등급 가짜 발동.
- 정책: None 유지 + 다운스트림 처리, 또는 raise.

### 5. `rate_spread_prev_v` 22일 미만 fallback이 EVT-05 무력화
**위치**: `pipeline/orchestrator.py:178-180`

데이터가 짧으면 `prev = curr` → `(rate_spread_prev > 0) and (rate_spread_curr <= 0)` (EVT-05 yield inversion) 절대 발동 불가.

### 6. M2/CPI `iloc[-22]` = "한 달 전" 가정 경계 이슈
**위치**: `pipeline/orchestrator.py:173, 183, 187`

월별 데이터를 영업일로 ffill → 22 영업일 전 값이 이번 달인지 직전 달인지 시점 의존.
수정 권장: `s.resample("M").last().shift(1).iloc[-1]`.

---

## 🟢 사소 (스타일/추적성)

### 7. R5 재정렬의 dead code
**위치**: `layer6_insight/insight.py:118`

`"Critical_Alert" in active_alerts` — active_alerts는 ALT-XX ID 리스트라 절대 매칭 안 됨. 제거.

### 8. `alert.py:86` ALT-02 로컬 dedup 주석 오해
함수 내 신규 `alerts` 리스트라 OVR-02 외부 dedup과 무관. orchestrator가 처리. 주석 수정 또는 로컬 체크 제거.

### 9. `state.py:26 INSIGHT_IDS`에 `"INS-STRATEGY"` 누락
OVR-05 강제 append ID. R4가 무시하도록 설계되어 무해하지만 명시 권장.

### 10. ALT-06 vs Risk-A 경계 미세 불일치
- Risk-A: `disp_ma20 < 90` → Critical
- ALT-06: `disp_ma20 <= 90` → 발동
- `disp==90` 시 grade=High인데 alert는 발동. leading-indicator 설계로 보이나 Skills.md 명시 필요.

---

## ✅ 정상 확인 항목
- `WEIGHTS` 모든 phase 합 = 1.0 (점수 범위 1.0~4.0 보장)
- `m2_contraction` / `m2_growth_slowdown` 상호 배타 (재귀 ~check)
- Override 적용 순서 (STEP4=01→06→02, STEP7=03→04, STEP8=05) 일치
- 5개 리스크 모두 동일 `RiskOutput` 스키마 + `extra="forbid"` 준수
- CR-01 (MAX(hv, vkospi)) / CR-02 (MAX(mdd, var)) / CR-05 (bearish>sideways) 명세 일치
- SCN 우선순위 04→03→02→01 강도순 정확
- `score_to_band` 경계 "상위 구간 적용" 일관

---

## 즉시 수정 추천 우선순위
1. `_apply_cr03`의 두 번째 if → `elif` (실제 결과 달라짐)
2. OVR-03/04 하드코딩 → `EQUITY_CEILING_DEFAULT[strategy]` 참조
3. `or 0` 트릭 정책 결정 (silent fallback ↔ raise)

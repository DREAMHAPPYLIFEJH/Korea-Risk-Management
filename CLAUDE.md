# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Part A — Behavioral Guidelines

Reduce common LLM coding mistakes. Bias toward caution over speed; for trivial tasks use judgment.

### 1. Think Before Coding
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
- No features beyond what was asked.
- No abstractions for single-use code, no speculative "flexibility".
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

### 3. Surgical Changes
- Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Match existing style, even if you'd do it differently.
- Mention unrelated dead code; don't delete it.
- Remove imports/variables made unused **by your changes**, not pre-existing.

### 4. Goal-Driven Execution
Transform tasks into verifiable goals before coding:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"

For multi-step tasks, state a brief plan with verify steps.

---

## Part B — Project Context

**KOSPI Risk Intelligence Dashboard.** Analyzes KOSPI market risk across 5 risk types, produces a weighted integrated score, and maps it to investment strategy + asset allocation. Comments, docstrings, and insight templates are written in **Korean** — preserve that when editing.

### Source of truth

- **`Skills.md` is the contract document** (v6.1). Every implementation choice traces back to a section there. Threshold values, grade boundaries, rule IDs (`CR-XX`, `OVR-XX`, `ALT-XX`, `INS-XX`), JSON field structure — all live in Skills.md. Phase 2 (섹터) / Phase 3 (S&P 500) / Phase 4 (보조 마켓 컨텍스트 — PER/PBR 구현·나머지 계획) / Phase 5 (변동성 리스크 프레임워크 — 구현, 표시 전용) 섹션도 동일 문서 안에 정식화.
- When implementing or modifying behavior, **cite the Skills.md section ID in the docstring** (`# Risk-A`, `# OVR-03`, `# CR-02`, etc.). Existing code follows this convention — match it.
- `README.md` describes user-facing behavior and architecture. `preceed.md` is a chronological progress log.
- Do not edit Skills.md or the Korean planning PDF/MD as a side-effect of code changes.

### Architecture — 7 layers, strict one-way dependency

```
Layer 7 Visualization  ── plotly/streamlit components
Layer 6 Insight        ── 11 insights + R1~R5 dedup + OVR-05
Layer 5 Strategy       ── 6-step decision tree (OVR-03/04, CR-03)
Layer 4 Scoring        ── phase (bullish/bearish/sideways) + integrated_score
Layer 3 Risk           ── 5 risks, each producing a Pydantic RiskOutput
Layer 2 Indicator      ── price / volatility / liquidity / downside / derived
Layer 1 Data           ── kiwoom_client, kospi_fetcher, macro_fetcher (ECOS), cleaner, state
```

Cross-cutting modules (allowed to be imported by multiple layers):
- `config/constants.py` — `GRADE_MAP`, `STRATEGY_LEVEL`, `EQUITY_CEILING_DEFAULT`, `STRATEGY_INSIGHT_TEMPLATE`, `SCORE_BAND_THRESHOLDS`, etc.
- `config/thresholds.py` — every numeric grade boundary. **Market expansion (S&P500, crypto, etc.) is done by swapping only this file.** Do not hardcode thresholds elsewhere.
- `rules/override.py`, `rules/alert.py` — `OVR-01~06`, `ALT-01~12` (구현 완료).
- `rules/conflict.py` — `CR-01~05` 목록만 docstring으로 존재 (스텁). 실제 구현은 각 layer 내부: CR-01 → `layer3_risk/volatility.py`, CR-02 → `layer3_risk/downside.py`, CR-03 → `layer5_strategy/strategy.py`.

Orchestration:
- `pipeline/orchestrator.py::run_snapshot()` — KOSPI, STEP 1→9 in order.
- `pipeline/us_pipeline.py::run_us_snapshot()` — S&P 500 (Phase 3). 동일 키 구조 dict 반환 + `market="us"` / `fred_available` 필드. Layer 2~6 + Rules 전부 재사용; STEP 1만 `us_fetcher` + `fred_fetcher`로 교체, Risk-E만 `us_macro`로 교체. VIX는 `risk_volatility.evaluate(vkospi=vix, ...)`에 직접 전달 (KOSPI의 `vkospi=None` 보류 분기 활용).
- `pipeline/sector_pipeline.py::run_sector_analysis(result)` — Phase 2 섹터, KOSPI 한정 보조 분석.
- `pipeline/vol_pipeline.py::run_vol_analysis(kospi_result, us_result)` — Phase 5 한미 변동성 관계 (RI-01~05, 5분류 레짐, TRG-01~04). 표시 전용 — 통합 점수·5리스크·Override·Alert 무영향. V-KOSPI(KRX)·VVIX·SKEW를 직접 수집하고 두 result의 close/hv는 재사용.

The dashboard entry point is `app/streamlit_app.py`. 헤더 아래 시장 선택 라디오로 KOSPI/S&P 500 분기 → 공통 함수 `render_market_dashboard(result, *, price_label)`로 동일 본문 렌더링. 섹터 분석은 KOSPI 한정.

**Hard rules** when editing:
1. **Layer N may import only from Layer N-1, `config/`, or `rules/`.** Never sideways or upward. New cross-layer imports are a code smell — surface it.
2. **All 5 Risk outputs share the same Pydantic schema** (`layer3_risk/schema.py`): 6 top-level fields + 9 fields inside `details`. Adding/removing/renaming a field breaks every downstream consumer. The schema uses `extra="forbid"` — adding an undocumented field will raise at runtime.
3. **Override application order is fixed:** STEP 4 applies `OVR-01 → OVR-06 → OVR-02`; STEP 7 applies `OVR-03 → OVR-04`; STEP 8 applies `OVR-05`. Reordering changes semantics.
4. **STATE** (`data/state.json`) is updated at end-of-day only via `layer1_data/state.update_eod()`. Mid-pipeline mutation is a bug — sole exception: `roll_vol_ratio_window()` is called during STEP 9 alert evaluation (ALT-04 requires the value before the check).

### Phase 1 deliberate gaps

These are **known and intentional** — do not "fix" them without confirming intent:
- **VKOSPI is on hold *for grading*** (KOSPI 측, 의도적 결정): a V-KOSPI fetcher now exists (`layer1_data/vkospi_fetcher.py` — KRX 로그인 + `MDCSTAT01402`) and feeds **Phase 5 (display-only)**, but is **deliberately NOT wired into `Risk-B`**. By decision, V-KOSPI/VRP must not affect the 5-risk grade/score — they live only in Phase 5. So `Risk-B` still computes from HV20 alone; `vkospi`/`vkospi_grade` serialize as `null`; CR-01's `MAX(hv_grade, vkospi_grade)` collapses to `hv_grade`. The conditional branch is in place, but wiring it would flip Risk-B to Critical at current V-KOSPI levels and cascade into score/strategy/alerts — **do not wire without confirming intent**. (S&P 500 측은 yfinance `^VIX`를 `vkospi=` 자리에 전달하여 Risk-B에서 활성화됨.)
- **No Korean exchange holiday calendar**: `pd.bdate_range` includes 5/1, 5/5, etc. The cleaner's forward-fill absorbs this.
- **pytest is stubbed**: tests under `tests/` exist as files but coverage is inline / manual. Treat the README's "라이브 검증 결과" section as the regression baseline.

### Build / run / test

All commands assume the conda env `kospi_risk` (Python 3.10–3.12) is active and `.env` is populated.

| Task | Command |
|------|---------|
| Install deps | `pip install -r requirements.txt` |
| Launch dashboard | `streamlit run app/streamlit_app.py` → http://localhost:8501 |
| Headless KOSPI snapshot | `python -c "from datetime import date; from pipeline.orchestrator import run_snapshot; print(run_snapshot(date(2026,4,30)))"` |
| Headless S&P 500 snapshot | `python -c "from datetime import date; from pipeline.us_pipeline import run_us_snapshot; print(run_us_snapshot(date(2026,4,30)))"` |
| Run all tests | `pytest tests/` |
| Run one test | `pytest tests/test_pipeline.py::test_name -v` |

First run of `run_snapshot` takes 30–60s because `ka10051` (foreign net buying) loops day-by-day and hits a 429 rate limit. Streamlit caches snapshots for 1 hour via `@st.cache_data(ttl=3600)`.

**Fast iteration without live APIs**: `data/demo_*.pkl` hold full `run_snapshot()` / `run_us_snapshot()` / sector results. For Phase 2/3/5 or Layer 7 viz work, `pickle.load()` these instead of the slow live snapshot — e.g. `run_vol_analysis(pickle.load(open("data/demo_kospi.pkl","rb")), pickle.load(open("data/demo_sp500.pkl","rb")))`. Regenerate via `scripts/generate_demo_data.py` when the result dict shape changes (e.g. new top-level keys). Note: `pytest tests/` exists but coverage is **inline/manual** (see Phase 1 deliberate gaps) — the README's "라이브 검증 결과" is the regression baseline.

### Environment variables (required)

`.env` at repo root (gitignored). Template in `.env.example`.
- `ECOS_API_KEY` — Bank of Korea ECOS, https://ecos.bok.or.kr/api/
- `KIWOOM_APPKEY`, `KIWOOM_SECRETKEY` — Kiwoom Securities REST API, https://openapi.kiwoom.com
- `FRED_API_KEY` (Phase 3, optional) — St. Louis Fed FRED, https://fredaccount.stlouisfed.org/apikey. 미설정 시 `us_pipeline`의 `fed_rate`/`cpi_yoy`/`m2_contraction`가 None → DXY 단독으로 매크로 평가 (graceful degradation).
- `KRX_ID`, `KRX_PW` (Phase 4/5, optional) — KRX 정보데이터시스템 무료 회원 로그인. pykrx 자동 로그인에 사용 → **V-KOSPI**(Phase 5)·**KOSPI PER/PBR**(Phase 4) 조회. V-KOSPI 현물은 KRX 로그인 게이트 뒤에 있어 필수. 미설정 시 해당 지표 graceful degradation (V-KOSPI/PER/PBR None → Phase 5는 미국 단독 판정으로 대체).

Also gitignored and **never to be committed**: `*appkey*.txt`, `*secretkey*.txt`, the Kiwoom PDF/XLS docs (copyright).

### Conventions

- **Korean docstrings/comments are normal** — match the surrounding tone. User-facing insight strings (`STRATEGY_INSIGHT_TEMPLATE`, etc.) are deliberately Korean.
- **Cite the rule ID** in docstrings: `# OVR-03 — critical_count >= 1 → 최소 Moderate_Defensive 강제`. Future readers grep for these.
- **No new top-level files** unless the scope demands it. Adding a new risk type, indicator, or rule belongs in its layer module.
- **Thresholds belong in `config/thresholds.py`.** Magic numbers in layer modules are a bug.
- **Layer 7 plotly figures fail only at render, not import.** `py_compile`/import won't catch invalid props (e.g. the deprecated `titlefont` → must be `title=dict(text=, font=)`). Validate new figures headlessly with `fig.to_json()`, not just compile. When running headless tests, **don't pipe stderr to `/dev/null`** — it hides plotly errors; filter pykrx login noise with `grep -v "로그인\|시간:"` instead, and wrap stdout (`io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`) so Korean/`−`(U+2212) prints don't crash on cp949 consoles.

---

## Part C — Observed Patterns (derived from codebase)

These supplement Part B with patterns visible only by reading multiple files.

### Layer 3 Risk module contract

Every risk module (`layer3_risk/*.py`) must define these four module-level constants before the `evaluate()` function:

```python
RISK_ID             = "RISK-X"   # one of RiskId literals
WEIGHT_DEFAULT      = 0.XX
CONFLICT_RULE       = "none"     # or the rule applied
CONDITION_CANDIDATES = [...]     # full list of string condition names
```

`evaluate()` must use **keyword-only args** (`def evaluate(*, ...)`) and return `RiskOutput`. New risk types that deviate from this layout will break documentation tooling and downstream greps.

### `indicators` / `flags` / `sub_grades` field discipline

Inside `RiskDetails`:
- `indicators`: raw numeric inputs only (no booleans, no derived grades).
- `flags`: boolean signals and string tags computed inside `evaluate()`.
- `sub_grades`: numeric sub-scores if a risk uses internal grading steps; otherwise `{}`.

Mixing types across these three dicts causes downstream dashboard code to break silently (type coercion in `st.json` display).

### `result["series"]` is not JSON-serializable

`run_snapshot()` returns a `"series"` key containing live `pd.Series` objects. This is intentional — Layer 7 visualization consumes them directly. Do **not** call `model_dump()` or `json.dumps()` on the top-level result dict; only `result["risks"]` is already serialized via `.model_dump()`.

### `rules/conflict.py` is intentionally a stub

CR-01~05 are documented in the module docstring but not implemented as functions. CR-01 (HV vs VKOSPI max) is handled inside `layer3_risk/volatility.py`; CR-02 (MDD vs VaR max) inside `layer3_risk/downside.py`; CR-03 inside `layer5_strategy/strategy.py`. Do not add cross-cutting conflict logic to `rules/conflict.py` without confirming scope.

### One STATE mutation exception

`roll_vol_ratio_window(state, vol_ratio)` is called **during** STEP 9 alert evaluation, not at EOD. This is the sole sanctioned mid-pipeline STATE mutation (ALT-04 requires the window to be updated before the check). Do not introduce any other mid-pipeline state writes.

### Known `None` inputs — preserve the conditional branch pattern

Two inputs are permanently `None` in Phase 1:
- `vkospi=None` → `risk_volatility.evaluate()`
- `conc_ratio=None` → `risk_liquidity.evaluate()`

Both risk modules already have `if vkospi is not None:` / `if conc_ratio is not None:` guards. When hooking up a real data source, **only remove the guard and wire the value** — do not restructure the grading logic.

> **참고 (Phase 5)**: V-KOSPI 데이터 소스는 이제 존재하지만(`vkospi_fetcher`), Risk-B에는 **의도적으로 연결하지 않았습니다** — `risk_volatility.evaluate(vkospi=None)` 유지. V-KOSPI는 Phase 5 표시 전용으로만 사용. 등급 반영은 별도 결정 필요 (위 "Phase 1 deliberate gaps" 참조).

### `from __future__ import annotations`

All modules use this import as the first non-comment line. Include it in any new file to maintain uniform deferred annotation evaluation.

### Phase 2 섹터 리스크 — 독립 분석 구조

섹터 리스크는 Phase 1 파이프라인과 완전히 분리됩니다:
- `pipeline/sector_pipeline.py::run_sector_analysis(result)` — Phase 1 result를 받아 독립 실행
- `layer3_risk/sector.py::SectorOutput` — Phase 1 RiskOutput과 **별도 스키마** (`grade=None` 허용)
- 통합 점수·Override·Alert에 영향 없음

섹터 코드는 `config/constants.py::SECTOR_CODES`에서 관리. `inds_cd`에 "?"가 있으면 API 호출 없이 `data_available=False` 반환.

Skills.md 참조: `Phase 2 §P2-1 ~ P2-6`

### Phase 3 us_pipeline — orchestrator와 동일 dict 계약

`run_us_snapshot()`는 `run_snapshot()`과 **완전히 같은 top-level 키 집합**을 반환합니다 (+`market`, `fred_available` 두 필드만 추가). 그래서 `render_market_dashboard()` 한 함수로 두 시장 모두 렌더링 가능. 새 시장(예: 닛케이/암호화폐)을 추가할 때도 같은 계약을 따르면 UI 변경 불필요.

`series` dict도 동일 키 (`close`, `ma20/60/120`, `hv20`, `mdd60`, `mdd60_mc_p50`, `var95`, `vol_ratio`). Risk-D MC 메트릭(`mdd_60_mc`, `mdd_252_mc`, `var_95_mc`, `cvar_mc`)도 양 파이프라인 모두 wiring 완료 — `simulate_paths` + `mc_mdd_percentiles` 호출 패턴은 두 곳에서 동일.

Skills.md 참조: `Phase 3 §P3-1 ~ P3-6` (P3-6에 변경 이력 정리). Phase 4 `§P4-0 ~ P4-5`. Phase 5 `§P5-0 ~ P5-8`.

### Phase 5 vol_pipeline — 표시 전용 한미 변동성 관계

`run_vol_analysis(kospi_result, us_result)`는 sector_pipeline처럼 **독립 실행 + 등급 무영향**입니다. 두 result에서 `series["close"]`/`series["hv20"]`를 추출하고, V-KOSPI(KRX)·VVIX·SKEW는 직접 수집. 산출물은 별도 dict (RI-01~05, `regime`, `triggers`, `data_available`) — Phase 1 RiskOutput 스키마와 무관.

지표 계산은 `layer2_indicator/cross_market.py` (순수 함수: 스프레드·HV비율·VRP·상관·베타·레짐 분류·트리거). 임계값은 `config/thresholds.py` Phase 5 섹션. 모든 룰 ID(`RI-`, `REG-`, `TRG-`)는 Skills.md §P5 추적.

**orchestrator 추가 노출** (Phase 5 TRG-01 입력): `result["foreign"]["streak_sell"]` + `result["series"]["fx_rate"]`. 둘 다 이미 계산되던 값을 dict에 노출만 한 것 — 기존 동작 무변경. 구 데모 pkl엔 없으므로 vol_pipeline은 `.get()`으로 graceful.

**V-KOSPI/VRP는 Phase 5에서만 사용** — Risk-B 등급에 미반영 (위 deliberate gaps 참조). CBOE Put/Call·옵션 서피스(한국)는 데이터 부재로 미구현.

### Headless debugging without the full pipeline

To inspect a single indicator or risk without running `run_snapshot()`, import the layer directly:

```python
from layer3_risk.market import evaluate
from layer2_indicator.price import moving_average, disparity
```

The `at(series, default)` pattern in `pipeline/orchestrator.py:145` is the canonical way to extract a scalar from a `pd.Series` safely — replicate it in ad-hoc scripts rather than using `.iloc[-1]` directly.

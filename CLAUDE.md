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

- **`Skills.md` is the contract document** (v6.0). Every implementation choice traces back to a section there. Threshold values, grade boundaries, rule IDs (`CR-XX`, `OVR-XX`, `ALT-XX`, `INS-XX`), JSON field structure — all live in Skills.md.
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

Orchestration: `pipeline/orchestrator.py::run_snapshot()` runs STEP 1→9 in order. The dashboard entry point is `app/streamlit_app.py`, which only calls `run_snapshot()` and the Layer 7 builders.

**Hard rules** when editing:
1. **Layer N may import only from Layer N-1, `config/`, or `rules/`.** Never sideways or upward. New cross-layer imports are a code smell — surface it.
2. **All 5 Risk outputs share the same Pydantic schema** (`layer3_risk/schema.py`): 6 top-level fields + 9 fields inside `details`. Adding/removing/renaming a field breaks every downstream consumer. The schema uses `extra="forbid"` — adding an undocumented field will raise at runtime.
3. **Override application order is fixed:** STEP 4 applies `OVR-01 → OVR-06 → OVR-02`; STEP 7 applies `OVR-03 → OVR-04`; STEP 8 applies `OVR-05`. Reordering changes semantics.
4. **STATE** (`data/state.json`) is updated at end-of-day only via `layer1_data/state.update_eod()`. Mid-pipeline mutation is a bug — sole exception: `roll_vol_ratio_window()` is called during STEP 9 alert evaluation (ALT-04 requires the value before the check).

### Phase 1 deliberate gaps

These are **known and intentional** — do not "fix" them without confirming intent:
- **VKOSPI is on hold**: no external data source available. `Risk-B` computes from HV20 alone; `vkospi`/`vkospi_grade` fields serialize as `null`. CR-01's `MAX(hv_grade, vkospi_grade)` collapses to `hv_grade`. Fetcher hookup is the only thing missing — the conditional branch is already in place.
- **No Korean exchange holiday calendar**: `pd.bdate_range` includes 5/1, 5/5, etc. The cleaner's forward-fill absorbs this.
- **pytest is stubbed**: tests under `tests/` exist as files but coverage is inline / manual. Treat the README's "라이브 검증 결과" section as the regression baseline.

### Build / run / test

All commands assume the conda env `kospi_risk` (Python 3.10–3.12) is active and `.env` is populated.

| Task | Command |
|------|---------|
| Install deps | `pip install -r requirements.txt` |
| Launch dashboard | `streamlit run app/streamlit_app.py` → http://localhost:8501 |
| Headless snapshot | `python -c "from datetime import date; from pipeline.orchestrator import run_snapshot; print(run_snapshot(date(2026,4,30)))"` |
| Run all tests | `pytest tests/` |
| Run one test | `pytest tests/test_pipeline.py::test_name -v` |

First run of `run_snapshot` takes 30–60s because `ka10051` (foreign net buying) loops day-by-day and hits a 429 rate limit. Streamlit caches snapshots for 1 hour via `@st.cache_data(ttl=3600)`.

### Environment variables (required)

`.env` at repo root (gitignored). Template in `.env.example`.
- `ECOS_API_KEY` — Bank of Korea ECOS, https://ecos.bok.or.kr/api/
- `KIWOOM_APPKEY`, `KIWOOM_SECRETKEY` — Kiwoom Securities REST API, https://openapi.kiwoom.com

Also gitignored and **never to be committed**: `*appkey*.txt`, `*secretkey*.txt`, the Kiwoom PDF/XLS docs (copyright).

### Conventions

- **Korean docstrings/comments are normal** — match the surrounding tone. User-facing insight strings (`STRATEGY_INSIGHT_TEMPLATE`, etc.) are deliberately Korean.
- **Cite the rule ID** in docstrings: `# OVR-03 — critical_count >= 1 → 최소 Moderate_Defensive 강제`. Future readers grep for these.
- **No new top-level files** unless the scope demands it. Adding a new risk type, indicator, or rule belongs in its layer module.
- **Thresholds belong in `config/thresholds.py`.** Magic numbers in layer modules are a bug.

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

### `from __future__ import annotations`

All modules use this import as the first non-comment line. Include it in any new file to maintain uniform deferred annotation evaluation.

### Headless debugging without the full pipeline

To inspect a single indicator or risk without running `run_snapshot()`, import the layer directly:

```python
from layer3_risk.market import evaluate
from layer2_indicator.price import moving_average, disparity
```

The `at(series, default)` pattern in `pipeline/orchestrator.py:145` is the canonical way to extract a scalar from a `pd.Series` safely — replicate it in ad-hoc scripts rather than using `.iloc[-1]` directly.

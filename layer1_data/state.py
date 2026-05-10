"""STATE 영속화 — Skills.md §2 State Variables.

영업일 간 유지값 JSON 직렬화 → data/state.json.

업데이트 시점:
- ALT-04 알림 평가 중: roll_vol_ratio_window
- 영업일 마감 후: update_eod (또는 개별 함수들)

Skills.md §2 STATE 업데이트 규칙:
- prev_score_band       ← 당일 score_band
- prev_integrated_score ← 당일 integrated_score
- hv20_5d_ago           ← 5영업일 전 hv20 (롤링)
- vol_ratio_3d          ← 최근 3일 vol_ratio (롤링, 알림 평가 중 갱신)
- consecutive_days[id]  ← 인사이트 생성 시 +1, 미생성 시 0
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"

INSIGHT_IDS = [
    "INS-01", "INS-02", "INS-03", "INS-04", "INS-05",
    "INS-06", "INS-07", "INS-08", "INS-09", "INS-10", "INS-11",
]


def get_default_state() -> dict[str, Any]:
    """Skills.md §2 STATE 초기 구조."""
    return {
        "prev_score_band":        None,
        "prev_integrated_score":  None,
        "hv20_5d_ago":            None,
        "vol_ratio_3d":           [],
        "vol_ratio_streak_count": 0,
        "consecutive_days":       {iid: 0 for iid in INSIGHT_IDS},
    }


def load_state(path: Path | str = DEFAULT_STATE_PATH) -> dict[str, Any]:
    """JSON 파일에서 STATE 로드. 없거나 깨지면 기본값."""
    p = Path(path)
    if not p.exists():
        return get_default_state()
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return get_default_state()
    return _merge_with_defaults(loaded)


def save_state(state: dict[str, Any], path: Path | str = DEFAULT_STATE_PATH) -> None:
    """STATE를 JSON 파일로 저장. 부모 디렉토리 자동 생성."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _merge_with_defaults(loaded: dict[str, Any]) -> dict[str, Any]:
    """오래된 STATE 파일에 누락 필드가 있으면 기본값으로 보정."""
    state = get_default_state()
    for key, default in state.items():
        if key in loaded:
            state[key] = loaded[key]
    cd_loaded = loaded.get("consecutive_days", {})
    state["consecutive_days"] = {iid: cd_loaded.get(iid, 0) for iid in INSIGHT_IDS}
    return state


# ── 개별 업데이트 (Skills.md §2 규칙별) ──────────────────────
def update_score_band(
    state: dict[str, Any],
    score_band: str,
    integrated_score: float,
) -> None:
    """prev_score_band, prev_integrated_score 갱신 (영업일 마감)."""
    state["prev_score_band"] = score_band
    state["prev_integrated_score"] = float(integrated_score)


def update_hv20_5d_ago(
    state: dict[str, Any],
    hv20_history: list[float],
) -> None:
    """5영업일 전 hv20 갱신 (영업일 마감).

    hv20_history: 최근 hv20 시계열 (마지막 원소 = 오늘).
    길이가 5 미만이면 갱신하지 않음 (None 유지).
    """
    if len(hv20_history) >= 5:
        state["hv20_5d_ago"] = float(hv20_history[-5])


def roll_vol_ratio_window(
    state: dict[str, Any],
    vol_ratio_today: float,
) -> None:
    """vol_ratio_3d 롤링 윈도우 갱신 (ALT-04 평가 중).

    Skills.md §14 ALT-04: 오늘 값 push, 3개 초과 시 가장 오래된 것 pop.
    vol_ratio_streak_count도 함께 갱신 (≤ 0.6 연속 일수).
    """
    state["vol_ratio_3d"].append(float(vol_ratio_today))
    if len(state["vol_ratio_3d"]) > 3:
        state["vol_ratio_3d"] = state["vol_ratio_3d"][-3:]

    if vol_ratio_today <= 0.6:
        state["vol_ratio_streak_count"] = state["vol_ratio_streak_count"] + 1
    else:
        state["vol_ratio_streak_count"] = 0


def update_consecutive_days(
    state: dict[str, Any],
    generated_insight_ids: list[str],
) -> None:
    """인사이트 ID별 연속 생성 일수 갱신 (Skills.md §10 R4).

    생성된 ID는 +1, 미생성 ID는 0으로 초기화.
    """
    for iid in INSIGHT_IDS:
        if iid in generated_insight_ids:
            state["consecutive_days"][iid] = state["consecutive_days"].get(iid, 0) + 1
        else:
            state["consecutive_days"][iid] = 0


# ── 통합 (영업일 마감 시 일괄 호출) ───────────────────────────
def update_eod(
    state: dict[str, Any],
    *,
    score_band: str,
    integrated_score: float,
    hv20_history: list[float],
    generated_insight_ids: list[str],
) -> dict[str, Any]:
    """영업일 마감 후 STATE 일괄 갱신.

    vol_ratio_3d / vol_ratio_streak_count는 알림 평가 중 이미 갱신된 상태.
    """
    update_score_band(state, score_band, integrated_score)
    update_hv20_5d_ago(state, hv20_history)
    update_consecutive_days(state, generated_insight_ids)
    return state

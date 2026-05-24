"""한미 변동성 관계 지표 — Phase 5 (RI-01~05 + 레짐 분류 + 트리거).

VIX(미국)·V-KOSPI(한국) 양 시장 변동성의 관계를 정량화한다. 전부 순수 함수
(I/O 없음) — `pipeline/vol_pipeline.py`가 데이터를 받아 호출하고 결과를 조립한다.
표시 전용 — 통합 점수·5리스크·Override·Alert에 영향 없음.

Skills.md 참조: Phase 5 §P5-2(RI-01~05), §P5-4(REG-01~05), §P5-5(TRG)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.thresholds import (
    VIX_HIGH_ABS, VIX_LOW_ABS, VKOSPI_HIGH_ABS, VKOSPI_LOW_ABS,
    VIX_PCTL_HIGH, VIX_PCTL_LOW, VKOSPI_PCTL_HIGH, VKOSPI_PCTL_LOW,
    VVIX_WARNING, CORR_SYSTEMIC, CORR_WINDOW, VOL_PCTL_WINDOW,
    VKOSPI_PEAK_WINDOW, VIX_TRIGGER, VKOSPI_SYNC,
)

# 5분류 레짐 라벨 (Skills.md §P5-4)
REGIME_LABELS = {
    "REG-01": "글로벌 안정 (Global Stable)",
    "REG-02": "동조화 위기 (Synchronized Crisis)",
    "REG-03": "한국 단독 위기 (Korea-Only Stress)",
    "REG-04": "글로벌 회복기 (Global Recovery)",
    "REG-05": "미국 경계 (US Watch)",
}


# ── RI-01 ~ RI-03: 스칼라 관계 지표 ────────────────────────────
def vix_vkospi_spread(vix: float, vkospi: float) -> float | None:
    """RI-01 — VIX − V-KOSPI 스프레드 (line 81~91). 평소 음수(한국 프리미엄)."""
    if vix is None or vkospi is None:
        return None
    return vix - vkospi


def hv_ratio(kospi_hv20: float, sp_hv20: float) -> float | None:
    """RI-02 — KOSPI HV20 / S&P HV20 (line 115~124). 정상 1.2~1.5."""
    if kospi_hv20 is None or sp_hv20 is None or sp_hv20 == 0:
        return None
    return kospi_hv20 / sp_hv20


def vrp(implied: float, realized: float) -> float | None:
    """변동성 리스크 프리미엄 = 내재 − 실현 (line 133). us_vrp/kr_vrp 공통."""
    if implied is None or realized is None:
        return None
    return implied - realized


def vrp_divergence(us_vrp: float, kr_vrp: float) -> float | None:
    """RI-03 — US VRP − KR VRP (line 147~155)."""
    if us_vrp is None or kr_vrp is None:
        return None
    return us_vrp - kr_vrp


# ── RI-05: 한미 60일 상관계수 + 베타 ──────────────────────────
def correlation_beta(
    kospi_close: pd.Series, sp_close: pd.Series, window: int = CORR_WINDOW
) -> tuple[float | None, float | None]:
    """RI-05 — 한미 60일 상관계수·베타 (line 126~128, 229~238).

    두 종가 시계열을 공통 날짜로 정렬 → 일별 로그수익률 → 최근 window일 기준.
    데이터 부족(< window+1) 시 (None, None).
    Returns (corr_60d, kospi_beta). beta = Cov(KOSPI, S&P) / Var(S&P).
    """
    if kospi_close is None or sp_close is None:
        return None, None
    k = np.log(kospi_close).diff()
    s = np.log(sp_close).diff()
    aligned = pd.concat([k.rename("k"), s.rename("s")], axis=1).dropna()
    if len(aligned) < window + 1:
        return None, None
    aligned = aligned.tail(window)
    var_s = aligned["s"].var()
    if var_s == 0:
        return None, None
    corr = float(aligned["k"].corr(aligned["s"]))
    beta = float(aligned[["k", "s"]].cov().loc["k", "s"] / var_s)
    return corr, beta


def lead_lag_correlation(
    kospi_close: pd.Series, sp_close: pd.Series,
    lag: int = 1, window: int = CORR_WINDOW,
) -> float | None:
    """미국→한국 전이 상관 — S&P가 lag일 선행 (line 128). corr(KOSPI(t), S&P(t-lag)).

    동시점 상관(correlation_beta)과 달리 시차(7시간 오프셋)를 반영 — 문서상 더 강함.
    S&P 수익률을 lag일 앞당겨(shift) KOSPI 당일에 정렬. 데이터 부족 시 None.
    """
    if kospi_close is None or sp_close is None:
        return None
    k = np.log(kospi_close).diff()
    s = np.log(sp_close).diff().shift(lag)        # S&P(t-lag)을 KOSPI(t)에 맞춤
    aligned = pd.concat([k.rename("k"), s.rename("s")], axis=1).dropna()
    if len(aligned) < window + 1:
        return None
    aligned = aligned.tail(window)
    return float(aligned["k"].corr(aligned["s"]))


def garch_conditional_vol(close: pd.Series) -> pd.Series | None:
    """GARCH(1,1) 조건부 변동성 (연율화 %) 시계열 — 실현변동성 추이를 함수로 모델링.

    log 수익률(×100)에 GARCH(1,1) 적합(mean='Zero') → 일별 조건부 변동성 → 연율화(×√252).
    변동성 클러스터링(큰 변동 뒤 큰 변동)을 반영해 단순 HV20보다 매끄러운 추이.
    데이터 부족(<60) 또는 적합 실패 시 None.
    """
    if close is None or len(close) < 60:
        return None
    ret = (np.log(close / close.shift(1)).dropna()) * 100.0
    if len(ret) < 60:
        return None
    try:
        from arch import arch_model
        res = arch_model(ret, vol="Garch", p=1, q=1, mean="Zero", dist="normal").fit(
            disp="off", show_warning=False)
        cv = np.asarray(res.conditional_volatility)
    except Exception:
        return None
    return pd.Series(cv * np.sqrt(252), index=ret.index, name="garch_vol")


# ── 레짐 분류 (REG-01~05) ─────────────────────────────────────
def _pctl_rank(hist: pd.Series, value: float) -> float | None:
    """value가 hist(최근 1년) 분포에서 차지하는 백분위(0~100)."""
    if hist is None or len(hist) < VOL_PCTL_WINDOW:
        return None
    window = hist.dropna().tail(VOL_PCTL_WINDOW)
    if window.empty:
        return None
    return float((window < value).mean() * 100)


def _level(
    value: float, hist: pd.Series,
    abs_high: float, abs_low: float, pctl_high: float, pctl_low: float,
) -> str:
    """변동성 수준 판정 → 'high' / 'low' / 'mid'.

    1년치(252일+) 있으면 백분위, 아니면 절대값 fallback (line 279~288).
    """
    if value is None:
        return "mid"
    p = _pctl_rank(hist, value)
    if p is not None:
        if p >= pctl_high:
            return "high"
        if p <= pctl_low:
            return "low"
        return "mid"
    if value >= abs_high:
        return "high"
    if value <= abs_low:
        return "low"
    return "mid"


def classify_regime(
    vix: float, vkospi: float | None,
    vix_hist: pd.Series | None = None, vkospi_hist: pd.Series | None = None,
) -> tuple[str, str]:
    """5분류 통합 레짐 판정 (Skills.md §P5-4, IF/THEN).

    Returns (regime_id, regime_label). V-KOSPI None(데이터 결손) 시 미국 단독으로
    REG-05(US Watch)/REG-01만 구분.
    """
    vix_lv = _level(vix, vix_hist, VIX_HIGH_ABS, VIX_LOW_ABS,
                    VIX_PCTL_HIGH, VIX_PCTL_LOW)
    vix_high = (vix_lv == "high")

    if vkospi is None:                                   # 한국 데이터 결손
        reg = "REG-05" if vix_high else "REG-01"
        return reg, REGIME_LABELS[reg]

    vk_lv = _level(vkospi, vkospi_hist, VKOSPI_HIGH_ABS, VKOSPI_LOW_ABS,
                   VKOSPI_PCTL_HIGH, VKOSPI_PCTL_LOW)
    vkospi_high = (vk_lv == "high")

    # REG-02 동조화 위기 (둘 다 높음, 최우선)
    if vix_high and vkospi_high:
        reg = "REG-02"
    # REG-05 미국 경계 (미국만 높음 — 가장 중요한 조기경보)
    # 의도적으로 `not vkospi_high`로 넓게 잡음 (문서 line 268은 "V-KOSPI 낮음"이지만
    # V-KOSPI가 mid여도 "아직 안 터진 상태"는 조기경보 대상 — 옵션 A, Skills.md §P5-4).
    elif vix_high and not vkospi_high:
        reg = "REG-05"
    # REG-03 한국 단독 위기 (한국만 높음)
    elif vkospi_high and not vix_high:
        reg = "REG-03"
    # REG-04 글로벌 회복기 (분기 위치상 vix·vkospi 모두 not-high 확정 →
    # 최근 위기 통과 후 진정 중이면 회복기, 아니면 평온. mid·low 모두 회복으로 인정)
    elif _falling_from_peak(vkospi, vkospi_hist):
        reg = "REG-04"
    # REG-01 글로벌 안정 (기본)
    else:
        reg = "REG-01"
    return reg, REGIME_LABELS[reg]


def _falling_from_peak(
    vkospi: float, hist: pd.Series | None, window: int = VKOSPI_PEAK_WINDOW
) -> bool:
    """REG-04 판별 — 최근 window일 V-KOSPI 고점이 위기 수준(≥25)이었고 현재 그 아래.

    window는 V-KOSPI 평균회귀 반감기(~50일)에 맞춰 60일 (Skills.md §P5-3, P5-8).
    위기를 통과해 안정화되는 국면을 글로벌 안정(REG-01)과 구분.
    """
    if vkospi is None or hist is None or len(hist) < window:
        return False
    recent_peak = float(hist.dropna().tail(window).max())
    return recent_peak >= VKOSPI_HIGH_ABS and vkospi < recent_peak


# ── 핵심 신호 (TRG-01~04) ─────────────────────────────────────
def fx_vol_spike(fx_rate: pd.Series, window: int = 20, k: float = 2.0) -> bool:
    """TRG-01 보조 — 원/달러 변동성 급등 (잠정 정의, Skills.md §P5-8).

    최근 5일 실현변동성이 직전 window일 중앙값의 k배 초과면 급등으로 판정.
    """
    if fx_rate is None or len(fx_rate) < window + 6:
        return False
    ret = fx_rate.pct_change().dropna()
    roll5 = ret.rolling(5).std()
    recent = roll5.iloc[-1]
    baseline = roll5.tail(window).median()
    if pd.isna(recent) or pd.isna(baseline) or baseline == 0:
        return False
    return bool(recent > k * baseline)


def evaluate_triggers(
    vix: float, vkospi: float | None, corr_60d: float | None, vvix: float | None,
    fx_spike: bool, foreign_net_sell_5d: bool,
) -> dict[str, bool]:
    """TRG-01~04 평가 (Skills.md §P5-5). 입력 결손 시 해당 트리거 False."""
    return {
        # TRG-01 한국 단일 핵심 신호 (line 384~388)
        "TRG-01": bool(vix is not None and vix > VIX_TRIGGER
                       and fx_spike and foreign_net_sell_5d),
        # TRG-02 동조화 위기 진입 (line 349)
        "TRG-02": bool(vix is not None and vkospi is not None
                       and vix > VIX_TRIGGER and vkospi > VKOSPI_SYNC),
        # TRG-03 시스템 리스크 (line 351)
        "TRG-03": bool(corr_60d is not None and corr_60d > CORR_SYSTEMIC),
        # TRG-04 VVIX/SKEW 조기경보 — 미국 단독 (line 79)
        "TRG-04": bool(vvix is not None and vix is not None
                       and vvix > VVIX_WARNING and vix < VIX_LOW_ABS),
    }

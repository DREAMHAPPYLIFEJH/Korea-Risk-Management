"""해커톤 데모용 분석 결과 pickle 생성.

로컬에서 1회 실행하여 data/demo_*.pkl 6개 생성:
  - demo_kospi.pkl              : Phase 1 KOSPI 통합 분석
  - demo_sectors.pkl            : Phase 2 5섹터 분석
  - demo_sp500.pkl              : Phase 3 S&P500 분석
  - demo_kospi_fundamental.pkl  : Phase 4 KOSPI PER/PBR 시계열 (KRX)
  - demo_sp500_fundamental.pkl  : Phase 4 S&P500 PER/PBR 현재값 (SPY 근사)
  - demo_vol.pkl                : Phase 5 한미 변동성 관계 분석

Streamlit Cloud 에서는 키움/KRX API 호출 불가 → 이 pickle 들을 load 해서 시연.
앱은 DEMO_MODE=1 환경변수가 있으면 이 pickle 들을 읽는다 (app/streamlit_app.py).
"""

from __future__ import annotations

import pickle
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEMO_DATE = date(2026, 4, 30)
DEMO_DIR  = ROOT / "data"
DEMO_DIR.mkdir(exist_ok=True)


def _save(obj, name: str) -> None:
    path = DEMO_DIR / name
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    size_kb = path.stat().st_size / 1024
    print(f"  [OK] {name}  ({size_kb:.1f} KB)")


def main() -> None:
    print(f"[1/3] KOSPI 통합 분석 (기준일 {DEMO_DATE})...")
    t0 = time.time()
    from pipeline.orchestrator import run_snapshot
    kospi = run_snapshot(end_date=DEMO_DATE, lookback_days=400)
    print(f"  완료 ({time.time()-t0:.1f}s) - score={kospi['score']:.2f} → {kospi['score_band']}")
    _save(kospi, "demo_kospi.pkl")

    print(f"\n[2/3] 5 섹터 분석...")
    t0 = time.time()
    from pipeline.sector_pipeline import run_sector_analysis
    sectors = run_sector_analysis(kospi)
    print(f"  완료 ({time.time()-t0:.1f}s) - {len(sectors)}개 섹터")
    _save(sectors, "demo_sectors.pkl")

    print(f"\n[3/6] S&P500 분석...")
    t0 = time.time()
    from pipeline.us_pipeline import run_us_snapshot
    sp500 = run_us_snapshot(end_date=DEMO_DATE)
    print(f"  완료 ({time.time()-t0:.1f}s) - score={sp500['score']:.2f} → {sp500['score_band']}")
    _save(sp500, "demo_sp500.pkl")

    print(f"\n[4/6] KOSPI PER/PBR 시계열 (Phase 4, KRX)...")
    t0 = time.time()
    from layer1_data.krx_fetcher import get_kospi_fundamental
    start = (DEMO_DATE - timedelta(days=365)).strftime("%Y%m%d")
    end   = DEMO_DATE.strftime("%Y%m%d")
    kospi_fund = get_kospi_fundamental(start, end)
    n = 0 if kospi_fund is None else len(kospi_fund)
    print(f"  완료 ({time.time()-t0:.1f}s) - {n} 행" + ("" if n else " (KRX 미수집 → None 저장)"))
    _save(kospi_fund, "demo_kospi_fundamental.pkl")

    print(f"\n[5/6] S&P500 PER/PBR 현재값 (Phase 4, SPY 근사)...")
    t0 = time.time()
    from layer1_data.us_fetcher import get_sp500_fundamental
    sp500_fund = get_sp500_fundamental()
    print(f"  완료 ({time.time()-t0:.1f}s) - {sp500_fund}")
    _save(sp500_fund, "demo_sp500_fundamental.pkl")

    print(f"\n[6/6] 한미 변동성 관계 분석 (Phase 5)...")
    t0 = time.time()
    from pipeline.vol_pipeline import run_vol_analysis
    vol = run_vol_analysis(kospi, sp500)
    print(f"  완료 ({time.time()-t0:.1f}s) - regime={vol.get('regime')}")
    _save(vol, "demo_vol.pkl")

    print(f"\n[DONE] 모든 pickle 생성 완료 -> {DEMO_DIR}")


if __name__ == "__main__":
    main()

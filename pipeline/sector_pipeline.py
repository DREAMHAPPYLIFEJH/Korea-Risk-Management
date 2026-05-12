"""섹터 리스크 파이프라인 — Phase 2.

run_sector_analysis(result): Phase 1 run_snapshot() 결과를 받아
섹터별 리스크를 독립 분석. 통합 점수·Override·Alert에 영향 없음.
"""

from __future__ import annotations

from typing import Any

from config.constants import SECTOR_NAMES
from layer1_data.sector_fetcher import get_sector_ohlcv
from layer3_risk.sector import SectorOutput, evaluate


def run_sector_analysis(result: dict[str, Any]) -> list[SectorOutput]:
    """섹터 리스크 분석 — Phase 1 result에서 필요 데이터 추출.

    result["series"]["close"]: KOSPI 종가 시계열 (pd.Series).
    result["timestamp"]:       분석 기준일 (YYYY-MM-DD).

    업종 코드가 확보되지 않은 섹터는 data_available=False로 반환.
    """
    market_close = result["series"]["close"]
    start = market_close.index[0].strftime("%Y%m%d")
    end   = market_close.index[-1].strftime("%Y%m%d")

    outputs: list[SectorOutput] = []
    for sector in SECTOR_NAMES:
        sector_df    = get_sector_ohlcv(sector, start, end)
        sector_close = sector_df["close"] if sector_df is not None else None
        outputs.append(evaluate(
            sector=sector,
            sector_close=sector_close,
            market_close=market_close,
        ))
    return outputs

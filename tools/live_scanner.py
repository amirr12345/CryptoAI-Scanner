from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from collections import Counter
from dataclasses import dataclass

from core.candle_store import CandleStore
from core.trade_store import TradeStore
from services.live_confluence_service import (
    LiveConfluenceResult,
    LiveConfluenceService,
)
from services.market_service import MarketService


@dataclass(slots=True, frozen=True)
class ScanSummary:
    total_symbols: int
    evaluated: int
    stale_candles: int
    no_candles: int
    no_structure: int
    no_structure_break: int
    no_liquidity_sweep: int
    no_structure_setup: int
    no_historical_data: int
    insufficient_candles: int
    errors: int
    grades: dict[str, int]


class LiveScanner:
    """
    Scan live markets using:

        Live CandleStore
            ↓
        REST candle bootstrap
            ↓
        LiveConfluenceService
            ↓
        Historical Context
            ↓
        Confluence
    """

    def __init__(
        self,
        market_service: MarketService | None = None,
        candle_store: CandleStore | None = None,
        trade_store: TradeStore | None = None,
        confluence_service: LiveConfluenceService | None = None,
        timeframe: str = "60",
        candle_limit: int = 200,
    ) -> None:
        self.market_service = (
            market_service
            if market_service is not None
            else MarketService()
        )

        self.candle_store = (
            candle_store
            if candle_store is not None
            else CandleStore()
        )

        self.trade_store = (
            trade_store
            if trade_store is not None
            else TradeStore()
        )

        self.confluence_service = (
            confluence_service
            if confluence_service is not None
            else LiveConfluenceService(
                candle_store=self.candle_store
            )
        )

        self.timeframe = str(timeframe)
        self.candle_limit = int(candle_limit)

    @staticmethod
    def _extract_symbols(
        markets: dict,
    ) -> list[str]:
        stats = markets.get(
            "stats",
            {},
        )

        symbols = {
            key[:-4].upper()
            for key in stats
            if key.endswith("-rls")
        }

        return sorted(symbols)

    def scan_symbol(
        self,
        symbol: str,
    ) -> LiveConfluenceResult:
        normalized_symbol = (
            symbol.strip().upper()
        )

        bootstrap_candles = (
            self.market_service.history(
                normalized_symbol,
                resolution=self.timeframe,
                countback=self.candle_limit,
            )
        )

        latest_trade_timestamp = (
            self.trade_store.latest_timestamp(
                normalized_symbol
            )
        )

        return self.confluence_service.evaluate(
            symbol=normalized_symbol,
            candles=bootstrap_candles,
            latest_trade_timestamp=(
                latest_trade_timestamp
            ),
            timeframe=self.timeframe,
            candle_limit=self.candle_limit,
        )

    def scan(
        self,
        symbols: list[str] | None = None,
    ) -> tuple[
        list[tuple[str, LiveConfluenceResult]],
        ScanSummary,
    ]:
        if symbols is None:
            markets = (
                self.market_service.markets()
            )

            symbols = self._extract_symbols(
                markets
            )

        results: list[
            tuple[str, LiveConfluenceResult]
        ] = []

        status_counter = Counter()
        grade_counter = Counter()

        for symbol in symbols:
            normalized_symbol = (
                symbol.strip().upper()
            )

            try:
                result = self.scan_symbol(
                    normalized_symbol
                )

            except Exception as exc:
                result = LiveConfluenceResult(
                    symbol=normalized_symbol,
                    setup=None,
                    confluence=None,
                    status="ERROR",
                    reason=str(exc),
                )

            results.append(
                (
                    normalized_symbol,
                    result,
                )
            )

            status_counter[
                result.status
            ] += 1

            if (
                result.confluence is not None
            ):
                grade_counter[
                    result.confluence.grade
                ] += 1

        summary = ScanSummary(
            total_symbols=len(symbols),
            evaluated=status_counter[
                "EVALUATED"
            ],
            stale_candles=status_counter[
                "STALE_CANDLES"
            ],
            no_candles=status_counter[
                "NO_CANDLES"
            ],
            no_structure=status_counter[
                "NO_STRUCTURE"
            ],
            no_structure_break=status_counter[
                "NO_STRUCTURE_BREAK"
            ],
            no_liquidity_sweep=status_counter[
                "NO_LIQUIDITY_SWEEP"
            ],
            no_structure_setup=status_counter[
                "NO_STRUCTURE_SETUP"
            ],
            no_historical_data=status_counter[
                "NO_HISTORICAL_DATA"
            ],
            insufficient_candles=status_counter[
                "INSUFFICIENT_CANDLES"
            ],
            errors=(
                status_counter["ERROR"]
                + status_counter[
                    "FRESHNESS_CHECK_ERROR"
                ]
                + status_counter[
                    "HISTORICAL_CONTEXT_ERROR"
                ]
                + status_counter[
                    "CONFLUENCE_ERROR"
                ]
            ),
            grades=dict(
                grade_counter
            ),
        )

        return results, summary


def print_results(
    results: list[
        tuple[str, LiveConfluenceResult]
    ],
    summary: ScanSummary,
) -> None:
    print()
    print("=" * 120)
    print("LIVE CONFLUENCE SCANNER")
    print("=" * 120)

    print(
        f"Total symbols       : "
        f"{summary.total_symbols}"
    )
    print(
        f"Evaluated           : "
        f"{summary.evaluated}"
    )
    print(
        f"STALE_CANDLES       : "
        f"{summary.stale_candles}"
    )
    print(
        f"NO_CANDLES          : "
        f"{summary.no_candles}"
    )
    print(
        f"NO_STRUCTURE        : "
        f"{summary.no_structure}"
    )
    print(
        f"NO_STRUCTURE_BREAK  : "
        f"{summary.no_structure_break}"
    )
    print(
        f"NO_LIQUIDITY_SWEEP  : "
        f"{summary.no_liquidity_sweep}"
    )
    print(
        f"NO_STRUCTURE_SETUP  : "
        f"{summary.no_structure_setup}"
    )
    print(
        f"NO_HISTORICAL_DATA  : "
        f"{summary.no_historical_data}"
    )
    print(
        f"INSUFFICIENT_CANDLES: "
        f"{summary.insufficient_candles}"
    )
    print(
        f"ERRORS              : "
        f"{summary.errors}"
    )

    print()
    print("GRADE DISTRIBUTION")
    print("-" * 120)

    for grade in (
        "A+",
        "A",
        "B",
        "CONFLICT",
        "REJECT",
    ):
        print(
            f"{grade:<12}: "
            f"{summary.grades.get(grade, 0)}"
        )

    print()
    print("MARKET RESULTS")
    print("-" * 120)

    for symbol, result in results:
        if result.confluence is not None:
            print(
                f"{symbol:<12} "
                f"{result.status:<24} "
                f"{result.setup.direction:<9} "
                f"{result.confluence.grade:<9} "
                f"{result.confluence.score:>6.1f} "
                f"{result.reason}"
            )
        else:
            setup_direction = (
                result.setup.direction
                if result.setup is not None
                else "-"
            )

            print(
                f"{symbol:<12} "
                f"{result.status:<24} "
                f"{setup_direction:<9} "
                f"{'-':<9} "
                f"{'-':>6} "
                f"{result.reason}"
            )

    print()
    print("=" * 120)


def main() -> None:
    scanner = LiveScanner(
        timeframe="60",
        candle_limit=200,
    )

    results, summary = scanner.scan()

    print_results(
        results=results,
        summary=summary,
    )


if __name__ == "__main__":
    main()
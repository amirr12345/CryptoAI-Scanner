from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.candle_store import CandleStore
from core.market_registry import (
    MarketDescriptor,
    MarketRegistry,
)
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
    Live scanner with BASE/USDT as the primary
    analytical market.

    BASE/IRT is not the analytical source.

    USDT/IRT is only the local quote bridge.
    """

    def __init__(
        self,
        market_service: MarketService | None = None,
        candle_store: CandleStore | None = None,
        trade_store: TradeStore | None = None,
        confluence_service: LiveConfluenceService | None = None,
        market_registry: MarketRegistry | None = None,
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

        self.market_registry = (
            market_registry
            if market_registry is not None
            else MarketRegistry()
        )

        self.confluence_service = (
            confluence_service
            if confluence_service is not None
            else LiveConfluenceService(
                candle_store=self.candle_store
            )
        )

        self.timeframe = str(
            timeframe
        )

        self.candle_limit = int(
            candle_limit
        )

    @staticmethod
    def _extract_usdt_markets(
        markets: dict,
    ) -> list[str]:
        """
        Discover BASEUSDT analysis markets
        directly from Nobitex.
        """

        stats = markets.get(
            "stats",
            {},
        )

        analysis_markets: set[str] = set()

        for key in stats:
            value = (
                str(key)
                .strip()
                .upper()
            )

            if not value.endswith(
                "-USDT"
            ):
                continue

            base = value[:-5]

            if not base:
                continue

            analysis_markets.add(
                f"{base}USDT"
            )

        return sorted(
            analysis_markets
        )

    @staticmethod
    def _base_from_usdt_market(
        market_symbol: str,
    ) -> str:
        value = (
            market_symbol
            .strip()
            .upper()
        )

        if not value.endswith(
            "USDT"
        ):
            raise ValueError(
                f"Not a USDT market: "
                f"{market_symbol}"
            )

        base = value[:-4]

        if not base:
            raise ValueError(
                f"Invalid USDT market: "
                f"{market_symbol}"
            )

        return base

    def _resolve_market(
        self,
        analysis_market: str,
    ) -> MarketDescriptor:
        value = (
            analysis_market
            .strip()
            .upper()
        )

        if not value.endswith(
            "USDT"
        ):
            raise ValueError(
                "Analysis market must be BASEUSDT."
            )

        descriptor = (
            self.market_registry.get(
                value
            )
        )

        if descriptor is not None:
            return descriptor

        base = (
            self._base_from_usdt_market(
                value
            )
        )

        return MarketDescriptor(
            market_symbol=value,
            base_asset=base,
            quote_asset="USDT",
            analysis_market=value,
            execution_market=(
                f"{base}IRT"
            ),
        )

    def scan_market(
        self,
        analysis_market: str,
    ) -> LiveConfluenceResult:
        """
        Scan one BASE/USDT analytical market.
        """

        descriptor = (
            self._resolve_market(
                analysis_market
            )
        )

        bootstrap_candles = (
            self.market_service.history(
                descriptor.analysis_market,
                resolution=self.timeframe,
                countback=self.candle_limit,
            )
        )

        latest_trade_timestamp = (
            self.trade_store.latest_timestamp(
                descriptor.base_asset
            )
        )

        return (
            self.confluence_service.evaluate(
                symbol=descriptor.base_asset,
                candles=bootstrap_candles,
                latest_trade_timestamp=(
                    latest_trade_timestamp
                ),
                timeframe=self.timeframe,
                candle_limit=self.candle_limit,
            )
        )

    def scan(
        self,
        symbols: list[str] | None = None,
    ) -> tuple[
        list[
            tuple[
                str,
                MarketDescriptor,
                LiveConfluenceResult,
            ]
        ],
        ScanSummary,
    ]:
        if symbols is None:
            markets = (
                self.market_service.markets()
            )

            symbols = (
                self._extract_usdt_markets(
                    markets
                )
            )

        results = []

        status_counter = Counter()
        grade_counter = Counter()

        for analysis_market in symbols:
            analysis_market = (
                analysis_market
                .strip()
                .upper()
            )

            base_symbol = (
                self._base_from_usdt_market(
                    analysis_market
                )
            )

            try:
                descriptor = (
                    self._resolve_market(
                        analysis_market
                    )
                )

                result = (
                    self.scan_market(
                        analysis_market
                    )
                )

            except Exception as exc:
                descriptor = (
                    self._resolve_market(
                        analysis_market
                    )
                )

                result = (
                    LiveConfluenceResult(
                        symbol=base_symbol,
                        setup=None,
                        confluence=None,
                        status="ERROR",
                        reason=str(exc),
                    )
                )

            results.append(
                (
                    base_symbol,
                    descriptor,
                    result,
                )
            )

            status_counter[
                result.status
            ] += 1

            if (
                result.confluence
                is not None
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
        tuple[
            str,
            MarketDescriptor,
            LiveConfluenceResult,
        ]
    ],
    summary: ScanSummary,
) -> None:
    print()
    print("=" * 150)
    print(
        "LIVE CONFLUENCE SCANNER "
        "- USDT ANALYSIS"
    )
    print("=" * 150)

    print(
        f"Total USDT markets : "
        f"{summary.total_symbols}"
    )

    print(
        f"Evaluated          : "
        f"{summary.evaluated}"
    )

    print(
        f"STALE_CANDLES      : "
        f"{summary.stale_candles}"
    )

    print(
        f"NO_CANDLES         : "
        f"{summary.no_candles}"
    )

    print(
        f"NO_STRUCTURE       : "
        f"{summary.no_structure}"
    )

    print(
        f"NO_STRUCTURE_BREAK : "
        f"{summary.no_structure_break}"
    )

    print(
        f"NO_LIQUIDITY_SWEEP : "
        f"{summary.no_liquidity_sweep}"
    )

    print(
        f"NO_STRUCTURE_SETUP : "
        f"{summary.no_structure_setup}"
    )

    print(
        f"NO_HISTORICAL_DATA : "
        f"{summary.no_historical_data}"
    )

    print(
        f"INSUFFICIENT_CANDLES: "
        f"{summary.insufficient_candles}"
    )

    print(
        f"ERRORS             : "
        f"{summary.errors}"
    )

    print()
    print("GRADE DISTRIBUTION")
    print("-" * 150)

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
    print("-" * 150)

    print(
        f"{'BASE':<12} "
        f"{'ANALYSIS':<14} "
        f"{'EXECUTION':<14} "
        f"{'STATUS':<24} "
        f"{'DIR':<9} "
        f"{'GRADE':<10} "
        f"{'SCORE':>6} "
        f"REASON"
    )

    print("-" * 150)

    for (
        base,
        descriptor,
        result,
    ) in results:
        direction = (
            result.setup.direction
            if result.setup is not None
            else "-"
        )

        if (
            result.confluence
            is not None
        ):
            print(
                f"{base:<12} "
                f"{descriptor.analysis_market:<14} "
                f"{descriptor.execution_market:<14} "
                f"{result.status:<24} "
                f"{direction:<9} "
                f"{result.confluence.grade:<10} "
                f"{result.confluence.score:>6.1f} "
                f"{result.reason}"
            )

        else:
            print(
                f"{base:<12} "
                f"{descriptor.analysis_market:<14} "
                f"{descriptor.execution_market:<14} "
                f"{result.status:<24} "
                f"{direction:<9} "
                f"{'-':<10} "
                f"{'-':>6} "
                f"{result.reason}"
            )

    print()
    print("=" * 150)


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
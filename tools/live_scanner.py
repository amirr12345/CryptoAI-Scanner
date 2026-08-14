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
    Live market scanner with USDT as the analysis reference.

    Market identity:

        BASE/USDT
            -> primary analysis market

        BASE/IRT
            -> local Nobitex execution market

        USDT/IRT
            -> quote bridge

    The scanner never treats BASE/IRT as the primary
    analytical identity when a BASE/USDT reference exists.
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

        self.timeframe = str(timeframe)
        self.candle_limit = int(candle_limit)

    @staticmethod
    def _extract_symbols(
        markets: dict,
    ) -> list[str]:
        """
        Extract BASE assets from the RLS market list.

        Example:

            BTC-rls -> BTC
            ETH-rls -> ETH

        The scanner subsequently resolves BASE -> BASEUSDT
        through MarketRegistry.
        """

        stats = markets.get(
            "stats",
            {},
        )

        symbols: set[str] = set()

        for key in stats:
            if not key.endswith("-rls"):
                continue

            symbol = (
                key[:-4]
                .strip()
                .upper()
            )

            if symbol:
                symbols.add(symbol)

        return sorted(symbols)

    def _resolve_market(
        self,
        base_symbol: str,
    ) -> MarketDescriptor:
        """
        Resolve the analytical and execution identity
        of a BASE asset.
        """

        base = (
            base_symbol
            .strip()
            .upper()
        )

        if not base:
            raise ValueError(
                "Base symbol cannot be empty."
            )

        usdt_market = (
            self.market_registry.usdt_market(
                base
            )
        )

        irt_market = (
            self.market_registry.irt_market(
                base
            )
        )

        # Prefer the USDT market if it exists in the
        # discovered registry.
        usdt_descriptor = (
            self.market_registry.get(
                usdt_market
            )
        )

        if usdt_descriptor is not None:
            return usdt_descriptor

        # If BASE/USDT is not in the discovered market set,
        # keep BASE/IRT as execution while preserving
        # BASE/USDT as the analytical reference.
        return MarketDescriptor(
            market_symbol=irt_market,
            base_asset=base,
            quote_asset="IRT",
            analysis_market=usdt_market,
            execution_market=irt_market,
        )

    def _history_symbol(
        self,
        descriptor: MarketDescriptor,
    ) -> str:
        """
        Return the market identifier expected by the
        current MarketService.

        BASEUSDT remains the analytical reference.

        The current scanner uses the same logical market
        identifier for historical candles.
        """

        return descriptor.analysis_market

    def scan_symbol(
        self,
        symbol: str,
    ) -> LiveConfluenceResult:
        """
        Scan one BASE asset using BASE/USDT as the
        analytical reference.
        """

        descriptor = (
            self._resolve_market(
                symbol
            )
        )

        analysis_market = (
            self._history_symbol(
                descriptor
            )
        )

        # Bootstrap history using the analytical market.
        bootstrap_candles = (
            self.market_service.history(
                analysis_market,
                resolution=self.timeframe,
                countback=self.candle_limit,
            )
        )

        # Live candles are also looked up by the analytical
        # market identifier first.
        latest_trade_timestamp = (
            self.trade_store.latest_timestamp(
                descriptor.base_asset
            )
        )

        result = (
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

        return result

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
        """
        Scan all BASE assets.

        Each result carries:
            BASE
            analysis market
            execution market
            confluence result
        """

        if symbols is None:
            markets = (
                self.market_service.markets()
            )

            symbols = (
                self._extract_symbols(
                    markets
                )
            )

        results: list[
            tuple[
                str,
                MarketDescriptor,
                LiveConfluenceResult,
            ]
        ] = []

        status_counter = Counter()
        grade_counter = Counter()

        for symbol in symbols:
            base_symbol = (
                symbol.strip().upper()
            )

            try:
                descriptor = (
                    self._resolve_market(
                        base_symbol
                    )
                )

                result = (
                    self.scan_symbol(
                        base_symbol
                    )
                )

            except Exception as exc:
                descriptor = (
                    self._resolve_market(
                        base_symbol
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
    print("LIVE CONFLUENCE SCANNER - USDT REFERENCE")
    print("=" * 150)

    print(
        f"Total BASE assets      : "
        f"{summary.total_symbols}"
    )

    print(
        f"Evaluated              : "
        f"{summary.evaluated}"
    )

    print(
        f"STALE_CANDLES          : "
        f"{summary.stale_candles}"
    )

    print(
        f"NO_CANDLES             : "
        f"{summary.no_candles}"
    )

    print(
        f"NO_STRUCTURE           : "
        f"{summary.no_structure}"
    )

    print(
        f"NO_STRUCTURE_BREAK     : "
        f"{summary.no_structure_break}"
    )

    print(
        f"NO_LIQUIDITY_SWEEP     : "
        f"{summary.no_liquidity_sweep}"
    )

    print(
        f"NO_STRUCTURE_SETUP     : "
        f"{summary.no_structure_setup}"
    )

    print(
        f"NO_HISTORICAL_DATA     : "
        f"{summary.no_historical_data}"
    )

    print(
        f"INSUFFICIENT_CANDLES   : "
        f"{summary.insufficient_candles}"
    )

    print(
        f"ERRORS                 : "
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
        symbol,
        descriptor,
        result,
    ) in results:
        if (
            result.confluence
            is not None
        ):
            direction = (
                result.setup.direction
                if result.setup is not None
                else "-"
            )

            print(
                f"{symbol:<12} "
                f"{descriptor.analysis_market:<14} "
                f"{descriptor.execution_market:<14} "
                f"{result.status:<24} "
                f"{direction:<9} "
                f"{result.confluence.grade:<10} "
                f"{result.confluence.score:>6.1f} "
                f"{result.reason}"
            )

        else:
            direction = (
                result.setup.direction
                if result.setup is not None
                else "-"
            )

            print(
                f"{symbol:<12} "
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

    results, summary = (
        scanner.scan()
    )

    print_results(
        results=results,
        summary=summary,
    )


if __name__ == "__main__":
    main()
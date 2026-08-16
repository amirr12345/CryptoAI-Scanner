from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

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
    warming_up: int
    errors: int
    grades: dict[str, int]


class LiveScanner:
    """
    Candidate-first Gate.io USDT scanner.

    Production pipeline:

        Gate.io candles
              ↓
        Structure / MSS / Sweep
              ↓
        Candidate?
          ├── No  → STOP
          └── Yes
                ↓
        Historical Trades
                ↓
        Historical Context
                ↓
        Confluence

    Backward compatibility:

        Test doubles or legacy confluence services that do not
        implement find_candidate() fall back to evaluate().
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
        historical_trade_lookback_seconds: int = 3600,
        historical_trade_max_pages: int = 3,
        minimum_historical_trades: int = 50,
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

        self.historical_trade_lookback_seconds = int(
            historical_trade_lookback_seconds
        )

        self.historical_trade_max_pages = int(
            historical_trade_max_pages
        )

        self.minimum_historical_trades = int(
            minimum_historical_trades
        )

    @staticmethod
    def _extract_usdt_markets(
        markets: dict,
    ) -> list[str]:
        stats = markets.get(
            "stats",
            {},
        )

        symbols: set[str] = set()

        for key in stats:
            value = (
                str(key)
                .strip()
                .upper()
                .replace("-", "")
                .replace("_", "")
            )

            if not value.endswith(
                "USDT"
            ):
                continue

            base = value[:-4]

            if base:
                symbols.add(
                    f"{base}USDT"
                )

        return sorted(
            symbols
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
        symbol: str,
    ) -> MarketDescriptor:
        normalized = (
            symbol
            .strip()
            .upper()
        )

        if not normalized.endswith(
            "USDT"
        ):
            raise ValueError(
                "Analysis market must be BASEUSDT."
            )

        descriptor = (
            self.market_registry.get(
                normalized
            )
        )

        if descriptor is not None:
            return descriptor

        return (
            self.market_registry.register_symbol(
                normalized
            )
        )

    def _store_count(
        self,
        symbol: str,
    ) -> int:
        method = getattr(
            self.trade_store,
            "count",
            None,
        )

        if not callable(method):
            return 0

        return int(
            method(symbol)
        )

    def _store_latest_timestamp(
        self,
        symbol: str,
    ) -> int | None:
        method = getattr(
            self.trade_store,
            "latest_timestamp",
            None,
        )

        if not callable(method):
            return None

        return method(symbol)

    def _has_candidate_pipeline(
        self,
    ) -> bool:
        return callable(
            getattr(
                self.confluence_service,
                "find_candidate",
                None,
            )
        )

    def _legacy_evaluate(
        self,
        descriptor: MarketDescriptor,
        candles,
    ) -> LiveConfluenceResult:
        """
        Backward-compatible path for older FakeConfluenceService
        / test doubles.

        Production LiveConfluenceService has find_candidate(),
        so production never uses this path.
        """

        evaluate = getattr(
            self.confluence_service,
            "evaluate",
            None,
        )

        if not callable(evaluate):
            raise AttributeError(
                "Configured confluence service must implement "
                "find_candidate() or evaluate()."
            )

        return evaluate(
            symbol=descriptor.base_asset,
            candles=candles,
            latest_trade_timestamp=(
                self._store_latest_timestamp(
                    descriptor.base_asset
                )
            ),
            timeframe=self.timeframe,
            candle_limit=self.candle_limit,
        )

    def _bootstrap_historical_trades(
        self,
        descriptor: MarketDescriptor,
        candidate: LiveConfluenceResult,
    ) -> tuple[int, bool]:
        """
        Historical trades are fetched only for a valid candidate.
        """

        if candidate.setup is None:
            return (
                self._store_count(
                    descriptor.base_asset
                ),
                False,
            )

        method = getattr(
            self.market_service,
            "historical_trades",
            None,
        )

        if not callable(method):
            return (
                self._store_count(
                    descriptor.base_asset
                ),
                False,
            )

        setup_timestamp_ms = (
            int(candidate.setup.timestamp)
            * 1000
        )

        trades = method(
            symbol=descriptor.analysis_market,
            end_timestamp_ms=setup_timestamp_ms,
            lookback_seconds=(
                self.historical_trade_lookback_seconds
            ),
            max_pages=(
                self.historical_trade_max_pages
            ),
        )

        save_method = getattr(
            self.trade_store,
            "save_trades",
            None,
        )

        if (
            trades
            and callable(save_method)
        ):
            save_method(
                trades
            )

        return (
            self._store_count(
                descriptor.base_asset
            ),
            True,
        )

    def scan_market(
        self,
        analysis_market: str,
    ) -> LiveConfluenceResult:
        descriptor = (
            self._resolve_market(
                analysis_market
            )
        )

        candles = (
            self.market_service.history(
                descriptor.analysis_market,
                resolution=self.timeframe,
                countback=self.candle_limit,
            )
        )

        # --------------------------------------------------
        # Compatibility path for existing test doubles.
        # --------------------------------------------------

        if not self._has_candidate_pipeline():
            return self._legacy_evaluate(
                descriptor=descriptor,
                candles=candles,
            )

        # --------------------------------------------------
        # Production Candidate-first path.
        # --------------------------------------------------

        candidate = (
            self.confluence_service.find_candidate(
                symbol=descriptor.base_asset,
                candles=candles,
                timeframe=self.timeframe,
                candle_limit=self.candle_limit,
            )
        )

        if candidate.status != "CANDIDATE":
            return candidate

        # --------------------------------------------------
        # Historical trades ONLY for candidates.
        # --------------------------------------------------

        (
            trade_count,
            historical_supported,
        ) = (
            self._bootstrap_historical_trades(
                descriptor=descriptor,
                candidate=candidate,
            )
        )

        if (
            historical_supported
            and
            trade_count
            < self.minimum_historical_trades
        ):
            return LiveConfluenceResult(
                symbol=descriptor.base_asset,
                setup=candidate.setup,
                confluence=None,
                status="WARMING_UP",
                reason=(
                    "Historical trade coverage is "
                    f"insufficient: "
                    f"{trade_count} < "
                    f"{self.minimum_historical_trades}."
                ),
            )

        # --------------------------------------------------
        # Final Historical Context + Confluence.
        # --------------------------------------------------

        evaluate = getattr(
            self.confluence_service,
            "evaluate",
            None,
        )

        if not callable(evaluate):
            return LiveConfluenceResult(
                symbol=descriptor.base_asset,
                setup=candidate.setup,
                confluence=None,
                status="ERROR",
                reason=(
                    "Confluence service does not implement "
                    "evaluate()."
                ),
            )

        return evaluate(
            symbol=descriptor.base_asset,
            candles=candles,
            latest_trade_timestamp=(
                self._store_latest_timestamp(
                    descriptor.base_asset
                )
            ),
            timeframe=self.timeframe,
            candle_limit=self.candle_limit,
        )

    def scan(
        self,
        symbols: list[str] | None = None,
    ):
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

        for symbol in symbols:
            analysis_market = (
                symbol
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

            if result.confluence is not None:
                grade_counter[
                    result.confluence.grade
                ] += 1

        summary = ScanSummary(
            total_symbols=len(
                symbols
            ),
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
            warming_up=status_counter[
                "WARMING_UP"
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
    results,
    summary: ScanSummary,
) -> None:
    print()
    print("=" * 150)

    print(
        "LIVE CONFLUENCE SCANNER "
        "- GATE.IO USDT ANALYSIS"
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
        f"WARMING_UP         : "
        f"{summary.warming_up}"
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

        if result.confluence is not None:
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
        historical_trade_lookback_seconds=3600,
        historical_trade_max_pages=3,
        minimum_historical_trades=50,
    )

    results, summary = scanner.scan()

    print_results(
        results,
        summary,
    )


if __name__ == "__main__":
    main()
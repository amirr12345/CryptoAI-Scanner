from __future__ import annotations

import sys
from collections import Counter
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
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

        Gate.io markets
              ↓
        Top N USDT by 24h quote volume
              ↓
        Parallel candle bootstrap
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

    Performance:

        Candle requests are fetched concurrently using a bounded
        ThreadPoolExecutor.

    Historical trades remain candidate-only.
    """

    def __init__(
        self,
        market_service: MarketService | None = None,
        candle_store: CandleStore | None = None,
        trade_store: TradeStore | None = None,
        confluence_service: (
            LiveConfluenceService | None
        ) = None,
        market_registry: (
            MarketRegistry | None
        ) = None,
        timeframe: str = "60",
        candle_limit: int = 200,
        historical_trade_lookback_seconds: int = 3600,
        historical_trade_max_pages: int = 3,
        minimum_historical_trades: int = 50,
        max_symbols: int = 100,
        candle_workers: int = 10,
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

        self.max_symbols = int(
            max_symbols
        )

        self.candle_workers = int(
            candle_workers
        )

        if self.candle_limit <= 0:
            raise ValueError(
                "candle_limit must be greater than zero."
            )

        if (
            self.historical_trade_lookback_seconds
            <= 0
        ):
            raise ValueError(
                "historical_trade_lookback_seconds "
                "must be greater than zero."
            )

        if (
            self.historical_trade_max_pages
            <= 0
        ):
            raise ValueError(
                "historical_trade_max_pages "
                "must be greater than zero."
            )

        if (
            self.minimum_historical_trades
            <= 0
        ):
            raise ValueError(
                "minimum_historical_trades "
                "must be greater than zero."
            )

        if self.max_symbols <= 0:
            raise ValueError(
                "max_symbols must be greater than zero."
            )

        if self.candle_workers <= 0:
            raise ValueError(
                "candle_workers must be greater than zero."
            )

    @staticmethod
    def _extract_usdt_markets(
        markets: dict,
        limit: int = 100,
    ) -> list[str]:
        """
        Select Top-N USDT markets by 24h quote volume.

        Sorting:
            1. Highest quote volume first.
            2. Equal volume -> alphabetical symbol order.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        stats = markets.get(
            "stats",
            {},
        )

        candidates: list[
            tuple[str, float]
        ] = []

        for key, item in stats.items():
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

            if not base:
                continue

            if not isinstance(
                item,
                dict,
            ):
                continue

            try:
                quote_volume = float(
                    item.get(
                        "quote_volume",
                        0.0,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                quote_volume = 0.0

            if quote_volume < 0:
                quote_volume = 0.0

            candidates.append(
                (
                    f"{base}USDT",
                    quote_volume,
                )
            )

        candidates.sort(
            key=lambda item: (
                -item[1],
                item[0],
            )
        )

        return [
            symbol
            for symbol, _volume
            in candidates[:limit]
        ]

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

        if not callable(
            method
        ):
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

        if not callable(
            method
        ):
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
        evaluate = getattr(
            self.confluence_service,
            "evaluate",
            None,
        )

        if not callable(
            evaluate
        ):
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
        Fetch historical trades only for valid candidates.
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

        if not callable(
            method
        ):
            return (
                self._store_count(
                    descriptor.base_asset
                ),
                False,
            )

        setup_timestamp_ms = (
            int(
                candidate.setup.timestamp
            )
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
            and callable(
                save_method
            )
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

    def _fetch_candles(
        self,
        symbol: str,
    ):
        """
        Fetch one symbol's bootstrap candles.

        Returns:
            (symbol, candles, error)
        """

        try:
            candles = (
                self.market_service.history(
                    symbol,
                    resolution=self.timeframe,
                    countback=self.candle_limit,
                )
            )

            return (
                symbol,
                candles,
                None,
            )

        except Exception as exc:
            return (
                symbol,
                [],
                exc,
            )

    def _fetch_candles_parallel(
        self,
        symbols: list[str],
    ) -> dict[
        str,
        tuple[
            list,
            Exception | None,
        ],
    ]:
        """
        Fetch bootstrap candles concurrently.

        The dictionary preserves every requested symbol.
        """

        result: dict[
            str,
            tuple[
                list,
                Exception | None,
            ],
        ] = {}

        workers = min(
            self.candle_workers,
            max(
                1,
                len(symbols),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="gate-candle",
        ) as executor:

            futures = {
                executor.submit(
                    self._fetch_candles,
                    symbol,
                ): symbol
                for symbol in symbols
            }

            for future in as_completed(
                futures
            ):
                symbol = futures[
                    future
                ]

                try:
                    (
                        returned_symbol,
                        candles,
                        error,
                    ) = future.result()

                except Exception as exc:
                    result[
                        symbol
                    ] = (
                        [],
                        exc,
                    )
                    continue

                result[
                    returned_symbol
                ] = (
                    candles,
                    error,
                )

        return result

    def _evaluate_with_candles(
        self,
        descriptor: MarketDescriptor,
        candles,
    ) -> LiveConfluenceResult:
        """
        Run candidate-first pipeline using preloaded candles.
        """

        if not self._has_candidate_pipeline():
            return self._legacy_evaluate(
                descriptor=descriptor,
                candles=candles,
            )

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

        evaluate = getattr(
            self.confluence_service,
            "evaluate",
            None,
        )

        if not callable(
            evaluate
        ):
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

    def scan_market(
        self,
        analysis_market: str,
        candles=None,
    ) -> LiveConfluenceResult:
        """
        Scan one market.

        `candles` can be supplied by the parallel bootstrap stage.
        """

        descriptor = (
            self._resolve_market(
                analysis_market
            )
        )

        if candles is None:
            try:
                candles = (
                    self.market_service.history(
                        descriptor.analysis_market,
                        resolution=self.timeframe,
                        countback=self.candle_limit,
                    )
                )
            except Exception as exc:
                return LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=None,
                    confluence=None,
                    status="ERROR",
                    reason=str(exc),
                )

        if not self._has_candidate_pipeline():
            return self._legacy_evaluate(
                descriptor=descriptor,
                candles=candles,
            )

        return self._evaluate_with_candles(
            descriptor=descriptor,
            candles=candles,
        )

    def scan(
        self,
        symbols: list[str] | None = None,
    ):
        """
        Scan configured market universe.

        Default:

            all Gate.io markets
                 ↓
            USDT filter
                 ↓
            Top 100 by quote volume
                 ↓
            parallel candle bootstrap
                 ↓
            candidate-first
                 ↓
            historical trades only for candidates

        Explicit symbols bypass Top-N selection.
        """

        if symbols is None:
            markets = (
                self.market_service.markets()
            )

            symbols = (
                self._extract_usdt_markets(
                    markets,
                    limit=self.max_symbols,
                )
            )

        else:
            symbols = [
                symbol.strip().upper()
                for symbol in symbols
            ]

        # --------------------------------------------------
        # Parallel candle bootstrap.
        # --------------------------------------------------

        candle_map = (
            self._fetch_candles_parallel(
                symbols
            )
        )

        results = []

        status_counter = Counter()
        grade_counter = Counter()

        for symbol in symbols:
            analysis_market = (
                symbol.strip().upper()
            )

            base_symbol = (
                self._base_from_usdt_market(
                    analysis_market
                )
            )

            descriptor = (
                self._resolve_market(
                    analysis_market
                )
            )

            candles, candle_error = (
                candle_map.get(
                    analysis_market,
                    (
                        [],
                        RuntimeError(
                            "Candle bootstrap result missing."
                        ),
                    ),
                )
            )

            if candle_error is not None:
                result = (
                    LiveConfluenceResult(
                        symbol=base_symbol,
                        setup=None,
                        confluence=None,
                        status="ERROR",
                        reason=(
                            "Candle bootstrap failed: "
                            f"{candle_error}"
                        ),
                    )
                )

            else:
                try:
                    result = (
                        self.scan_market(
                            analysis_market,
                            candles=candles,
                        )
                    )

                except Exception as exc:
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
                status_counter[
                    "ERROR"
                ]
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

        return (
            results,
            summary,
        )


def print_results(
    results,
    summary: ScanSummary,
) -> None:
    print()
    print(
        "=" * 150
    )

    print(
        "LIVE CONFLUENCE SCANNER "
        "- GATE.IO USDT ANALYSIS"
    )

    print(
        "=" * 150
    )

    print(
        f"Universe           : "
        f"Top {summary.total_symbols} USDT markets "
        f"by 24h quote volume"
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
    print(
        "GRADE DISTRIBUTION"
    )

    print(
        "-" * 150
    )

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
    print(
        "MARKET RESULTS"
    )

    print(
        "-" * 150
    )

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

    print(
        "-" * 150
    )

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
    print(
        "=" * 150
    )


def main() -> None:
    # Fix Windows PowerShell / cp1256 console encoding.
    if hasattr(
        sys.stdout,
        "reconfigure",
    ):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    if hasattr(
        sys.stderr,
        "reconfigure",
    ):
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    scanner = LiveScanner(
        timeframe="60",
        candle_limit=200,
        historical_trade_lookback_seconds=3600,
        historical_trade_max_pages=3,
        minimum_historical_trades=50,
        max_symbols=100,
        candle_workers=10,
    )

    results, summary = (
        scanner.scan()
    )

    print_results(
        results,
        summary,
    )


if __name__ == "__main__":
    main()
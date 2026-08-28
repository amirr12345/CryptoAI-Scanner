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
from microstructure.session_ranking import (
    SessionRankingEngine,
)
from services.live_confluence_service import (
    LiveConfluenceResult,
    LiveConfluenceService,
)
from services.live_data_freshness import (
    LiveDataFreshness,
)
from services.market_service import (
    MarketService,
)


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

    order_book_unavailable: int

    errors: int

    execution_execute: int
    execution_wait: int
    execution_block: int

    grades: dict[str, int]
    sessions: dict[str, int]


class LiveScanner:
    """
    Candidate-first Gate.io USDT scanner.

    Modern production pipeline:

        Gate.io markets
              ↓
        Top-N USDT by quote volume
              ↓
        Parallel candle bootstrap
              ↓
        Parallel candidate detection
              ↓
        Parallel historical trade bootstrap
              ↓
        Parallel historical context
              ↓
        Parallel historical confluence
              ↓
        Parallel current Order Book
              ↓
        Parallel live execution confirmation
              ↓
        EXECUTE / WAIT / BLOCK

    Backward compatibility:

        Legacy test doubles that only implement evaluate()
        continue to work through _legacy_evaluate().

    Important:

        Current Order Book never changes the primary
        historical confluence score.

        It is used only by the live execution gate.
    """

    # ==========================================================
    # DATA MODES
    # ==========================================================

    DATA_MODE_REST_BOOTSTRAP = (
        "REST_BOOTSTRAP"
    )

    DATA_MODE_LIVE = (
        LiveDataFreshness.LIVE
    )

    # ==========================================================
    # DEFAULT WORKERS
    # ==========================================================

    DEFAULT_CANDLE_WORKERS = 10
    DEFAULT_CONTEXT_WORKERS = 10
    DEFAULT_ORDER_BOOK_WORKERS = 10

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

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
        context_workers: int | None = None,
        order_book_workers: int | None = None,
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
                candle_store=self.candle_store,
                market_service=self.market_service,
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

        self.context_workers = int(
            context_workers
            if context_workers is not None
            else self.DEFAULT_CONTEXT_WORKERS
        )

        self.order_book_workers = int(
            order_book_workers
            if order_book_workers is not None
            else self.DEFAULT_ORDER_BOOK_WORKERS
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

        if self.context_workers <= 0:
            raise ValueError(
                "context_workers must be greater than zero."
            )

        if self.order_book_workers <= 0:
            raise ValueError(
                "order_book_workers must be greater than zero."
            )

    # ==========================================================
    # MARKET SELECTION
    # ==========================================================

    @staticmethod
    def _extract_usdt_markets(
        markets: dict,
        limit: int = 100,
    ) -> list[str]:

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

    # ==========================================================
    # STORE HELPERS
    # ==========================================================

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

        try:
            return int(
                method(symbol)
            )
        except Exception:
            return 0

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

        try:
            return method(symbol)
        except Exception:
            return None

    # ==========================================================
    # CANDIDATE API
    # ==========================================================

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

    # ==========================================================
    # LEGACY API
    # ==========================================================

    def _legacy_evaluate(
        self,
        descriptor: MarketDescriptor,
        candles,
    ) -> LiveConfluenceResult:
        """
        Backward-compatible path for older test doubles.

        Older FakeConfluenceService implementations may expose
        evaluate() but not find_candidate().

        Such services must not be treated as runtime errors.
        """

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
            data_mode=(
                self.DATA_MODE_REST_BOOTSTRAP
            ),
        )

    # ==========================================================
    # CANDLE FETCHING
    # ==========================================================

    def _fetch_candles(
        self,
        symbol: str,
    ):

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

        result = {}

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

    # ==========================================================
    # CANDIDATE DETECTION
    # ==========================================================

    def _detect_candidate(
        self,
        symbol: str,
        candle_map,
    ):
        """
        Detect candidate.

        Modern:
            find_candidate()

        Legacy:
            evaluate()

        The legacy path is intentionally preserved because
        existing unit tests use lightweight fake services.
        """

        descriptor = (
            self._resolve_market(
                symbol
            )
        )

        candles, candle_error = (
            candle_map.get(
                symbol,
                (
                    [],
                    RuntimeError(
                        "Missing candle result."
                    ),
                ),
            )
        )

        if candle_error is not None:

            return (
                symbol,
                descriptor,
                None,
                candle_error,
            )

        # ------------------------------------------------------
        # Modern candidate-first path
        # ------------------------------------------------------

        if self._has_candidate_pipeline():

            try:

                candidate = (
                    self.confluence_service
                    .find_candidate(
                        symbol=descriptor.base_asset,
                        candles=candles,
                        timeframe=self.timeframe,
                        candle_limit=self.candle_limit,
                        data_mode=(
                            self.DATA_MODE_REST_BOOTSTRAP
                        ),
                    )
                )

                return (
                    symbol,
                    descriptor,
                    candidate,
                    None,
                )

            except Exception as exc:

                return (
                    symbol,
                    descriptor,
                    None,
                    exc,
                )

        # ------------------------------------------------------
        # Legacy fallback
        # ------------------------------------------------------

        try:

            legacy_result = (
                self._legacy_evaluate(
                    descriptor=descriptor,
                    candles=candles,
                )
            )

            return (
                symbol,
                descriptor,
                legacy_result,
                None,
            )

        except Exception as exc:

            return (
                symbol,
                descriptor,
                None,
                exc,
            )

    def _detect_candidates_parallel(
        self,
        symbols: list[str],
        candle_map,
    ):

        result = {}

        workers = min(
            self.context_workers,
            max(
                1,
                len(symbols),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="candidate",
        ) as executor:

            futures = {
                executor.submit(
                    self._detect_candidate,
                    symbol,
                    candle_map,
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
                        descriptor,
                        candidate,
                        error,
                    ) = future.result()

                except Exception as exc:

                    result[
                        symbol
                    ] = (
                        None,
                        None,
                        exc,
                    )

                    continue

                result[
                    returned_symbol
                ] = (
                    descriptor,
                    candidate,
                    error,
                )

        return result

    # ==========================================================
    # HISTORICAL TRADES
    # ==========================================================

    def _bootstrap_historical_trades(
        self,
        descriptor: MarketDescriptor,
        candidate: LiveConfluenceResult,
    ) -> tuple[int, bool]:

        if (
            candidate is None
            or candidate.setup is None
        ):

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

    def _bootstrap_candidate_trades(
        self,
        symbol: str,
        candidate_data,
    ):

        (
            descriptor,
            candidate,
            error,
        ) = candidate_data

        if error is not None:

            return (
                symbol,
                descriptor,
                candidate,
                0,
                False,
                error,
            )

        if candidate is None:

            return (
                symbol,
                descriptor,
                candidate,
                0,
                False,
                None,
            )

        # Legacy FakeConfluenceService:
        #
        # Its evaluate() result already represents the final
        # test result and should not be passed through modern
        # historical bootstrap.
        if not self._has_candidate_pipeline():

            return (
                symbol,
                descriptor,
                candidate,
                0,
                False,
                None,
            )

        if candidate.status != "CANDIDATE":

            return (
                symbol,
                descriptor,
                candidate,
                0,
                False,
                None,
            )

        try:

            (
                count,
                supported,
            ) = (
                self._bootstrap_historical_trades(
                    descriptor=descriptor,
                    candidate=candidate,
                )
            )

            return (
                symbol,
                descriptor,
                candidate,
                count,
                supported,
                None,
            )

        except Exception as exc:

            return (
                symbol,
                descriptor,
                candidate,
                0,
                False,
                exc,
            )

    def _bootstrap_trades_parallel(
        self,
        candidate_results,
    ):

        result = {}

        candidates = [
            (
                symbol,
                data,
            )
            for symbol, data
            in candidate_results.items()
            if (
                data[1] is not None
                and
                data[1].status
                == "CANDIDATE"
            )
        ]

        if not candidates:
            return result

        workers = min(
            self.context_workers,
            max(
                1,
                len(candidates),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="historical-trades",
        ) as executor:

            futures = {
                executor.submit(
                    self._bootstrap_candidate_trades,
                    symbol,
                    data,
                ): symbol
                for symbol, data
                in candidates
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
                        descriptor,
                        candidate,
                        count,
                        supported,
                        error,
                    ) = future.result()

                except Exception as exc:

                    result[
                        symbol
                    ] = (
                        None,
                        None,
                        0,
                        False,
                        exc,
                    )

                    continue

                result[
                    returned_symbol
                ] = (
                    descriptor,
                    candidate,
                    count,
                    supported,
                    error,
                )

        return result

    # ==========================================================
    # HISTORICAL CONTEXT
    # ==========================================================

    def _build_historical_context(
        self,
        symbol: str,
        trade_result,
    ):

        (
            descriptor,
            candidate,
            trade_count,
            supported,
            trade_error,
        ) = trade_result

        if descriptor is None:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                trade_count,
                supported,
                trade_error,
            )

        if trade_error is not None:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                trade_count,
                supported,
                trade_error,
            )

        if (
            candidate is None
            or candidate.status
            != "CANDIDATE"
            or candidate.setup is None
        ):

            return (
                symbol,
                descriptor,
                candidate,
                None,
                trade_count,
                supported,
                None,
            )

        if (
            supported
            and
            trade_count
            < self.minimum_historical_trades
        ):

            return (
                symbol,
                descriptor,
                candidate,
                None,
                trade_count,
                supported,
                None,
            )

        try:

            context = (
                self.confluence_service
                .historical_context
                .calculate(
                    symbol=descriptor.base_asset,
                    timestamp=int(
                        candidate.setup.timestamp
                    ),
                    lookback_seconds=(
                        self
                        .historical_trade_lookback_seconds
                    ),
                )
            )

            return (
                symbol,
                descriptor,
                candidate,
                context,
                trade_count,
                supported,
                None,
            )

        except Exception as exc:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                trade_count,
                supported,
                exc,
            )

    def _build_historical_context_parallel(
        self,
        trade_results,
    ):

        result = {}

        candidates = [
            (
                symbol,
                data,
            )
            for symbol, data
            in trade_results.items()
            if (
                data[1] is not None
                and
                data[1].status
                == "CANDIDATE"
            )
        ]

        if not candidates:
            return result

        workers = min(
            self.context_workers,
            max(
                1,
                len(candidates),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="historical-context",
        ) as executor:

            futures = {
                executor.submit(
                    self._build_historical_context,
                    symbol,
                    data,
                ): symbol
                for symbol, data
                in candidates
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
                        descriptor,
                        candidate,
                        context,
                        trade_count,
                        supported,
                        error,
                    ) = future.result()

                except Exception as exc:

                    result[
                        symbol
                    ] = (
                        None,
                        None,
                        None,
                        0,
                        False,
                        exc,
                    )

                    continue

                result[
                    returned_symbol
                ] = (
                    descriptor,
                    candidate,
                    context,
                    trade_count,
                    supported,
                    error,
                )

        return result

    # ==========================================================
    # HISTORICAL CONFLUENCE
    # ==========================================================

    def _evaluate_historical_context(
        self,
        symbol: str,
        context_result,
    ):

        (
            descriptor,
            candidate,
            context,
            trade_count,
            supported,
            context_error,
        ) = context_result

        if descriptor is None:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                context_error,
            )

        if candidate is None:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                context_error,
            )

        if candidate.status != "CANDIDATE":

            return (
                symbol,
                descriptor,
                candidate,
                None,
                None,
            )

        if context_error is not None:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                context_error,
            )

        if context is None:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                None,
            )

        try:

            historical = (
                self.confluence_service
                .historical_confluence
                .evaluate(
                    setup=candidate.setup,
                    context=context,
                    order_book=None,
                    live_mode=False,
                )
            )

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
            )

        except Exception as exc:

            return (
                symbol,
                descriptor,
                candidate,
                None,
                exc,
            )

    def _evaluate_historical_parallel(
        self,
        context_results,
    ):

        result = {}

        candidates = [
            (
                symbol,
                data,
            )
            for symbol, data
            in context_results.items()
            if (
                data[1] is not None
                and
                data[1].status
                == "CANDIDATE"
            )
        ]

        if not candidates:
            return result

        workers = min(
            self.context_workers,
            max(
                1,
                len(candidates),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="historical-score",
        ) as executor:

            futures = {
                executor.submit(
                    self._evaluate_historical_context,
                    symbol,
                    data,
                ): symbol
                for symbol, data
                in candidates
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
                        descriptor,
                        candidate,
                        historical,
                        error,
                    ) = future.result()

                except Exception as exc:

                    result[
                        symbol
                    ] = (
                        None,
                        None,
                        None,
                        exc,
                    )

                    continue

                result[
                    returned_symbol
                ] = (
                    descriptor,
                    candidate,
                    historical,
                    error,
                )

        return result

    # ==========================================================
    # ORDER BOOK
    # ==========================================================

    def _fetch_live_order_book(
        self,
        symbol: str,
    ):

        try:

            order_book = (
                self.confluence_service
                ._get_live_order_book_context(
                    symbol=symbol
                )
            )

            return (
                symbol,
                order_book,
                None,
            )

        except Exception as exc:

            return (
                symbol,
                None,
                exc,
            )

    def _fetch_live_order_books_parallel(
        self,
        symbols: list[str],
    ):

        result = {}

        if not symbols:
            return result

        workers = min(
            self.order_book_workers,
            max(
                1,
                len(symbols),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="live-orderbook",
        ) as executor:

            futures = {
                executor.submit(
                    self._fetch_live_order_book,
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
                        order_book,
                        error,
                    ) = future.result()

                except Exception as exc:

                    result[
                        symbol
                    ] = (
                        None,
                        exc,
                    )

                    continue

                result[
                    returned_symbol
                ] = (
                    order_book,
                    error,
                )

        return result

    # ==========================================================
    # LIVE CONFIRMATION
    # ==========================================================

    def _confirm_live_order_book(
        self,
        symbol: str,
        historical_result,
        order_book_result,
    ):

        (
            descriptor,
            candidate,
            historical,
            historical_error,
        ) = historical_result

        (
            order_book,
            order_book_error,
        ) = order_book_result

        if descriptor is None:

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
                historical_error,
            )

        if candidate is None:

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
                historical_error,
            )

        if candidate.setup is None:

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
                historical_error,
            )

        if historical_error is not None:

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
                historical_error,
            )

        if historical is None:

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
                None,
            )

        # ------------------------------------------------------
        # Order Book unavailable
        # ------------------------------------------------------

        if (
            order_book_error is not None
            or order_book is None
        ):

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=candidate.setup,
                    confluence=(
                        historical.confluence
                    ),
                    status="ORDER_BOOK_UNAVAILABLE",
                    reason=(
                        "Current Order Book was unavailable."
                    ),
                ),
                None,
            )

        # ------------------------------------------------------
        # Live confirmation
        # ------------------------------------------------------

        try:

            context = (
                self.confluence_service
                .historical_context
                .calculate(
                    symbol=descriptor.base_asset,
                    timestamp=int(
                        candidate.setup.timestamp
                    ),
                    lookback_seconds=(
                        self
                        .historical_trade_lookback_seconds
                    ),
                )
            )

            live = (
                self.confluence_service
                .historical_confluence
                .evaluate(
                    setup=candidate.setup,
                    context=context,
                    order_book=order_book,
                    live_mode=True,
                )
            )

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=candidate.setup,
                    confluence=live,
                    status="EVALUATED",
                    reason=(
                        "Live confluence evaluated with "
                        "current Order Book execution gate."
                    ),
                ),
                None,
            )

        except Exception as exc:

            return (
                symbol,
                descriptor,
                candidate,
                historical,
                None,
                exc,
            )

    def _build_live_results_parallel(
        self,
        historical_results,
        orderbook_results,
    ):

        result = {}

        symbols = [
            symbol
            for symbol, data
            in historical_results.items()
            if (
                data[1] is not None
                and data[1].status
                == "CANDIDATE"
            )
        ]

        if not symbols:
            return result

        workers = min(
            self.order_book_workers,
            max(
                1,
                len(symbols),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="live-confirmation",
        ) as executor:

            futures = {}

            for symbol in symbols:

                order_book_result = (
                    orderbook_results.get(
                        symbol,
                        (
                            None,
                            RuntimeError(
                                "Order Book result missing."
                            ),
                        ),
                    )
                )

                futures[
                    executor.submit(
                        self._confirm_live_order_book,
                        symbol,
                        historical_results[
                            symbol
                        ],
                        order_book_result,
                    )
                ] = symbol

            for future in as_completed(
                futures
            ):

                symbol = futures[
                    future
                ]

                try:

                    (
                        returned_symbol,
                        descriptor,
                        candidate,
                        historical,
                        live,
                        error,
                    ) = future.result()

                except Exception as exc:

                    result[
                        symbol
                    ] = (
                        None,
                        None,
                        None,
                        None,
                        exc,
                    )

                    continue

                result[
                    returned_symbol
                ] = (
                    descriptor,
                    candidate,
                    historical,
                    live,
                    error,
                )

        return result

    # ==========================================================
    # SINGLE-MARKET EVALUATION
    # ==========================================================

    def _evaluate_with_candles(
        self,
        descriptor: MarketDescriptor,
        candles,
    ) -> LiveConfluenceResult:

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
                data_mode=(
                    self.DATA_MODE_REST_BOOTSTRAP
                ),
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
            data_mode=(
                self.DATA_MODE_LIVE
            ),
        )

    def scan_market(
        self,
        analysis_market: str,
        candles=None,
    ) -> LiveConfluenceResult:

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

        return self._evaluate_with_candles(
            descriptor=descriptor,
            candles=candles,
        )

    # ==========================================================
    # FULL PARALLEL SCAN
    # ==========================================================

    def scan(
        self,
        symbols: list[str] | None = None,
    ):

        # ------------------------------------------------------
        # 1. Universe
        # ------------------------------------------------------

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
                symbol
                .strip()
                .upper()
                for symbol
                in symbols
            ]

        # ------------------------------------------------------
        # 2. Candles
        # ------------------------------------------------------

        candle_map = (
            self._fetch_candles_parallel(
                symbols
            )
        )

        # ------------------------------------------------------
        # 3. Candidates
        # ------------------------------------------------------

        candidate_results = (
            self._detect_candidates_parallel(
                symbols=symbols,
                candle_map=candle_map,
            )
        )

        # ------------------------------------------------------
        # LEGACY MODE
        #
        # Existing unit-test fake services should retain their
        # old behavior and should not be forced through the
        # modern multi-stage pipeline.
        # ------------------------------------------------------

        if not self._has_candidate_pipeline():

            ordered_results = []

            for symbol in symbols:

                (
                    descriptor,
                    result,
                    error,
                ) = candidate_results.get(
                    symbol,
                    (
                        None,
                        None,
                        RuntimeError(
                            "Candidate result missing."
                        ),
                    ),
                )

                if descriptor is None:

                    descriptor = (
                        self._resolve_market(
                            symbol
                        )
                    )

                if error is not None:

                    result = (
                        LiveConfluenceResult(
                            symbol=descriptor.base_asset,
                            setup=None,
                            confluence=None,
                            status="ERROR",
                            reason=str(error),
                        )
                    )

                elif result is None:

                    result = (
                        LiveConfluenceResult(
                            symbol=descriptor.base_asset,
                            setup=None,
                            confluence=None,
                            status="ERROR",
                            reason=(
                                "Legacy evaluation "
                                "returned no result."
                            ),
                        )
                    )

                ordered_results.append(
                    (
                        descriptor.base_asset,
                        descriptor,
                        result,
                    )
                )

            return (
                ordered_results,
                self._build_summary(
                    ordered_results
                ),
            )

        # ------------------------------------------------------
        # 4. Historical trades
        # ------------------------------------------------------

        trade_results = (
            self._bootstrap_trades_parallel(
                candidate_results
            )
        )

        final_results: dict[
            str,
            LiveConfluenceResult,
        ] = {}

        # ------------------------------------------------------
        # Preserve non-candidate states
        # ------------------------------------------------------

        for symbol in symbols:

            candidate_data = (
                candidate_results.get(
                    symbol
                )
            )

            if candidate_data is None:

                descriptor = (
                    self._resolve_market(
                        symbol
                    )
                )

                final_results[
                    symbol
                ] = LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=None,
                    confluence=None,
                    status="ERROR",
                    reason=(
                        "Candidate result missing."
                    ),
                )

                continue

            (
                descriptor,
                candidate,
                candidate_error,
            ) = candidate_data

            if candidate_error is not None:

                final_results[
                    symbol
                ] = LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=None,
                    confluence=None,
                    status="ERROR",
                    reason=str(
                        candidate_error
                    ),
                )

                continue

            if candidate is None:

                final_results[
                    symbol
                ] = LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=None,
                    confluence=None,
                    status="ERROR",
                    reason=(
                        "Candidate result was empty."
                    ),
                )

                continue

            if candidate.status != "CANDIDATE":

                final_results[
                    symbol
                ] = candidate

        # ------------------------------------------------------
        # 5. Historical Context
        # ------------------------------------------------------

        context_input = {}

        for symbol, (
            descriptor,
            candidate,
            trade_count,
            supported,
            trade_error,
        ) in trade_results.items():

            if trade_error is not None:

                final_results[
                    symbol
                ] = LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=(
                        candidate.setup
                        if candidate
                        else None
                    ),
                    confluence=None,
                    status="NO_HISTORICAL_DATA",
                    reason=str(
                        trade_error
                    ),
                )

                continue

            if (
                candidate is None
                or candidate.status
                != "CANDIDATE"
            ):
                continue

            if (
                supported
                and
                trade_count
                < self.minimum_historical_trades
            ):

                final_results[
                    symbol
                ] = LiveConfluenceResult(
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

                continue

            context_input[
                symbol
            ] = (
                descriptor,
                candidate,
                trade_count,
                supported,
                None,
            )

        context_results = (
            self._build_historical_context_parallel(
                {
                    symbol: (
                        descriptor,
                        candidate,
                        trade_count,
                        supported,
                        error,
                    )
                    for symbol, (
                        descriptor,
                        candidate,
                        trade_count,
                        supported,
                        error,
                    ) in context_input.items()
                }
            )
        )

        # ------------------------------------------------------
        # 6. Historical Confluence
        # ------------------------------------------------------

        historical_results = (
            self._evaluate_historical_parallel(
                context_results
            )
        )

        # ------------------------------------------------------
        # 7. Only valid historical candidates proceed to
        #    current Order Book.
        # ------------------------------------------------------

        live_candidate_symbols = []

        for symbol, (
            descriptor,
            candidate,
            historical,
            historical_error,
        ) in historical_results.items():

            if historical_error is not None:

                final_results[
                    symbol
                ] = LiveConfluenceResult(
                    symbol=descriptor.base_asset,
                    setup=(
                        candidate.setup
                        if candidate
                        else None
                    ),
                    confluence=None,
                    status=(
                        "NO_HISTORICAL_DATA"
                        if isinstance(
                            historical_error,
                            ValueError,
                        )
                        else "HISTORICAL_CONTEXT_ERROR"
                    ),
                    reason=str(
                        historical_error
                    ),
                )

                continue

            if (
                historical is None
                or candidate is None
            ):
                continue

            live_candidate_symbols.append(
                symbol
            )

        # ------------------------------------------------------
        # 8. Current Order Book
        # ------------------------------------------------------

        orderbook_results = (
            self._fetch_live_order_books_parallel(
                live_candidate_symbols
            )
        )

        # ------------------------------------------------------
        # 9. Live confirmation
        # ------------------------------------------------------

        live_results = (
            self._build_live_results_parallel(
                historical_results={
                    symbol: data
                    for symbol, data
                    in historical_results.items()
                    if symbol
                    in live_candidate_symbols
                },
                orderbook_results=(
                    orderbook_results
                ),
            )
        )

        # ------------------------------------------------------
        # 10. Final assembly
        # ------------------------------------------------------

        for symbol, (
            descriptor,
            candidate,
            historical,
            live,
            error,
        ) in live_results.items():

            if (
                error is not None
                or live is None
            ):

                if descriptor is not None:

                    final_results[
                        symbol
                    ] = LiveConfluenceResult(
                        symbol=descriptor.base_asset,
                        setup=(
                            candidate.setup
                            if candidate
                            else None
                        ),
                        confluence=None,
                        status="CONFLUENCE_ERROR",
                        reason=(
                            str(error)
                            if error is not None
                            else (
                                "Live result missing."
                            )
                        ),
                    )

                continue

            final_results[
                symbol
            ] = live

        # ------------------------------------------------------
        # 11. Ordered output
        # ------------------------------------------------------

        ordered_results = []

        for symbol in symbols:

            descriptor = (
                self._resolve_market(
                    symbol
                )
            )

            result = (
                final_results.get(
                    symbol
                )
            )

            if result is None:

                result = (
                    LiveConfluenceResult(
                        symbol=descriptor.base_asset,
                        setup=None,
                        confluence=None,
                        status="ERROR",
                        reason=(
                            "Final result was not produced."
                        ),
                    )
                )

            ordered_results.append(
                (
                    descriptor.base_asset,
                    descriptor,
                    result,
                )
            )

        return (
            ordered_results,
            self._build_summary(
                ordered_results
            ),
        )

    # ==========================================================
    # SUMMARY
    # ==========================================================

    @staticmethod
    def _build_summary(
        results,
    ) -> ScanSummary:

        status_counter = Counter()
        grade_counter = Counter()
        session_counter = Counter()
        execution_counter = Counter()

        for (
            _base,
            _descriptor,
            result,
        ) in results:

            status_counter[
                result.status
            ] += 1

            if result.confluence is not None:

                confluence = (
                    result.confluence
                )

                grade_counter[
                    confluence.grade
                ] += 1

                session_counter[
                    confluence.session_name
                ] += 1

                execution_counter[
                    confluence.execution_status
                ] += 1

        return ScanSummary(
            total_symbols=len(
                results
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

            order_book_unavailable=status_counter[
                "ORDER_BOOK_UNAVAILABLE"
            ],

            errors=(
                status_counter["ERROR"]
                + status_counter[
                    "HISTORICAL_CONTEXT_ERROR"
                ]
                + status_counter[
                    "CONFLUENCE_ERROR"
                ]
            ),

            execution_execute=(
                execution_counter[
                    "EXECUTE"
                ]
            ),

            execution_wait=(
                execution_counter[
                    "WAIT"
                ]
            ),

            execution_block=(
                execution_counter[
                    "BLOCK"
                ]
            ),

            grades=dict(
                grade_counter
            ),

            sessions=dict(
                session_counter
            ),
        )


# ==================================================================
# OUTPUT
# ==================================================================


def print_results(
    results,
    summary: ScanSummary,
) -> None:

    print()
    print("=" * 180)

    print(
        "LIVE CONFLUENCE SCANNER - "
        "STRUCTURE + CVD + VWAP + PROFILE + "
        "ORDER FLOW + ORDER BOOK + SESSION"
    )

    print("=" * 180)

    print(
        f"Universe                 : "
        f"Top {summary.total_symbols} USDT markets"
    )

    print(
        f"Evaluated                : "
        f"{summary.evaluated}"
    )

    print(
        f"WARMING_UP               : "
        f"{summary.warming_up}"
    )

    print(
        f"STALE_CANDLES            : "
        f"{summary.stale_candles}"
    )

    print(
        f"NO_CANDLES               : "
        f"{summary.no_candles}"
    )

    print(
        f"NO_STRUCTURE             : "
        f"{summary.no_structure}"
    )

    print(
        f"NO_STRUCTURE_BREAK      : "
        f"{summary.no_structure_break}"
    )

    print(
        f"NO_LIQUIDITY_SWEEP      : "
        f"{summary.no_liquidity_sweep}"
    )

    print(
        f"NO_STRUCTURE_SETUP      : "
        f"{summary.no_structure_setup}"
    )

    print(
        f"NO_HISTORICAL_DATA      : "
        f"{summary.no_historical_data}"
    )

    print(
        f"INSUFFICIENT_CANDLES    : "
        f"{summary.insufficient_candles}"
    )

    print(
        f"ORDER_BOOK_UNAVAILABLE  : "
        f"{summary.order_book_unavailable}"
    )

    print(
        f"ERRORS                  : "
        f"{summary.errors}"
    )

    # --------------------------------------------------------------
    # EXECUTION
    # --------------------------------------------------------------

    print()
    print(
        "EXECUTION DISTRIBUTION"
    )

    print(
        "-" * 80
    )

    print(
        f"EXECUTE                 : "
        f"{summary.execution_execute}"
    )

    print(
        f"WAIT                    : "
        f"{summary.execution_wait}"
    )

    print(
        f"BLOCK                   : "
        f"{summary.execution_block}"
    )

    # --------------------------------------------------------------
    # GRADE
    # --------------------------------------------------------------

    print()
    print(
        "GRADE DISTRIBUTION"
    )

    print(
        "-" * 80
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

    # --------------------------------------------------------------
    # SESSION
    # --------------------------------------------------------------

    print()
    print(
        "SESSION DISTRIBUTION"
    )

    print(
        "-" * 80
    )

    for session_name in (
        "ASIA",
        "LONDON",
        "LONDON_NY_OVERLAP",
        "NEW_YORK",
        "OFF_HOURS",
        "UNKNOWN",
    ):

        print(
            f"{session_name:<24}: "
            f"{summary.sessions.get(session_name, 0)}"
        )

    # --------------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------------

    print()
    print(
        "MARKET RESULTS"
    )

    print(
        "-" * 180
    )

    print(
        f"{'BASE':<10}"
        f"{'ANALYSIS':<14}"
        f"{'EXECUTION':<12}"
        f"{'STATUS':<24}"
        f"{'DIR':<9}"
        f"{'GRADE':<10}"
        f"{'SCORE':>7} "
        f"{'SESSION':<22}"
        f"{'SESSION_Q':>10} "
        f"{'OB':>9}"
        f"  REASON"
    )

    print(
        "-" * 180
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

        if result.confluence is None:

            print(
                f"{base:<10}"
                f"{descriptor.analysis_market:<14}"
                f"{'-':<12}"
                f"{result.status:<24}"
                f"{direction:<9}"
                f"{'-':<10}"
                f"{'-':>7} "
                f"{'-':<22}"
                f"{'-':>10} "
                f"{'-':>9}"
                f"  {result.reason}"
            )

            continue

        confluence = (
            result.confluence
        )

        print(
            f"{base:<10}"
            f"{descriptor.analysis_market:<14}"
            f"{confluence.execution_status:<12}"
            f"{result.status:<24}"
            f"{direction:<9}"
            f"{confluence.grade:<10}"
            f"{confluence.score:>7.2f} "
            f"{confluence.session_name:<22}"
            f"{confluence.session_quality:>10.2f} "
            f"{confluence.order_book_imbalance:>+9.3f}"
            f"  {result.reason}"
        )

    print()
    print(
        "=" * 180
    )


def main() -> None:

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
        context_workers=10,
        order_book_workers=10,
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
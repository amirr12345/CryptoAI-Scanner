from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from core.candle_store import CandleStore
from microstructure.confluence_engine import (
    ConfluenceEngine,
)
from microstructure.historical_confluence import (
    HistoricalConfluenceEngine,
)
from microstructure.historical_context import (
    HistoricalContextEngine,
)
from microstructure.liquidity_sweep import (
    LiquiditySweepEngine,
)
from microstructure.market_structure import (
    MarketStructureEngine,
)
from microstructure.structure_break import (
    StructureBreakEngine,
)
from microstructure.structure_setup import (
    StructureSetupEngine,
)
from models.candle import Candle
from models.confluence_result import (
    ConfluenceResult,
)
from models.structure_setup import (
    StructureSetup,
)
from services.live_data_freshness import (
    LiveDataFreshness,
)
from services.market_service import (
    MarketService,
)


@dataclass(slots=True, frozen=True)
class LiveConfluenceResult:
    """
    Result of the live structure/confluence pipeline.
    """

    symbol: str
    setup: StructureSetup | None
    confluence: ConfluenceResult | None
    status: str
    reason: str


class LiveConfluenceService:
    """
    Live structure/confluence pipeline.

    Production LIVE:

        Candles
          ↓
        Freshness
          ↓
        Structure / MSS
          ↓
        Liquidity Sweep
          ↓
        Structure Setup
          ↓
        Historical Context
          ↓
        Current Order Book
          ↓
        Execution Gate

    REST/Historical:

        Candidate
          ↓
        Historical Context
          ↓
        Historical Confluence

    Historical calculations never use current Order Book.
    """

    ORDER_BOOK_DEPTH = 20

    def __init__(
        self,
        market_structure_engine: MarketStructureEngine | None = None,
        structure_break_engine: StructureBreakEngine | None = None,
        liquidity_sweep_engine: LiquiditySweepEngine | None = None,
        structure_setup_engine: StructureSetupEngine | None = None,
        historical_context_engine: HistoricalContextEngine | None = None,
        historical_confluence_engine: (
            HistoricalConfluenceEngine | None
        ) = None,
        freshness_checker: LiveDataFreshness | None = None,
        candle_store: CandleStore | None = None,
        market_service: MarketService | None = None,
        min_candles_for_structure: int = 20,
        order_book_depth: int = 20,
    ) -> None:

        if min_candles_for_structure <= 0:
            raise ValueError(
                "min_candles_for_structure "
                "must be greater than zero."
            )

        if order_book_depth <= 0:
            raise ValueError(
                "order_book_depth "
                "must be greater than zero."
            )

        self.market_structure = (
            market_structure_engine
            if market_structure_engine is not None
            else MarketStructureEngine()
        )

        self.structure_break = (
            structure_break_engine
            if structure_break_engine is not None
            else StructureBreakEngine()
        )

        self.liquidity_sweep = (
            liquidity_sweep_engine
            if liquidity_sweep_engine is not None
            else LiquiditySweepEngine()
        )

        self.structure_setup = (
            structure_setup_engine
            if structure_setup_engine is not None
            else StructureSetupEngine()
        )

        self.historical_context = (
            historical_context_engine
            if historical_context_engine is not None
            else HistoricalContextEngine()
        )

        self.historical_confluence = (
            historical_confluence_engine
            if historical_confluence_engine is not None
            else HistoricalConfluenceEngine(
                confluence_engine=ConfluenceEngine()
            )
        )

        self.freshness = (
            freshness_checker
            if freshness_checker is not None
            else LiveDataFreshness(
                max_candle_lag_seconds=300
            )
        )

        self.candle_store = (
            candle_store
            if candle_store is not None
            else CandleStore()
        )

        self.market_service = (
            market_service
            if market_service is not None
            else MarketService()
        )

        self.min_candles_for_structure = int(
            min_candles_for_structure
        )

        self.order_book_depth = int(
            order_book_depth
        )

    # ============================================================
    # CANDLES
    # ============================================================

    def get_live_candles(
        self,
        symbol: str,
        fallback_candles=None,
        timeframe: str = "60",
        limit: int = 200,
    ) -> list[Candle]:

        normalized_symbol = (
            symbol.strip().upper()
        )

        stored = (
            self.candle_store.get_recent(
                symbol=normalized_symbol,
                timeframe=timeframe,
                limit=limit,
            )
        )

        bootstrap = list(
            fallback_candles or []
        )

        if not stored:
            return bootstrap

        if not bootstrap:
            return stored

        merged: dict[
            int,
            Candle,
        ] = {
            int(candle.timestamp): candle
            for candle in bootstrap
        }

        for candle in stored:
            merged[
                int(candle.timestamp)
            ] = candle

        ordered = sorted(
            merged.values(),
            key=lambda candle: int(
                candle.timestamp
            ),
        )

        return ordered[-limit:]

    def latest_live_candle(
        self,
        symbol: str,
        timeframe: str = "60",
    ) -> Candle | None:

        return self.candle_store.latest(
            symbol=symbol,
            timeframe=timeframe,
        )

    # ============================================================
    # ORDER BOOK
    # ============================================================

    @staticmethod
    def _normalize_orderbook_symbol(
        symbol: str,
    ) -> str:

        normalized = (
            str(symbol)
            .strip()
            .upper()
        )

        if normalized.endswith(
            "USDT"
        ):
            return normalized

        return f"{normalized}USDT"

    def _get_live_order_book_context(
        self,
        symbol: str,
    ):

        market_symbol = (
            self._normalize_orderbook_symbol(
                symbol
            )
        )

        order_book = (
            self.market_service.orderbook(
                symbol=market_symbol,
                depth=self.order_book_depth,
            )
        )

        if order_book is None:
            return None

        imbalance = (
            order_book.imbalance(
                levels=self.order_book_depth
            )
        )

        bid_volume = (
            order_book.bid_volume(
                levels=self.order_book_depth
            )
        )

        ask_volume = (
            order_book.ask_volume(
                levels=self.order_book_depth
            )
        )

        if imbalance >= 0.15:
            wall_bias = "BULLISH"

        elif imbalance <= -0.15:
            wall_bias = "BEARISH"

        else:
            wall_bias = "NEUTRAL"

        best_bid = (
            order_book.best_bid()
        )

        best_ask = (
            order_book.best_ask()
        )

        spread_pct = 0.0

        if (
            best_bid is not None
            and best_ask is not None
            and float(best_bid.price) > 0
        ):

            spread_pct = (
                (
                    float(best_ask.price)
                    - float(best_bid.price)
                )
                / float(best_bid.price)
                * 100.0
            )

        return SimpleNamespace(
            symbol=market_symbol,

            imbalance=float(
                imbalance
            ),

            bid_volume=float(
                bid_volume
            ),

            ask_volume=float(
                ask_volume
            ),

            best_bid=(
                float(
                    best_bid.price
                )
                if best_bid is not None
                else None
            ),

            best_ask=(
                float(
                    best_ask.price
                )
                if best_ask is not None
                else None
            ),

            spread_pct=float(
                spread_pct
            ),

            wall_bias=wall_bias,

            timestamp=int(
                order_book.timestamp
            ),
        )

    def _get_live_order_book_safe(
        self,
        symbol: str,
    ):

        try:

            return (
                self._get_live_order_book_context(
                    symbol=symbol
                )
            )

        except Exception:

            return None

    # ============================================================
    # BENCHMARK ORDER BOOK CONFIRMATION
    # ============================================================

    def evaluate_order_book_confirmation(
        self,
        symbol: str,
        setup: StructureSetup,
        context,
        order_book=None,
    ) -> LiveConfluenceResult:
        """
        Apply current Order Book to an already reconstructed
        historical setup/context.

        This bypasses candle freshness intentionally.

        It is designed for feature-impact benchmarking.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        if setup is None:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE_SETUP",
                reason=(
                    "Setup is required for Order Book "
                    "confirmation."
                ),
            )

        if context is None:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=setup,
                confluence=None,
                status="NO_HISTORICAL_DATA",
                reason=(
                    "Historical context is required for "
                    "Order Book confirmation."
                ),
            )

        if order_book is None:

            order_book = (
                self._get_live_order_book_safe(
                    symbol=normalized_symbol
                )
            )

        if order_book is None:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=setup,
                confluence=None,
                status="ORDER_BOOK_UNAVAILABLE",
                reason=(
                    "Current Order Book was unavailable."
                ),
            )

        try:

            confluence = (
                self.historical_confluence.evaluate(
                    setup=setup,
                    context=context,
                    order_book=order_book,
                    live_mode=True,
                )
            )

        except Exception as exc:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=setup,
                confluence=None,
                status="CONFLUENCE_ERROR",
                reason=str(exc),
            )

        return LiveConfluenceResult(
            symbol=normalized_symbol,
            setup=setup,
            confluence=confluence,
            status="ORDER_BOOK_CONFIRMED",
            reason=(
                "Historical setup/context enriched with "
                "current live Order Book execution gate."
            ),
        )

    # ============================================================
    # PREPARE ANALYSIS
    # ============================================================

    def _prepare_analysis(
        self,
        symbol: str,
        candles=None,
        latest_trade_timestamp: int | None = None,
        timeframe: str = "60",
        candle_limit: int = 200,
        data_mode: str = LiveDataFreshness.LIVE,
    ) -> tuple[
        list[Candle],
        Candle | None,
        LiveConfluenceResult | None,
    ]:

        normalized_symbol = (
            symbol.strip().upper()
        )

        live_candle = (
            self.latest_live_candle(
                symbol=normalized_symbol,
                timeframe=timeframe,
            )
        )

        analysis_candles = (
            self.get_live_candles(
                symbol=normalized_symbol,
                fallback_candles=candles,
                timeframe=timeframe,
                limit=candle_limit,
            )
        )

        if not analysis_candles:

            return (
                [],
                None,
                LiveConfluenceResult(
                    symbol=normalized_symbol,
                    setup=None,
                    confluence=None,
                    status="NO_CANDLES",
                    reason=(
                        "No candles were available."
                    ),
                ),
            )

        if (
            data_mode
            == LiveDataFreshness.LIVE
            and live_candle is not None
        ):

            latest_candle = (
                live_candle
            )

        else:

            latest_candle = (
                live_candle
                if (
                    live_candle is not None
                    and data_mode
                    == LiveDataFreshness.LIVE
                )
                else analysis_candles[-1]
            )

        if (
            latest_trade_timestamp is None
            and data_mode
            == LiveDataFreshness.LIVE
        ):

            try:

                latest_trade_timestamp = (
                    self.historical_context
                    .trade_store
                    .latest_timestamp(
                        normalized_symbol
                    )
                )

            except Exception:

                latest_trade_timestamp = None

        try:

            freshness = (
                self.freshness.check(
                    latest_candle_timestamp=int(
                        latest_candle.timestamp
                    ),
                    latest_trade_timestamp=(
                        latest_trade_timestamp
                    ),
                    mode=data_mode,
                )
            )

        except Exception as exc:

            return (
                analysis_candles,
                latest_candle,
                LiveConfluenceResult(
                    symbol=normalized_symbol,
                    setup=None,
                    confluence=None,
                    status="FRESHNESS_CHECK_ERROR",
                    reason=str(exc),
                ),
            )

        if not freshness.fresh:

            return (
                analysis_candles,
                latest_candle,
                LiveConfluenceResult(
                    symbol=normalized_symbol,
                    setup=None,
                    confluence=None,
                    status="STALE_CANDLES",
                    reason=(
                        "Latest candle is stale: "
                        f"{freshness.candle_lag_seconds}s "
                        f"> "
                        f"{freshness.max_allowed_lag_seconds}s."
                    ),
                ),
            )

        if (
            len(analysis_candles)
            < self.min_candles_for_structure
        ):

            return (
                analysis_candles,
                latest_candle,
                LiveConfluenceResult(
                    symbol=normalized_symbol,
                    setup=None,
                    confluence=None,
                    status="INSUFFICIENT_CANDLES",
                    reason=(
                        f"Only {len(analysis_candles)} candles "
                        f"available; "
                        f"{self.min_candles_for_structure} "
                        f"required."
                    ),
                ),
            )

        return (
            analysis_candles,
            latest_candle,
            None,
        )

    # ============================================================
    # CANDIDATE
    # ============================================================

    def find_candidate(
        self,
        symbol: str,
        candles=None,
        timeframe: str = "60",
        candle_limit: int = 200,
        swing_window: int = 2,
        displacement_pct: float = 0.15,
        max_bars_after_sweep: int = 10,
        data_mode: str = LiveDataFreshness.LIVE,
    ) -> LiveConfluenceResult:

        normalized_symbol = (
            symbol.strip().upper()
        )

        (
            analysis_candles,
            _latest_candle,
            early_result,
        ) = self._prepare_analysis(
            symbol=normalized_symbol,
            candles=candles,
            latest_trade_timestamp=None,
            timeframe=timeframe,
            candle_limit=candle_limit,
            data_mode=data_mode,
        )

        if early_result is not None:
            return early_result

        structure = (
            self.market_structure.calculate(
                candles=analysis_candles,
                swing_window=swing_window,
            )
        )

        if not structure.swings:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE",
                reason=(
                    "No confirmed market structure swings."
                ),
            )

        structure_breaks = (
            self.structure_break.calculate(
                candles=analysis_candles,
                structure=structure,
                displacement_pct=displacement_pct,
            )
        )

        if not structure_breaks.events:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE_BREAK",
                reason=(
                    "No structure-break events were detected."
                ),
            )

        sweeps = (
            self.liquidity_sweep.calculate(
                candles=analysis_candles,
                structure=structure,
            )
        )

        if not sweeps.events:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_LIQUIDITY_SWEEP",
                reason=(
                    "No confirmed liquidity sweep was detected."
                ),
            )

        setups = (
            self.structure_setup.calculate(
                sweeps=sweeps.events,
                structure_breaks=(
                    structure_breaks.events
                ),
                max_bars_after_sweep=(
                    max_bars_after_sweep
                ),
            )
        )

        if not setups.setups:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE_SETUP",
                reason=(
                    "No valid Sweep + MSS "
                    "structure setup was detected."
                ),
            )

        latest_setup = max(
            setups.setups,
            key=lambda item: (
                int(item.timestamp),
                int(item.index),
            ),
        )

        return LiveConfluenceResult(
            symbol=normalized_symbol,
            setup=latest_setup,
            confluence=None,
            status="CANDIDATE",
            reason=(
                "Valid Sweep + MSS structure "
                "candidate detected."
            ),
        )

    # ============================================================
    # PRODUCTION EVALUATION
    # ============================================================

    def evaluate(
        self,
        symbol: str,
        candles=None,
        latest_trade_timestamp: int | None = None,
        timeframe: str = "60",
        candle_limit: int = 200,
        swing_window: int = 2,
        displacement_pct: float = 0.15,
        max_bars_after_sweep: int = 10,
        lookback_seconds: int = 3600,
        data_mode: str = LiveDataFreshness.LIVE,
    ) -> LiveConfluenceResult:

        candidate = (
            self.find_candidate(
                symbol=symbol,
                candles=candles,
                timeframe=timeframe,
                candle_limit=candle_limit,
                swing_window=swing_window,
                displacement_pct=(
                    displacement_pct
                ),
                max_bars_after_sweep=(
                    max_bars_after_sweep
                ),
                data_mode=data_mode,
            )
        )

        if candidate.status != "CANDIDATE":
            return candidate

        normalized_symbol = (
            symbol.strip().upper()
        )

        latest_setup = (
            candidate.setup
        )

        if latest_setup is None:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE_SETUP",
                reason=(
                    "Candidate result did not contain "
                    "a setup."
                ),
            )

        try:

            context = (
                self.historical_context.calculate(
                    symbol=normalized_symbol,
                    timestamp=int(
                        latest_setup.timestamp
                    ),
                    lookback_seconds=(
                        lookback_seconds
                    ),
                )
            )

        except ValueError as exc:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=latest_setup,
                confluence=None,
                status="NO_HISTORICAL_DATA",
                reason=str(exc),
            )

        except Exception as exc:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=latest_setup,
                confluence=None,
                status="HISTORICAL_CONTEXT_ERROR",
                reason=str(exc),
            )

        live_order_book = None

        if (
            data_mode
            == LiveDataFreshness.LIVE
        ):

            live_order_book = (
                self._get_live_order_book_safe(
                    symbol=normalized_symbol
                )
            )

        try:

            confluence = (
                self.historical_confluence.evaluate(
                    setup=latest_setup,
                    context=context,
                    order_book=live_order_book,
                    live_mode=(
                        data_mode
                        == LiveDataFreshness.LIVE
                    ),
                )
            )

        except Exception as exc:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=latest_setup,
                confluence=None,
                status="CONFLUENCE_ERROR",
                reason=str(exc),
            )

        if (
            data_mode
            == LiveDataFreshness.LIVE
        ):

            if live_order_book is not None:

                reason = (
                    "Live confluence evaluated with "
                    "current Order Book execution gate."
                )

            else:

                reason = (
                    "Live confluence evaluated, but "
                    "current Order Book was unavailable."
                )

        else:

            reason = (
                "Historical/REST bootstrap confluence "
                "evaluated without current Order Book."
            )

        return LiveConfluenceResult(
            symbol=normalized_symbol,
            setup=latest_setup,
            confluence=confluence,
            status="EVALUATED",
            reason=reason,
        )
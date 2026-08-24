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

    Pipeline:

        Candles
          ↓
        Freshness
          ↓
        Market Structure
          ↓
        Structure Break / MSS
          ↓
        Liquidity Sweep
          ↓
        Structure Setup
          ↓
        Historical Context
          ↓
        Current Live Order Book
          ↓
        Historical Confluence
          ↓
        Final Live Signal

    Candidate-first support:

        find_candidate()

    Important architecture rule:

        Historical Context:
            - CVD
            - VWAP
            - Volume Profile
            - Order Flow
            - Session

        Live-only:
            - Current Order Book Imbalance

    This prevents current Level-2 data from leaking into
    historical calculations.
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
        if (
            min_candles_for_structure
            <= 0
        ):
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
        """
        Return the best available candle set.

        Live CandleStore is preferred.
        Bootstrap candles are merged with live candles.
        """

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

    def _get_live_order_book_context(
        self,
        symbol: str,
    ):
        """
        Fetch the current live Order Book and convert it into
        the duck-typed context expected by ConfluenceEngine.

        Historical evaluation MUST NOT call this method.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        order_book = (
            self.market_service.orderbook(
                symbol=normalized_symbol,
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

        # A simple directional wall/depth bias derived from
        # the same Level-2 snapshot.
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
                float(best_bid.price)
                if best_bid is not None
                else None
            ),
            best_ask=(
                float(best_ask.price)
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
        """
        Safe live Order Book wrapper.

        A temporary L2/API failure must not destroy the
        entire Structure/CVD/Profile/VWAP signal.
        """

        try:
            return (
                self._get_live_order_book_context(
                    symbol=symbol
                )
            )

        except Exception:
            return None

    # ============================================================
    # PREPARATION
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
        """
        Prepare candles and apply freshness policy.

        LIVE:
            freshness is enforced.

        REST_BOOTSTRAP:
            historical candle age does not invalidate the data.
        """

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
                    status=(
                        "FRESHNESS_CHECK_ERROR"
                    ),
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
        """
        Run only through Structure Setup.

        Historical Context and Order Book are intentionally not
        calculated here.
        """

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
    # COMPLETE EVALUATION
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
        """
        Run the complete live/historical confluence pipeline.

        LIVE:
            Historical context + CURRENT Order Book.

        REST_BOOTSTRAP:
            Historical context only.
            Current Order Book is intentionally excluded.
        """

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

        # --------------------------------------------------------
        # Historical context
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # CURRENT live Order Book
        #
        # Never call this for REST_BOOTSTRAP/historical mode.
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # HistoricalConfluenceEngine
        # --------------------------------------------------------

        try:
            confluence = (
                self.historical_confluence.evaluate(
                    setup=latest_setup,
                    context=context,
                    order_book=live_order_book,
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

        # --------------------------------------------------------
        # Final reason
        # --------------------------------------------------------

        if (
            data_mode
            == LiveDataFreshness.LIVE
        ):
            if live_order_book is not None:
                reason = (
                    "Live historical confluence evaluated "
                    "with current Order Book confirmation."
                )
            else:
                reason = (
                    "Live historical confluence evaluated; "
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
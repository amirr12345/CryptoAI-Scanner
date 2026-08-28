from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
from microstructure.session_engine import (
    SessionEngine,
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


@dataclass(slots=True, frozen=True)
class CurrentSessionContext:
    """
    Current live session information.

    This is intentionally separate from HistoricalContext.

    HistoricalContext describes the market at the timestamp of
    the structure setup.

    CurrentSessionContext describes the market session at the
    actual live execution time.
    """

    timestamp: int

    session_name: str

    session_quality: float

    session_classification: str

    execution_allowed: bool

    is_overlap: bool

    trade_count: int

    order_flow_strength: float

    cvd_strength: float

    liquidity_ratio: float


class LiveConfluenceService:
    """
    Live structure/confluence pipeline.

    Historical pipeline:

        Candles
          ↓
        Structure / MSS
          ↓
        Liquidity Sweep
          ↓
        Structure Setup
          ↓
        Historical Trades
          ↓
        Historical Context
          ↓
        Historical Confluence

    Live pipeline:

        Historical Structure Setup
          ↓
        Historical Context
          ↓
        Current Session
          ↓
        Current Order Book
          ↓
        Execution Gate

    IMPORTANT:

        Historical Context remains strictly as-of the setup
        timestamp.

        Current Session is evaluated separately and never
        modifies HistoricalContext.

        Current Order Book is never used in historical
        calculations.
    """

    ORDER_BOOK_DEPTH = 20

    # ============================================================
    # SESSION
    # ============================================================

    SESSION_CURRENT_LOOKBACK_SECONDS = 300

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

        self.session_engine = (
            SessionEngine()
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
            symbol
            .strip()
            .upper()
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
    # CURRENT SESSION
    # ============================================================

    def _latest_current_trade_stats(
        self,
        symbol: str,
    ) -> tuple[
        int,
        float,
        float,
        float,
    ]:
        """
        Return recent trade statistics for the live session.

        Returns:

            trade_count
            order_flow_strength
            cvd_strength
            liquidity_ratio

        The method intentionally uses only the most recent
        available trades.

        If the configured TradeStore/API does not expose the
        required data, safe zero values are returned.
        """

        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        trade_store = (
            self.historical_context.trade_store
        )

        trades = []

        # --------------------------------------------------------
        # Try recent stored trades first.
        # --------------------------------------------------------

        recent_method = getattr(
            trade_store,
            "get_recent",
            None,
        )

        if callable(
            recent_method
        ):

            try:

                trades = list(
                    recent_method(
                        symbol=normalized_symbol,
                        limit=500,
                    )
                    or []
                )

            except TypeError:

                try:

                    trades = list(
                        recent_method(
                            normalized_symbol,
                            500,
                        )
                        or []
                    )

                except Exception:

                    trades = []

            except Exception:

                trades = []

        # --------------------------------------------------------
        # Fallback: get all stored trades and take the latest
        # subset where supported.
        # --------------------------------------------------------

        if not trades:

            all_method = getattr(
                trade_store,
                "get_trades",
                None,
            )

            if callable(
                all_method
            ):

                try:

                    trades = list(
                        all_method(
                            symbol=normalized_symbol,
                        )
                        or []
                    )

                except TypeError:

                    try:

                        trades = list(
                            all_method(
                                normalized_symbol,
                            )
                            or []
                        )

                    except Exception:

                        trades = []

                except Exception:

                    trades = []

        if not trades:

            return (
                0,
                0.0,
                0.0,
                0.0,
            )

        trades = sorted(
            trades,
            key=lambda trade: int(
                getattr(
                    trade,
                    "timestamp",
                    0,
                )
            ),
        )

        # Keep only the latest 500 trades.
        trades = trades[-500:]

        buy_volume = 0.0
        sell_volume = 0.0

        for trade in trades:

            try:

                volume = max(
                    0.0,
                    float(
                        trade.volume
                    ),
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            side = str(
                getattr(
                    trade,
                    "side",
                    "",
                )
            ).strip().lower()

            if side == "buy":

                buy_volume += volume

            elif side == "sell":

                sell_volume += volume

        total_volume = (
            buy_volume
            + sell_volume
        )

        if total_volume <= 0:

            return (
                len(trades),
                0.0,
                0.0,
                0.0,
            )

        delta = (
            buy_volume
            - sell_volume
        )

        delta_pct = (
            delta
            / total_volume
            * 100.0
        )

        order_flow_strength = min(
            100.0,
            abs(delta_pct),
        )

        # Current session liquidity-quality proxy.
        balance = (
            1.0
            - abs(
                buy_volume
                - sell_volume
            )
            / total_volume
        )

        liquidity_activity = min(
            1.0,
            total_volume
            / 1_000_000.0,
        )

        liquidity_ratio = max(
            0.0,
            min(
                1.0,
                balance * 0.7
                + liquidity_activity * 0.3,
            ),
        )

        # CVD strength is not reconstructed here from a second
        # engine. For current session gating we use recent
        # executed-flow strength as a conservative proxy.
        cvd_strength = min(
            100.0,
            abs(delta_pct),
        )

        return (
            len(trades),
            order_flow_strength,
            cvd_strength,
            liquidity_ratio,
        )

    def current_session_context(
        self,
        symbol: str,
        timestamp: int | None = None,
    ) -> CurrentSessionContext:
        """
        Build current live session context.

        This is separate from the historical setup/session.

        timestamp:
            Unix timestamp in seconds.
            Defaults to current UTC time.
        """

        if timestamp is None:

            timestamp = int(
                datetime.now(
                    timezone.utc
                ).timestamp()
            )

        trade_count = 0
        order_flow_strength = 0.0
        cvd_strength = 0.0
        liquidity_ratio = 0.0

        try:

            (
                trade_count,
                order_flow_strength,
                cvd_strength,
                liquidity_ratio,
            ) = (
                self._latest_current_trade_stats(
                    symbol
                )
            )

        except Exception:

            pass

        analysis = (
            self.session_engine.analyze(
                timestamp=int(
                    timestamp
                ),
                trade_count=(
                    trade_count
                ),
                order_flow_strength=(
                    order_flow_strength
                ),
                cvd_strength=(
                    cvd_strength
                ),
                liquidity_ratio=(
                    liquidity_ratio
                ),
            )
        )

        return CurrentSessionContext(
            timestamp=int(
                timestamp
            ),

            session_name=(
                analysis.name
            ),

            session_quality=(
                analysis.quality
            ),

            session_classification=(
                analysis.classification
            ),

            execution_allowed=(
                analysis.execution_allowed
            ),

            is_overlap=(
                analysis.is_overlap
            ),

            trade_count=(
                analysis.trade_count
            ),

            order_flow_strength=(
                order_flow_strength
            ),

            cvd_strength=(
                cvd_strength
            ),

            liquidity_ratio=(
                liquidity_ratio
            ),
        )

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

        Designed for feature-impact benchmarking.
        """

        normalized_symbol = (
            symbol
            .strip()
            .upper()
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
            symbol
            .strip()
            .upper()
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
            symbol
            .strip()
            .upper()
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
        current_timestamp: int | None = None,
    ) -> LiveConfluenceResult:
        """
        Run the complete live/historical confluence pipeline.

        HistoricalContext is always evaluated using the setup
        timestamp.

        Live Session is evaluated separately using the actual
        current execution timestamp.
        """

        candidate = self.find_candidate(
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

        if candidate.status != "CANDIDATE":
            return candidate

        normalized_symbol = (
            symbol
            .strip()
            .upper()
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

        # ========================================================
        # HISTORICAL CONTEXT
        # ========================================================

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

        # ========================================================
        # CURRENT SESSION
        # ========================================================

        current_session = None

        if (
            data_mode
            == LiveDataFreshness.LIVE
        ):

            try:

                current_session = (
                    self.current_session_context(
                        symbol=normalized_symbol,
                        timestamp=current_timestamp,
                    )
                )

            except Exception:

                current_session = None

        # ========================================================
        # CURRENT ORDER BOOK
        # ========================================================

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

        # ========================================================
        # CONFLUENCE SESSION OVERRIDE
        # ========================================================

        session_for_confluence = (
            current_session
            if current_session is not None
            else context
        )

        try:

            confluence = (
                self.historical_confluence.evaluate(
                    setup=latest_setup,
                    context=context,
                    order_book=live_order_book,
                    session=session_for_confluence,
                    live_mode=(
                        data_mode
                        == LiveDataFreshness.LIVE
                    ),
                )
            )

        except TypeError:

            # Backward compatibility with versions whose
            # HistoricalConfluenceEngine does not yet expose
            # session= explicitly.

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

        except Exception as exc:

            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=latest_setup,
                confluence=None,
                status="CONFLUENCE_ERROR",
                reason=str(exc),
            )

        # ========================================================
        # REASON
        # ========================================================

        if (
            data_mode
            == LiveDataFreshness.LIVE
        ):

            if (
                current_session is not None
                and live_order_book is not None
            ):

                reason = (
                    "Live confluence evaluated using "
                    "current Session + current Order Book."
                )

            elif current_session is not None:

                reason = (
                    "Live confluence evaluated using "
                    "current Session; Order Book unavailable."
                )

            elif live_order_book is not None:

                reason = (
                    "Live confluence evaluated using "
                    "historical Session fallback + current "
                    "Order Book."
                )

            else:

                reason = (
                    "Live confluence evaluated without "
                    "current Session/Order Book context."
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
from __future__ import annotations

from dataclasses import dataclass

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
from models.confluence_result import (
    ConfluenceResult,
)
from models.candle import Candle
from models.structure_setup import (
    StructureSetup,
)
from services.live_data_freshness import (
    LiveDataFreshness,
)


@dataclass(slots=True, frozen=True)
class LiveConfluenceResult:
    """
    Result of the complete live structure/confluence pipeline.
    """

    symbol: str
    setup: StructureSetup | None
    confluence: ConfluenceResult | None
    status: str
    reason: str


class LiveConfluenceService:
    """
    Live structure/confluence pipeline.

    Candle source priority:

        1. Live CandleStore
        2. Explicit candles argument

    Live CandleStore is the preferred source because it is fed
    by the Nobitex WebSocket candle stream.

    Historical REST candles remain useful as bootstrap data.
    """

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
        min_candles_for_structure: int = 20,
    ) -> None:
        if min_candles_for_structure <= 0:
            raise ValueError(
                "min_candles_for_structure must be greater than zero."
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

        self.min_candles_for_structure = (
            int(min_candles_for_structure)
        )

    def get_live_candles(
        self,
        symbol: str,
        fallback_candles=None,
        timeframe: str = "60",
        limit: int = 200,
    ) -> list[Candle]:
        """
        Return the best available candle set.

        The WebSocket CandleStore is preferred when it has enough
        candles. Otherwise the explicitly supplied bootstrap/history
        candles are used.

        When a live candle exists, it replaces the same timestamp
        in the bootstrap series or is appended when newer.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        stored = self.candle_store.get_recent(
            symbol=normalized_symbol,
            timeframe=timeframe,
            limit=limit,
        )

        bootstrap = list(
            fallback_candles or []
        )

        if not stored:
            return bootstrap

        if not bootstrap:
            return stored

        merged: dict[int, Candle] = {
            int(candle.timestamp): candle
            for candle in bootstrap
        }

        for candle in stored:
            merged[int(candle.timestamp)] = candle

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
        """
        Return the latest WebSocket candle from CandleStore.
        """

        return self.candle_store.latest(
            symbol=symbol,
            timeframe=timeframe,
        )

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
    ) -> LiveConfluenceResult:
        """
        Run the complete live analysis pipeline.

        Live WebSocket candles are preferred.

        Bootstrap candles may be supplied through `candles`.
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
            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_CANDLES",
                reason="No candles were available.",
            )

        # --------------------------------------------------
        # Freshness reference
        # --------------------------------------------------

        latest_candle = (
            live_candle
            if live_candle is not None
            else analysis_candles[-1]
        )

        if latest_trade_timestamp is None:
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
            freshness = self.freshness.check(
                latest_candle_timestamp=int(
                    latest_candle.timestamp
                ),
                latest_trade_timestamp=(
                    latest_trade_timestamp
                ),
            )
        except Exception as exc:
            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="FRESHNESS_CHECK_ERROR",
                reason=str(exc),
            )

        if not freshness.fresh:
            return LiveConfluenceResult(
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
            )

        # --------------------------------------------------
        # Structure needs enough candles
        # --------------------------------------------------

        if (
            len(analysis_candles)
            < self.min_candles_for_structure
        ):
            return LiveConfluenceResult(
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
            )

        # --------------------------------------------------
        # Market Structure
        # --------------------------------------------------

        structure = self.market_structure.calculate(
            candles=analysis_candles,
            swing_window=swing_window,
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

        # --------------------------------------------------
        # Structure Break
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Liquidity Sweep
        # --------------------------------------------------

        sweeps = self.liquidity_sweep.calculate(
            candles=analysis_candles,
            structure=structure,
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

        # --------------------------------------------------
        # Structure Setup
        # --------------------------------------------------

        setups = self.structure_setup.calculate(
            sweeps=sweeps.events,
            structure_breaks=(
                structure_breaks.events
            ),
            max_bars_after_sweep=(
                max_bars_after_sweep
            ),
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

        # --------------------------------------------------
        # Historical Context
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Historical Confluence
        # --------------------------------------------------

        try:
            confluence = (
                self.historical_confluence.evaluate(
                    setup=latest_setup,
                    context=context,
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

        return LiveConfluenceResult(
            symbol=normalized_symbol,
            setup=latest_setup,
            confluence=confluence,
            status="EVALUATED",
            reason=(
                "Live historical confluence "
                "evaluated successfully."
            ),
        )
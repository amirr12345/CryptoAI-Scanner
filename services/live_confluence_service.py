from __future__ import annotations

from dataclasses import dataclass

from microstructure.confluence_engine import ConfluenceEngine
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
from models.confluence_result import ConfluenceResult
from models.structure_setup import StructureSetup


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
    Orchestrate the existing microstructure engines.

    Pipeline:

        MarketStructure
            ↓
        StructureBreak
            ↓
        LiquiditySweep
            ↓
        StructureSetup
            ↓
        HistoricalContext
            ↓
        HistoricalConfluence
    """

    def __init__(
        self,
        market_structure_engine: MarketStructureEngine | None = None,
        structure_break_engine: StructureBreakEngine | None = None,
        liquidity_sweep_engine: LiquiditySweepEngine | None = None,
        structure_setup_engine: StructureSetupEngine | None = None,
        historical_context_engine: HistoricalContextEngine | None = None,
        historical_confluence_engine: HistoricalConfluenceEngine | None = None,
    ) -> None:
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

    def evaluate(
        self,
        symbol: str,
        candles,
        swing_window: int = 2,
        displacement_pct: float = 0.15,
        max_bars_after_sweep: int = 10,
        lookback_seconds: int = 3600,
    ) -> LiveConfluenceResult:
        """
        Run complete live analysis for one symbol.

        The latest valid StructureSetup is selected.

        Historical Context is evaluated using that setup's
        own timestamp.

        No current/future trade context is injected manually.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        if not candles:
            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_CANDLES",
                reason="No candles were supplied.",
            )

        # --------------------------------------------------
        # 1. Market Structure
        # --------------------------------------------------

        structure = self.market_structure.calculate(
            candles=candles,
            swing_window=swing_window,
        )

        if not structure.swings:
            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE",
                reason="No confirmed market structure swings.",
            )

        # --------------------------------------------------
        # 2. Structure Break
        # --------------------------------------------------

        structure_breaks = (
            self.structure_break.calculate(
                candles=candles,
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
                reason="No structure-break events were detected.",
            )

        # --------------------------------------------------
        # 3. Liquidity Sweep
        # --------------------------------------------------

        sweeps = self.liquidity_sweep.calculate(
            candles=candles,
            structure=structure,
        )

        if not sweeps.events:
            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_LIQUIDITY_SWEEP",
                reason="No confirmed liquidity sweep was detected.",
            )

        # --------------------------------------------------
        # 4. Structure Setup
        # --------------------------------------------------

        setups = self.structure_setup.calculate(
            sweeps=sweeps.events,
            structure_breaks=structure_breaks.events,
            max_bars_after_sweep=max_bars_after_sweep,
        )

        if not setups.setups:
            return LiveConfluenceResult(
                symbol=normalized_symbol,
                setup=None,
                confluence=None,
                status="NO_STRUCTURE_SETUP",
                reason=(
                    "No valid Sweep + MSS structure setup was detected."
                ),
            )

        latest_setup = max(
            setups.setups,
            key=lambda item: (
                item.timestamp,
                item.index,
            ),
        )

        # --------------------------------------------------
        # 5. Historical Context
        # --------------------------------------------------

        try:
            context = self.historical_context.calculate(
                symbol=normalized_symbol,
                timestamp=int(latest_setup.timestamp),
                lookback_seconds=lookback_seconds,
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
        # 6. Historical Confluence
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
            reason="Live historical confluence evaluated successfully.",
        )
from __future__ import annotations

from types import SimpleNamespace

from microstructure.confluence_engine import (
    ConfluenceEngine,
)
from models.confluence_result import ConfluenceResult
from models.historical_context import HistoricalContext
from models.structure_setup import StructureSetup


class HistoricalConfluenceEngine:
    """
    Integrate Structure Setup with Historical Context.

    Flow:

        StructureSetup.timestamp
                ↓
        HistoricalContext.timestamp
                ↓
        CVD + VWAP + Volume Profile
                ↓
        ConfluenceEngine

    The integration refuses to evaluate when the timestamps
    do not match, preventing accidental use of a different
    historical context.
    """

    def __init__(
        self,
        confluence_engine: ConfluenceEngine | None = None,
    ) -> None:
        self.confluence = (
            confluence_engine
            if confluence_engine is not None
            else ConfluenceEngine()
        )

    def evaluate(
        self,
        setup: StructureSetup,
        context: HistoricalContext,
    ) -> ConfluenceResult:
        """
        Evaluate one StructureSetup using its historical context.
        """

        if int(setup.timestamp) != int(
            context.timestamp
        ):
            raise ValueError(
                "Structure setup timestamp and "
                "historical context timestamp must match."
            )

        if not context.historical:
            raise ValueError(
                "Historical context is not marked historical."
            )

        cvd = SimpleNamespace(
            direction=context.cvd_direction,
            strength=context.cvd_strength,
        )

        profile = SimpleNamespace(
            position=context.profile_position,
        )

        vwap = SimpleNamespace(
            direction=self._vwap_direction(
                context
            )
        )

        return self.confluence.evaluate(
            setup=setup,
            cvd=cvd,
            profile=profile,
            vwap=vwap,
        )

    @staticmethod
    def _vwap_direction(
        context: HistoricalContext,
    ) -> str:
        """
        Derive VWAP directional bias from historical VWAP slope.

        Positive slope  -> BULLISH
        Negative slope  -> BEARISH
        Flat/unknown     -> NEUTRAL

        Price position relative to VWAP is intentionally not
        treated as trend direction. The existing ConfluenceEngine
        expects a directional context here.
        """

        slope = float(
            context.vwap_slope
        )

        if slope > 0:
            return "BULLISH"

        if slope < 0:
            return "BEARISH"

        return "NEUTRAL"
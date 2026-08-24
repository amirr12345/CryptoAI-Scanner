from __future__ import annotations

from types import SimpleNamespace

from microstructure.confluence_engine import (
    ConfluenceEngine,
)
from models.confluence_result import (
    ConfluenceResult,
)
from models.historical_context import (
    HistoricalContext,
)
from models.structure_setup import (
    StructureSetup,
)


class HistoricalConfluenceEngine:
    """
    Integrate Structure Setup with Historical Context.

    Historical data:

        CVD
        Delta
        VWAP
        Volume Profile
        Order Flow
        Session Quality

    Optional live enrichment:

        Current Order Book

    IMPORTANT:

        The historical context remains strictly as-of the setup
        timestamp.

        Current Order Book is accepted only as an optional live
        confirmation and must never be stored inside the historical
        context itself.
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
        order_book=None,
    ) -> ConfluenceResult:
        """
        Evaluate one StructureSetup.

        `order_book` is optional and is intended only for live
        confirmation.

        Historical callers should leave it as None.
        """

        # --------------------------------------------------------
        # Timestamp protection
        # --------------------------------------------------------

        if int(
            setup.timestamp
        ) != int(
            context.timestamp
        ):
            raise ValueError(
                "Structure setup timestamp and "
                "historical context timestamp must match."
            )

        # --------------------------------------------------------
        # Historical marker
        # --------------------------------------------------------

        if not context.historical:
            raise ValueError(
                "Historical context is not marked historical."
            )

        # --------------------------------------------------------
        # CVD / Delta
        # --------------------------------------------------------

        cvd = SimpleNamespace(
            direction=(
                context.cvd_direction
            ),
            strength=(
                context.cvd_strength
            ),
            cvd_direction=(
                context.cvd_direction
            ),
            cvd_strength=(
                context.cvd_strength
            ),
            cvd_divergence=(
                context.cvd_divergence
            ),
            cvd_delta=(
                context.cvd_delta
            ),
            cvd_change=(
                context.cvd_change
            ),
            delta=(
                context.delta
            ),
            delta_pct=(
                context.delta_pct
            ),
        )

        # --------------------------------------------------------
        # Volume Profile
        # --------------------------------------------------------

        profile = SimpleNamespace(
            position=(
                context.profile_position
            ),
            profile_position=(
                context.profile_position
            ),
            poc=context.poc,
            vah=context.vah,
            val=context.val,
        )

        # --------------------------------------------------------
        # VWAP
        # --------------------------------------------------------

        vwap_direction = (
            self._vwap_direction(
                context
            )
        )

        vwap = SimpleNamespace(
            direction=vwap_direction,
            vwap_direction=vwap_direction,
            vwap_position=(
                context.vwap_position
            ),
            vwap_distance_pct=(
                context.vwap_distance_pct
            ),
            vwap_slope=(
                context.vwap_slope
            ),
            vwap=context.vwap,
            previous_vwap=(
                context.previous_vwap
            ),
        )

        # --------------------------------------------------------
        # Order Flow
        # --------------------------------------------------------

        order_flow = SimpleNamespace(
            buy_volume=(
                context.buy_volume
            ),
            sell_volume=(
                context.sell_volume
            ),
            delta=(
                context.delta
            ),
            delta_pct=(
                context.delta_pct
            ),
            buy_ratio=(
                context.buy_ratio
            ),
            sell_ratio=(
                context.sell_ratio
            ),
            trade_count=(
                context.trade_count
            ),
            average_trade_size=(
                context.average_trade_size
            ),
            large_trade_buy_volume=(
                context.large_trade_buy_volume
            ),
            large_trade_sell_volume=(
                context.large_trade_sell_volume
            ),
            large_trade_imbalance=(
                context.large_trade_imbalance
            ),
            order_flow_aggression=(
                context.order_flow_aggression
            ),
            order_flow_strength=(
                context.order_flow_strength
            ),
            aggression=(
                context.order_flow_aggression
            ),
            aggression_strength=(
                context.order_flow_strength
            ),
        )

        # --------------------------------------------------------
        # Session
        # --------------------------------------------------------

        session = SimpleNamespace(
            session_name=(
                context.session_name
            ),
            session_quality=(
                context.session_quality
            ),
            session_is_overlap=(
                context.session_is_overlap
            ),
            name=(
                context.session_name
            ),
            quality_score=(
                context.session_quality
            ),
            is_overlap=(
                context.session_is_overlap
            ),
        )

        # --------------------------------------------------------
        # Order Book
        #
        # Historical call:
        #     None
        #
        # Live call:
        #     current live order-book context
        # --------------------------------------------------------

        return self.confluence.evaluate(
            setup=setup,
            cvd=cvd,
            profile=profile,
            vwap=vwap,
            order_flow=order_flow,
            order_book=order_book,
            session=session,
            historical_context=context,
        )

    @staticmethod
    def _vwap_direction(
        context: HistoricalContext,
    ) -> str:
        """
        Derive VWAP directional bias from historical VWAP slope.

        Positive slope -> BULLISH
        Negative slope -> BEARISH
        Flat -> NEUTRAL
        """

        slope = float(
            context.vwap_slope
        )

        if slope > 0:
            return "BULLISH"

        if slope < 0:
            return "BEARISH"

        return "NEUTRAL"
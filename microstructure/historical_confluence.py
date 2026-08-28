from __future__ import annotations

from types import SimpleNamespace

from microstructure.confluence_engine import (
    ConfluenceEngine,
)
from microstructure.session_ranking import (
    SessionPerformance,
    SessionRankingEngine,
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

    Historical information:

        CVD
        Delta
        VWAP
        Volume Profile
        Order Flow
        Historical Session Quality

    Optional live enrichment:

        Current Order Book
        Current Session
        Session Performance Ranking

    Architecture:

        Primary Confluence Score
                +
        Live Execution Gates
                +
        Session Performance Ranking

    IMPORTANT:

        Session Ranking NEVER changes the primary score.

        Session Ranking may only preserve or tighten the live
        execution decision.

        It must NEVER upgrade:

            BLOCK -> EXECUTE

        or:

            WAIT -> EXECUTE
    """

    def __init__(
        self,
        confluence_engine: ConfluenceEngine | None = None,
        session_ranking_engine: (
            SessionRankingEngine | None
        ) = None,
    ) -> None:

        self.confluence = (
            confluence_engine
            if confluence_engine is not None
            else ConfluenceEngine()
        )

        self.session_ranking = (
            session_ranking_engine
            if session_ranking_engine is not None
            else SessionRankingEngine()
        )

    # ============================================================
    # MAIN EVALUATION
    # ============================================================

    def evaluate(
        self,
        setup: StructureSetup,
        context: HistoricalContext,
        order_book=None,
        live_mode: bool = False,
        session=None,
        session_performance: (
            SessionPerformance | None
        ) = None,
    ) -> ConfluenceResult:
        """
        Evaluate one StructureSetup using historical context.

        Parameters
        ----------
        setup:
            Structure setup.

        context:
            Historical context reconstructed strictly as-of the
            setup timestamp.

        order_book:
            Current live Order Book.

            Used only when live_mode=True.

        live_mode:
            False:
                Historical evaluation.

            True:
                Live execution evaluation.

        session:
            Current session context for the live execution layer.

            When omitted, the historical session is used as a
            fallback.

        session_performance:
            Optional observed performance ranking for the current
            session.

            Applied only in live mode.
        """

        # --------------------------------------------------------
        # Timestamp safety
        # --------------------------------------------------------

        if (
            int(setup.timestamp)
            != int(context.timestamp)
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
        # CVD
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

            location=(
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
        # Historical Session
        # --------------------------------------------------------

        historical_session = (
            self._build_session(
                name=context.session_name,

                quality=context.session_quality,

                is_overlap=(
                    context.session_is_overlap
                ),
            )
        )

        # --------------------------------------------------------
        # Execution Session
        # --------------------------------------------------------

        execution_session = (
            session
            if session is not None
            else historical_session
        )

        # --------------------------------------------------------
        # Primary / Execution Engine
        # --------------------------------------------------------

        result = self.confluence.evaluate(
            setup=setup,

            cvd=cvd,

            profile=profile,

            vwap=vwap,

            order_flow=order_flow,

            order_book=(
                order_book
                if live_mode
                else None
            ),

            session=execution_session,

            historical_context=context,

            live_mode=live_mode,
        )

        # --------------------------------------------------------
        # Session Ranking
        # --------------------------------------------------------

        if (
            live_mode
            and session_performance is not None
        ):

            result = (
                self._apply_session_ranking(
                    result=result,

                    session_performance=(
                        session_performance
                    ),
                )
            )

        return result

    # ============================================================
    # SESSION RANKING
    # ============================================================

    def _apply_session_ranking(
        self,
        result: ConfluenceResult,
        session_performance: SessionPerformance,
    ) -> ConfluenceResult:
        """
        Apply SessionRankingEngine to the live execution result.

        CRITICAL GATE RULE:

            Session Ranking may ONLY preserve or tighten
            the existing execution decision.

        It may NEVER loosen an already existing gate.

        Therefore:

            BLOCK -> BLOCK
            WAIT  -> WAIT
            EXECUTE + ranking EXECUTE -> EXECUTE
            EXECUTE + ranking WAIT -> WAIT
            EXECUTE + ranking BLOCK -> BLOCK

        Primary score is never changed.
        """

        primary_conflict = bool(
            result.conflicts
        )

        decision = (
            self.session_ranking.decide(
                performance=(
                    session_performance
                ),

                primary_grade=(
                    result.grade
                ),

                primary_conflict=(
                    primary_conflict
                ),
            )
        )

        reasons = list(
            result.reasons
        )

        confirmations = list(
            result.confirmations
        )

        # --------------------------------------------------------
        # Ranking diagnostic
        # --------------------------------------------------------

        reasons.append(
            "Session Ranking: "
            f"rank={decision.rank}, "
            f"confidence={decision.confidence}, "
            f"observed_score="
            f"{decision.observed_score:.2f}, "
            f"decision={decision.decision}."
        )

        existing_gate = str(
            result.execution_status
            if result.execution_status is not None
            else "WAIT"
        ).strip().upper()

        # ========================================================
        # HARD SAFETY RULE
        #
        # Existing BLOCK can never become anything else.
        # ========================================================

        if existing_gate == "BLOCK":

            reasons.append(
                "Session Ranking cannot override the existing "
                "BLOCK execution gate."
            )

            return self._replace_result(
                result=result,

                execution_status="BLOCK",

                actionable=False,

                confirmations=tuple(
                    confirmations
                ),

                reasons=tuple(
                    reasons
                ),
            )

        # ========================================================
        # EXISTING WAIT
        #
        # Ranking may not upgrade WAIT to EXECUTE.
        # ========================================================

        if existing_gate == "WAIT":

            if decision.decision == "BLOCK":

                reasons.append(
                    "Session Ranking tightened existing WAIT "
                    "to BLOCK."
                )

                return self._replace_result(
                    result=result,

                    execution_status="BLOCK",

                    actionable=False,

                    confirmations=tuple(
                        confirmations
                    ),

                    reasons=tuple(
                        reasons
                    ),
                )

            reasons.append(
                "Session Ranking cannot upgrade existing "
                "WAIT to EXECUTE."
            )

            return self._replace_result(
                result=result,

                execution_status="WAIT",

                actionable=False,

                confirmations=tuple(
                    confirmations
                ),

                reasons=tuple(
                    reasons
                ),
            )

        # ========================================================
        # EXISTING EXECUTE
        # ========================================================

        if existing_gate == "EXECUTE":

            # ----------------------------------------------------
            # Ranking allows execution
            # ----------------------------------------------------

            if decision.decision == "EXECUTE":

                confirmations.append(
                    "Session performance ranking "
                    "permits execution"
                )

                reasons.append(
                    "Session Ranking preserved the existing "
                    "EXECUTE gate."
                )

                return self._replace_result(
                    result=result,

                    execution_status="EXECUTE",

                    actionable=(
                        result.actionable
                        and not primary_conflict
                    ),

                    confirmations=tuple(
                        confirmations
                    ),

                    reasons=tuple(
                        reasons
                    ),
                )

            # ----------------------------------------------------
            # Ranking blocks execution
            # ----------------------------------------------------

            if decision.decision == "BLOCK":

                reasons.append(
                    "Session performance ranking "
                    "tightened EXECUTE to BLOCK."
                )

                return self._replace_result(
                    result=result,

                    execution_status="BLOCK",

                    actionable=False,

                    confirmations=tuple(
                        confirmations
                    ),

                    reasons=tuple(
                        reasons
                    ),
                )

            # ----------------------------------------------------
            # Ranking requires waiting
            # ----------------------------------------------------

            reasons.append(
                "Session performance ranking "
                "tightened EXECUTE to WAIT."
            )

            return self._replace_result(
                result=result,

                execution_status="WAIT",

                actionable=False,

                confirmations=tuple(
                    confirmations
                ),

                reasons=tuple(
                    reasons
                ),
            )

        # ========================================================
        # UNKNOWN EXISTING STATE
        # ========================================================

        reasons.append(
            "Unknown existing execution state; "
            "falling back to WAIT for safety."
        )

        return self._replace_result(
            result=result,

            execution_status="WAIT",

            actionable=False,

            confirmations=tuple(
                confirmations
            ),

            reasons=tuple(
                reasons
            ),
        )

    # ============================================================
    # RESULT REPLACEMENT
    # ============================================================

    @staticmethod
    def _replace_result(
        result: ConfluenceResult,
        execution_status: str,
        actionable: bool,
        confirmations: tuple[str, ...],
        reasons: tuple[str, ...],
    ) -> ConfluenceResult:
        """
        Rebuild ConfluenceResult while preserving every
        primary-score field.
        """

        return ConfluenceResult(
            direction=result.direction,

            score=result.score,

            grade=result.grade,

            structure_points=(
                result.structure_points
            ),

            cvd_points=(
                result.cvd_points
            ),

            profile_points=(
                result.profile_points
            ),

            vwap_points=(
                result.vwap_points
            ),

            confirmations=(
                confirmations
            ),

            conflicts=(
                result.conflicts
            ),

            reasons=(
                reasons
            ),

            actionable=(
                actionable
            ),

            liquidity_points=(
                result.liquidity_points
            ),

            order_flow_points=(
                result.order_flow_points
            ),

            order_book_points=(
                result.order_book_points
            ),

            session_quality=(
                result.session_quality
            ),

            session_name=(
                result.session_name
            ),

            execution_status=(
                execution_status
            ),

            order_book_imbalance=(
                result.order_book_imbalance
            ),
        )

    # ============================================================
    # SESSION BUILDER
    # ============================================================

    @staticmethod
    def _build_session(
        name: str,
        quality: float,
        is_overlap: bool,
    ) -> SimpleNamespace:
        """
        Create a provider-agnostic session context.
        """

        normalized_name = str(
            name
            if name is not None
            else "UNKNOWN"
        ).strip().upper()

        try:

            normalized_quality = float(
                quality
            )

        except (
            TypeError,
            ValueError,
        ):

            normalized_quality = 0.0

        normalized_quality = max(
            0.0,
            min(
                10.0,
                normalized_quality,
            ),
        )

        return SimpleNamespace(
            session_name=(
                normalized_name
            ),

            name=(
                normalized_name
            ),

            session_quality=(
                normalized_quality
            ),

            quality_score=(
                normalized_quality
            ),

            session_is_overlap=(
                bool(is_overlap)
            ),

            is_overlap=(
                bool(is_overlap)
            ),
        )

    # ============================================================
    # VWAP DIRECTION
    # ============================================================

    @staticmethod
    def _vwap_direction(
        context: HistoricalContext,
    ) -> str:
        """
        Derive VWAP direction from historical VWAP slope.

        Positive slope:
            BULLISH

        Negative slope:
            BEARISH

        Flat:
            NEUTRAL
        """

        try:

            slope = float(
                context.vwap_slope
            )

        except (
            TypeError,
            ValueError,
        ):

            slope = 0.0

        if slope > 0:
            return "BULLISH"

        if slope < 0:
            return "BEARISH"

        return "NEUTRAL"
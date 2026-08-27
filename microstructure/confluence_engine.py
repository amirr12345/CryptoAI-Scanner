from __future__ import annotations

from typing import Any

from models.confluence_result import (
    ConfluenceResult,
)


class ConfluenceEngine:
    """
    Primary market confluence engine.

    PRIMARY SCORE = 100

        Structure / MSS        25
        Liquidity Sweep        15
        Volume Profile         15
        CVD / Delta             15
        VWAP                    10
        Order Flow              10
        --------------------------
                              90 -> normalized to 100

    Order Book:
        NOT part of the primary score.

    Session:
        NOT part of the primary score.

    Order Book + Session:
        Execution Gate.

    Historical evaluation:
        Order Book is optional/not applicable.

    Live evaluation:
        Order Book confirmation is required for EXECUTE.

    RSI / MACD / EMA:
        intentionally excluded.
    """

    STRUCTURE_WEIGHT = 25.0
    LIQUIDITY_WEIGHT = 15.0
    CVD_WEIGHT = 15.0
    PROFILE_WEIGHT = 15.0
    VWAP_WEIGHT = 10.0
    ORDER_FLOW_WEIGHT = 10.0

    PRIMARY_MAX_SCORE = (
        STRUCTURE_WEIGHT
        + LIQUIDITY_WEIGHT
        + CVD_WEIGHT
        + PROFILE_WEIGHT
        + VWAP_WEIGHT
        + ORDER_FLOW_WEIGHT
    )

    MAX_SCORE = 100.0

    # ------------------------------------------------------------
    # Order Book
    # ------------------------------------------------------------

    OB_NEUTRAL_THRESHOLD = 0.10
    OB_MODERATE_OPPOSING = 0.20
    OB_STRONG_OPPOSING = 0.35

    # ------------------------------------------------------------
    # Session
    # ------------------------------------------------------------

    SESSION_EXECUTE_MIN = 8.0
    SESSION_WAIT_MIN = 5.0

    def evaluate(
        self,
        setup: Any,
        cvd: Any | None = None,
        profile: Any | None = None,
        vwap: Any | None = None,
        order_flow: Any | None = None,
        order_book: Any | None = None,
        session: Any | None = None,
        historical_context: Any | None = None,
        live_mode: bool = False,
    ) -> ConfluenceResult:
        """
        Evaluate one directional setup.

        live_mode=False:
            Historical evaluation.
            Order Book is optional/not applicable.

        live_mode=True:
            Production live evaluation.
            Current Order Book acts as an execution gate.
        """

        direction = self._normalize_direction(
            getattr(
                setup,
                "direction",
                "NEUTRAL",
            )
        )

        if direction not in {
            "BULLISH",
            "BEARISH",
        }:
            return self._build_result(
                direction="NEUTRAL",
                score=0.0,
                structure_points=0.0,
                liquidity_points=0.0,
                cvd_points=0.0,
                profile_points=0.0,
                vwap_points=0.0,
                order_flow_points=0.0,
                order_book_points=0.0,
                session_quality=0.0,
                session_name="UNKNOWN",
                order_book_imbalance=0.0,
                execution_status="BLOCK",
                confirmations=(),
                conflicts=(
                    "Invalid or neutral structure setup",
                ),
                reasons=(
                    "Structure setup is not directional.",
                ),
                actionable=False,
                grade="REJECT",
            )

        confirmations: list[str] = []
        conflicts: list[str] = []
        reasons: list[str] = []

        # --------------------------------------------------------
        # HistoricalContext fallback
        # --------------------------------------------------------

        if historical_context is not None:

            if cvd is None:
                cvd = historical_context

            if profile is None:
                profile = historical_context

            if vwap is None:
                vwap = historical_context

            if order_flow is None:
                order_flow = historical_context

            if session is None:
                session = historical_context

        cvd_available = (
            cvd is not None
        )

        profile_available = (
            profile is not None
        )

        vwap_available = (
            vwap is not None
        )

        order_flow_available = (
            self._order_flow_is_available(
                order_flow
            )
        )

        # --------------------------------------------------------
        # PRIMARY SCORE
        # --------------------------------------------------------

        structure_points = (
            self._score_structure(
                setup=setup,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        liquidity_points = (
            self._score_liquidity(
                setup=setup,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        cvd_points = (
            self._score_cvd(
                direction=direction,
                cvd=cvd,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        profile_points = (
            self._score_profile(
                direction=direction,
                profile=profile,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        vwap_points = (
            self._score_vwap(
                direction=direction,
                vwap=vwap,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        order_flow_points = (
            self._score_order_flow(
                direction=direction,
                order_flow=(
                    order_flow
                    if order_flow_available
                    else None
                ),
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        raw_primary_score = (
            structure_points
            + liquidity_points
            + cvd_points
            + profile_points
            + vwap_points
            + order_flow_points
        )

        available_max_score = (
            structure_points
            + self.LIQUIDITY_WEIGHT
        )

        if cvd_available:
            available_max_score += (
                self.CVD_WEIGHT
            )

        if profile_available:
            available_max_score += (
                self.PROFILE_WEIGHT
            )

        if vwap_available:
            available_max_score += (
                self.VWAP_WEIGHT
            )

        if order_flow_available:
            available_max_score += (
                self.ORDER_FLOW_WEIGHT
            )

        has_real_context = (
            cvd_available
            or profile_available
            or vwap_available
            or order_flow_available
        )

        if (
            not has_real_context
            or available_max_score <= 0
        ):
            score = 0.0

            reasons.append(
                "No independent market-context confirmation "
                "was available."
            )

        else:

            score = (
                raw_primary_score
                / available_max_score
                * self.MAX_SCORE
            )

        score = max(
            0.0,
            min(
                self.MAX_SCORE,
                score,
            ),
        )

        # --------------------------------------------------------
        # SESSION
        # --------------------------------------------------------

        session_quality, session_name = (
            self._extract_session(
                session=session
            )
        )

        self._append_session_reason(
            session_name=session_name,
            session_quality=session_quality,
            confirmations=confirmations,
            reasons=reasons,
        )

        # --------------------------------------------------------
        # ORDER BOOK
        #
        # Diagnostic only for score.
        # Execution gate decides its live effect.
        # --------------------------------------------------------

        order_book_imbalance = 0.0

        if order_book is not None:

            order_book_imbalance = (
                self._safe_float(
                    getattr(
                        order_book,
                        "imbalance",
                        0.0,
                    )
                )
            )

        order_book_points = (
            self._diagnostic_order_book_score(
                direction=direction,
                order_book=order_book,
            )
        )

        # --------------------------------------------------------
        # GRADE
        # --------------------------------------------------------

        grade = self._grade(
            score=score,
            conflicts=len(conflicts),
        )

        # --------------------------------------------------------
        # EXECUTION GATE
        # --------------------------------------------------------

        execution_status = (
            self._execution_gate(
                direction=direction,
                grade=grade,
                session_quality=session_quality,
                order_book=order_book,
                order_book_imbalance=(
                    order_book_imbalance
                ),
                conflicts=conflicts,
                confirmations=confirmations,
                reasons=reasons,
                live_mode=live_mode,
            )
        )

        # --------------------------------------------------------
        # ACTIONABLE
        # --------------------------------------------------------

        if live_mode:

            actionable = (
                execution_status
                == "EXECUTE"
                and grade in {
                    "A+",
                    "A",
                }
                and not conflicts
                and has_real_context
            )

        else:

            # Historical evaluation:
            # Order Book is not required.
            actionable = (
                grade in {
                    "A+",
                    "A",
                }
                and not conflicts
                and (
                    session_quality <= 0.0
                    or session_quality
                    >= self.SESSION_WAIT_MIN
                )
                and has_real_context
            )

        return self._build_result(
            direction=direction,
            score=score,
            structure_points=structure_points,
            liquidity_points=liquidity_points,
            cvd_points=cvd_points,
            profile_points=profile_points,
            vwap_points=vwap_points,
            order_flow_points=order_flow_points,
            order_book_points=order_book_points,
            session_quality=session_quality,
            session_name=session_name,
            order_book_imbalance=(
                order_book_imbalance
            ),
            execution_status=execution_status,
            confirmations=tuple(
                confirmations
            ),
            conflicts=tuple(
                conflicts
            ),
            reasons=tuple(
                reasons
            ),
            actionable=actionable,
            grade=grade,
        )

    # ============================================================
    # STRUCTURE
    # ============================================================

    def _score_structure(
        self,
        setup: Any,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        direction = self._normalize_direction(
            getattr(
                setup,
                "direction",
                "NEUTRAL",
            )
        )

        if direction not in {
            "BULLISH",
            "BEARISH",
        }:

            conflicts.append(
                "Invalid structure direction"
            )

            reasons.append(
                "Structure setup direction is invalid."
            )

            return 0.0

        confirmations.append(
            "Structure / MSS confirmed"
        )

        reasons.append(
            "Directional Sweep + MSS structure setup confirmed."
        )

        return self.STRUCTURE_WEIGHT

    # ============================================================
    # LIQUIDITY
    # ============================================================

    def _score_liquidity(
        self,
        setup: Any,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        confirmations.append(
            "Liquidity Sweep confirmed"
        )

        reasons.append(
            "Validated liquidity sweep is part of the "
            "structure setup."
        )

        return self.LIQUIDITY_WEIGHT

    # ============================================================
    # CVD
    # ============================================================

    def _score_cvd(
        self,
        direction: str,
        cvd: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        if cvd is None:

            reasons.append(
                "CVD context unavailable."
            )

            return 0.0

        cvd_direction = self._normalize_direction(
            getattr(
                cvd,
                "cvd_direction",
                getattr(
                    cvd,
                    "direction",
                    "NEUTRAL",
                ),
            )
        )

        strength = self._safe_float(
            getattr(
                cvd,
                "cvd_strength",
                getattr(
                    cvd,
                    "strength",
                    0.0,
                ),
            )
        )

        delta = self._safe_float(
            getattr(
                cvd,
                "cvd_delta",
                getattr(
                    cvd,
                    "delta",
                    0.0,
                ),
            )
        )

        divergence = str(
            getattr(
                cvd,
                "cvd_divergence",
                getattr(
                    cvd,
                    "divergence",
                    "NONE",
                ),
            )
        ).strip().upper()

        if (
            cvd_direction == direction
            and strength >= 60.0
        ):

            confirmations.append(
                "CVD strong directional alignment"
            )

            reasons.append(
                f"CVD {cvd_direction}, "
                f"strength={strength:.2f}, "
                f"delta={delta:.4f}."
            )

            if divergence not in {
                "",
                "NONE",
                "NEUTRAL",
                "UNKNOWN",
            }:

                reasons.append(
                    f"CVD divergence={divergence}."
                )

            return self.CVD_WEIGHT

        if cvd_direction == direction:

            confirmations.append(
                "CVD directional alignment"
            )

            reasons.append(
                f"CVD direction aligns with {direction}."
            )

            return 8.0

        if cvd_direction == "NEUTRAL":

            reasons.append(
                "CVD is neutral."
            )

            return 7.0

        conflicts.append(
            "CVD opposing structure setup"
        )

        reasons.append(
            f"CVD {cvd_direction} conflicts with "
            f"{direction} setup."
        )

        return 0.0

    # ============================================================
    # VOLUME PROFILE
    # ============================================================

    def _score_profile(
        self,
        direction: str,
        profile: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        if profile is None:

            reasons.append(
                "Volume Profile context unavailable."
            )

            return 0.0

        location = str(
            getattr(
                profile,
                "profile_position",
                getattr(
                    profile,
                    "position",
                    getattr(
                        profile,
                        "location",
                        "UNKNOWN",
                    ),
                ),
            )
        ).strip().upper()

        if direction == "BULLISH":

            supportive = {
                "BELOW_VALUE_AREA",
                "BELOW_VALUE",
                "BELOW_VA",
            }

            opposing = {
                "ABOVE_VALUE_AREA",
                "ABOVE_VALUE",
                "ABOVE_VA",
            }

        else:

            supportive = {
                "ABOVE_VALUE_AREA",
                "ABOVE_VALUE",
                "ABOVE_VA",
            }

            opposing = {
                "BELOW_VALUE_AREA",
                "BELOW_VALUE",
                "BELOW_VA",
            }

        if location in supportive:

            confirmations.append(
                "Volume Profile location supportive"
            )

            reasons.append(
                f"Volume Profile location {location} "
                f"supports {direction}."
            )

            return self.PROFILE_WEIGHT

        if location in opposing:

            conflicts.append(
                "Volume Profile location opposing setup"
            )

            reasons.append(
                f"Volume Profile location {location} "
                f"opposes {direction}."
            )

            return 0.0

        if location in {
            "INSIDE_VALUE_AREA",
            "INSIDE_VALUE",
            "INSIDE_VA",
        }:

            confirmations.append(
                "Price inside Volume Profile value area"
            )

            reasons.append(
                "Price is inside the Volume Profile value area."
            )

            return 8.0

        reasons.append(
            "Volume Profile location neutral/unknown."
        )

        return 8.0

    # ============================================================
    # VWAP
    # ============================================================

    def _score_vwap(
        self,
        direction: str,
        vwap: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        if vwap is None:

            reasons.append(
                "VWAP context unavailable."
            )

            return 0.0

        vwap_direction = self._normalize_direction(
            getattr(
                vwap,
                "vwap_direction",
                getattr(
                    vwap,
                    "direction",
                    "NEUTRAL",
                ),
            )
        )

        vwap_position = str(
            getattr(
                vwap,
                "vwap_position",
                "UNKNOWN",
            )
        ).strip().upper()

        vwap_slope = self._safe_float(
            getattr(
                vwap,
                "vwap_slope",
                0.0,
            )
        )

        if vwap_direction == direction:

            confirmations.append(
                "VWAP directional alignment"
            )

            reasons.append(
                f"VWAP {vwap_direction} supports {direction}."
            )

            return self.VWAP_WEIGHT

        if (
            direction == "BULLISH"
            and vwap_position == "ABOVE_VWAP"
            and vwap_slope > 0
        ):

            confirmations.append(
                "Price above rising VWAP"
            )

            reasons.append(
                "Price is above a rising VWAP."
            )

            return self.VWAP_WEIGHT

        if (
            direction == "BEARISH"
            and vwap_position == "BELOW_VWAP"
            and vwap_slope < 0
        ):

            confirmations.append(
                "Price below falling VWAP"
            )

            reasons.append(
                "Price is below a falling VWAP."
            )

            return self.VWAP_WEIGHT

        if vwap_direction == "NEUTRAL":

            reasons.append(
                "VWAP is neutral."
            )

            return 7.0

        conflicts.append(
            "VWAP opposing structure setup"
        )

        reasons.append(
            f"VWAP {vwap_direction} opposes "
            f"{direction} setup."
        )

        return 0.0

    # ============================================================
    # ORDER FLOW
    # ============================================================

    def _score_order_flow(
        self,
        direction: str,
        order_flow: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        if order_flow is None:

            reasons.append(
                "Order Flow context unavailable."
            )

            return 0.0

        aggression = str(
            getattr(
                order_flow,
                "order_flow_aggression",
                getattr(
                    order_flow,
                    "aggression",
                    "NEUTRAL",
                ),
            )
        ).strip().upper()

        strength = self._safe_float(
            getattr(
                order_flow,
                "order_flow_strength",
                getattr(
                    order_flow,
                    "aggression_strength",
                    0.0,
                ),
            )
        )

        delta_pct = self._safe_float(
            getattr(
                order_flow,
                "delta_pct",
                0.0,
            )
        )

        aligned = (
            (
                direction == "BULLISH"
                and aggression == "BULLISH"
            )
            or
            (
                direction == "BEARISH"
                and aggression == "BEARISH"
            )
        )

        if aligned and strength >= 60.0:

            confirmations.append(
                "Order Flow strong directional alignment"
            )

            reasons.append(
                f"Order Flow {aggression}, "
                f"strength={strength:.2f}, "
                f"delta_pct={delta_pct:.2f}%."
            )

            return self.ORDER_FLOW_WEIGHT

        if aligned:

            confirmations.append(
                "Order Flow directional alignment"
            )

            reasons.append(
                f"Order Flow {aggression} aligns with "
                f"{direction}."
            )

            return 6.0

        if aggression == "NEUTRAL":

            reasons.append(
                "Order Flow is neutral."
            )

            return 5.0

        conflicts.append(
            "Order Flow opposing structure setup"
        )

        reasons.append(
            f"Order Flow {aggression} opposes "
            f"{direction} setup."
        )

        return 0.0

    # ============================================================
    # ORDER BOOK DIAGNOSTIC
    # ============================================================

    def _diagnostic_order_book_score(
        self,
        direction: str,
        order_book: Any | None,
    ) -> float:

        if order_book is None:
            return 0.0

        imbalance = self._safe_float(
            getattr(
                order_book,
                "imbalance",
                0.0,
            )
        )

        absolute_imbalance = abs(
            imbalance
        )

        aligned = (
            (
                direction == "BULLISH"
                and imbalance > 0
            )
            or
            (
                direction == "BEARISH"
                and imbalance < 0
            )
        )

        if (
            absolute_imbalance
            < self.OB_NEUTRAL_THRESHOLD
        ):
            return 5.0

        if aligned:

            if (
                absolute_imbalance
                >= self.OB_STRONG_OPPOSING
            ):
                return 10.0

            if (
                absolute_imbalance
                >= self.OB_MODERATE_OPPOSING
            ):
                return 8.0

            return 6.0

        if (
            absolute_imbalance
            < self.OB_MODERATE_OPPOSING
        ):
            return 4.0

        if (
            absolute_imbalance
            < self.OB_STRONG_OPPOSING
        ):
            return 2.0

        return 0.0

    # ============================================================
    # EXECUTION GATE
    # ============================================================

    def _execution_gate(
        self,
        direction: str,
        grade: str,
        session_quality: float,
        order_book: Any | None,
        order_book_imbalance: float,
        conflicts: list[str],
        confirmations: list[str],
        reasons: list[str],
        live_mode: bool,
    ) -> str:

        # --------------------------------------------------------
        # Historical mode
        #
        # Order Book is not required.
        # --------------------------------------------------------

        if not live_mode:

            if conflicts:

                reasons.append(
                    "Historical evaluation contains primary "
                    "market conflict."
                )

                return "BLOCK"

            if grade not in {
                "A+",
                "A",
            }:

                return "WAIT"

            if (
                session_quality > 0
                and
                session_quality
                < self.SESSION_WAIT_MIN
            ):

                reasons.append(
                    "Historical setup is strong but session "
                    f"quality={session_quality:.2f}/10."
                )

                return "WAIT"

            return "HISTORICAL_OK"

        # --------------------------------------------------------
        # LIVE mode
        # --------------------------------------------------------

        if conflicts:

            reasons.append(
                "Execution gate = BLOCK because the primary "
                "confluence contains a hard conflict."
            )

            return "BLOCK"

        if grade not in {
            "A+",
            "A",
        }:

            reasons.append(
                f"Execution gate = WAIT because grade={grade}."
            )

            return "WAIT"

        if (
            session_quality > 0
            and
            session_quality
            < self.SESSION_WAIT_MIN
        ):

            reasons.append(
                "Execution gate = WAIT because session "
                f"quality={session_quality:.2f}/10."
            )

            return "WAIT"

        if order_book is None:

            reasons.append(
                "Execution gate = WAIT because current "
                "Order Book is unavailable."
            )

            return "WAIT"

        absolute_imbalance = abs(
            order_book_imbalance
        )

        aligned = (
            (
                direction == "BULLISH"
                and order_book_imbalance >= 0
            )
            or
            (
                direction == "BEARISH"
                and order_book_imbalance <= 0
            )
        )

        if aligned:

            confirmations.append(
                "Order Book supports execution direction"
            )

            reasons.append(
                "Execution gate = EXECUTE: "
                f"Order Book imbalance="
                f"{order_book_imbalance:.3f}."
            )

            return "EXECUTE"

        if (
            absolute_imbalance
            < self.OB_MODERATE_OPPOSING
        ):

            reasons.append(
                f"Execution gate = WAIT: mild opposing "
                f"Order Book imbalance="
                f"{order_book_imbalance:.3f}."
            )

            return "WAIT"

        if (
            absolute_imbalance
            < self.OB_STRONG_OPPOSING
        ):

            reasons.append(
                f"Execution gate = WAIT: material opposing "
                f"Order Book imbalance="
                f"{order_book_imbalance:.3f}."
            )

            return "WAIT"

        reasons.append(
            f"Execution gate = BLOCK: extreme opposing "
            f"Order Book imbalance="
            f"{order_book_imbalance:.3f}."
        )

        return "BLOCK"

    # ============================================================
    # ORDER FLOW AVAILABILITY
    # ============================================================

    @staticmethod
    def _order_flow_is_available(
        order_flow: Any | None,
    ) -> bool:

        if order_flow is None:
            return False

        buy_volume = (
            ConfluenceEngine._safe_float(
                getattr(
                    order_flow,
                    "buy_volume",
                    0.0,
                )
            )
        )

        sell_volume = (
            ConfluenceEngine._safe_float(
                getattr(
                    order_flow,
                    "sell_volume",
                    0.0,
                )
            )
        )

        delta = (
            ConfluenceEngine._safe_float(
                getattr(
                    order_flow,
                    "delta",
                    0.0,
                )
            )
        )

        delta_pct = (
            ConfluenceEngine._safe_float(
                getattr(
                    order_flow,
                    "delta_pct",
                    0.0,
                )
            )
        )

        trade_count = int(
            ConfluenceEngine._safe_float(
                getattr(
                    order_flow,
                    "trade_count",
                    0,
                )
            )
        )

        return (
            trade_count > 0
            or abs(buy_volume) > 0.0
            or abs(sell_volume) > 0.0
            or abs(delta) > 0.0
            or abs(delta_pct) > 0.0
        )

    # ============================================================
    # SESSION
    # ============================================================

    @staticmethod
    def _extract_session(
        session: Any | None,
    ) -> tuple[float, str]:

        if session is None:
            return (
                0.0,
                "UNKNOWN",
            )

        quality = 0.0

        for attribute in (
            "session_quality",
            "quality_score",
        ):

            value = getattr(
                session,
                attribute,
                None,
            )

            if value is not None:

                quality = max(
                    0.0,
                    min(
                        10.0,
                        ConfluenceEngine._safe_float(
                            value
                        ),
                    ),
                )

                break

        name = str(
            getattr(
                session,
                "session_name",
                getattr(
                    session,
                    "name",
                    "UNKNOWN",
                ),
            )
        ).strip().upper()

        return (
            quality,
            name or "UNKNOWN",
        )

    @staticmethod
    def _append_session_reason(
        session_name: str,
        session_quality: float,
        confirmations: list[str],
        reasons: list[str],
    ) -> None:

        if session_name == "UNKNOWN":
            return

        reasons.append(
            f"Session={session_name}, "
            f"quality={session_quality:.2f}/10."
        )

        if session_quality >= 8.0:

            confirmations.append(
                "High-quality trading session"
            )

        elif session_quality >= 5.0:

            confirmations.append(
                "Acceptable trading session"
            )

        else:

            reasons.append(
                "Session liquidity quality is weak."
            )

    # ============================================================
    # GRADE
    # ============================================================

    @staticmethod
    def _grade(
        score: float,
        conflicts: int,
    ) -> str:

        if conflicts > 0:
            return "CONFLICT"

        if score >= 85.0:
            return "A+"

        if score >= 70.0:
            return "A"

        if score >= 55.0:
            return "B"

        return "REJECT"

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _normalize_direction(
        value: Any,
    ) -> str:

        value = str(
            value
            if value is not None
            else "NEUTRAL"
        ).strip().upper()

        if value in {
            "BUY",
            "LONG",
            "BULL",
            "BULLISH",
        }:
            return "BULLISH"

        if value in {
            "SELL",
            "SHORT",
            "BEAR",
            "BEARISH",
        }:
            return "BEARISH"

        return "NEUTRAL"

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float:

        try:

            result = float(
                value
            )

            if result != result:
                return 0.0

            if result in {
                float("inf"),
                float("-inf"),
            }:
                return 0.0

            return result

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    @staticmethod
    def _build_result(
        direction: str,
        score: float,
        structure_points: float,
        liquidity_points: float,
        cvd_points: float,
        profile_points: float,
        vwap_points: float,
        order_flow_points: float,
        order_book_points: float,
        session_quality: float,
        session_name: str,
        order_book_imbalance: float,
        execution_status: str,
        confirmations: tuple[str, ...],
        conflicts: tuple[str, ...],
        reasons: tuple[str, ...],
        actionable: bool,
        grade: str,
    ) -> ConfluenceResult:

        return ConfluenceResult(
            direction=direction,

            score=round(
                score,
                2,
            ),

            grade=grade,

            structure_points=round(
                structure_points,
                2,
            ),

            cvd_points=round(
                cvd_points,
                2,
            ),

            profile_points=round(
                profile_points,
                2,
            ),

            vwap_points=round(
                vwap_points,
                2,
            ),

            confirmations=confirmations,
            conflicts=conflicts,
            reasons=reasons,
            actionable=actionable,

            liquidity_points=round(
                liquidity_points,
                2,
            ),

            order_flow_points=round(
                order_flow_points,
                2,
            ),

            order_book_points=round(
                order_book_points,
                2,
            ),

            session_quality=round(
                session_quality,
                2,
            ),

            session_name=session_name,

            execution_status=(
                execution_status
            ),

            order_book_imbalance=round(
                order_book_imbalance,
                4,
            ),
        )
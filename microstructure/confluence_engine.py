from __future__ import annotations

from typing import Any

from models.confluence_result import (
    ConfluenceResult,
)


class ConfluenceEngine:
    """
    Primary market confluence engine.

    Primary score = 100

        Structure / MSS        25
        Liquidity Sweep        15
        CVD / Delta            15
        Volume Profile         15
        VWAP                   10
        Order Flow             10
        Order Book             10

    Session quality is stored separately and does not change
    the primary 100-point market score.

    RSI / MACD / EMA are intentionally excluded.

    Historical safety:
        Current Order Book data must not be used in historical
        evaluation unless timestamped historical Level-2 data exists.

    Normalization:
        When a feature is genuinely unavailable, its weight is
        removed from the denominator and the available score is
        normalized to 100.

        This prevents missing Order Book data in Historical mode
        from artificially reducing the final score.

    IMPORTANT:
        Structure + Liquidity alone are NOT sufficient for a signal.
        At least one real market-context confirmation must exist.
    """

    STRUCTURE_WEIGHT = 25.0
    LIQUIDITY_WEIGHT = 15.0
    CVD_WEIGHT = 15.0
    PROFILE_WEIGHT = 15.0
    VWAP_WEIGHT = 10.0
    ORDER_FLOW_WEIGHT = 10.0
    ORDER_BOOK_WEIGHT = 10.0

    MAX_SCORE = 100.0

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
    ) -> ConfluenceResult:
        """
        Evaluate one structure setup.

        Context objects support duck typing so existing tests and
        historical/live context objects remain compatible.
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

        # --------------------------------------------------------
        # Determine whether each context is genuinely available.
        #
        # HistoricalContext contains default neutral/zero values
        # even when a unit test did not actually provide an
        # Order Flow context. We must not count that as a real
        # confirmation source.
        # --------------------------------------------------------

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

        order_book_available = (
            order_book is not None
        )

        # --------------------------------------------------------
        # 1. Structure / MSS
        # --------------------------------------------------------

        structure_points = (
            self._score_structure(
                setup=setup,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        # --------------------------------------------------------
        # 2. Liquidity Sweep
        # --------------------------------------------------------

        liquidity_points = (
            self._score_liquidity(
                setup=setup,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        # --------------------------------------------------------
        # 3. CVD / Delta
        # --------------------------------------------------------

        cvd_points = (
            self._score_cvd(
                direction=direction,
                cvd=cvd,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        # --------------------------------------------------------
        # 4. Volume Profile
        # --------------------------------------------------------

        profile_points = (
            self._score_profile(
                direction=direction,
                profile=profile,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        # --------------------------------------------------------
        # 5. VWAP
        # --------------------------------------------------------

        vwap_points = (
            self._score_vwap(
                direction=direction,
                vwap=vwap,
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        # --------------------------------------------------------
        # 6. Order Flow
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # 7. Order Book
        # --------------------------------------------------------

        order_book_points = (
            self._score_order_book(
                direction=direction,
                order_book=(
                    order_book
                    if order_book_available
                    else None
                ),
                confirmations=confirmations,
                conflicts=conflicts,
                reasons=reasons,
            )
        )

        # --------------------------------------------------------
        # Raw primary score
        # --------------------------------------------------------

        raw_score = (
            structure_points
            + liquidity_points
            + cvd_points
            + profile_points
            + vwap_points
            + order_flow_points
            + order_book_points
        )

        # --------------------------------------------------------
        # Genuine market-context confirmation
        #
        # Structure + Liquidity alone must not become A/A+.
        # --------------------------------------------------------

        has_real_context = (
            cvd_available
            or profile_available
            or vwap_available
            or order_flow_available
            or order_book_available
        )

        if not has_real_context:
            score = 0.0

            reasons.append(
                "No independent market-context confirmation "
                "was available."
            )

        else:

            # ----------------------------------------------------
            # Available weight
            #
            # Only genuinely available features participate in
            # the normalization denominator.
            # ----------------------------------------------------

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

            if order_book_available:
                available_max_score += (
                    self.ORDER_BOOK_WEIGHT
                )

            # ----------------------------------------------------
            # Normalize available score to 100.
            # ----------------------------------------------------

            if available_max_score > 0:
                score = (
                    raw_score
                    / available_max_score
                    * self.MAX_SCORE
                )
            else:
                score = 0.0

        score = max(
            0.0,
            min(
                self.MAX_SCORE,
                score,
            ),
        )

        # --------------------------------------------------------
        # Session Quality
        # --------------------------------------------------------

        session_quality, session_name = (
            self._extract_session(
                session=session,
            )
        )

        self._append_session_reason(
            session_name=session_name,
            session_quality=session_quality,
            confirmations=confirmations,
            reasons=reasons,
        )

        # --------------------------------------------------------
        # Grade
        # --------------------------------------------------------

        grade = self._grade(
            score=score,
            conflicts=len(conflicts),
        )

        has_hard_conflict = bool(
            conflicts
        )

        # Weak session is not a market conflict.
        # It only prevents automatic action.
        session_allows_execution = (
            session_quality <= 0.0
            or session_quality >= 5.0
        )

        actionable = (
            grade in {
                "A+",
                "A",
            }
            and not has_hard_conflict
            and session_allows_execution
            and has_real_context
        )

        if (
            grade in {
                "A+",
                "A",
            }
            and not session_allows_execution
        ):
            reasons.append(
                "Session quality is below the execution "
                f"threshold: {session_quality:.2f}/10."
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
    # CVD / DELTA
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

        if (
            direction == "BULLISH"
            and aggression == "BULLISH"
        ) or (
            direction == "BEARISH"
            and aggression == "BEARISH"
        ):

            if strength >= 60.0:
                confirmations.append(
                    "Order Flow strong directional alignment"
                )

                reasons.append(
                    f"Order Flow {aggression}, "
                    f"strength={strength:.2f}, "
                    f"delta_pct={delta_pct:.2f}%."
                )

                return self.ORDER_FLOW_WEIGHT

            confirmations.append(
                "Order Flow directional alignment"
            )

            reasons.append(
                f"Order Flow {aggression} aligns with {direction}."
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
    # ORDER BOOK
    # ============================================================

    def _score_order_book(
        self,
        direction: str,
        order_book: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:

        if order_book is None:
            reasons.append(
                "Order Book unavailable; "
                "live L2 score not applied."
            )

            return 0.0

        imbalance = self._safe_float(
            getattr(
                order_book,
                "imbalance",
                0.0,
            )
        )

        wall_bias = str(
            getattr(
                order_book,
                "wall_bias",
                "NEUTRAL",
            )
        ).strip().upper()

        if direction == "BULLISH":

            aligned = (
                imbalance >= 0.15
                or wall_bias == "BULLISH"
            )

            opposing = (
                imbalance <= -0.15
                or wall_bias == "BEARISH"
            )

        else:

            aligned = (
                imbalance <= -0.15
                or wall_bias == "BEARISH"
            )

            opposing = (
                imbalance >= 0.15
                or wall_bias == "BULLISH"
            )

        if aligned and abs(imbalance) >= 0.30:
            confirmations.append(
                "Order Book strong imbalance alignment"
            )

            reasons.append(
                f"Order Book imbalance={imbalance:.3f} "
                f"supports {direction}."
            )

            return self.ORDER_BOOK_WEIGHT

        if aligned:
            confirmations.append(
                "Order Book imbalance alignment"
            )

            reasons.append(
                f"Order Book imbalance={imbalance:.3f} "
                f"aligns with {direction}."
            )

            return 6.0

        if opposing:
            conflicts.append(
                "Order Book imbalance opposing setup"
            )

            reasons.append(
                f"Order Book imbalance={imbalance:.3f} "
                f"opposes {direction}."
            )

            return 0.0

        reasons.append(
            "Order Book imbalance is neutral."
        )

        return 5.0

    # ============================================================
    # AVAILABILITY
    # ============================================================

    @staticmethod
    def _order_flow_is_available(
        order_flow: Any | None,
    ) -> bool:
        """
        Detect whether Order Flow is genuinely populated.

        HistoricalContext always has default values, so simply
        checking `order_flow is not None` is not sufficient.
        """

        if order_flow is None:
            return False

        buy_volume = ConfluenceEngine._safe_float(
            getattr(
                order_flow,
                "buy_volume",
                0.0,
            )
        )

        sell_volume = ConfluenceEngine._safe_float(
            getattr(
                order_flow,
                "sell_volume",
                0.0,
            )
        )

        delta = ConfluenceEngine._safe_float(
            getattr(
                order_flow,
                "delta",
                0.0,
            )
        )

        delta_pct = ConfluenceEngine._safe_float(
            getattr(
                order_flow,
                "delta_pct",
                0.0,
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

        # Real historical Order Flow must have actual trade
        # evidence. This avoids counting default zero/neutral
        # dataclass fields as an available feature.
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
            result = float(value)

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
        )
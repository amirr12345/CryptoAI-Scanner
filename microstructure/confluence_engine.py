from __future__ import annotations

from typing import Any

from models.confluence_result import ConfluenceResult


class ConfluenceEngine:
    """
    Rank a structure setup using:

        1. Structure Setup
        2. CVD / Order Flow
        3. Volume Profile
        4. VWAP

    Technical indicators are intentionally excluded.

    Maximum score:
        100

    Weighting:
        Structure Setup : 40
        CVD              : 25
        Volume Profile  : 20
        VWAP             : 15

    Important rule:
        A hard conflict makes a setup non-actionable even when
        the raw score is high enough for grade A or A+.
    """

    STRUCTURE_WEIGHT = 40.0
    CVD_WEIGHT = 25.0
    PROFILE_WEIGHT = 20.0
    VWAP_WEIGHT = 15.0

    def evaluate(
        self,
        setup: Any,
        cvd: Any | None = None,
        profile: Any | None = None,
        vwap: Any | None = None,
    ) -> ConfluenceResult:
        """
        Evaluate one structure setup.

        Expected setup:
            direction = BULLISH / BEARISH

        The engine intentionally uses duck typing so it remains
        decoupled from concrete context implementations.
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
                cvd_points=0.0,
                profile_points=0.0,
                vwap_points=0.0,
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

        # --------------------------------------------------
        # 1. Structure Setup
        # --------------------------------------------------

        structure_points = self.STRUCTURE_WEIGHT

        confirmations.append(
            "Structure Setup confirmed"
        )

        reasons.append(
            "Liquidity Sweep + MSS structure setup confirmed."
        )

        # --------------------------------------------------
        # 2. CVD
        # --------------------------------------------------

        cvd_points = self._score_cvd(
            direction=direction,
            cvd=cvd,
            confirmations=confirmations,
            conflicts=conflicts,
            reasons=reasons,
        )

        # --------------------------------------------------
        # 3. Volume Profile
        # --------------------------------------------------

        profile_points = self._score_profile(
            direction=direction,
            profile=profile,
            confirmations=confirmations,
            conflicts=conflicts,
            reasons=reasons,
        )

        # --------------------------------------------------
        # 4. VWAP
        # --------------------------------------------------

        vwap_points = self._score_vwap(
            direction=direction,
            vwap=vwap,
            confirmations=confirmations,
            conflicts=conflicts,
            reasons=reasons,
        )

        score = (
            structure_points
            + cvd_points
            + profile_points
            + vwap_points
        )

        score = max(
            0.0,
            min(100.0, score),
        )

        grade = self._grade(
            score=score,
            conflicts=len(conflicts),
        )

        # A hard conflict invalidates actionability even when
        # the raw score remains above the A/A+ threshold.
        has_hard_conflict = bool(
            conflicts
        )

        actionable = (
            grade in {"A+", "A"}
            and not has_hard_conflict
        )

        return self._build_result(
            direction=direction,
            score=score,
            structure_points=structure_points,
            cvd_points=cvd_points,
            profile_points=profile_points,
            vwap_points=vwap_points,
            confirmations=tuple(confirmations),
            conflicts=tuple(conflicts),
            reasons=tuple(reasons),
            actionable=actionable,
            grade=grade,
        )

    def _score_cvd(
        self,
        direction: str,
        cvd: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:
        """
        Score CVD direction and strength.

        Strong alignment:
            25

        Directional but weaker:
             8

        Neutral:
             8

        Opposing:
             0 + hard conflict
        """

        if cvd is None:
            reasons.append(
                "CVD context unavailable."
            )
            return 0.0

        cvd_direction = self._normalize_direction(
            getattr(
                cvd,
                "direction",
                "NEUTRAL",
            )
        )

        strength = self._safe_float(
            getattr(
                cvd,
                "strength",
                0.0,
            )
        )

        if (
            cvd_direction == direction
            and strength >= 60.0
        ):
            confirmations.append(
                "CVD strong alignment"
            )

            reasons.append(
                f"CVD {cvd_direction} with strength "
                f"{strength:.2f} supports setup."
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

            return 8.0

        conflicts.append(
            "CVD opposing structure setup"
        )

        reasons.append(
            f"CVD {cvd_direction} conflicts with "
            f"{direction} setup."
        )

        return 0.0

    def _score_profile(
        self,
        direction: str,
        profile: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:
        """
        Score Volume Profile location.

        Supportive:
            20

        Inside value area:
             8

        Opposing:
             0 + hard conflict
        """

        if profile is None:
            reasons.append(
                "Volume Profile context unavailable."
            )
            return 0.0

        location = str(
            getattr(
                profile,
                "location",
                getattr(
                    profile,
                    "position",
                    "UNKNOWN",
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
                f"supports {direction} setup."
            )

            return self.PROFILE_WEIGHT

        if location in opposing:
            conflicts.append(
                "Volume Profile location opposing setup"
            )

            reasons.append(
                f"Volume Profile location {location} "
                f"opposes {direction} setup."
            )

            return 0.0

        if location in {
            "INSIDE_VALUE_AREA",
            "INSIDE_VALUE",
            "INSIDE_VA",
        }:
            reasons.append(
                "Price is inside the value area."
            )

            return 8.0

        reasons.append(
            "Volume Profile location is neutral/unknown."
        )

        return 8.0

    def _score_vwap(
        self,
        direction: str,
        vwap: Any | None,
        confirmations: list[str],
        conflicts: list[str],
        reasons: list[str],
    ) -> float:
        """
        Score VWAP direction.

        Supportive:
            15

        Neutral:
             7

        Opposing:
             0 + hard conflict
        """

        if vwap is None:
            reasons.append(
                "VWAP context unavailable."
            )
            return 0.0

        vwap_direction = self._normalize_direction(
            getattr(
                vwap,
                "direction",
                "NEUTRAL",
            )
        )

        if vwap_direction == direction:
            confirmations.append(
                "VWAP directional alignment"
            )

            reasons.append(
                f"VWAP {vwap_direction} supports setup."
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

    @staticmethod
    def _grade(
        score: float,
        conflicts: int,
    ) -> str:
        """
        Convert raw score into setup grade.

        A+:
            85-100

        A:
            70-84.99

        B:
            55-69.99

        CONFLICT:
            one or more hard conflicts

        REJECT:
            insufficient score
        """

        # Any hard conflict is explicitly represented as
        # CONFLICT, regardless of raw score.
        if conflicts > 0:
            return "CONFLICT"

        if score >= 85.0:
            return "A+"

        if score >= 70.0:
            return "A"

        if score >= 55.0:
            return "B"

        return "REJECT"

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
        cvd_points: float,
        profile_points: float,
        vwap_points: float,
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
        )
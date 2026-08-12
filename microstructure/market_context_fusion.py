from __future__ import annotations

from indicators.vwap_context import VWAPContext
from models.cvd_strength import CVDStrengthResult
from models.market_context import MarketContextFusion
from models.volume_profile import VolumeProfileResult


class MarketContextFusionEngine:
    """
    Fuse CVD Strength, VWAP Context and Volume Profile.

    This engine does not create BUY/SELL signals.

    It produces directional market context that can later be
    consumed by the final setup/risk engine.
    """

    def combine(
        self,
        cvd: CVDStrengthResult,
        vwap: VWAPContext,
        profile: VolumeProfileResult | None = None,
    ) -> MarketContextFusion:
        """
        Combine CVD, VWAP and optional Volume Profile context.

        Alignment states
        ----------------
        CONFIRMED:
            CVD and VWAP agree and Volume Profile does not
            oppose the directional context.

        CONFLICT:
            CVD and VWAP directly conflict, or Volume Profile
            explicitly opposes the directional context.

        NEUTRAL:
            CVD is neutral or directional confirmation is
            insufficient.
        """

        cvd_direction = cvd.direction.strip().upper()
        vwap_trend = vwap.trend.strip().upper()

        if profile is None:
            profile_position = "UNKNOWN"
            profile_alignment = "UNKNOWN"
        else:
            profile_position = profile.position.strip().upper()

            profile_alignment = self._profile_alignment(
                direction=cvd_direction,
                profile=profile,
            )

        directional_alignment = self._directional_alignment(
            cvd_direction=cvd_direction,
            vwap_trend=vwap_trend,
        )

        # ---------------------------------------------------------
        # Direct CVD/VWAP conflict
        # ---------------------------------------------------------
        if directional_alignment == "CONFLICT":
            alignment = "CONFLICT"
            direction = "CONFLICT"
            effective_strength = 0.0

        # ---------------------------------------------------------
        # CVD + VWAP confirmed
        # ---------------------------------------------------------
        elif directional_alignment == "CONFIRMED":
            direction = cvd_direction

            if profile_alignment == "OPPOSING":
                alignment = "CONFLICT"
                direction = "CONFLICT"
                effective_strength = 0.0

            elif profile_alignment == "SUPPORTIVE":
                alignment = "CONFIRMED"
                effective_strength = min(
                    cvd.overall_strength * 1.10,
                    100.0,
                )

            else:
                alignment = "CONFIRMED"
                effective_strength = cvd.overall_strength

        # ---------------------------------------------------------
        # CVD/VWAP not confirmed
        # ---------------------------------------------------------
        else:
            # A neutral CVD must not be promoted to a directional
            # signal merely because VWAP is directional.
            direction = "NEUTRAL"

            if profile_alignment == "OPPOSING":
                alignment = "CONFLICT"
                direction = "CONFLICT"
                effective_strength = 0.0

            else:
                alignment = "NEUTRAL"
                effective_strength = (
                    cvd.overall_strength * 0.5
                )

        return MarketContextFusion(
            cvd_direction=cvd_direction,
            vwap_trend=vwap_trend,
            profile_position=profile_position,
            profile_alignment=profile_alignment,
            alignment=alignment,
            direction=direction,
            cvd_strength=round(
                cvd.overall_strength,
                2,
            ),
            effective_strength=round(
                effective_strength,
                2,
            ),
            vwap_position=vwap.position,
            vwap_distance_pct=vwap.distance_pct,
            vwap_slope=vwap.slope,
            poc=(
                profile.poc
                if profile is not None
                else None
            ),
            vah=(
                profile.vah
                if profile is not None
                else None
            ),
            val=(
                profile.val
                if profile is not None
                else None
            ),
            current_price=(
                profile.current_price
                if profile is not None
                else None
            ),
        )

    @staticmethod
    def _directional_alignment(
        cvd_direction: str,
        vwap_trend: str,
    ) -> str:
        """
        Determine CVD/VWAP directional relationship.
        """

        if (
            cvd_direction in {"BULLISH", "BEARISH"}
            and vwap_trend == cvd_direction
        ):
            return "CONFIRMED"

        if (
            cvd_direction in {"BULLISH", "BEARISH"}
            and vwap_trend in {"BULLISH", "BEARISH"}
            and cvd_direction != vwap_trend
        ):
            return "CONFLICT"

        return "NEUTRAL"

    @staticmethod
    def _profile_alignment(
        direction: str,
        profile: VolumeProfileResult,
    ) -> str:
        """
        Determine whether Volume Profile location supports
        the directional context.

        BULLISH:
            Below VAL      -> SUPPORTIVE
            Above VAH      -> OPPOSING
            Inside VA      -> NEUTRAL

        BEARISH:
            Above VAH      -> SUPPORTIVE
            Below VAL      -> OPPOSING
            Inside VA      -> NEUTRAL
        """

        if direction not in {"BULLISH", "BEARISH"}:
            return "NEUTRAL"

        if profile.position == "UNKNOWN":
            return "NEUTRAL"

        if (
            direction == "BULLISH"
            and profile.position == "BELOW_VALUE_AREA"
        ):
            return "SUPPORTIVE"

        if (
            direction == "BULLISH"
            and profile.position == "ABOVE_VALUE_AREA"
        ):
            return "OPPOSING"

        if (
            direction == "BEARISH"
            and profile.position == "ABOVE_VALUE_AREA"
        ):
            return "SUPPORTIVE"

        if (
            direction == "BEARISH"
            and profile.position == "BELOW_VALUE_AREA"
        ):
            return "OPPOSING"

        return "NEUTRAL"
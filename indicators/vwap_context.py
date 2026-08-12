from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class VWAPContext:
    """
    Market context derived from price and VWAP.

    Attributes
    ----------
    position:
        ABOVE, BELOW or AT_VWAP.

    distance_pct:
        Percentage distance of price from VWAP.

    slope:
        Simple VWAP slope between two consecutive observations.

    trend:
        BULLISH, BEARISH or NEUTRAL.
    """

    position: str
    distance_pct: float
    slope: float
    trend: str


def build_vwap_context(
    price: float,
    vwap: float,
    previous_vwap: float | None = None,
) -> VWAPContext:
    """
    Build normalized VWAP market context.
    """

    if vwap <= 0:
        raise ValueError(
            "VWAP must be greater than zero."
        )

    if price < 0:
        raise ValueError(
            "Price cannot be negative."
        )

    distance_pct = (
        (price - vwap)
        / vwap
        * 100.0
    )

    tolerance = 1e-12

    if distance_pct > tolerance:
        position = "ABOVE_VWAP"
    elif distance_pct < -tolerance:
        position = "BELOW_VWAP"
    else:
        position = "AT_VWAP"

    slope = 0.0

    if previous_vwap is not None:
        slope = vwap - previous_vwap

    if (
        position == "ABOVE_VWAP"
        and slope > tolerance
    ):
        trend = "BULLISH"

    elif (
        position == "BELOW_VWAP"
        and slope < -tolerance
    ):
        trend = "BEARISH"

    else:
        trend = "NEUTRAL"

    return VWAPContext(
        position=position,
        distance_pct=round(
            distance_pct,
            4,
        ),
        slope=round(
            slope,
            8,
        ),
        trend=trend,
    )
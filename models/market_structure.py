from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MarketSwing:
    """
    Confirmed market-structure swing.

    A swing becomes usable only after the confirmation window
    has elapsed.

    confirmation_index:
        Candle index at which the swing becomes observable.
    """

    index: int
    timestamp: int
    price: float
    kind: str
    label: str
    confirmation_index: int


@dataclass(slots=True, frozen=True)
class MarketStructureResult:
    """
    Market structure analysis result.
    """

    swings: list[MarketSwing]

    latest_high: MarketSwing | None
    previous_high: MarketSwing | None

    latest_low: MarketSwing | None
    previous_low: MarketSwing | None

    structure: str
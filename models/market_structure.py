from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MarketSwing:
    """
    Confirmed market-structure swing.
    """

    index: int
    timestamp: int

    price: float

    kind: str
    label: str


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
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StructureBreak:
    """
    Detected market-structure break.
    """

    index: int
    timestamp: int
    price: float

    event: str
    direction: str

    broken_index: int
    broken_price: float

    displacement: float
    displacement_pct: float
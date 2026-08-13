from __future__ import annotations

from dataclasses import dataclass, field

from models.structure_break import StructureBreak


@dataclass(slots=True, frozen=True)
class StructureBreakResult:
    """
    BOS / CHoCH / MSS analysis result.
    """

    events: list[StructureBreak] = field(
        default_factory=list
    )

    latest_event: str = "NONE"
    latest_direction: str = "NEUTRAL"

    bullish_bos_count: int = 0
    bearish_bos_count: int = 0

    bullish_choch_count: int = 0
    bearish_choch_count: int = 0

    bullish_mss_count: int = 0
    bearish_mss_count: int = 0
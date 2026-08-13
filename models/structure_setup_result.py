from __future__ import annotations

from dataclasses import dataclass, field

from models.structure_setup import StructureSetup


@dataclass(slots=True, frozen=True)
class StructureSetupResult:
    """
    Structure setup analysis result.
    """

    setups: list[StructureSetup] = field(
        default_factory=list
    )

    latest_setup: str = "NONE"
    latest_direction: str = "NEUTRAL"

    bullish_setup_count: int = 0
    bearish_setup_count: int = 0
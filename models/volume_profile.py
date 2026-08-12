from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class VolumeProfileLevel:
    """
    Volume traded inside one price bin.
    """

    price_low: float
    price_high: float
    volume: float

    @property
    def price_center(self) -> float:
        return (
            self.price_low
            + self.price_high
        ) / 2.0


@dataclass(slots=True, frozen=True)
class VolumeProfileResult:
    """
    Normalized volume profile analysis.
    """

    levels: list[VolumeProfileLevel]

    poc: float | None
    vah: float | None
    val: float | None

    total_volume: float

    hvn: list[float]
    lvn: list[float]

    current_price: float | None
    position: str
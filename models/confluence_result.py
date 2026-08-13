from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ConfluenceResult:
    """
    Confluence evaluation for a structure setup.

    Score is intentionally separate from the old technical
    score used by SignalEngine.
    """

    direction: str

    score: float

    grade: str

    structure_points: float
    cvd_points: float
    profile_points: float
    vwap_points: float

    confirmations: tuple[str, ...]
    conflicts: tuple[str, ...]
    reasons: tuple[str, ...]

    actionable: bool
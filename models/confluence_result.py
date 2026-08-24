from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ConfluenceResult:
    """
    Confluence evaluation for a structure setup.

    Primary market score = 100:

        Structure / MSS        25
        Liquidity Sweep        15
        Volume Profile         15
        VWAP                   10
        CVD / Delta             15
        Order Flow             10
        Order Book             10

    Session quality is kept separate from the 100-point
    primary market score.
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

    # ------------------------------------------------------------
    # New scoring components
    # ------------------------------------------------------------

    liquidity_points: float = 0.0
    order_flow_points: float = 0.0
    order_book_points: float = 0.0

    # ------------------------------------------------------------
    # Session quality is NOT part of the 100-point score.
    # ------------------------------------------------------------

    session_quality: float = 0.0
    session_name: str = "UNKNOWN"
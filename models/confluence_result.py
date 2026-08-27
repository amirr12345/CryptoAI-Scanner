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
        CVD / Delta             15
        VWAP                    10
        Order Flow              10
        --------------------------
                              90 -> normalized to 100

    Order Book is NOT part of the primary score.

    Order Book and Session Quality are execution gates.
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
    # Supporting components
    # ------------------------------------------------------------

    liquidity_points: float = 0.0
    order_flow_points: float = 0.0

    # Kept for backward compatibility.
    # This is now diagnostic only and is NOT part of score.
    order_book_points: float = 0.0

    # ------------------------------------------------------------
    # Session
    # ------------------------------------------------------------

    session_quality: float = 0.0
    session_name: str = "UNKNOWN"

    # ------------------------------------------------------------
    # Execution Gate
    # ------------------------------------------------------------

    execution_status: str = "WAIT"
    order_book_imbalance: float = 0.0
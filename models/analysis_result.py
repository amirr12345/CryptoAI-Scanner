from __future__ import annotations

from dataclasses import dataclass, field

from models.market_context_snapshot import (
    MarketContextSnapshot,
)


@dataclass(slots=True, frozen=True)
class AnalysisResult:
    """
    Final market analysis result.

    The technical signal remains independent from the
    market-context layer.
    """

    symbol: str
    timestamp: int

    price: float

    total_score: int
    confidence: float
    signal: str

    reasons: list[str] = field(
        default_factory=list
    )

    indicators: dict[str, float] = field(
        default_factory=dict
    )

    market_context: MarketContextSnapshot | None = None
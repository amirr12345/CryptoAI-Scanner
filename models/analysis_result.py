from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class AnalysisResult:
    """
    Final market analysis result.
    """

    symbol: str
    timestamp: int

    price: float

    total_score: int
    confidence: float
    signal: str

    reasons: list[str] = field(default_factory=list)

    indicators: dict[str, float] = field(default_factory=dict)
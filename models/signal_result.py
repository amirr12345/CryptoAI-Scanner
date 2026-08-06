from dataclasses import dataclass


@dataclass(slots=True)
class SignalResult:
    """
    Final trading signal generated from ScoreEngine.
    """

    signal: str
    score: int
    confidence: float
    reasons: list[str]
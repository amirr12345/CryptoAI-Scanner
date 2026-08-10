from dataclasses import dataclass


@dataclass(slots=True)
class DetectorResult:
    """
    Standard output returned by every detector.
    """

    detector: str
    signal: str
    score: int = 0
    confidence: float = 0.0
    description: str = ""
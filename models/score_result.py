from dataclasses import dataclass, field


@dataclass(slots=True)
class ScoreResult:
    """
    Final aggregated score from all detectors.
    """

    total_score: int
    detector_count: int
    confidence: float
    reasons: list[str] = field(default_factory=list)
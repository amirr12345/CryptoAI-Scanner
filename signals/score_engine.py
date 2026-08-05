from models.detector_result import DetectorResult
from models.score_result import ScoreResult


class ScoreEngine:
    """
    Combine detector outputs into one score.
    """

    def calculate(
        self,
        results: list[DetectorResult],
    ) -> ScoreResult:

        total_score = sum(r.score for r in results)

        detector_count = len(results)

        reasons = [
            f"{r.detector}: {r.signal}"
            for r in results
        ]

        confidence = 0.0

        if detector_count > 0:
            confidence = (
                sum(r.confidence for r in results)
                / detector_count
            )

        return ScoreResult(
            total_score=total_score,
            detector_count=detector_count,
            confidence=round(confidence, 2),
            reasons=reasons,
        )
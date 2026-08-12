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

        total_score = sum(
            result.score
            for result in results
        )

        detector_count = len(results)

        reasons = [
            f"{result.detector}: {result.signal}"
            for result in results
        ]

        active_results = [
            result
            for result in results
            if result.score != 0
        ]

        confidence = 0.0

        if active_results:
            confidence = (
                sum(
                    result.confidence
                    for result in active_results
                )
                / len(active_results)
            )

        return ScoreResult(
            total_score=total_score,
            detector_count=detector_count,
            confidence=round(confidence, 2),
            reasons=reasons,
        )
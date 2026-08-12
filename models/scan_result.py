from dataclasses import dataclass, field

from models.analysis_result import AnalysisResult


@dataclass(slots=True, frozen=True)
class ScanResult:
    """
    Result of scanning multiple markets.
    """

    results: list[AnalysisResult] = field(
        default_factory=list
    )

    failed_symbols: dict[str, str] = field(
        default_factory=dict
    )

    @property
    def successful_count(self) -> int:
        return len(self.results)

    @property
    def failed_count(self) -> int:
        return len(self.failed_symbols)

    @property
    def ranked_results(self) -> list[AnalysisResult]:
        """
        All successful analysis results ranked by score.
        """

        return sorted(
            self.results,
            key=lambda result: result.total_score,
            reverse=True,
        )

    @property
    def actionable_results(self) -> list[AnalysisResult]:
        """
        Analysis results with a non-zero score.

        Score zero means no active detector signal was generated.
        Such results remain available in `results` but are excluded
        from the actionable ranking.
        """

        return [
            result
            for result in self.ranked_results
            if result.total_score != 0
        ]
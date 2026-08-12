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
        Rank all successful analysis results.

        Primary sort:
            total_score descending

        Secondary sort:
            confidence descending
        """

        return sorted(
            self.results,
            key=lambda result: (
                result.total_score,
                result.confidence,
            ),
            reverse=True,
        )

    @property
    def actionable_results(self) -> list[AnalysisResult]:
        """
        Return actionable trading signals only.

        HOLD results remain available in:
            results
            ranked_results

        but are excluded from actionable ranking.
        """

        return [
            result
            for result in self.ranked_results
            if result.signal != "HOLD"
        ]

    def top_actionable(
        self,
        limit: int = 10,
    ) -> list[AnalysisResult]:
        """
        Return the top N actionable trading signals.

        Parameters
        ----------
        limit:
            Maximum number of actionable signals to return.

        Returns
        -------
        list[AnalysisResult]
            Top actionable signals according to the current ranking.

        Raises
        ------
        ValueError
            If limit is less than or equal to zero.
        """

        if limit <= 0:
            raise ValueError(
                "Limit must be greater than zero."
            )

        return self.actionable_results[:limit]
from dataclasses import dataclass, field

from models.analysis_result import AnalysisResult


@dataclass(slots=True, frozen=True)
class ScanResult:
    """
    Result of scanning multiple markets.
    """

    results: list[AnalysisResult] = field(default_factory=list)
    failed_symbols: dict[str, str] = field(default_factory=dict)

    @property
    def successful_count(self) -> int:
        return len(self.results)

    @property
    def failed_count(self) -> int:
        return len(self.failed_symbols)

    @property
    def ranked_results(self) -> list[AnalysisResult]:
        return sorted(
            self.results,
            key=lambda result: result.total_score,
            reverse=True,
        )
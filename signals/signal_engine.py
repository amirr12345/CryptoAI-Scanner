from models.score_result import ScoreResult
from models.signal_result import SignalResult
from signals.detector_config import DetectorConfig


class SignalEngine:
    """
    Convert ScoreResult into a trading signal.
    """

    def generate(
        self,
        score: ScoreResult,
    ) -> SignalResult:

        total = score.total_score

        if total >= DetectorConfig.STRONG_BUY_SCORE:
            signal = "STRONG_BUY"

        elif total >= DetectorConfig.BUY_SCORE:
            signal = "BUY"

        elif total <= DetectorConfig.STRONG_SELL_SCORE:
            signal = "STRONG_SELL"

        elif total <= DetectorConfig.SELL_SCORE:
            signal = "SELL"

        else:
            signal = "HOLD"

        return SignalResult(
            signal=signal,
            score=score.total_score,
            confidence=score.confidence,
            reasons=score.reasons,
        )
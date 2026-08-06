from models.score_result import ScoreResult
from models.signal_result import SignalResult


class SignalEngine:
    """
    Convert ScoreResult into a trading signal.
    """

    def generate(self, score: ScoreResult) -> SignalResult:

        total = score.total_score

        if total >= 40:
            signal = "STRONG_BUY"

        elif total >= 20:
            signal = "BUY"

        elif total <= -40:
            signal = "STRONG_SELL"

        elif total <= -20:
            signal = "SELL"

        else:
            signal = "HOLD"

        return SignalResult(
            signal=signal,
            score=score.total_score,
            confidence=score.confidence,
            reasons=score.reasons,
        )
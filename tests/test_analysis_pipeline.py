import pandas as pd

from models.score_result import ScoreResult
from models.signal_result import SignalResult
from signals.detector_engine import DetectorEngine
from signals.detectors.ema_cross import EMACrossDetector
from signals.detectors.macd_cross import MACDCrossDetector
from signals.detectors.volume_confirmation import VolumeConfirmationDetector
from signals.score_engine import ScoreEngine
from signals.signal_engine import SignalEngine


def test_full_analysis_pipeline():

    df = pd.DataFrame(
        {
            "ema20": [10] * 19 + [15],
            "ema50": [12] * 19 + [14],
            "macd": [1.0] * 19 + [2.0],
            "signal": [1.5] * 19 + [1.8],
            "volume": [100] * 19 + [150],
            "volume_sma20": [100] * 20,
            "volume_ratio": [1.0] * 19 + [1.5],
        }
    )

    # 1. Detection
    detector_engine = DetectorEngine(
        [
            EMACrossDetector(),
            MACDCrossDetector(),
            VolumeConfirmationDetector(),
        ]
    )

    detector_results = detector_engine.run(df)

    assert len(detector_results) == 3

    # 2. Scoring
    score_result = ScoreEngine().calculate(detector_results)

    assert isinstance(score_result, ScoreResult)
    assert score_result.total_score == 60
    assert score_result.detector_count == 3

    # 3. Signal
    signal_result = SignalEngine().generate(score_result)

    assert isinstance(signal_result, SignalResult)
    assert signal_result.signal == "STRONG_BUY"
    assert signal_result.score == 60
    assert signal_result.confidence == score_result.confidence
    assert signal_result.reasons == score_result.reasons
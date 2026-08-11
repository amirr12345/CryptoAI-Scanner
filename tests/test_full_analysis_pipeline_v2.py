import pandas as pd

from indicators.indicator_engine import IndicatorEngine
from signals.detector_engine import DetectorEngine
from signals.detectors.bollinger_breakout import BollingerBreakoutDetector
from signals.detectors.ema_cross import EMACrossDetector
from signals.detectors.macd_cross import MACDCrossDetector
from signals.detectors.volume_confirmation import VolumeConfirmationDetector
from signals.score_engine import ScoreEngine
from signals.signal_engine import SignalEngine


def test_full_analysis_pipeline_v2():
    rows = 80

    df = pd.DataFrame(
        {
            "open": list(range(100, 100 + rows)),
            "high": list(range(102, 102 + rows)),
            "low": list(range(98, 98 + rows)),
            "close": list(range(100, 100 + rows)),
            "volume": [1000] * rows,
        }
    )

    # 1. Indicators
    indicator_engine = IndicatorEngine()
    enriched_df = indicator_engine.calculate(df)

    required_indicator_columns = {
        "ema20",
        "ema50",
        "macd",
        "signal",
        "histogram",
        "rsi",
        "atr",
        "middle_band",
        "upper_band",
        "lower_band",
        "bandwidth",
        "volume_sma20",
        "volume_ratio",
    }

    assert required_indicator_columns.issubset(
        enriched_df.columns
    )

    # 2. Detectors
    detector_engine = DetectorEngine(
        [
            EMACrossDetector(),
            MACDCrossDetector(),
            BollingerBreakoutDetector(),
            VolumeConfirmationDetector(),
        ]
    )

    detector_results = detector_engine.run(enriched_df)

    assert len(detector_results) == 4

    # 3. Score
    score_result = ScoreEngine().calculate(detector_results)

    assert score_result.detector_count == 4
    assert isinstance(score_result.total_score, int)
    assert 0.0 <= score_result.confidence <= 1.0
    assert len(score_result.reasons) == 4

    # 4. Signal
    signal_result = SignalEngine().generate(score_result)

    assert signal_result.score == score_result.total_score
    assert signal_result.confidence == score_result.confidence
    assert signal_result.reasons == score_result.reasons

    assert signal_result.signal in {
        "STRONG_BUY",
        "BUY",
        "HOLD",
        "SELL",
        "STRONG_SELL",
    }
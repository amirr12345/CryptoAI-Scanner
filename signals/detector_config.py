from dataclasses import dataclass


@dataclass(frozen=True)
class DetectorConfig:
    """
    Global detector configuration.

    All detector weights, thresholds and signal
    classification limits are centralized here.
    """

    # -----------------------------
    # Detector Weights
    # -----------------------------

    EMA_WEIGHT: int = 25
    MACD_WEIGHT: int = 20
    BOLLINGER_WEIGHT: int = 20
    VOLUME_WEIGHT: int = 15

    # -----------------------------
    # Volume Thresholds
    # -----------------------------

    VOLUME_STRONG_RATIO: float = 1.50
    VOLUME_WEAK_RATIO: float = 1.10

    # -----------------------------
    # RSI Thresholds
    # -----------------------------

    RSI_OVERSOLD: int = 30
    RSI_OVERBOUGHT: int = 70

    # -----------------------------
    # Score Thresholds
    # -----------------------------

    STRONG_BUY_SCORE: int = 40
    BUY_SCORE: int = 20

    STRONG_SELL_SCORE: int = -40
    SELL_SCORE: int = -20
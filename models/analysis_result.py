from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisResult:
    """
    Final result of market analysis.
    """

    symbol: str

    price: float

    ema20: float

    ema50: float

    rsi: float = 0.0

    macd: float = 0.0

    trend: str = "NEUTRAL"

    signal: str = "HOLD"

    score: int = 0

    atr: float = 0.0

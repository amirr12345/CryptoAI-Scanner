from dataclasses import dataclass


@dataclass
class AnalysisResult:

    symbol: str

    price: float

    ema20: float

    ema50: float

    rsi: float

    macd: float

    signal: str

    score: int
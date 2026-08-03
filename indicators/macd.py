import pandas as pd


class MACDIndicator:

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:

        close = df["close"]

        ema_fast = close.ewm(span=self.fast, adjust=False).mean()

        ema_slow = close.ewm(span=self.slow, adjust=False).mean()

        macd = ema_fast - ema_slow

        signal = macd.ewm(span=self.signal, adjust=False).mean()

        histogram = macd - signal

        return pd.DataFrame(
            {
                "macd": macd,
                "signal": signal,
                "histogram": histogram,
            }
        )

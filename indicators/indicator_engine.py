from __future__ import annotations

import pandas as pd

from indicators.atr_indicator import ATRIndicator
from indicators.bollinger_indicator import BollingerIndicator
from indicators.ema_indicator import EMAIndicator
from indicators.macd_indicator import MACDIndicator
from indicators.rsi_indicator import RSIIndicator
from indicators.volume_indicator import VolumeIndicator


class IndicatorEngine:
    """
    Calculates all configured indicators and enriches the candle DataFrame.

    The engine does not create trading signals.
    Detectors remain responsible for interpreting indicator values.
    """

    def __init__(
        self,
        ema_fast_period: int = 20,
        ema_slow_period: int = 50,
        macd_fast_period: int = 12,
        macd_slow_period: int = 26,
        macd_signal_period: int = 9,
        rsi_period: int = 14,
        atr_period: int = 14,
        bollinger_period: int = 20,
        bollinger_std_dev: float = 2.0,
        volume_period: int = 20,
    ):
        self.ema_fast = EMAIndicator(ema_fast_period)
        self.ema_slow = EMAIndicator(ema_slow_period)

        self.macd = MACDIndicator(
            fast=macd_fast_period,
            slow=macd_slow_period,
            signal=macd_signal_period,
        )

        self.rsi = RSIIndicator(rsi_period)

        self.atr = ATRIndicator(atr_period)

        self.bollinger = BollingerIndicator(
            period=bollinger_period,
            std_dev=bollinger_std_dev,
        )

        self.volume = VolumeIndicator(volume_period)

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators and return an enriched DataFrame.

        The original OHLCV columns are preserved.
        """

        if data.empty:
            return data.copy()

        result = data.copy()

        indicator_frames = [
            self.ema_fast.calculate(result),
            self.ema_slow.calculate(result),
            self.macd.calculate(result),
            self.rsi.calculate(result),
            self.atr.calculate(result),
            self.bollinger.calculate(result),
            self.volume.calculate(result),
        ]

        for indicator_frame in indicator_frames:
            result = result.join(
                indicator_frame,
                how="left",
            )

        return result
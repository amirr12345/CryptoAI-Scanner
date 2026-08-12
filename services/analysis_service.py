from __future__ import annotations

import math

import pandas as pd

from indicators.indicator_engine import IndicatorEngine
from models.analysis_result import AnalysisResult
from services.market_service import MarketService
from signals.detector_engine import DetectorEngine
from signals.detectors.bollinger_breakout import BollingerBreakoutDetector
from signals.detectors.ema_cross import EMACrossDetector
from signals.detectors.macd_cross import MACDCrossDetector
from signals.detectors.volume_confirmation import (
    VolumeConfirmationDetector,
)
from signals.score_engine import ScoreEngine
from signals.signal_engine import SignalEngine


class AnalysisService:
    """
    Orchestrates market data, indicators, detectors, scoring
    and final signal generation.
    """

    MIN_ANALYSIS_CANDLES = 50

    def __init__(
        self,
        market_service: MarketService | None = None,
        indicator_engine: IndicatorEngine | None = None,
        detector_engine: DetectorEngine | None = None,
        score_engine: ScoreEngine | None = None,
        signal_engine: SignalEngine | None = None,
    ):
        self.market_service = market_service or MarketService()

        self.indicator_engine = (
            indicator_engine or IndicatorEngine()
        )

        self.detector_engine = detector_engine or DetectorEngine(
            [
                EMACrossDetector(),
                MACDCrossDetector(),
                BollingerBreakoutDetector(),
                VolumeConfirmationDetector(),
            ]
        )

        self.score_engine = score_engine or ScoreEngine()
        self.signal_engine = signal_engine or SignalEngine()

    @staticmethod
    def _candles_to_dataframe(candles) -> pd.DataFrame:
        """
        Convert Candle objects into the OHLCV DataFrame expected
        by IndicatorEngine.
        """

        if not candles:
            raise ValueError("No candles available for analysis.")

        return pd.DataFrame(
            {
                "timestamp": [candle.timestamp for candle in candles],
                "open": [candle.open for candle in candles],
                "high": [candle.high for candle in candles],
                "low": [candle.low for candle in candles],
                "close": [candle.close for candle in candles],
                "volume": [candle.volume for candle in candles],
            }
        )

    @classmethod
    def _validate_market_data(
        cls,
        df: pd.DataFrame,
    ) -> None:
        """
        Validate candle data before running indicators.

        Raises
        ------
        ValueError
            When the market data is not suitable for analysis.
        """

        required_columns = {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                "Invalid market data: missing columns: "
                + ", ".join(sorted(missing))
            )

        if len(df) < cls.MIN_ANALYSIS_CANDLES:
            raise ValueError(
                "Invalid market data: insufficient candles. "
                f"Required={cls.MIN_ANALYSIS_CANDLES}, "
                f"Received={len(df)}"
            )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:
            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            if numeric_values.isna().any():
                raise ValueError(
                    f"Invalid market data: non-numeric values in {column}."
                )

            if not numeric_values.map(math.isfinite).all():
                raise ValueError(
                    f"Invalid market data: non-finite values in {column}."
                )

        if (df["high"] < df["low"]).any():
            raise ValueError(
                "Invalid market data: high is below low."
            )

        if (df["close"] < df["low"]).any():
            raise ValueError(
                "Invalid market data: close is below low."
            )

        if (df["close"] > df["high"]).any():
            raise ValueError(
                "Invalid market data: close is above high."
            )

        if (df["volume"] < 0).any():
            raise ValueError(
                "Invalid market data: negative volume."
            )

        close_min = float(df["close"].min())
        close_max = float(df["close"].max())

        if close_min == close_max:
            raise ValueError(
                "Invalid market data: flat price."
            )

        total_volume = float(df["volume"].sum())

        if total_volume <= 0:
            raise ValueError(
                "Invalid market data: zero trading volume."
            )

    @staticmethod
    def _latest_indicators(
        enriched_df: pd.DataFrame,
    ) -> dict[str, float]:
        """
        Extract latest finite numeric indicator values.
        """

        indicator_columns = {
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

        latest = enriched_df.iloc[-1]

        indicators: dict[str, float] = {}

        for column in indicator_columns:
            if column not in enriched_df.columns:
                continue

            value = latest[column]

            if pd.isna(value):
                continue

            numeric_value = float(value)

            if not math.isfinite(numeric_value):
                continue

            indicators[column] = numeric_value

        return indicators

    def analyze(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> AnalysisResult:
        """
        Execute the complete analysis pipeline for one market.
        """

        candles = self.market_service.history(
            symbol=symbol,
            resolution=resolution,
            countback=countback,
        )

        df = self._candles_to_dataframe(candles)

        self._validate_market_data(df)

        enriched_df = self.indicator_engine.calculate(df)

        detector_results = self.detector_engine.run(
            enriched_df
        )

        score_result = self.score_engine.calculate(
            detector_results
        )

        signal_result = self.signal_engine.generate(
            score_result
        )

        latest = enriched_df.iloc[-1]

        return AnalysisResult(
            symbol=symbol.upper(),
            timestamp=int(latest["timestamp"]),
            price=float(latest["close"]),
            total_score=score_result.total_score,
            confidence=score_result.confidence,
            signal=signal_result.signal,
            reasons=signal_result.reasons,
            indicators=self._latest_indicators(enriched_df),
        )
from __future__ import annotations

from core.trade_store import TradeStore
from microstructure.bucketed_cvd_divergence import (
    BucketedCVDAnalyzer,
)
from microstructure.cvd_engine import CVDEngine
from microstructure.cvd_strength import (
    CVDStrengthAnalyzer,
)
from microstructure.time_bucketed_cvd import (
    TimeBucketedCVDEngine,
)
from microstructure.volume_profile import (
    VolumeProfileEngine,
)
from models.historical_context import (
    HistoricalContext,
)


class HistoricalContextEngine:
    """
    Reconstruct market context at a historical timestamp.

    HARD RULE:

        only trades with timestamp <= target_timestamp
        are allowed into every calculation.

    The public candle/structure timestamps in this project
    are seconds, while live captured trades are stored in
    milliseconds.

    This engine automatically normalizes the query timestamp
    to the timestamp unit used by TradeStore while preserving
    the original historical timestamp in the result.
    """

    MILLISECOND_THRESHOLD = 100_000_000_000

    def __init__(
        self,
        trade_store: TradeStore | None = None,
        bucket_interval_seconds: int = 60,
        cvd_lookback: int = 5,
        cvd_swing_window: int = 2,
        volume_profile_bins: int = 24,
        value_area_pct: float = 70.0,
    ) -> None:
        self.trade_store = (
            trade_store
            if trade_store is not None
            else TradeStore()
        )

        self.bucket_interval_seconds = (
            bucket_interval_seconds
        )

        self.cvd_lookback = cvd_lookback
        self.cvd_swing_window = cvd_swing_window

        self.volume_profile_bins = (
            volume_profile_bins
        )

        self.value_area_pct = (
            value_area_pct
        )

        self.cvd_engine = CVDEngine()

        self.bucketed_cvd = (
            TimeBucketedCVDEngine()
        )

        self.cvd_analyzer = (
            BucketedCVDAnalyzer()
        )

        self.cvd_strength = (
            CVDStrengthAnalyzer()
        )

        self.volume_profile = (
            VolumeProfileEngine()
        )

    def calculate(
        self,
        symbol: str,
        timestamp: int,
        lookback_seconds: int = 3600,
    ) -> HistoricalContext:
        """
        Reconstruct context at `timestamp`.

        `timestamp` is expected to be in the same unit as
        candle/structure timestamps.

        The engine detects the unit used by TradeStore and
        converts the query timestamp when required.

        Only trades inside:

            [timestamp - lookback_seconds, timestamp]

        are used.
        """

        if timestamp <= 0:
            raise ValueError(
                "Timestamp must be greater than zero."
            )

        if lookback_seconds <= 0:
            raise ValueError(
                "Lookback seconds must be greater than zero."
            )

        normalized_symbol = (
            symbol.strip().upper()
        )

        timestamp_scale = (
            self._detect_timestamp_scale(
                symbol=normalized_symbol,
            )
        )

        query_timestamp = (
            int(timestamp)
            * timestamp_scale
        )

        lookback_units = (
            int(lookback_seconds)
            * timestamp_scale
        )

        start_timestamp = (
            query_timestamp
            - lookback_units
        )

        trades = (
            self.trade_store.get_trades(
                symbol=normalized_symbol,
                start_timestamp=start_timestamp,
                end_timestamp=query_timestamp,
            )
        )

        if not trades:
            raise ValueError(
                "No historical trades available "
                f"for {normalized_symbol} at "
                f"timestamp={timestamp}."
            )

        # --------------------------------------------------
        # HARD AS-OF VALIDATION
        # --------------------------------------------------

        future_trades = [
            trade
            for trade in trades
            if int(trade.timestamp)
            > query_timestamp
        ]

        if future_trades:
            raise RuntimeError(
                "Historical context contains future trades."
            )

        # --------------------------------------------------
        # CVD
        # --------------------------------------------------

        cvd = self.cvd_engine.calculate(
            trades=trades,
            starting_cvd=0.0,
            swing_window=self.cvd_swing_window,
        )

        # --------------------------------------------------
        # Time-bucketed CVD
        # --------------------------------------------------

        buckets = (
            self.bucketed_cvd.calculate(
                trades=trades,
                interval_seconds=(
                    self.bucket_interval_seconds
                ),
            )
        )

        bucket_analysis = (
            self.cvd_analyzer.analyze(
                buckets=buckets,
                swing_window=self.cvd_swing_window,
            )
        )

        cvd_strength = (
            self.cvd_strength.analyze(
                buckets=buckets,
                analysis=bucket_analysis,
                lookback=self.cvd_lookback,
            )
        )

        # --------------------------------------------------
        # Historical VWAP
        # --------------------------------------------------

        vwap = self._calculate_vwap(
            trades=trades
        )

        previous_vwap = (
            self._calculate_previous_vwap(
                trades=trades,
                lookback_seconds=min(
                    lookback_seconds,
                    900,
                ),
                timestamp_scale=timestamp_scale,
            )
        )

        last_price = float(
            trades[-1].price
        )

        vwap_position = (
            self._vwap_position(
                price=last_price,
                vwap=vwap,
            )
        )

        vwap_distance_pct = (
            self._vwap_distance_pct(
                price=last_price,
                vwap=vwap,
            )
        )

        vwap_slope = 0.0

        if (
            vwap is not None
            and previous_vwap is not None
        ):
            vwap_slope = (
                vwap
                - previous_vwap
            )

        # --------------------------------------------------
        # Volume Profile
        # --------------------------------------------------

        profile = (
            self.volume_profile.calculate(
                trades=trades,
                bins=self.volume_profile_bins,
                value_area_pct=self.value_area_pct,
                current_price=last_price,
            )
        )

        return HistoricalContext(
            # IMPORTANT:
            # Keep original Setup/Candle timestamp.
            symbol=normalized_symbol,
            timestamp=int(timestamp),

            trade_count=len(trades),
            lookback_seconds=int(
                lookback_seconds
            ),

            cvd_direction=(
                cvd_strength.direction
            ),
            cvd_strength=(
                cvd_strength.overall_strength
            ),
            cvd_divergence=(
                cvd_strength.divergence
            ),
            cvd_delta=(
                cvd.delta
            ),
            cvd_change=(
                cvd.cvd_change
            ),

            vwap=vwap,
            previous_vwap=previous_vwap,
            vwap_position=vwap_position,
            vwap_distance_pct=(
                vwap_distance_pct
            ),
            vwap_slope=vwap_slope,

            poc=profile.poc,
            vah=profile.vah,
            val=profile.val,
            profile_position=(
                profile.position
            ),

            historical=True,
        )

    def _detect_timestamp_scale(
        self,
        symbol: str,
    ) -> int:
        """
        Detect the timestamp unit stored in TradeStore.

        Returns:

            1     -> seconds
            1000  -> milliseconds

        The threshold is intentionally simple and deterministic.
        """

        latest_timestamp = (
            self.trade_store.latest_timestamp(
                symbol
            )
        )

        if latest_timestamp is None:
            return 1

        if (
            latest_timestamp
            >= self.MILLISECOND_THRESHOLD
        ):
            return 1000

        return 1

    @staticmethod
    def _calculate_vwap(
        trades,
    ) -> float | None:
        """
        Calculate volume-weighted average price
        from historical trades only.
        """

        total_volume = sum(
            float(trade.volume)
            for trade in trades
        )

        if total_volume <= 0:
            return None

        weighted_value = sum(
            float(trade.price)
            * float(trade.volume)
            for trade in trades
        )

        return (
            weighted_value
            / total_volume
        )

    @staticmethod
    def _calculate_previous_vwap(
        trades,
        lookback_seconds: int,
        timestamp_scale: int,
    ) -> float | None:
        """
        Calculate VWAP for the previous time slice.

        The previous slice is expressed in the same timestamp
        unit as the trades.
        """

        if len(trades) < 2:
            return None

        latest_timestamp = int(
            trades[-1].timestamp
        )

        lookback_units = (
            int(lookback_seconds)
            * int(timestamp_scale)
        )

        cutoff = (
            latest_timestamp
            - lookback_units
        )

        previous = [
            trade
            for trade in trades
            if int(trade.timestamp)
            < cutoff
        ]

        if not previous:
            return None

        return HistoricalContextEngine._calculate_vwap(
            previous
        )

    @staticmethod
    def _vwap_position(
        price: float,
        vwap: float | None,
    ) -> str:
        if vwap is None:
            return "UNKNOWN"

        if price > vwap:
            return "ABOVE_VWAP"

        if price < vwap:
            return "BELOW_VWAP"

        return "AT_VWAP"

    @staticmethod
    def _vwap_distance_pct(
        price: float,
        vwap: float | None,
    ) -> float:
        if (
            vwap is None
            or vwap == 0
        ):
            return 0.0

        return (
            (
                price - vwap
            )
            / abs(vwap)
            * 100.0
        )
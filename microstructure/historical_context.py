from __future__ import annotations

from datetime import datetime, timezone

from core.trade_store import TradeStore

from microstructure.bucketed_cvd_divergence import (
    BucketedCVDAnalyzer,
)
from microstructure.cvd_engine import CVDEngine
from microstructure.cvd_strength import (
    CVDStrengthAnalyzer,
)
from microstructure.session_engine import (
    SessionEngine,
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
    Reconstruct market context strictly from information
    available at a historical timestamp.

    Historical features:

        - CVD
        - Delta
        - VWAP
        - Volume Profile
        - Order Flow
        - Session Quality

    HARD AS-OF RULE:

        Only trades with:

            trade.timestamp <= target_timestamp

        may participate in historical calculations.

    IMPORTANT:

        Current Order Book data is intentionally NOT included
        in HistoricalContext because that would introduce
        look-ahead bias.

        Order Book belongs to the live execution/confirmation
        layer.
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
        large_trade_multiplier: float = 3.0,
    ) -> None:
        self.trade_store = (
            trade_store
            if trade_store is not None
            else TradeStore()
        )

        self.bucket_interval_seconds = int(
            bucket_interval_seconds
        )

        self.cvd_lookback = int(
            cvd_lookback
        )

        self.cvd_swing_window = int(
            cvd_swing_window
        )

        self.volume_profile_bins = int(
            volume_profile_bins
        )

        self.value_area_pct = float(
            value_area_pct
        )

        if self.bucket_interval_seconds <= 0:
            raise ValueError(
                "bucket_interval_seconds "
                "must be greater than zero."
            )

        if self.cvd_lookback <= 0:
            raise ValueError(
                "cvd_lookback "
                "must be greater than zero."
            )

        if self.cvd_swing_window <= 0:
            raise ValueError(
                "cvd_swing_window "
                "must be greater than zero."
            )

        if self.volume_profile_bins <= 0:
            raise ValueError(
                "volume_profile_bins "
                "must be greater than zero."
            )

        if not (
            0.0
            < self.value_area_pct
            <= 100.0
        ):
            raise ValueError(
                "value_area_pct must be between "
                "0 and 100."
            )

        if large_trade_multiplier <= 0:
            raise ValueError(
                "large_trade_multiplier "
                "must be greater than zero."
            )

        self.large_trade_multiplier = float(
            large_trade_multiplier
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

        # Session Engine is deterministic for the timestamp
        # and dynamically evaluates market activity.
        self.session_engine = SessionEngine()

    # ============================================================
    # MAIN HISTORICAL CONTEXT
    # ============================================================

    def calculate(
        self,
        symbol: str,
        timestamp: int,
        lookback_seconds: int = 3600,
    ) -> HistoricalContext:
        """
        Reconstruct context at `timestamp`.

        `timestamp` uses the same unit as structure/candle
        timestamps.

        Only trades inside:

            [timestamp - lookback_seconds, timestamp]

        participate.

        No future trades are permitted.
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
            symbol
            .strip()
            .upper()
        )

        # --------------------------------------------------------
        # Timestamp scale
        # --------------------------------------------------------

        timestamp_scale = (
            self._detect_timestamp_scale(
                symbol=normalized_symbol
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

        # --------------------------------------------------------
        # Historical trades
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # HARD AS-OF VALIDATION
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # Ensure chronological order
        # --------------------------------------------------------

        trades = sorted(
            trades,
            key=lambda trade: int(
                trade.timestamp
            ),
        )

        # ========================================================
        # CVD
        # ========================================================

        cvd = self.cvd_engine.calculate(
            trades=trades,
            starting_cvd=0.0,
            swing_window=self.cvd_swing_window,
        )

        # ========================================================
        # TIME-BUCKETED CVD
        # ========================================================

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

        # ========================================================
        # HISTORICAL VWAP
        # ========================================================

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

        # ========================================================
        # VOLUME PROFILE
        # ========================================================

        profile = (
            self.volume_profile.calculate(
                trades=trades,
                bins=self.volume_profile_bins,
                value_area_pct=self.value_area_pct,
                current_price=last_price,
            )
        )

        # ========================================================
        # ORDER FLOW
        # ========================================================

        (
            buy_volume,
            sell_volume,
            delta,
            delta_pct,
            buy_ratio,
            sell_ratio,
            average_trade_size,
            large_trade_buy_volume,
            large_trade_sell_volume,
            large_trade_imbalance,
            order_flow_aggression,
            order_flow_strength,
        ) = self._calculate_order_flow(
            trades=trades
        )

        # ========================================================
        # SESSION ENGINE
        # ========================================================

        session = (
            self.session_engine.analyze(
                timestamp=int(
                    timestamp
                ),
                trade_count=len(
                    trades
                ),
                order_flow_strength=(
                    order_flow_strength
                ),
                cvd_strength=(
                    cvd_strength.overall_strength
                ),
                liquidity_ratio=(
                    self._liquidity_activity_ratio(
                        buy_volume=buy_volume,
                        sell_volume=sell_volume,
                    )
                ),
            )
        )

        # ========================================================
        # FINAL HISTORICAL CONTEXT
        # ========================================================

        return HistoricalContext(
            symbol=normalized_symbol,
            timestamp=int(timestamp),

            trade_count=len(
                trades
            ),

            lookback_seconds=int(
                lookback_seconds
            ),

            # ----------------------------------------------------
            # CVD
            # ----------------------------------------------------

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

            # ----------------------------------------------------
            # VWAP
            # ----------------------------------------------------

            vwap=vwap,

            previous_vwap=(
                previous_vwap
            ),

            vwap_position=(
                vwap_position
            ),

            vwap_distance_pct=(
                vwap_distance_pct
            ),

            vwap_slope=(
                vwap_slope
            ),

            # ----------------------------------------------------
            # Volume Profile
            # ----------------------------------------------------

            poc=profile.poc,
            vah=profile.vah,
            val=profile.val,

            profile_position=(
                profile.position
            ),

            # ----------------------------------------------------
            # Order Flow
            # ----------------------------------------------------

            buy_volume=(
                buy_volume
            ),

            sell_volume=(
                sell_volume
            ),

            delta=(
                delta
            ),

            delta_pct=(
                delta_pct
            ),

            buy_ratio=(
                buy_ratio
            ),

            sell_ratio=(
                sell_ratio
            ),

            average_trade_size=(
                average_trade_size
            ),

            large_trade_buy_volume=(
                large_trade_buy_volume
            ),

            large_trade_sell_volume=(
                large_trade_sell_volume
            ),

            large_trade_imbalance=(
                large_trade_imbalance
            ),

            order_flow_aggression=(
                order_flow_aggression
            ),

            order_flow_strength=(
                order_flow_strength
            ),

            # ----------------------------------------------------
            # Session
            # ----------------------------------------------------

            session_name=(
                session.name
            ),

            session_quality=(
                session.quality
            ),

            session_is_overlap=(
                session.is_overlap
            ),

            # ----------------------------------------------------
            # Historical marker
            # ----------------------------------------------------

            historical=True,
        )

    # ============================================================
    # ORDER FLOW
    # ============================================================

    def _calculate_order_flow(
        self,
        trades,
    ) -> tuple[
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        str,
        float,
    ]:
        """
        Calculate executed-trade order flow.

        Buy/sell volume comes directly from Trade.side.

        Returns:

            buy_volume
            sell_volume
            delta
            delta_pct
            buy_ratio
            sell_ratio
            average_trade_size
            large_trade_buy_volume
            large_trade_sell_volume
            large_trade_imbalance
            order_flow_aggression
            order_flow_strength
        """

        if not trades:
            return (
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                "NEUTRAL",
                0.0,
            )

        buy_volume = 0.0
        sell_volume = 0.0

        volumes: list[float] = []

        for trade in trades:

            volume = max(
                0.0,
                float(
                    trade.volume
                ),
            )

            volumes.append(
                volume
            )

            side = (
                str(
                    trade.side
                )
                .strip()
                .lower()
            )

            if side == "buy":

                buy_volume += volume

            elif side == "sell":

                sell_volume += volume

        total_volume = (
            buy_volume
            + sell_volume
        )

        average_trade_size = (
            total_volume
            / len(volumes)
            if volumes
            else 0.0
        )

        delta = (
            buy_volume
            - sell_volume
        )

        delta_pct = (
            delta
            / total_volume
            * 100.0
            if total_volume > 0
            else 0.0
        )

        buy_ratio = (
            buy_volume
            / total_volume
            if total_volume > 0
            else 0.0
        )

        sell_ratio = (
            sell_volume
            / total_volume
            if total_volume > 0
            else 0.0
        )

        # ========================================================
        # LARGE TRADES
        # ========================================================

        large_threshold = (
            average_trade_size
            * self.large_trade_multiplier
        )

        large_trade_buy_volume = 0.0
        large_trade_sell_volume = 0.0

        if large_threshold > 0:

            for trade in trades:

                volume = max(
                    0.0,
                    float(
                        trade.volume
                    ),
                )

                if (
                    volume
                    < large_threshold
                ):
                    continue

                side = (
                    str(
                        trade.side
                    )
                    .strip()
                    .lower()
                )

                if side == "buy":

                    large_trade_buy_volume += (
                        volume
                    )

                elif side == "sell":

                    large_trade_sell_volume += (
                        volume
                    )

        large_total = (
            large_trade_buy_volume
            + large_trade_sell_volume
        )

        large_trade_imbalance = (
            (
                large_trade_buy_volume
                - large_trade_sell_volume
            )
            / large_total
            if large_total > 0
            else 0.0
        )

        # ========================================================
        # ORDER FLOW DIRECTION
        # ========================================================

        if delta_pct >= 15.0:

            order_flow_aggression = (
                "BULLISH"
            )

        elif delta_pct <= -15.0:

            order_flow_aggression = (
                "BEARISH"
            )

        else:

            order_flow_aggression = (
                "NEUTRAL"
            )

        order_flow_strength = min(
            100.0,
            abs(
                delta_pct
            ),
        )

        return (
            buy_volume,
            sell_volume,
            delta,
            delta_pct,
            buy_ratio,
            sell_ratio,
            average_trade_size,
            large_trade_buy_volume,
            large_trade_sell_volume,
            large_trade_imbalance,
            order_flow_aggression,
            order_flow_strength,
        )

    # ============================================================
    # LIQUIDITY ACTIVITY RATIO
    # ============================================================

    @staticmethod
    def _liquidity_activity_ratio(
        buy_volume: float,
        sell_volume: float,
    ) -> float:
        """
        Return a bounded activity/balance ratio.

        This is deliberately different from directional delta.

        A balanced market receives a higher liquidity-quality
        contribution than a one-sided market of the same volume.

        Result:

            0.0 <= value <= 1.0
        """

        buy = max(
            0.0,
            float(
                buy_volume
            ),
        )

        sell = max(
            0.0,
            float(
                sell_volume
            ),
        )

        total = (
            buy
            + sell
        )

        if total <= 0:
            return 0.0

        balance = (
            1.0
            - abs(
                buy
                - sell
            )
            / total
        )

        activity = min(
            1.0,
            total
            / 1_000_000.0,
        )

        return max(
            0.0,
            min(
                1.0,
                balance * 0.7
                + activity * 0.3,
            ),
        )

    # ============================================================
    # TIMESTAMP
    # ============================================================

    def _detect_timestamp_scale(
        self,
        symbol: str,
    ) -> int:
        """
        Detect timestamp unit stored in TradeStore.

        Returns:

            1    -> seconds
            1000 -> milliseconds
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

    # ============================================================
    # VWAP
    # ============================================================

    @staticmethod
    def _calculate_vwap(
        trades,
    ) -> float | None:
        """
        Calculate historical volume-weighted average price.
        """

        total_volume = sum(
            float(
                trade.volume
            )
            for trade in trades
        )

        if total_volume <= 0:
            return None

        weighted_value = sum(
            float(
                trade.price
            )
            * float(
                trade.volume
            )
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
        Calculate VWAP for the previous historical slice.
        """

        if len(trades) < 2:
            return None

        latest_timestamp = int(
            trades[-1].timestamp
        )

        lookback_units = (
            int(
                lookback_seconds
            )
            * int(
                timestamp_scale
            )
        )

        cutoff = (
            latest_timestamp
            - lookback_units
        )

        previous = [
            trade
            for trade in trades
            if int(
                trade.timestamp
            )
            < cutoff
        ]

        if not previous:
            return None

        return (
            HistoricalContextEngine
            ._calculate_vwap(
                previous
            )
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
                price
                - vwap
            )
            / abs(vwap)
            * 100.0
        )

    # ============================================================
    # LEGACY SESSION HELPERS
    # ============================================================

    @staticmethod
    def _session_name(
        timestamp: int,
    ) -> str:
        """
        Backward-compatible session resolver.

        New code should use SessionEngine.
        """

        dt = datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc,
        )

        hour = dt.hour

        if 0 <= hour < 8:
            return "ASIA"

        if 8 <= hour < 13:
            return "LONDON"

        if 13 <= hour < 17:
            return "LONDON_NY_OVERLAP"

        if 17 <= hour < 21:
            return "NEW_YORK"

        return "OFF_HOURS"

    @staticmethod
    def _session_quality(
        session_name: str,
        trade_count: int,
        order_flow_strength: float,
    ) -> float:
        """
        Backward-compatible wrapper around SessionEngine.

        New code should use SessionEngine.analyze().
        """

        # Convert name into a representative UTC timestamp.
        representative_hour = {
            "ASIA": 4,
            "LONDON": 10,
            "LONDON_NY_OVERLAP": 14,
            "NEW_YORK": 18,
            "OFF_HOURS": 22,
        }.get(
            str(
                session_name
            ).strip().upper(),
            22,
        )

        representative_timestamp = (
            representative_hour
            * 60
            * 60
        )

        result = (
            SessionEngine.analyze(
                timestamp=representative_timestamp,
                trade_count=trade_count,
                order_flow_strength=(
                    order_flow_strength
                ),
                cvd_strength=(
                    order_flow_strength
                ),
                liquidity_ratio=0.5,
            )
        )

        return result.quality
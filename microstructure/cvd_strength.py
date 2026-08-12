from __future__ import annotations

from models.cvd_bucket import CVDBucket
from models.cvd_bucket_analysis import BucketedCVDAnalysis
from models.cvd_strength import CVDStrengthResult


class CVDStrengthAnalyzer:
    """
    Analyze the quality and strength of time-bucketed CVD.

    This component does not produce trading signals.

    It produces normalized market-flow context that can later
    be combined with VWAP, L2, Footprint and Volume Profile.
    """

    def analyze(
        self,
        buckets: list[CVDBucket],
        analysis: BucketedCVDAnalysis | None = None,
        lookback: int = 5,
    ) -> CVDStrengthResult:
        """
        Calculate normalized CVD strength.

        Parameters
        ----------
        buckets:
            Time-bucketed CVD data.

        analysis:
            Optional bucketed CVD swing/divergence analysis.

        lookback:
            Number of latest buckets used for short-term flow
            and participation calculations.
        """

        if lookback <= 0:
            raise ValueError(
                "Lookback must be greater than zero."
            )

        if not buckets:
            return CVDStrengthResult(
                flow_strength=0.0,
                momentum_strength=0.0,
                divergence_strength=0.0,
                participation_strength=0.0,
                overall_strength=0.0,
                direction="NEUTRAL",
                divergence="NONE",
                recent_delta=0.0,
                recent_cvd_change=0.0,
                recent_volume=0.0,
                recent_trade_count=0,
            )

        recent = buckets[-lookback:]

        recent_delta = sum(
            bucket.delta
            for bucket in recent
        )

        recent_buy_volume = sum(
            bucket.buy_volume
            for bucket in recent
        )

        recent_sell_volume = sum(
            bucket.sell_volume
            for bucket in recent
        )

        recent_volume = (
            recent_buy_volume
            + recent_sell_volume
        )

        recent_trade_count = sum(
            bucket.trade_count
            for bucket in recent
        )

        previous_cvd = (
            recent[0].cumulative_delta
            - recent[0].delta
        )

        latest_cvd = recent[-1].cumulative_delta

        recent_cvd_change = (
            latest_cvd
            - previous_cvd
        )

        flow_strength = self._flow_strength(
            buy_volume=recent_buy_volume,
            sell_volume=recent_sell_volume,
        )

        momentum_strength = self._momentum_strength(
            buckets=recent,
            recent_cvd_change=recent_cvd_change,
        )

        participation_strength = (
            self._participation_strength(
                buckets=recent,
            )
        )

        divergence = (
            analysis.latest_signal
            if analysis is not None
            else "NONE"
        )

        divergence_strength = (
            self._divergence_strength(
                analysis=analysis,
            )
        )

        overall_strength = self._overall_strength(
            flow_strength=flow_strength,
            momentum_strength=momentum_strength,
            divergence_strength=divergence_strength,
            participation_strength=participation_strength,
        )

        direction = self._direction(
            recent_delta=recent_delta,
            recent_cvd_change=recent_cvd_change,
        )

        return CVDStrengthResult(
            flow_strength=round(
                flow_strength,
                2,
            ),
            momentum_strength=round(
                momentum_strength,
                2,
            ),
            divergence_strength=round(
                divergence_strength,
                2,
            ),
            participation_strength=round(
                participation_strength,
                2,
            ),
            overall_strength=round(
                overall_strength,
                2,
            ),
            direction=direction,
            divergence=divergence,
            recent_delta=round(
                recent_delta,
                8,
            ),
            recent_cvd_change=round(
                recent_cvd_change,
                8,
            ),
            recent_volume=round(
                recent_volume,
                8,
            ),
            recent_trade_count=recent_trade_count,
        )

    @staticmethod
    def _flow_strength(
        buy_volume: float,
        sell_volume: float,
    ) -> float:
        """
        Normalize directional volume imbalance.

        0:
            Perfectly balanced buy/sell volume.

        100:
            Only one side is present.
        """

        total = (
            buy_volume
            + sell_volume
        )

        if total == 0:
            return 0.0

        imbalance = abs(
            buy_volume - sell_volume
        ) / total

        return imbalance * 100.0

    @staticmethod
    def _momentum_strength(
        buckets: list[CVDBucket],
        recent_cvd_change: float,
    ) -> float:
        """
        Measure consistency of CVD movement.

        Uses absolute cumulative delta change relative to the
        sum of absolute bucket deltas.

        A value close to 100 means the recent flow was strongly
        directional with little cancellation.
        """

        if not buckets:
            return 0.0

        absolute_delta_sum = sum(
            abs(bucket.delta)
            for bucket in buckets
        )

        if absolute_delta_sum == 0:
            return 0.0

        strength = (
            abs(recent_cvd_change)
            / absolute_delta_sum
            * 100.0
        )

        return min(
            max(strength, 0.0),
            100.0,
        )

    @staticmethod
    def _participation_strength(
        buckets: list[CVDBucket],
    ) -> float:
        """
        Measure participation consistency.

        The metric is based on how many buckets contain trades.

        100:
            Every bucket contains trades.

        Lower values:
            More empty/inactive buckets.
        """

        if not buckets:
            return 0.0

        active_buckets = sum(
            1
            for bucket in buckets
            if bucket.trade_count > 0
        )

        return (
            active_buckets
            / len(buckets)
            * 100.0
        )

    @staticmethod
    def _divergence_strength(
        analysis: BucketedCVDAnalysis | None,
    ) -> float:
        """
        Normalize the latest divergence magnitude.

        A divergence is stronger when both price displacement
        and CVD displacement are larger.

        The magnitude is normalized without assigning a fixed
        trading weight to divergence.
        """

        if analysis is None:
            return 0.0

        if not analysis.divergences:
            return 0.0

        latest = analysis.divergences[-1]

        price_component = min(
            abs(latest.price_change_pct)
            / 2.0
            * 100.0,
            100.0,
        )

        cvd_component = min(
            abs(latest.cvd_change),
            100.0,
        )

        return (
            price_component
            + cvd_component
        ) / 2.0

    @staticmethod
    def _overall_strength(
        flow_strength: float,
        momentum_strength: float,
        divergence_strength: float,
        participation_strength: float,
    ) -> float:
        """
        Combine component strengths using an equal-weight mean.

        Equal weighting keeps the first version transparent and
        avoids embedding arbitrary trading preferences into the
        CVD engine.
        """

        return (
            flow_strength
            + momentum_strength
            + divergence_strength
            + participation_strength
        ) / 4.0

    @staticmethod
    def _direction(
        recent_delta: float,
        recent_cvd_change: float,
    ) -> str:
        """
        Determine directional CVD flow.
        """

        if (
            recent_delta > 0
            and recent_cvd_change > 0
        ):
            return "BULLISH"

        if (
            recent_delta < 0
            and recent_cvd_change < 0
        ):
            return "BEARISH"

        return "NEUTRAL"
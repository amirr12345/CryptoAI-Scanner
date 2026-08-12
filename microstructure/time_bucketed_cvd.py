from __future__ import annotations

from models.cvd_bucket import CVDBucket
from models.trade import Trade


class TimeBucketedCVDEngine:
    """
    Aggregate normalized trades into fixed time buckets and
    calculate cumulative volume delta.

    The engine is provider-agnostic.
    """

    def calculate(
        self,
        trades: list[Trade],
        interval_seconds: int = 60,
        starting_cvd: float = 0.0,
    ) -> list[CVDBucket]:
        """
        Aggregate trades into fixed time buckets.

        Parameters
        ----------
        trades:
            Executed trades.

        interval_seconds:
            Bucket size in seconds.

        starting_cvd:
            CVD value immediately before the first bucket.
        """

        if interval_seconds <= 0:
            raise ValueError(
                "Interval must be greater than zero."
            )

        if not trades:
            return []

        ordered_trades = sorted(
            trades,
            key=lambda trade: trade.timestamp,
        )

        buckets: dict[int, list[Trade]] = {}

        for trade in ordered_trades:
            timestamp_seconds = self._normalize_timestamp(
                trade.timestamp
            )

            bucket_start = (
                timestamp_seconds
                // interval_seconds
            ) * interval_seconds

            buckets.setdefault(
                bucket_start,
                [],
            ).append(trade)

        results: list[CVDBucket] = []

        cumulative_delta = starting_cvd

        for bucket_start in sorted(buckets):
            bucket_trades = buckets[bucket_start]

            buy_volume = 0.0
            sell_volume = 0.0

            for trade in bucket_trades:
                side = trade.side.strip().lower()

                if side == "buy":
                    buy_volume += trade.volume

                elif side == "sell":
                    sell_volume += trade.volume

                else:
                    raise ValueError(
                        "Trade side must be 'buy' or 'sell'."
                    )

            delta = (
                buy_volume
                - sell_volume
            )

            cumulative_delta += delta

            bucket_end = (
                bucket_start
                + interval_seconds
            )

            results.append(
                CVDBucket(
                    start_timestamp=bucket_start,
                    end_timestamp=bucket_end,
                    open_price=bucket_trades[0].price,
                    close_price=bucket_trades[-1].price,
                    buy_volume=round(
                        buy_volume,
                        8,
                    ),
                    sell_volume=round(
                        sell_volume,
                        8,
                    ),
                    delta=round(
                        delta,
                        8,
                    ),
                    cumulative_delta=round(
                        cumulative_delta,
                        8,
                    ),
                    trade_count=len(
                        bucket_trades
                    ),
                )
            )

        return results

    @staticmethod
    def _normalize_timestamp(
        timestamp: int,
    ) -> int:
        """
        Normalize Unix timestamps to seconds.

        Supports both:
            seconds
            milliseconds
            microseconds
        """

        value = int(timestamp)

        if value >= 10**15:
            return value // 1_000_000

        if value >= 10**12:
            return value // 1_000

        return value
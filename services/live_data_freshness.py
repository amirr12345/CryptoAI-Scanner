from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(slots=True, frozen=True)
class DataFreshnessResult:
    """
    Result of live market-data freshness validation.
    """

    latest_candle_timestamp: int
    latest_trade_timestamp: int | None
    candle_lag_seconds: int
    max_allowed_lag_seconds: int
    fresh: bool
    status: str


class LiveDataFreshness:
    """
    Validate candle freshness against the latest live trade.

    Candle timestamps are stored in seconds.

    Trade timestamps may be stored in seconds or milliseconds.
    """

    TIMESTAMP_MILLISECOND_THRESHOLD = 100_000_000_000

    def __init__(
        self,
        max_candle_lag_seconds: int = 300,
        clock=time.time,
    ) -> None:
        if max_candle_lag_seconds <= 0:
            raise ValueError(
                "max_candle_lag_seconds must be greater than zero."
            )

        self.max_candle_lag_seconds = int(
            max_candle_lag_seconds
        )
        self.clock = clock

    def check(
        self,
        latest_candle_timestamp: int,
        latest_trade_timestamp: int | None = None,
    ) -> DataFreshnessResult:
        """
        Check whether the latest candle is fresh.
        """

        if latest_candle_timestamp <= 0:
            raise ValueError(
                "latest_candle_timestamp must be greater than zero."
            )

        if latest_trade_timestamp is not None:
            trade_timestamp_seconds = (
                self._normalize_trade_timestamp(
                    latest_trade_timestamp
                )
            )

            reference_timestamp = (
                trade_timestamp_seconds
            )
        else:
            reference_timestamp = int(
                self.clock()
            )

        lag_seconds = max(
            0,
            reference_timestamp
            - int(latest_candle_timestamp),
        )

        fresh = (
            lag_seconds
            <= self.max_candle_lag_seconds
        )

        return DataFreshnessResult(
            latest_candle_timestamp=int(
                latest_candle_timestamp
            ),
            latest_trade_timestamp=(
                int(latest_trade_timestamp)
                if latest_trade_timestamp is not None
                else None
            ),
            candle_lag_seconds=lag_seconds,
            max_allowed_lag_seconds=(
                self.max_candle_lag_seconds
            ),
            fresh=fresh,
            status=(
                "FRESH"
                if fresh
                else "STALE_CANDLES"
            ),
        )

    @classmethod
    def _normalize_trade_timestamp(
        cls,
        timestamp: int,
    ) -> int:
        """
        Normalize trade timestamp to seconds.

        Real project timestamps are typically around
        1.7e12 when expressed in milliseconds.
        """

        timestamp = int(timestamp)

        if (
            timestamp
            >= cls.TIMESTAMP_MILLISECOND_THRESHOLD
        ):
            return timestamp // 1000

        return timestamp
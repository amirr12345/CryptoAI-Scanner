from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(slots=True, frozen=True)
class DataFreshnessResult:
    latest_candle_timestamp: int
    latest_trade_timestamp: int | None
    candle_lag_seconds: int
    max_allowed_lag_seconds: int
    fresh: bool
    status: str


class LiveDataFreshness:
    """
    Validate freshness for LIVE market data.

    Modes:
        LIVE
            Freshness is enforced.

        REST_BOOTSTRAP
            Freshness is not enforced. Historical REST candles
            are valid for structure/bootstrap analysis even when
            they are older than the live freshness threshold.
    """

    TIMESTAMP_MILLISECOND_THRESHOLD = 100_000_000_000

    LIVE = "LIVE"
    REST_BOOTSTRAP = "REST_BOOTSTRAP"

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
        mode: str = LIVE,
    ) -> DataFreshnessResult:
        """
        Check candle freshness.

        LIVE:
            Candle lag is enforced.

        REST_BOOTSTRAP:
            Candle is accepted regardless of age.
        """

        if latest_candle_timestamp <= 0:
            raise ValueError(
                "latest_candle_timestamp must be greater than zero."
            )

        normalized_mode = (
            str(mode)
            .strip()
            .upper()
        )

        if normalized_mode not in {
            self.LIVE,
            self.REST_BOOTSTRAP,
        }:
            raise ValueError(
                "mode must be LIVE or REST_BOOTSTRAP."
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

        if (
            normalized_mode
            == self.REST_BOOTSTRAP
        ):
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
                fresh=True,
                status="REST_BOOTSTRAP",
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
        timestamp = int(timestamp)

        if (
            timestamp
            >= cls.TIMESTAMP_MILLISECOND_THRESHOLD
        ):
            return timestamp // 1000

        return timestamp
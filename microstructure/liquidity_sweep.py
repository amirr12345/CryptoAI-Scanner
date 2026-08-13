from __future__ import annotations

from models.liquidity_sweep import LiquiditySweep
from models.liquidity_sweep_result import LiquiditySweepResult
from models.market_structure import (
    MarketStructureResult,
    MarketSwing,
)


class LiquiditySweepEngine:
    """
    Detect liquidity sweeps from confirmed market-structure swings.

    Bullish sweep:
        Price trades below a confirmed swing low and then
        closes back above that level.

    Bearish sweep:
        Price trades above a confirmed swing high and then
        closes back below that level.

    A swing can only be used after its confirmation_index.
    """

    def calculate(
        self,
        candles,
        structure: MarketStructureResult,
    ) -> LiquiditySweepResult:
        """
        Detect confirmed liquidity sweeps chronologically.
        """

        if not candles or not structure.swings:
            return LiquiditySweepResult()

        swings = sorted(
            structure.swings,
            key=lambda item: (
                item.confirmation_index,
                item.index,
                0 if item.kind == "HIGH" else 1,
            ),
        )

        swept_highs: set[int] = set()
        swept_lows: set[int] = set()

        events: list[LiquiditySweep] = []

        for candle_index, candle in enumerate(candles):
            confirmed_swings = [
                swing
                for swing in swings
                if swing.confirmation_index
                <= candle_index
            ]

            if not confirmed_swings:
                continue

            latest_high = self._latest_un_swept(
                confirmed_swings,
                "HIGH",
                swept_highs,
            )

            latest_low = self._latest_un_swept(
                confirmed_swings,
                "LOW",
                swept_lows,
            )

            candle_high = float(candle.high)
            candle_low = float(candle.low)
            candle_close = float(candle.close)

            timestamp = int(candle.timestamp)

            # -------------------------------------------------
            # Bearish liquidity sweep
            #
            # Buy-side liquidity:
            # candle high takes the confirmed swing high
            # and candle closes back below that level.
            # -------------------------------------------------
            if (
                latest_high is not None
                and latest_high.index not in swept_highs
                and candle_high > latest_high.price
                and candle_close < latest_high.price
            ):
                event = self._create_sweep(
                    candle_index=candle_index,
                    timestamp=timestamp,
                    event="BEARISH_LIQUIDITY_SWEEP",
                    direction="BEARISH",
                    level=latest_high,
                    candle_high=candle_high,
                    candle_low=candle_low,
                    candle_close=candle_close,
                )

                events.append(event)

                swept_highs.add(
                    latest_high.index
                )

                continue

            # -------------------------------------------------
            # Bullish liquidity sweep
            #
            # Sell-side liquidity:
            # candle low takes the confirmed swing low
            # and candle closes back above that level.
            # -------------------------------------------------
            if (
                latest_low is not None
                and latest_low.index not in swept_lows
                and candle_low < latest_low.price
                and candle_close > latest_low.price
            ):
                event = self._create_sweep(
                    candle_index=candle_index,
                    timestamp=timestamp,
                    event="BULLISH_LIQUIDITY_SWEEP",
                    direction="BULLISH",
                    level=latest_low,
                    candle_high=candle_high,
                    candle_low=candle_low,
                    candle_close=candle_close,
                )

                events.append(event)

                swept_lows.add(
                    latest_low.index
                )

        return self._build_result(events)

    @staticmethod
    def _latest_un_swept(
        swings: list[MarketSwing],
        kind: str,
        swept_indexes: set[int],
    ) -> MarketSwing | None:
        """
        Return the latest confirmed swing of the requested kind
        that has not already been swept.
        """

        candidates = [
            swing
            for swing in swings
            if (
                swing.kind == kind
                and swing.index not in swept_indexes
            )
        ]

        if not candidates:
            return None

        return candidates[-1]

    @staticmethod
    def _create_sweep(
        candle_index: int,
        timestamp: int,
        event: str,
        direction: str,
        level: MarketSwing,
        candle_high: float,
        candle_low: float,
        candle_close: float,
    ) -> LiquiditySweep:
        """
        Create immutable liquidity-sweep result.
        """

        if direction == "BULLISH":
            excursion = (
                level.price
                - candle_low
            )

            rejection = (
                candle_close
                - candle_low
            )

        else:
            excursion = (
                candle_high
                - level.price
            )

            rejection = (
                candle_high
                - candle_close
            )

        if level.price == 0:
            excursion_pct = 0.0
            rejection_pct = 0.0
        else:
            excursion_pct = (
                excursion
                / abs(level.price)
                * 100.0
            )

            rejection_pct = (
                rejection
                / abs(level.price)
                * 100.0
            )

        return LiquiditySweep(
            index=candle_index,
            timestamp=timestamp,
            event=event,
            direction=direction,
            level_index=level.index,
            level_price=level.price,
            level_kind=level.kind,
            candle_high=candle_high,
            candle_low=candle_low,
            candle_close=candle_close,
            excursion=round(
                excursion,
                8,
            ),
            excursion_pct=round(
                excursion_pct,
                6,
            ),
            rejection=round(
                rejection,
                8,
            ),
            rejection_pct=round(
                rejection_pct,
                6,
            ),
        )

    @staticmethod
    def _build_result(
        events: list[LiquiditySweep],
    ) -> LiquiditySweepResult:
        """
        Aggregate liquidity-sweep events.
        """

        if not events:
            return LiquiditySweepResult()

        bullish_count = sum(
            1
            for event in events
            if event.direction == "BULLISH"
        )

        bearish_count = sum(
            1
            for event in events
            if event.direction == "BEARISH"
        )

        latest = events[-1]

        return LiquiditySweepResult(
            events=events,
            latest_event=latest.event,
            latest_direction=latest.direction,
            bullish_sweep_count=bullish_count,
            bearish_sweep_count=bearish_count,
        )
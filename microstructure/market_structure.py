from __future__ import annotations

from models.market_structure import (
    MarketStructureResult,
    MarketSwing,
)


class MarketStructureEngine:
    """
    Detect swing highs/lows and classify market structure.

    A swing at index i with window N becomes confirmed at:

        confirmation_index = i + N

    The confirmation index is required to prevent
    look-ahead bias in downstream analysis.
    """

    def calculate(
        self,
        candles,
        swing_window: int = 2,
    ) -> MarketStructureResult:

        if swing_window < 1:
            raise ValueError(
                "Swing window must be greater than zero."
            )

        if not candles:
            return MarketStructureResult(
                swings=[],
                latest_high=None,
                previous_high=None,
                latest_low=None,
                previous_low=None,
                structure="NEUTRAL",
            )

        minimum_length = (
            swing_window * 2 + 1
        )

        if len(candles) < minimum_length:
            return MarketStructureResult(
                swings=[],
                latest_high=None,
                previous_high=None,
                latest_low=None,
                previous_low=None,
                structure="NEUTRAL",
            )

        raw_swings: list[MarketSwing] = []

        last_candidate_index = (
            len(candles)
            - swing_window
            - 1
        )

        for index in range(
            swing_window,
            last_candidate_index + 1,
        ):
            current = candles[index]

            left = candles[
                index - swing_window:index
            ]

            right = candles[
                index + 1:index + swing_window + 1
            ]

            surrounding = left + right

            is_high = all(
                current.high > candle.high
                for candle in surrounding
            )

            is_low = all(
                current.low < candle.low
                for candle in surrounding
            )

            confirmation_index = (
                index + swing_window
            )

            if is_high:
                raw_swings.append(
                    MarketSwing(
                        index=index,
                        timestamp=int(
                            current.timestamp
                        ),
                        price=float(
                            current.high
                        ),
                        kind="HIGH",
                        label="SWING_HIGH",
                        confirmation_index=(
                            confirmation_index
                        ),
                    )
                )

            if is_low:
                raw_swings.append(
                    MarketSwing(
                        index=index,
                        timestamp=int(
                            current.timestamp
                        ),
                        price=float(
                            current.low
                        ),
                        kind="LOW",
                        label="SWING_LOW",
                        confirmation_index=(
                            confirmation_index
                        ),
                    )
                )

        swings = self._classify_swings(
            raw_swings
        )

        high_swings = [
            swing
            for swing in swings
            if swing.kind == "HIGH"
        ]

        low_swings = [
            swing
            for swing in swings
            if swing.kind == "LOW"
        ]

        latest_high = (
            high_swings[-1]
            if high_swings
            else None
        )

        previous_high = (
            high_swings[-2]
            if len(high_swings) >= 2
            else None
        )

        latest_low = (
            low_swings[-1]
            if low_swings
            else None
        )

        previous_low = (
            low_swings[-2]
            if len(low_swings) >= 2
            else None
        )

        structure = self._detect_structure(
            previous_high=previous_high,
            latest_high=latest_high,
            previous_low=previous_low,
            latest_low=latest_low,
        )

        return MarketStructureResult(
            swings=swings,
            latest_high=latest_high,
            previous_high=previous_high,
            latest_low=latest_low,
            previous_low=previous_low,
            structure=structure,
        )

    @staticmethod
    def _classify_swings(
        swings: list[MarketSwing],
    ) -> list[MarketSwing]:

        if not swings:
            return []

        classified: list[MarketSwing] = []

        previous_high: MarketSwing | None = None
        previous_low: MarketSwing | None = None

        # Sort chronologically so classification never depends
        # on input ordering.
        ordered_swings = sorted(
            swings,
            key=lambda swing: (
                swing.index,
                0 if swing.kind == "HIGH" else 1,
            ),
        )

        for swing in ordered_swings:
            label = swing.label

            if swing.kind == "HIGH":
                if previous_high is None:
                    label = "SWING_HIGH"
                elif swing.price > previous_high.price:
                    label = "HH"
                elif swing.price < previous_high.price:
                    label = "LH"

                previous_high = swing

            elif swing.kind == "LOW":
                if previous_low is None:
                    label = "SWING_LOW"
                elif swing.price > previous_low.price:
                    label = "HL"
                elif swing.price < previous_low.price:
                    label = "LL"

                previous_low = swing

            classified.append(
                MarketSwing(
                    index=swing.index,
                    timestamp=swing.timestamp,
                    price=swing.price,
                    kind=swing.kind,
                    label=label,
                    confirmation_index=(
                        swing.confirmation_index
                    ),
                )
            )

        return classified

    @staticmethod
    def _detect_structure(
        previous_high: MarketSwing | None,
        latest_high: MarketSwing | None,
        previous_low: MarketSwing | None,
        latest_low: MarketSwing | None,
    ) -> str:

        if (
            previous_high is None
            or latest_high is None
            or previous_low is None
            or latest_low is None
        ):
            return "NEUTRAL"

        higher_high = (
            latest_high.price
            > previous_high.price
        )

        lower_high = (
            latest_high.price
            < previous_high.price
        )

        higher_low = (
            latest_low.price
            > previous_low.price
        )

        lower_low = (
            latest_low.price
            < previous_low.price
        )

        if higher_high and higher_low:
            return "BULLISH"

        if lower_high and lower_low:
            return "BEARISH"

        if (
            higher_high and lower_low
        ) or (
            lower_high and higher_low
        ):
            return "MIXED"

        return "NEUTRAL"
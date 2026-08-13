from __future__ import annotations

from models.market_structure import (
    MarketStructureResult,
    MarketSwing,
)
from models.structure_break import StructureBreak
from models.structure_break_result import StructureBreakResult


class StructureBreakEngine:
    """
    Chronological BOS / CHoCH / MSS engine.

    A swing becomes eligible for a break only after its
    confirmation_index has been reached.

    This prevents using future information before it is
    actually available.
    """

    def calculate(
        self,
        candles,
        structure: MarketStructureResult,
        displacement_pct: float = 0.15,
    ) -> StructureBreakResult:

        if displacement_pct < 0:
            raise ValueError(
                "Displacement percentage cannot be negative."
            )

        if not candles or not structure.swings:
            return StructureBreakResult()

        swings = sorted(
            structure.swings,
            key=lambda swing: (
                swing.confirmation_index,
                swing.index,
                0 if swing.kind == "HIGH" else 1,
            ),
        )

        broken_highs: set[int] = set()
        broken_lows: set[int] = set()

        events: list[StructureBreak] = []

        for candle_index, candle in enumerate(
            candles
        ):
            close_price = float(
                candle.close
            )

            timestamp = int(
                candle.timestamp
            )

            confirmed_swings = [
                swing
                for swing in swings
                if swing.confirmation_index
                <= candle_index
            ]

            if not confirmed_swings:
                continue

            regime = self._structure_at(
                confirmed_swings
            )

            latest_high = self._latest_unbroken(
                confirmed_swings,
                "HIGH",
                broken_highs,
            )

            latest_low = self._latest_unbroken(
                confirmed_swings,
                "LOW",
                broken_lows,
            )

            # -----------------------------------------------
            # BULLISH REGIME
            # -----------------------------------------------

            if (
                regime == "BULLISH"
                and latest_high is not None
                and latest_high.index
                not in broken_highs
                and close_price
                > latest_high.price
            ):
                event = self._create_break(
                    candle_index=candle_index,
                    timestamp=timestamp,
                    close_price=close_price,
                    broken_swing=latest_high,
                    event="BOS",
                    direction="BULLISH",
                )

                events.append(event)

                broken_highs.add(
                    latest_high.index
                )

                continue

            if (
                regime == "BULLISH"
                and latest_low is not None
                and latest_low.index
                not in broken_lows
                and close_price
                < latest_low.price
            ):
                displacement = self._displacement_pct(
                    close_price,
                    latest_low.price,
                )

                event_name = self._reversal_event(
                    displacement,
                    displacement_pct,
                )

                event = self._create_break(
                    candle_index=candle_index,
                    timestamp=timestamp,
                    close_price=close_price,
                    broken_swing=latest_low,
                    event=event_name,
                    direction="BEARISH",
                )

                events.append(event)

                broken_lows.add(
                    latest_low.index
                )

                continue

            # -----------------------------------------------
            # BEARISH REGIME
            # -----------------------------------------------

            if (
                regime == "BEARISH"
                and latest_low is not None
                and latest_low.index
                not in broken_lows
                and close_price
                < latest_low.price
            ):
                event = self._create_break(
                    candle_index=candle_index,
                    timestamp=timestamp,
                    close_price=close_price,
                    broken_swing=latest_low,
                    event="BOS",
                    direction="BEARISH",
                )

                events.append(event)

                broken_lows.add(
                    latest_low.index
                )

                continue

            if (
                regime == "BEARISH"
                and latest_high is not None
                and latest_high.index
                not in broken_highs
                and close_price
                > latest_high.price
            ):
                displacement = self._displacement_pct(
                    close_price,
                    latest_high.price,
                )

                event_name = self._reversal_event(
                    displacement,
                    displacement_pct,
                )

                event = self._create_break(
                    candle_index=candle_index,
                    timestamp=timestamp,
                    close_price=close_price,
                    broken_swing=latest_high,
                    event=event_name,
                    direction="BULLISH",
                )

                events.append(event)

                broken_highs.add(
                    latest_high.index
                )

                continue

            # -----------------------------------------------
            # MIXED / NEUTRAL
            # -----------------------------------------------

            if regime in {
                "MIXED",
                "NEUTRAL",
            }:
                if (
                    latest_high is not None
                    and latest_high.index
                    not in broken_highs
                    and close_price
                    > latest_high.price
                ):
                    event = self._create_break(
                        candle_index=candle_index,
                        timestamp=timestamp,
                        close_price=close_price,
                        broken_swing=latest_high,
                        event="BOS",
                        direction="BULLISH",
                    )

                    events.append(event)

                    broken_highs.add(
                        latest_high.index
                    )

                    continue

                if (
                    latest_low is not None
                    and latest_low.index
                    not in broken_lows
                    and close_price
                    < latest_low.price
                ):
                    event = self._create_break(
                        candle_index=candle_index,
                        timestamp=timestamp,
                        close_price=close_price,
                        broken_swing=latest_low,
                        event="BOS",
                        direction="BEARISH",
                    )

                    events.append(event)

                    broken_lows.add(
                        latest_low.index
                    )

        return self._build_result(
            events
        )

    @staticmethod
    def _structure_at(
        swings: list[MarketSwing],
    ) -> str:

        highs = [
            swing
            for swing in swings
            if swing.kind == "HIGH"
        ]

        lows = [
            swing
            for swing in swings
            if swing.kind == "LOW"
        ]

        if (
            len(highs) < 2
            or len(lows) < 2
        ):
            return "NEUTRAL"

        previous_high = highs[-2]
        latest_high = highs[-1]

        previous_low = lows[-2]
        latest_low = lows[-1]

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
            higher_high
            and lower_low
        ) or (
            lower_high
            and higher_low
        ):
            return "MIXED"

        return "NEUTRAL"

    @staticmethod
    def _latest_unbroken(
        swings: list[MarketSwing],
        kind: str,
        broken_indexes: set[int],
    ) -> MarketSwing | None:

        candidates = [
            swing
            for swing in swings
            if (
                swing.kind == kind
                and swing.index
                not in broken_indexes
            )
        ]

        if not candidates:
            return None

        return candidates[-1]

    @staticmethod
    def _displacement_pct(
        current_price: float,
        broken_price: float,
    ) -> float:

        if broken_price == 0:
            return 0.0

        return (
            abs(
                current_price
                - broken_price
            )
            / abs(broken_price)
            * 100.0
        )

    @staticmethod
    def _reversal_event(
        displacement: float,
        threshold: float,
    ) -> str:

        if displacement >= threshold:
            return "MSS"

        return "CHoCH"

    @staticmethod
    def _create_break(
        candle_index: int,
        timestamp: int,
        close_price: float,
        broken_swing: MarketSwing,
        event: str,
        direction: str,
    ) -> StructureBreak:

        displacement = (
            close_price
            - broken_swing.price
        )

        displacement_percentage = (
            abs(displacement)
            / abs(broken_swing.price)
            * 100.0
            if broken_swing.price != 0
            else 0.0
        )

        return StructureBreak(
            index=candle_index,
            timestamp=timestamp,
            price=close_price,
            event=event,
            direction=direction,
            broken_index=broken_swing.index,
            broken_price=broken_swing.price,
            displacement=round(
                displacement,
                8,
            ),
            displacement_pct=round(
                displacement_percentage,
                6,
            ),
        )

    @staticmethod
    def _build_result(
        events: list[StructureBreak],
    ) -> StructureBreakResult:

        if not events:
            return StructureBreakResult()

        bullish_bos = sum(
            1
            for event in events
            if (
                event.event == "BOS"
                and event.direction == "BULLISH"
            )
        )

        bearish_bos = sum(
            1
            for event in events
            if (
                event.event == "BOS"
                and event.direction == "BEARISH"
            )
        )

        bullish_choch = sum(
            1
            for event in events
            if (
                event.event == "CHoCH"
                and event.direction == "BULLISH"
            )
        )

        bearish_choch = sum(
            1
            for event in events
            if (
                event.event == "CHoCH"
                and event.direction == "BEARISH"
            )
        )

        bullish_mss = sum(
            1
            for event in events
            if (
                event.event == "MSS"
                and event.direction == "BULLISH"
            )
        )

        bearish_mss = sum(
            1
            for event in events
            if (
                event.event == "MSS"
                and event.direction == "BEARISH"
            )
        )

        latest = events[-1]

        return StructureBreakResult(
            events=events,
            latest_event=latest.event,
            latest_direction=latest.direction,
            bullish_bos_count=bullish_bos,
            bearish_bos_count=bearish_bos,
            bullish_choch_count=bullish_choch,
            bearish_choch_count=bearish_choch,
            bullish_mss_count=bullish_mss,
            bearish_mss_count=bearish_mss,
        )
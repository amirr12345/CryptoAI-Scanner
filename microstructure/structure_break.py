from __future__ import annotations

from models.market_structure import MarketStructureResult
from models.structure_break import StructureBreak
from models.structure_break_result import StructureBreakResult


class StructureBreakEngine:
    """
    Detect BOS, CHoCH and MSS from confirmed market swings.

    The engine does not create trading signals.
    """

    def calculate(
        self,
        candles,
        structure: MarketStructureResult,
        displacement_pct: float = 0.15,
    ) -> StructureBreakResult:
        """
        Detect structural breaks.

        Parameters
        ----------
        candles:
            Candle-like objects containing:
                timestamp
                close

        structure:
            Result produced by MarketStructureEngine.

        displacement_pct:
            Minimum percentage displacement required to classify
            a qualifying CHoCH as MSS.

            Example:
                0.15 = 0.15 percent
        """

        if displacement_pct < 0:
            raise ValueError(
                "Displacement percentage cannot be negative."
            )

        if not candles:
            return StructureBreakResult()

        swings = structure.swings

        if not swings:
            return StructureBreakResult()

        events: list[StructureBreak] = []

        # Only confirmed structural swings can be broken.
        #
        # We evaluate each candle after a swing against the
        # latest confirmed opposite swing.
        #
        # To avoid generating the same break repeatedly, each
        # reference swing can only be broken once.

        broken_highs: set[int] = set()
        broken_lows: set[int] = set()

        current_structure = structure.structure

        for index, candle in enumerate(candles):
            close_price = float(candle.close)
            timestamp = int(candle.timestamp)

            high_candidates = [
                swing
                for swing in swings
                if swing.kind == "HIGH"
                and swing.index < index
                and swing.index not in broken_highs
            ]

            low_candidates = [
                swing
                for swing in swings
                if swing.kind == "LOW"
                and swing.index < index
                and swing.index not in broken_lows
            ]

            latest_high = (
                high_candidates[-1]
                if high_candidates
                else None
            )

            latest_low = (
                low_candidates[-1]
                if low_candidates
                else None
            )

            # --------------------------------------------------
            # Bullish break: close above a confirmed swing high
            # --------------------------------------------------
            if (
                latest_high is not None
                and close_price > latest_high.price
            ):
                broken_highs.add(
                    latest_high.index
                )

                displacement = (
                    close_price
                    - latest_high.price
                )

                displacement_pct_value = (
                    displacement
                    / latest_high.price
                    * 100.0
                    if latest_high.price != 0
                    else 0.0
                )

                event = self._classify_break(
                    break_direction="BULLISH",
                    current_structure=current_structure,
                    displacement_pct_value=(
                        displacement_pct_value
                    ),
                    displacement_threshold=(
                        displacement_pct
                    ),
                )

                events.append(
                    StructureBreak(
                        index=index,
                        timestamp=timestamp,
                        price=close_price,
                        event=event,
                        direction="BULLISH",
                        broken_index=latest_high.index,
                        broken_price=latest_high.price,
                        displacement=round(
                            displacement,
                            8,
                        ),
                        displacement_pct=round(
                            displacement_pct_value,
                            6,
                        ),
                    )
                )

                current_structure = (
                    "BULLISH"
                )

            # --------------------------------------------------
            # Bearish break: close below a confirmed swing low
            # --------------------------------------------------
            if (
                latest_low is not None
                and close_price < latest_low.price
            ):
                broken_lows.add(
                    latest_low.index
                )

                displacement = (
                    close_price
                    - latest_low.price
                )

                displacement_pct_value = (
                    abs(displacement)
                    / latest_low.price
                    * 100.0
                    if latest_low.price != 0
                    else 0.0
                )

                event = self._classify_break(
                    break_direction="BEARISH",
                    current_structure=current_structure,
                    displacement_pct_value=(
                        displacement_pct_value
                    ),
                    displacement_threshold=(
                        displacement_pct
                    ),
                )

                events.append(
                    StructureBreak(
                        index=index,
                        timestamp=timestamp,
                        price=close_price,
                        event=event,
                        direction="BEARISH",
                        broken_index=latest_low.index,
                        broken_price=latest_low.price,
                        displacement=round(
                            displacement,
                            8,
                        ),
                        displacement_pct=round(
                            displacement_pct_value,
                            6,
                        ),
                    )
                )

                current_structure = (
                    "BEARISH"
                )

        return self._build_result(events)

    @staticmethod
    def _classify_break(
        break_direction: str,
        current_structure: str,
        displacement_pct_value: float,
        displacement_threshold: float,
    ) -> str:
        """
        Classify one structural break.
        """

        if current_structure == "BULLISH":
            if break_direction == "BULLISH":
                return "BOS"

            if (
                break_direction == "BEARISH"
                and displacement_pct_value
                >= displacement_threshold
            ):
                return "MSS"

            return "CHoCH"

        if current_structure == "BEARISH":
            if break_direction == "BEARISH":
                return "BOS"

            if (
                break_direction == "BULLISH"
                and displacement_pct_value
                >= displacement_threshold
            ):
                return "MSS"

            return "CHoCH"

        # Neutral or mixed structure:
        # first directional structural break is treated as BOS
        # rather than CHoCH because no prior directional regime
        # exists.
        return "BOS"

    @staticmethod
    def _build_result(
        events: list[StructureBreak],
    ) -> StructureBreakResult:
        """
        Aggregate structure-break events.
        """

        if not events:
            return StructureBreakResult()

        bullish_bos = sum(
            1
            for event in events
            if event.event == "BOS"
            and event.direction == "BULLISH"
        )

        bearish_bos = sum(
            1
            for event in events
            if event.event == "BOS"
            and event.direction == "BEARISH"
        )

        bullish_choch = sum(
            1
            for event in events
            if event.event == "CHoCH"
            and event.direction == "BULLISH"
        )

        bearish_choch = sum(
            1
            for event in events
            if event.event == "CHoCH"
            and event.direction == "BEARISH"
        )

        bullish_mss = sum(
            1
            for event in events
            if event.event == "MSS"
            and event.direction == "BULLISH"
        )

        bearish_mss = sum(
            1
            for event in events
            if event.event == "MSS"
            and event.direction == "BEARISH"
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
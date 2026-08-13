from __future__ import annotations

from models.liquidity_sweep import LiquiditySweep
from models.structure_break import StructureBreak
from models.structure_setup import StructureSetup
from models.structure_setup_result import (
    StructureSetupResult,
)


class StructureSetupEngine:
    """
    Combine Liquidity Sweep and MSS into a structure setup.

    Bullish:
        Bullish liquidity sweep
        ->
        Bullish MSS

    Bearish:
        Bearish liquidity sweep
        ->
        Bearish MSS

    The MSS must happen at the same candle or after the sweep,
    but no later than max_bars_after_sweep.

    Only MSS is accepted as the structural confirmation.
    BOS and CHoCH alone do not create a setup.
    """

    def calculate(
        self,
        sweeps: list[LiquiditySweep],
        structure_breaks: list[StructureBreak],
        max_bars_after_sweep: int = 10,
    ) -> StructureSetupResult:
        """
        Build structure setups chronologically.
        """

        if max_bars_after_sweep < 0:
            raise ValueError(
                "Max bars after sweep cannot be negative."
            )

        if not sweeps or not structure_breaks:
            return StructureSetupResult()

        ordered_sweeps = sorted(
            sweeps,
            key=lambda event: event.index,
        )

        ordered_breaks = sorted(
            structure_breaks,
            key=lambda event: event.index,
        )

        setups: list[StructureSetup] = []

        consumed_sweeps: set[int] = set()

        for mss in ordered_breaks:
            if mss.event != "MSS":
                continue

            matching_sweep = self._find_matching_sweep(
                mss=mss,
                sweeps=ordered_sweeps,
                consumed_sweeps=consumed_sweeps,
                max_bars_after_sweep=max_bars_after_sweep,
            )

            if matching_sweep is None:
                continue

            if (
                matching_sweep.direction
                != mss.direction
            ):
                continue

            if mss.direction == "BULLISH":
                setup_name = (
                    "BULLISH_STRUCTURE_SETUP"
                )

            elif mss.direction == "BEARISH":
                setup_name = (
                    "BEARISH_STRUCTURE_SETUP"
                )

            else:
                continue

            bars_between = (
                mss.index
                - matching_sweep.index
            )

            setups.append(
                StructureSetup(
                    index=mss.index,
                    timestamp=mss.timestamp,
                    direction=mss.direction,
                    setup=setup_name,
                    sweep_index=matching_sweep.index,
                    sweep_event=matching_sweep.event,
                    mss_index=mss.index,
                    mss_event=mss.event,
                    level_price=matching_sweep.level_price,
                    sweep_excursion_pct=(
                        matching_sweep.excursion_pct
                    ),
                    mss_displacement_pct=(
                        mss.displacement_pct
                    ),
                    bars_between=bars_between,
                )
            )

            consumed_sweeps.add(
                matching_sweep.index
            )

        return self._build_result(setups)

    @staticmethod
    def _find_matching_sweep(
        mss: StructureBreak,
        sweeps: list[LiquiditySweep],
        consumed_sweeps: set[int],
        max_bars_after_sweep: int,
    ) -> LiquiditySweep | None:
        """
        Find the closest valid sweep preceding the MSS.
        """

        candidates = [
            sweep
            for sweep in sweeps
            if (
                sweep.index <= mss.index
                and sweep.index
                not in consumed_sweeps
                and (
                    mss.index
                    - sweep.index
                ) <= max_bars_after_sweep
                and sweep.direction
                == mss.direction
            )
        ]

        if not candidates:
            return None

        # Closest sweep to the MSS.
        return max(
            candidates,
            key=lambda sweep: sweep.index,
        )

    @staticmethod
    def _build_result(
        setups: list[StructureSetup],
    ) -> StructureSetupResult:
        """
        Aggregate structure setups.
        """

        if not setups:
            return StructureSetupResult()

        bullish_count = sum(
            1
            for setup in setups
            if setup.direction == "BULLISH"
        )

        bearish_count = sum(
            1
            for setup in setups
            if setup.direction == "BEARISH"
        )

        latest = setups[-1]

        return StructureSetupResult(
            setups=setups,
            latest_setup=latest.setup,
            latest_direction=latest.direction,
            bullish_setup_count=bullish_count,
            bearish_setup_count=bearish_count,
        )
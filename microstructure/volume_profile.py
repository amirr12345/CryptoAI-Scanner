from __future__ import annotations

from models.trade import Trade
from models.volume_profile import (
    VolumeProfileLevel,
    VolumeProfileResult,
)


class VolumeProfileEngine:
    """
    Build a volume profile from executed trades.

    The engine is provider-agnostic and consumes normalized
    Trade objects only.
    """

    def calculate(
        self,
        trades: list[Trade],
        bins: int = 24,
        value_area_pct: float = 70.0,
        current_price: float | None = None,
    ) -> VolumeProfileResult:
        """
        Calculate Volume Profile.
        """

        if bins <= 0:
            raise ValueError(
                "Bins must be greater than zero."
            )

        if not (
            0.0 < value_area_pct <= 100.0
        ):
            raise ValueError(
                "Value area percentage must be "
                "greater than zero and less than "
                "or equal to 100."
            )

        if not trades:
            return VolumeProfileResult(
                levels=[],
                poc=None,
                vah=None,
                val=None,
                total_volume=0.0,
                hvn=[],
                lvn=[],
                current_price=current_price,
                position="UNKNOWN",
            )

        prices = [
            float(trade.price)
            for trade in trades
        ]

        volumes = [
            float(trade.volume)
            for trade in trades
        ]

        if any(price < 0 for price in prices):
            raise ValueError(
                "Trade price cannot be negative."
            )

        if any(volume < 0 for volume in volumes):
            raise ValueError(
                "Trade volume cannot be negative."
            )

        minimum_price = min(prices)
        maximum_price = max(prices)

        total_volume = sum(volumes)

        if total_volume == 0.0:
            return VolumeProfileResult(
                levels=[],
                poc=None,
                vah=None,
                val=None,
                total_volume=0.0,
                hvn=[],
                lvn=[],
                current_price=current_price,
                position="UNKNOWN",
            )

        if minimum_price == maximum_price:
            level = VolumeProfileLevel(
                price_low=minimum_price,
                price_high=maximum_price,
                volume=total_volume,
            )

            return VolumeProfileResult(
                levels=[level],
                poc=minimum_price,
                vah=maximum_price,
                val=minimum_price,
                total_volume=total_volume,
                hvn=[minimum_price],
                lvn=[minimum_price],
                current_price=current_price,
                position=self._position(
                    current_price,
                    minimum_price,
                    maximum_price,
                ),
            )

        bin_width = (
            maximum_price - minimum_price
        ) / bins

        volumes_by_bin = [0.0] * bins

        for price, volume in zip(
            prices,
            volumes,
        ):
            index = int(
                (price - minimum_price)
                / bin_width
            )

            if index >= bins:
                index = bins - 1

            volumes_by_bin[index] += volume

        levels: list[VolumeProfileLevel] = []

        for index, volume in enumerate(
            volumes_by_bin
        ):
            low = (
                minimum_price
                + index * bin_width
            )

            high = (
                minimum_price
                + (index + 1) * bin_width
            )

            levels.append(
                VolumeProfileLevel(
                    price_low=low,
                    price_high=high,
                    volume=volume,
                )
            )

        poc_index = max(
            range(len(levels)),
            key=lambda index: (
                levels[index].volume,
                -index,
            ),
        )

        poc = levels[poc_index].price_center

        val_index, vah_index = (
            self._calculate_value_area(
                levels=levels,
                poc_index=poc_index,
                target_volume=(
                    total_volume
                    * value_area_pct
                    / 100.0
                ),
            )
        )

        val = levels[val_index].price_low
        vah = levels[vah_index].price_high

        hvn = self._detect_hvn(levels)
        lvn = self._detect_lvn(levels)

        position = self._position(
            current_price,
            val,
            vah,
        )

        return VolumeProfileResult(
            levels=levels,
            poc=poc,
            vah=vah,
            val=val,
            total_volume=total_volume,
            hvn=hvn,
            lvn=lvn,
            current_price=current_price,
            position=position,
        )

    @staticmethod
    def _calculate_value_area(
        levels: list[VolumeProfileLevel],
        poc_index: int,
        target_volume: float,
    ) -> tuple[int, int]:
        """
        Expand Value Area outward from POC.
        """

        current_volume = levels[poc_index].volume

        low_index = poc_index
        high_index = poc_index

        while current_volume < target_volume:
            next_low = (
                low_index - 1
                if low_index > 0
                else None
            )

            next_high = (
                high_index + 1
                if high_index < len(levels) - 1
                else None
            )

            if (
                next_low is None
                and next_high is None
            ):
                break

            low_volume = (
                levels[next_low].volume
                if next_low is not None
                else -1.0
            )

            high_volume = (
                levels[next_high].volume
                if next_high is not None
                else -1.0
            )

            if high_volume > low_volume:
                high_index = next_high
                current_volume += high_volume
            else:
                low_index = next_low
                current_volume += low_volume

        return low_index, high_index

    @staticmethod
    def _detect_hvn(
        levels: list[VolumeProfileLevel],
    ) -> list[float]:
        """
        Detect local High Volume Nodes.
        """

        if len(levels) < 3:
            return []

        result: list[float] = []

        for index in range(
            1,
            len(levels) - 1,
        ):
            current = levels[index].volume
            previous = levels[index - 1].volume
            following = levels[index + 1].volume

            if (
                current > previous
                and current > following
            ):
                result.append(
                    levels[index].price_center
                )

        return result

    @staticmethod
    def _detect_lvn(
        levels: list[VolumeProfileLevel],
    ) -> list[float]:
        """
        Detect local Low Volume Nodes.
        """

        if len(levels) < 3:
            return []

        result: list[float] = []

        for index in range(
            1,
            len(levels) - 1,
        ):
            current = levels[index].volume
            previous = levels[index - 1].volume
            following = levels[index + 1].volume

            if (
                current < previous
                and current < following
            ):
                result.append(
                    levels[index].price_center
                )

        return result

    @staticmethod
    def _position(
        current_price: float | None,
        val: float,
        vah: float,
    ) -> str:
        """
        Determine current price position relative to Value Area.
        """

        if current_price is None:
            return "UNKNOWN"

        if current_price > vah:
            return "ABOVE_VALUE_AREA"

        if current_price < val:
            return "BELOW_VALUE_AREA"

        return "INSIDE_VALUE_AREA"
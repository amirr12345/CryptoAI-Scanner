from __future__ import annotations

from models.cvd_bucket import CVDBucket
from models.cvd_bucket_analysis import (
    BucketDivergence,
    BucketSwingPoint,
    BucketedCVDAnalysis,
)


class BucketedCVDAnalyzer:
    """
    Analyze time-bucketed CVD for swing points and divergence.
    """

    def analyze(
        self,
        buckets: list[CVDBucket],
        swing_window: int = 2,
    ) -> BucketedCVDAnalysis:
        """
        Detect price swings and price/CVD divergences.
        """

        if swing_window < 1:
            raise ValueError(
                "Swing window must be greater than zero."
            )

        if not buckets:
            return BucketedCVDAnalysis(
                swing_points=[],
                divergences=[],
                latest_signal="NONE",
            )

        swing_points = self._detect_swings(
            buckets=buckets,
            window=swing_window,
        )

        divergences = self._detect_divergences(
            swing_points=swing_points,
        )

        latest_signal = (
            divergences[-1].signal
            if divergences
            else "NONE"
        )

        return BucketedCVDAnalysis(
            swing_points=swing_points,
            divergences=divergences,
            latest_signal=latest_signal,
        )

    @staticmethod
    def _detect_swings(
        buckets: list[CVDBucket],
        window: int,
    ) -> list[BucketSwingPoint]:
        """
        Detect local price swing highs and lows.
        """

        if len(buckets) < (window * 2 + 1):
            return []

        swings: list[BucketSwingPoint] = []

        for index in range(
            window,
            len(buckets) - window,
        ):
            current = buckets[index]

            left = buckets[
                index - window:index
            ]

            right = buckets[
                index + 1:index + window + 1
            ]

            surrounding = left + right

            is_high = all(
                current.close_price > bucket.close_price
                for bucket in surrounding
            )

            is_low = all(
                current.close_price < bucket.close_price
                for bucket in surrounding
            )

            if is_high:
                swings.append(
                    BucketSwingPoint(
                        index=index,
                        timestamp=current.end_timestamp,
                        price=current.close_price,
                        cumulative_delta=current.cumulative_delta,
                        kind="HIGH",
                    )
                )

            elif is_low:
                swings.append(
                    BucketSwingPoint(
                        index=index,
                        timestamp=current.end_timestamp,
                        price=current.close_price,
                        cumulative_delta=current.cumulative_delta,
                        kind="LOW",
                    )
                )

        return swings

    @staticmethod
    def _detect_divergences(
        swing_points: list[BucketSwingPoint],
    ) -> list[BucketDivergence]:
        """
        Detect divergence between consecutive swings
        of the same type.
        """

        divergences: list[BucketDivergence] = []

        previous_by_kind: dict[
            str,
            BucketSwingPoint,
        ] = {}

        for current in swing_points:
            previous = previous_by_kind.get(
                current.kind
            )

            if previous is None:
                previous_by_kind[
                    current.kind
                ] = current

                continue

            price_change = (
                current.price
                - previous.price
            )

            if previous.price == 0:
                price_change_pct = 0.0
            else:
                price_change_pct = (
                    price_change
                    / previous.price
                    * 100.0
                )

            cvd_change = (
                current.cumulative_delta
                - previous.cumulative_delta
            )

            signal = "NONE"

            if (
                current.kind == "LOW"
                and price_change < 0
                and cvd_change > 0
            ):
                signal = "BULLISH_DIVERGENCE"

            elif (
                current.kind == "HIGH"
                and price_change > 0
                and cvd_change < 0
            ):
                signal = "BEARISH_DIVERGENCE"

            if signal != "NONE":
                divergences.append(
                    BucketDivergence(
                        signal=signal,
                        previous_index=previous.index,
                        current_index=current.index,
                        previous_price=previous.price,
                        current_price=current.price,
                        previous_cvd=previous.cumulative_delta,
                        current_cvd=current.cumulative_delta,
                        price_change_pct=round(
                            price_change_pct,
                            6,
                        ),
                        cvd_change=round(
                            cvd_change,
                            8,
                        ),
                    )
                )

            previous_by_kind[
                current.kind
            ] = current

        return divergences
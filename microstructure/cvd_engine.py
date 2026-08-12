from __future__ import annotations

from models.cvd_result import (
    CVDPoint,
    CVDResult,
    SwingDivergence,
    SwingPoint,
)
from models.trade import Trade


class CVDEngine:
    """
    Calculate Cumulative Volume Delta from normalized trades.

    Buy trades add volume to delta.
    Sell trades subtract volume from delta.

    The engine is provider-agnostic and works only with the
    normalized Trade model.
    """

    def calculate(
        self,
        trades: list[Trade],
        starting_cvd: float = 0.0,
        swing_window: int = 2,
    ) -> CVDResult:
        """
        Calculate CVD metrics and swing-based divergence.

        Parameters
        ----------
        trades:
            Ordered list of executed trades.

        starting_cvd:
            Existing cumulative delta before this batch.

        swing_window:
            Number of points on each side used to confirm a swing.

        Returns
        -------
        CVDResult
            Aggregated CVD analysis.
        """

        if swing_window < 1:
            raise ValueError(
                "Swing window must be greater than zero."
            )

        if not trades:
            return CVDResult(
                buy_volume=0.0,
                sell_volume=0.0,
                delta=0.0,
                starting_cvd=starting_cvd,
                cumulative_delta=starting_cvd,
                price_change=0.0,
                cvd_change=0.0,
                trend="NEUTRAL",
                divergence="NONE",
                points=[],
                swing_points=[],
                swing_divergences=[],
            )

        buy_volume = 0.0
        sell_volume = 0.0
        cumulative_delta = starting_cvd

        points: list[CVDPoint] = []

        first_price = trades[0].price
        last_price = trades[-1].price

        for trade in trades:
            side = trade.side.strip().lower()

            if side == "buy":
                trade_delta = trade.volume
                buy_volume += trade.volume

            elif side == "sell":
                trade_delta = -trade.volume
                sell_volume += trade.volume

            else:
                raise ValueError(
                    "Trade side must be 'buy' or 'sell'."
                )

            cumulative_delta += trade_delta

            points.append(
                CVDPoint(
                    timestamp=trade.timestamp,
                    price=trade.price,
                    delta=trade_delta,
                    cumulative_delta=cumulative_delta,
                )
            )

        delta = buy_volume - sell_volume

        price_change = last_price - first_price

        cvd_change = cumulative_delta - starting_cvd

        trend = self._detect_trend(
            price_change=price_change,
            cvd_change=cvd_change,
        )

        basic_divergence = self._detect_divergence(
            price_change=price_change,
            cvd_change=cvd_change,
        )

        swing_points = self._detect_swing_points(
            points=points,
            window=swing_window,
        )

        swing_divergences = (
            self._detect_swing_divergences(
                swing_points=swing_points,
            )
        )

        return CVDResult(
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
            starting_cvd=round(
                starting_cvd,
                8,
            ),
            cumulative_delta=round(
                cumulative_delta,
                8,
            ),
            price_change=round(
                price_change,
                8,
            ),
            cvd_change=round(
                cvd_change,
                8,
            ),
            trend=trend,
            divergence=basic_divergence,
            points=points,
            swing_points=swing_points,
            swing_divergences=swing_divergences,
        )

    @staticmethod
    def _detect_trend(
        price_change: float,
        cvd_change: float,
    ) -> str:
        """
        Detect directional market-flow agreement.
        """

        if (
            price_change > 0
            and cvd_change > 0
        ):
            return "BULLISH"

        if (
            price_change < 0
            and cvd_change < 0
        ):
            return "BEARISH"

        return "NEUTRAL"

    @staticmethod
    def _detect_divergence(
        price_change: float,
        cvd_change: float,
    ) -> str:
        """
        Detect basic price/CVD divergence.
        """

        if (
            price_change < 0
            and cvd_change > 0
        ):
            return "BULLISH_DIVERGENCE"

        if (
            price_change > 0
            and cvd_change < 0
        ):
            return "BEARISH_DIVERGENCE"

        return "NONE"

    @staticmethod
    def _detect_swing_points(
        points: list[CVDPoint],
        window: int,
    ) -> list[SwingPoint]:
        """
        Detect local price swing highs/lows.

        A point is a HIGH when its price is greater than every
        price inside the surrounding window.

        A point is a LOW when its price is lower than every
        price inside the surrounding window.

        The same point can only be classified as one type.
        """

        if len(points) < (window * 2 + 1):
            return []

        swings: list[SwingPoint] = []

        for index in range(
            window,
            len(points) - window,
        ):
            current = points[index]

            left = points[
                index - window:index
            ]

            right = points[
                index + 1:index + window + 1
            ]

            surrounding = left + right

            is_high = all(
                current.price > point.price
                for point in surrounding
            )

            is_low = all(
                current.price < point.price
                for point in surrounding
            )

            if is_high:
                swings.append(
                    SwingPoint(
                        index=index,
                        timestamp=current.timestamp,
                        price=current.price,
                        cumulative_delta=current.cumulative_delta,
                        kind="HIGH",
                    )
                )

            elif is_low:
                swings.append(
                    SwingPoint(
                        index=index,
                        timestamp=current.timestamp,
                        price=current.price,
                        cumulative_delta=current.cumulative_delta,
                        kind="LOW",
                    )
                )

        return swings

    @staticmethod
    def _detect_swing_divergences(
        swing_points: list[SwingPoint],
    ) -> list[SwingDivergence]:
        """
        Detect divergence between consecutive swings of the
        same type.

        LOW + lower price + higher CVD:
            BULLISH_DIVERGENCE

        HIGH + higher price + lower CVD:
            BEARISH_DIVERGENCE
        """

        divergences: list[SwingDivergence] = []

        previous_by_kind: dict[
            str,
            SwingPoint,
        ] = {}

        for current in swing_points:
            previous = previous_by_kind.get(
                current.kind
            )

            if previous is not None:
                price_change = (
                    current.price
                    - previous.price
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
                        SwingDivergence(
                            signal=signal,
                            price_change=round(
                                price_change,
                                8,
                            ),
                            cvd_change=round(
                                cvd_change,
                                8,
                            ),
                            previous_index=previous.index,
                            current_index=current.index,
                        )
                    )

            previous_by_kind[
                current.kind
            ] = current

        return divergences
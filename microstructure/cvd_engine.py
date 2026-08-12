from __future__ import annotations

from models.cvd_result import CVDPoint, CVDResult
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
    ) -> CVDResult:
        """
        Calculate CVD metrics from executed trades.

        Parameters
        ----------
        trades:
            Ordered list of executed trades.

        starting_cvd:
            Existing cumulative delta before this batch.
            May be positive, zero, or negative.

        Returns
        -------
        CVDResult
            Aggregated CVD analysis.
        """

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

        divergence = self._detect_divergence(
            price_change=price_change,
            cvd_change=cvd_change,
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
            divergence=divergence,
            points=points,
        )

    @staticmethod
    def _detect_trend(
        price_change: float,
        cvd_change: float,
    ) -> str:
        """
        Detect directional market-flow agreement.

        BULLISH:
            Price rising and CVD rising.

        BEARISH:
            Price falling and CVD falling.

        NEUTRAL:
            Mixed or unchanged conditions.
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

        BULLISH_DIVERGENCE:
            Price falling while CVD rises.

        BEARISH_DIVERGENCE:
            Price rising while CVD falls.

        NONE:
            No divergence.
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
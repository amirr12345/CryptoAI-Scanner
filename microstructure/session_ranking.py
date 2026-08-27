from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(slots=True, frozen=True)
class SessionPerformance:
    """
    Observed performance statistics for one trading session.
    """

    session_name: str

    sample_count: int

    average_quality: float

    average_trade_count: float
    average_order_flow_strength: float
    average_cvd_strength: float
    average_liquidity: float

    best_rate: float
    good_rate: float
    neutral_rate: float
    avoid_rate: float

    execute_rate: float

    observed_score: float
    confidence: str
    rank: int = 0


class SessionRankingEngine:
    """
    Rank sessions from observed market data instead of relying
    only on predefined session preferences.

    Ranking components:

        35% -> BEST/EXECUTE quality
        25% -> low AVOID rate
        20% -> Order Flow quality
        10% -> CVD quality
        10% -> Liquidity quality

    Minimum sample:

        < 5  -> NOT_RANKED
        5-9  -> LOW confidence
        10-19 -> MEDIUM confidence
        >=20 -> HIGH confidence
    """

    MIN_SAMPLE_FOR_RANKING = 5
    MEDIUM_SAMPLE = 10
    HIGH_SAMPLE = 20

    WEIGHT_BEST = 0.35
    WEIGHT_AVOID = 0.25
    WEIGHT_ORDER_FLOW = 0.20
    WEIGHT_CVD = 0.10
    WEIGHT_LIQUIDITY = 0.10

    @classmethod
    def rank(
        cls,
        session_rows: list[dict],
    ) -> list[SessionPerformance]:
        """
        Build ranked session performance from observed rows.

        Each row may contain:

            session_name
            quality
            trade_count
            order_flow_strength
            cvd_strength
            liquidity_score
            classification
            execute
        """

        grouped: dict[
            str,
            list[dict],
        ] = {}

        for row in session_rows:

            name = str(
                row.get(
                    "session_name",
                    "UNKNOWN",
                )
            ).strip().upper()

            if not name:
                name = "UNKNOWN"

            grouped.setdefault(
                name,
                [],
            ).append(row)

        results: list[
            SessionPerformance
        ] = []

        for (
            name,
            rows,
        ) in grouped.items():

            performance = (
                cls._build(
                    name=name,
                    rows=rows,
                )
            )

            results.append(
                performance
            )

        ranked = [
            item
            for item in results
            if item.sample_count
            >= cls.MIN_SAMPLE_FOR_RANKING
        ]

        ranked.sort(
            key=lambda item: (
                -item.observed_score,
                -item.average_quality,
                -item.best_rate,
                item.session_name,
            )
        )

        final: list[
            SessionPerformance
        ] = []

        for index, item in enumerate(
            ranked,
            start=1,
        ):
            final.append(
                SessionPerformance(
                    session_name=item.session_name,
                    sample_count=item.sample_count,
                    average_quality=item.average_quality,
                    average_trade_count=item.average_trade_count,
                    average_order_flow_strength=(
                        item.average_order_flow_strength
                    ),
                    average_cvd_strength=(
                        item.average_cvd_strength
                    ),
                    average_liquidity=(
                        item.average_liquidity
                    ),
                    best_rate=item.best_rate,
                    good_rate=item.good_rate,
                    neutral_rate=item.neutral_rate,
                    avoid_rate=item.avoid_rate,
                    execute_rate=item.execute_rate,
                    observed_score=item.observed_score,
                    confidence=item.confidence,
                    rank=index,
                )
            )

        # Sessions below minimum sample are retained but not ranked.
        unranked = [
            item
            for item in results
            if item.sample_count
            < cls.MIN_SAMPLE_FOR_RANKING
        ]

        for item in unranked:
            final.append(
                SessionPerformance(
                    session_name=item.session_name,
                    sample_count=item.sample_count,
                    average_quality=item.average_quality,
                    average_trade_count=item.average_trade_count,
                    average_order_flow_strength=(
                        item.average_order_flow_strength
                    ),
                    average_cvd_strength=(
                        item.average_cvd_strength
                    ),
                    average_liquidity=(
                        item.average_liquidity
                    ),
                    best_rate=item.best_rate,
                    good_rate=item.good_rate,
                    neutral_rate=item.neutral_rate,
                    avoid_rate=item.avoid_rate,
                    execute_rate=item.execute_rate,
                    observed_score=item.observed_score,
                    confidence="NOT_RANKED",
                    rank=0,
                )
            )

        return final

    @classmethod
    def _build(
        cls,
        name: str,
        rows: list[dict],
    ) -> SessionPerformance:

        count = len(rows)

        if count == 0:
            return SessionPerformance(
                session_name=name,
                sample_count=0,
                average_quality=0.0,
                average_trade_count=0.0,
                average_order_flow_strength=0.0,
                average_cvd_strength=0.0,
                average_liquidity=0.0,
                best_rate=0.0,
                good_rate=0.0,
                neutral_rate=0.0,
                avoid_rate=0.0,
                execute_rate=0.0,
                observed_score=0.0,
                confidence="NOT_RANKED",
            )

        quality_sum = 0.0
        trade_sum = 0.0
        order_flow_sum = 0.0
        cvd_sum = 0.0
        liquidity_sum = 0.0

        best_count = 0
        good_count = 0
        neutral_count = 0
        avoid_count = 0
        execute_count = 0

        for row in rows:

            quality_sum += cls._float(
                row.get(
                    "quality",
                    0.0,
                )
            )

            trade_sum += cls._float(
                row.get(
                    "trade_count",
                    0.0,
                )
            )

            order_flow_sum += cls._float(
                row.get(
                    "order_flow_strength",
                    0.0,
                )
            )

            cvd_sum += cls._float(
                row.get(
                    "cvd_strength",
                    0.0,
                )
            )

            liquidity_sum += cls._float(
                row.get(
                    "liquidity_score",
                    0.0,
                )
            )

            classification = str(
                row.get(
                    "classification",
                    "NEUTRAL",
                )
            ).strip().upper()

            if classification == "BEST":
                best_count += 1

            elif classification == "GOOD":
                good_count += 1

            elif classification == "AVOID":
                avoid_count += 1

            else:
                neutral_count += 1

            execute_value = row.get(
                "execute",
                False,
            )

            if bool(execute_value):
                execute_count += 1

        average_quality = (
            quality_sum / count
        )

        average_trade_count = (
            trade_sum / count
        )

        average_order_flow = (
            order_flow_sum
            / count
        )

        average_cvd = (
            cvd_sum
            / count
        )

        average_liquidity = (
            liquidity_sum
            / count
        )

        best_rate = (
            best_count
            / count
            * 100.0
        )

        good_rate = (
            good_count
            / count
            * 100.0
        )

        neutral_rate = (
            neutral_count
            / count
            * 100.0
        )

        avoid_rate = (
            avoid_count
            / count
            * 100.0
        )

        execute_rate = (
            execute_count
            / count
            * 100.0
        )

        # --------------------------------------------------------
        # Normalize observed components to 0-10.
        # --------------------------------------------------------

        best_component = (
            best_rate
            / 10.0
        )

        avoid_component = max(
            0.0,
            10.0
            - avoid_rate
            / 10.0,
        )

        order_flow_component = min(
            10.0,
            max(
                0.0,
                average_order_flow
                / 10.0,
            ),
        )

        cvd_component = min(
            10.0,
            max(
                0.0,
                average_cvd
                / 10.0,
            ),
        )

        liquidity_component = min(
            10.0,
            max(
                0.0,
                average_liquidity
                * 10.0,
            ),
        )

        observed_score = (
            best_component
            * cls.WEIGHT_BEST
            + avoid_component
            * cls.WEIGHT_AVOID
            + order_flow_component
            * cls.WEIGHT_ORDER_FLOW
            + cvd_component
            * cls.WEIGHT_CVD
            + liquidity_component
            * cls.WEIGHT_LIQUIDITY
        )

        confidence = cls._confidence(
            count
        )

        return SessionPerformance(
            session_name=name,
            sample_count=count,
            average_quality=round(
                average_quality,
                2,
            ),
            average_trade_count=round(
                average_trade_count,
                2,
            ),
            average_order_flow_strength=round(
                average_order_flow,
                2,
            ),
            average_cvd_strength=round(
                average_cvd,
                2,
            ),
            average_liquidity=round(
                average_liquidity,
                2,
            ),
            best_rate=round(
                best_rate,
                2,
            ),
            good_rate=round(
                good_rate,
                2,
            ),
            neutral_rate=round(
                neutral_rate,
                2,
            ),
            avoid_rate=round(
                avoid_rate,
                2,
            ),
            execute_rate=round(
                execute_rate,
                2,
            ),
            observed_score=round(
                observed_score,
                2,
            ),
            confidence=confidence,
        )

    @classmethod
    def _confidence(
        cls,
        sample_count: int,
    ) -> str:

        if sample_count < cls.MIN_SAMPLE_FOR_RANKING:
            return "NOT_RANKED"

        if sample_count < cls.MEDIUM_SAMPLE:
            return "LOW"

        if sample_count < cls.HIGH_SAMPLE:
            return "MEDIUM"

        return "HIGH"

    @staticmethod
    def _float(
        value,
    ) -> float:

        try:
            return float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0


def wilson_lower_bound(
    success_count: int,
    sample_count: int,
    confidence_z: float = 1.96,
) -> float:
    """
    Optional statistical lower bound for a success rate.

    Returns a proportion in [0, 1].

    This prevents a tiny sample with a 100% success rate from
    being treated as equivalent to a large sample with a 90%
    success rate.
    """

    n = int(sample_count)

    if n <= 0:
        return 0.0

    successes = max(
        0,
        min(
            n,
            int(success_count),
        ),
    )

    p = (
        successes
        / n
    )

    z = float(
        confidence_z
    )

    denominator = (
        1.0
        + z * z / n
    )

    centre = (
        p
        + z * z / (2.0 * n)
    )

    margin = (
        z
        * sqrt(
            (
                p * (1.0 - p)
                + z * z / (4.0 * n)
            )
            / n
        )
    )

    lower = (
        centre
        - margin
    ) / denominator

    return max(
        0.0,
        min(
            1.0,
            lower,
        ),
    )
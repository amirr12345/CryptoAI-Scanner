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


@dataclass(slots=True, frozen=True)
class SessionGateDecision:
    """
    Execution decision produced from the observed session
    ranking.

    This class is deliberately independent from the primary
    Confluence score.

    decision:

        EXECUTE
        WAIT
        BLOCK
    """

    session_name: str

    decision: str

    rank: int

    confidence: str

    observed_score: float

    sample_count: int

    average_quality: float

    best_rate: float

    avoid_rate: float

    execute_rate: float

    reason: str


class SessionRankingEngine:
    """
    Rank sessions from observed market data.

    Ranking components:

        35% -> BEST classification rate
        25% -> low AVOID rate
        20% -> Order Flow quality
        10% -> CVD quality
        10% -> Liquidity quality

    Minimum sample:

        < 5      -> NOT_RANKED
        5-9      -> LOW
        10-19    -> MEDIUM
        >=20     -> HIGH

    Important:

        Session ranking NEVER changes the primary
        confluence score.

        It is an execution-quality input only.
    """

    # ==========================================================
    # SAMPLE SIZE
    # ==========================================================

    MIN_SAMPLE_FOR_RANKING = 5

    MEDIUM_SAMPLE = 10

    HIGH_SAMPLE = 20

    # ==========================================================
    # RANKING WEIGHTS
    # ==========================================================

    WEIGHT_BEST = 0.35

    WEIGHT_AVOID = 0.25

    WEIGHT_ORDER_FLOW = 0.20

    WEIGHT_CVD = 0.10

    WEIGHT_LIQUIDITY = 0.10

    # ==========================================================
    # EXECUTION RANKING POLICY
    # ==========================================================

    # Rank 1 is the strongest observed session.
    MAX_EXECUTE_RANK = 2

    # Confidence required for direct execution.
    EXECUTE_CONFIDENCE = {
        "HIGH",
    }

    # Medium confidence can allow execution only when
    # observed quality is exceptionally strong.
    MEDIUM_CONFIDENCE_MIN_SCORE = 8.0

    # Minimum observed session quality.
    EXECUTE_MIN_QUALITY = 8.0

    WAIT_MIN_QUALITY = 5.0

    # Minimum BEST/EXECUTE evidence.
    EXECUTE_MIN_BEST_RATE = 40.0

    # AVOID rate above this level is considered unsafe.
    EXECUTE_MAX_AVOID_RATE = 20.0

    # ==========================================================
    # RANK
    # ==========================================================

    @classmethod
    def rank(
        cls,
        session_rows: list[dict],
    ) -> list[SessionPerformance]:
        """
        Build ranked session performance from observed rows.

        Expected row fields:

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

            results.append(
                cls._build(
                    name=name,
                    rows=rows,
                )
            )

        ranked = [
            item
            for item in results
            if (
                item.sample_count
                >= cls.MIN_SAMPLE_FOR_RANKING
            )
        ]

        ranked.sort(
            key=lambda item: (
                -item.observed_score,
                -item.average_quality,
                -item.best_rate,
                -item.execute_rate,
                item.session_name,
            )
        )

        final: list[
            SessionPerformance
        ] = []

        # ------------------------------------------------------
        # Ranked sessions
        # ------------------------------------------------------

        for index, item in enumerate(
            ranked,
            start=1,
        ):

            final.append(
                cls._copy_with_rank(
                    item=item,
                    rank=index,
                )
            )

        # ------------------------------------------------------
        # Sessions without enough sample
        # ------------------------------------------------------

        unranked = [
            item
            for item in results
            if (
                item.sample_count
                < cls.MIN_SAMPLE_FOR_RANKING
            )
        ]

        unranked.sort(
            key=lambda item: (
                -item.average_quality,
                -item.sample_count,
                item.session_name,
            )
        )

        for item in unranked:

            final.append(
                cls._copy_with_rank(
                    item=item,
                    rank=0,
                    confidence_override="NOT_RANKED",
                )
            )

        return final

    # ==========================================================
    # SESSION DECISION
    # ==========================================================

    @classmethod
    def decide(
        cls,
        performance: SessionPerformance | None,
        primary_grade: str,
        primary_conflict: bool = False,
    ) -> SessionGateDecision:
        """
        Decide whether the observed session performance is
        compatible with live execution.

        Primary confluence grade remains independent.

        Parameters:

            performance:
                Ranked observed session performance.

            primary_grade:
                A+, A, B, CONFLICT, REJECT, etc.

            primary_conflict:
                Whether the primary confluence already has a
                hard conflict.

        Rules:

            Missing ranking
                -> WAIT

            Not ranked
                -> WAIT

            Weak primary grade
                -> WAIT

            Primary conflict
                -> BLOCK

            Low session quality
                -> BLOCK

            Rank too low
                -> WAIT/BLOCK

            Low confidence
                -> WAIT

            Strong confidence + strong quality +
            low avoid rate + good BEST rate
                -> EXECUTE
        """

        grade = str(
            primary_grade
            if primary_grade is not None
            else "REJECT"
        ).strip().upper()

        # ------------------------------------------------------
        # No ranking available
        # ------------------------------------------------------

        if performance is None:

            return SessionGateDecision(
                session_name="UNKNOWN",
                decision="WAIT",
                rank=0,
                confidence="NOT_RANKED",
                observed_score=0.0,
                sample_count=0,
                average_quality=0.0,
                best_rate=0.0,
                avoid_rate=0.0,
                execute_rate=0.0,
                reason=(
                    "Session ranking is unavailable."
                ),
            )

        # ------------------------------------------------------
        # Not enough sample
        # ------------------------------------------------------

        if (
            performance.confidence
            == "NOT_RANKED"
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Session does not have enough observed "
                    "samples for ranking."
                ),
            )

        # ------------------------------------------------------
        # Hard primary conflict
        # ------------------------------------------------------

        if primary_conflict:

            return cls._decision_from_performance(
                performance=performance,
                decision="BLOCK",
                reason=(
                    "Primary confluence contains a hard "
                    "market conflict."
                ),
            )

        # ------------------------------------------------------
        # Primary grade
        # ------------------------------------------------------

        if grade == "CONFLICT":

            return cls._decision_from_performance(
                performance=performance,
                decision="BLOCK",
                reason=(
                    "Primary confluence grade is CONFLICT."
                ),
            )

        if grade == "REJECT":

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Primary confluence grade is REJECT."
                ),
            )

        if grade == "B":

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Primary confluence grade B is not "
                    "eligible for Session-based execution."
                ),
            )

        if grade not in {
            "A+",
            "A",
        }:

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    f"Unsupported primary grade: {grade}."
                ),
            )

        # ------------------------------------------------------
        # Session quality
        # ------------------------------------------------------

        if (
            performance.average_quality
            < cls.WAIT_MIN_QUALITY
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="BLOCK",
                reason=(
                    "Observed session quality is too low: "
                    f"{performance.average_quality:.2f}/10."
                ),
            )

        if (
            performance.average_quality
            < cls.EXECUTE_MIN_QUALITY
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Observed session quality is below "
                    f"execution threshold: "
                    f"{performance.average_quality:.2f}/10."
                ),
            )

        # ------------------------------------------------------
        # Rank
        # ------------------------------------------------------

        if (
            performance.rank <= 0
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Session has no valid performance rank."
                ),
            )

        if (
            performance.rank
            > cls.MAX_EXECUTE_RANK
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    f"Session rank "
                    f"{performance.rank} is below the "
                    f"execution rank threshold."
                ),
            )

        # ------------------------------------------------------
        # AVOID rate
        # ------------------------------------------------------

        if (
            performance.avoid_rate
            > cls.EXECUTE_MAX_AVOID_RATE
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Session AVOID rate is too high: "
                    f"{performance.avoid_rate:.2f}%."
                ),
            )

        # ------------------------------------------------------
        # BEST rate
        # ------------------------------------------------------

        if (
            performance.best_rate
            < cls.EXECUTE_MIN_BEST_RATE
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Observed BEST-session rate is too low: "
                    f"{performance.best_rate:.2f}%."
                ),
            )

        # ------------------------------------------------------
        # Confidence
        # ------------------------------------------------------

        confidence = (
            performance.confidence
        )

        if confidence in cls.EXECUTE_CONFIDENCE:

            return cls._decision_from_performance(
                performance=performance,
                decision="EXECUTE",
                reason=(
                    "Session ranking permits execution: "
                    f"rank={performance.rank}, "
                    f"confidence={confidence}, "
                    f"quality={performance.average_quality:.2f}, "
                    f"BEST={performance.best_rate:.2f}%, "
                    f"AVOID={performance.avoid_rate:.2f}%."
                ),
            )

        if (
            confidence == "MEDIUM"
            and
            performance.observed_score
            >= cls.MEDIUM_CONFIDENCE_MIN_SCORE
        ):

            return cls._decision_from_performance(
                performance=performance,
                decision="WAIT",
                reason=(
                    "Session metrics are strong but statistical "
                    "confidence is only MEDIUM."
                ),
            )

        return cls._decision_from_performance(
            performance=performance,
            decision="WAIT",
            reason=(
                "Session ranking does not provide sufficient "
                "confidence for execution."
            ),
        )

    # ==========================================================
    # LOOKUP
    # ==========================================================

    @staticmethod
    def get_session(
        rankings: list[SessionPerformance],
        session_name: str,
    ) -> SessionPerformance | None:
        """
        Find a specific session performance from a ranking list.
        """

        target = str(
            session_name
            if session_name is not None
            else ""
        ).strip().upper()

        if not target:
            return None

        for item in rankings:

            if (
                item.session_name
                == target
            ):
                return item

        return None

    # ==========================================================
    # BUILD
    # ==========================================================

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

            if bool(
                execute_value
            ):

                execute_count += 1

        average_quality = (
            quality_sum
            / count
        )

        average_trade_count = (
            trade_sum
            / count
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

        # ------------------------------------------------------
        # Normalize to 0-10
        # ------------------------------------------------------

        best_component = (
            best_rate
            / 10.0
        )

        avoid_component = max(
            0.0,
            10.0
            - avoid_rate / 10.0,
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

    # ==========================================================
    # COPY
    # ==========================================================

    @staticmethod
    def _copy_with_rank(
        item: SessionPerformance,
        rank: int,
        confidence_override: str | None = None,
    ) -> SessionPerformance:

        return SessionPerformance(
            session_name=item.session_name,

            sample_count=item.sample_count,

            average_quality=item.average_quality,

            average_trade_count=(
                item.average_trade_count
            ),

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

            confidence=(
                confidence_override
                if confidence_override is not None
                else item.confidence
            ),

            rank=rank,
        )

    # ==========================================================
    # DECISION RESULT
    # ==========================================================

    @staticmethod
    def _decision_from_performance(
        performance: SessionPerformance,
        decision: str,
        reason: str,
    ) -> SessionGateDecision:

        return SessionGateDecision(
            session_name=(
                performance.session_name
            ),

            decision=decision,

            rank=performance.rank,

            confidence=(
                performance.confidence
            ),

            observed_score=(
                performance.observed_score
            ),

            sample_count=(
                performance.sample_count
            ),

            average_quality=(
                performance.average_quality
            ),

            best_rate=(
                performance.best_rate
            ),

            avoid_rate=(
                performance.avoid_rate
            ),

            execute_rate=(
                performance.execute_rate
            ),

            reason=reason,
        )

    # ==========================================================
    # CONFIDENCE
    # ==========================================================

    @classmethod
    def _confidence(
        cls,
        sample_count: int,
    ) -> str:

        if (
            sample_count
            < cls.MIN_SAMPLE_FOR_RANKING
        ):

            return "NOT_RANKED"

        if (
            sample_count
            < cls.MEDIUM_SAMPLE
        ):

            return "LOW"

        if (
            sample_count
            < cls.HIGH_SAMPLE
        ):

            return "MEDIUM"

        return "HIGH"

    # ==========================================================
    # FLOAT
    # ==========================================================

    @staticmethod
    def _float(
        value,
    ) -> float:

        try:

            result = float(
                value
            )

            if result != result:
                return 0.0

            if result in {
                float("inf"),
                float("-inf"),
            }:

                return 0.0

            return result

        except (
            TypeError,
            ValueError,
        ):

            return 0.0


# ==================================================================
# WILSON LOWER BOUND
# ==================================================================


def wilson_lower_bound(
    success_count: int,
    sample_count: int,
    confidence_z: float = 1.96,
) -> float:
    """
    Wilson score lower confidence bound.

    Returns a proportion in [0, 1].

    Useful when comparing success rates with different
    sample sizes.
    """

    n = int(
        sample_count
    )

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
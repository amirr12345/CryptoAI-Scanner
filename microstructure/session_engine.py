from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True, frozen=True)
class SessionAnalysis:
    """
    Dynamic trading-session quality analysis.

    Session quality is separate from the primary confluence
    score.

    Inputs:

        - session window
        - trade activity
        - order-flow strength
        - CVD strength
        - liquidity/activity quality
    """

    name: str
    quality: float

    trade_count: int

    activity_score: float
    order_flow_score: float
    cvd_score: float
    liquidity_score: float

    classification: str
    is_overlap: bool

    execution_allowed: bool


class SessionEngine:
    """
    Dynamic crypto trading-session quality engine.

    All session windows use UTC:

        00:00-08:00 -> ASIA
        08:00-13:00 -> LONDON
        13:00-17:00 -> LONDON_NY_OVERLAP
        17:00-21:00 -> NEW_YORK
        21:00-24:00 -> OFF_HOURS

    Session quality does NOT modify the primary confluence
    score.

    Session quality is used as an execution-quality layer.
    """

    # ============================================================
    # SESSION WINDOWS
    # ============================================================

    SESSION_WINDOWS = {
        "ASIA": (0, 8),
        "LONDON": (8, 13),
        "LONDON_NY_OVERLAP": (13, 17),
        "NEW_YORK": (17, 21),
        "OFF_HOURS": (21, 24),
    }

    # ============================================================
    # SESSION BASE QUALITY
    # ============================================================

    BASE_QUALITY = {
        "ASIA": 5.0,
        "LONDON": 7.0,
        "LONDON_NY_OVERLAP": 8.5,
        "NEW_YORK": 8.0,
        "OFF_HOURS": 3.0,
    }

    # ============================================================
    # EXECUTION LEVELS
    # ============================================================

    EXECUTE_MIN = 8.0
    GOOD_MIN = 6.5
    NEUTRAL_MIN = 5.0

    # ============================================================
    # SESSION NAME
    # ============================================================

    @classmethod
    def session_name(
        cls,
        timestamp: int,
    ) -> str:
        """
        Resolve a Unix timestamp to a UTC session.
        """

        dt = datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc,
        )

        hour = int(
            dt.hour
        )

        for (
            name,
            (
                start_hour,
                end_hour,
            ),
        ) in cls.SESSION_WINDOWS.items():

            if (
                start_hour
                <= hour
                < end_hour
            ):
                return name

        return "OFF_HOURS"

    # ============================================================
    # MAIN ANALYSIS
    # ============================================================

    @classmethod
    def analyze(
        cls,
        timestamp: int,
        trade_count: int,
        order_flow_strength: float,
        cvd_strength: float,
        liquidity_ratio: float = 0.0,
    ) -> SessionAnalysis:
        """
        Calculate dynamic session quality.

        The base session quality establishes the potential
        quality of the time window.

        Actual market activity determines how much of that
        potential can be realized.

        This prevents a quiet market from being classified as
        BEST solely because the clock is inside a preferred
        session.
        """

        name = cls.session_name(
            timestamp
        )

        is_overlap = (
            name
            == "LONDON_NY_OVERLAP"
        )

        base_quality = cls.BASE_QUALITY.get(
            name,
            3.0,
        )

        # --------------------------------------------------------
        # Dynamic market components
        # --------------------------------------------------------

        activity_score = (
            cls._activity_score(
                trade_count
            )
        )

        order_flow_score = (
            cls._strength_score(
                order_flow_strength
            )
        )

        cvd_score = (
            cls._strength_score(
                cvd_strength
            )
        )

        liquidity_score = max(
            0.0,
            min(
                1.0,
                float(
                    liquidity_ratio
                ),
            ),
        )

        dynamic_score = (
            activity_score
            + order_flow_score
            + cvd_score
            + liquidity_score
        )

        dynamic_max = 7.0

        dynamic_ratio = (
            dynamic_score
            / dynamic_max
            if dynamic_max > 0
            else 0.0
        )

        # --------------------------------------------------------
        # Quality
        #
        # Critical rule:
        #
        # Zero activity must be materially below the base
        # quality of the session.
        #
        # High base session + weak market activity cannot become
        # BEST.
        # --------------------------------------------------------

        quality = (
            base_quality
            + (
                10.0
                - base_quality
            )
            * dynamic_ratio
        )

        # Explicit activity penalty.
        #
        # This keeps inactive markets away from BEST even
        # during London/NY overlap.

        if trade_count <= 0:

            quality = min(
                quality,
                cls.NEUTRAL_MIN - 0.1,
            )

        elif trade_count < 50:

            quality = min(
                quality,
                5.5,
            )

        elif trade_count < 100:

            quality = min(
                quality,
                6.5,
            )

        quality = max(
            0.0,
            min(
                10.0,
                quality,
            ),
        )

        # --------------------------------------------------------
        # Classification
        # --------------------------------------------------------

        if quality >= cls.EXECUTE_MIN:

            classification = "BEST"

        elif quality >= cls.GOOD_MIN:

            classification = "GOOD"

        elif quality >= cls.NEUTRAL_MIN:

            classification = "NEUTRAL"

        else:

            classification = "AVOID"

        # --------------------------------------------------------
        # Execution permission
        # --------------------------------------------------------

        execution_allowed = (
            quality >= cls.EXECUTE_MIN
            and trade_count > 0
        )

        return SessionAnalysis(
            name=name,

            quality=round(
                quality,
                2,
            ),

            trade_count=int(
                trade_count
            ),

            activity_score=round(
                activity_score,
                2,
            ),

            order_flow_score=round(
                order_flow_score,
                2,
            ),

            cvd_score=round(
                cvd_score,
                2,
            ),

            liquidity_score=round(
                liquidity_score,
                2,
            ),

            classification=(
                classification
            ),

            is_overlap=is_overlap,

            execution_allowed=(
                execution_allowed
            ),
        )

    # ============================================================
    # ACTIVITY SCORE
    # ============================================================

    @staticmethod
    def _activity_score(
        trade_count: int,
    ) -> float:
        """
        Convert trade count into a 0-2 activity score.
        """

        count = max(
            0,
            int(trade_count),
        )

        if count <= 0:
            return 0.0

        if count < 50:
            return 0.25

        if count < 100:
            return 0.50

        if count < 250:
            return 0.75

        if count < 500:
            return 1.00

        if count < 1000:
            return 1.25

        if count < 2000:
            return 1.50

        if count < 5000:
            return 1.75

        return 2.00

    # ============================================================
    # STRENGTH SCORE
    # ============================================================

    @staticmethod
    def _strength_score(
        value: float,
    ) -> float:
        """
        Convert 0-100 strength into 0-2.
        """

        strength = max(
            0.0,
            min(
                100.0,
                abs(
                    float(value)
                ),
            ),
        )

        return (
            strength
            / 50.0
        )

    # ============================================================
    # EXECUTION PRIORITY
    # ============================================================

    @classmethod
    def execution_priority(
        cls,
        quality: float,
    ) -> str:
        """
        Convert quality into execution priority.
        """

        quality = float(
            quality
        )

        if quality >= cls.EXECUTE_MIN:
            return "BEST"

        if quality >= cls.GOOD_MIN:
            return "GOOD"

        if quality >= cls.NEUTRAL_MIN:
            return "NEUTRAL"

        return "AVOID"
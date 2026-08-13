from dataclasses import dataclass

from microstructure.confluence_engine import (
    ConfluenceEngine,
)


@dataclass
class Setup:
    direction: str
    setup: str = "BULLISH_STRUCTURE_SETUP"


@dataclass
class CVD:
    direction: str
    strength: float


@dataclass
class Profile:
    location: str


@dataclass
class VWAP:
    direction: str


def test_bullish_a_plus_alignment():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        ),
        cvd=CVD(
            direction="BULLISH",
            strength=80.0,
        ),
        profile=Profile(
            location="BELOW_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="BULLISH"
        ),
    )

    assert result.direction == "BULLISH"
    assert result.score == 100.0
    assert result.grade == "A+"
    assert result.actionable is True
    assert not result.conflicts


def test_bearish_a_plus_alignment():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BEARISH",
            setup="BEARISH_STRUCTURE_SETUP",
        ),
        cvd=CVD(
            direction="BEARISH",
            strength=80.0,
        ),
        profile=Profile(
            location="ABOVE_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="BEARISH"
        ),
    )

    assert result.direction == "BEARISH"
    assert result.score == 100.0
    assert result.grade == "A+"
    assert result.actionable is True


def test_opposing_cvd_rejects_high_quality_setup():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        ),
        cvd=CVD(
            direction="BEARISH",
            strength=80.0,
        ),
        profile=Profile(
            location="BELOW_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="BULLISH"
        ),
    )

    assert result.cvd_points == 0.0
    assert "CVD opposing structure setup" in (
        result.conflicts
    )
    assert result.actionable is False


def test_two_conflicts_create_conflict_grade():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        ),
        cvd=CVD(
            direction="BEARISH",
            strength=80.0,
        ),
        profile=Profile(
            location="ABOVE_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="BEARISH"
        ),
    )

    assert result.grade == "CONFLICT"
    assert result.actionable is False
    assert len(result.conflicts) >= 2


def test_neutral_vwap_does_not_create_conflict():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        ),
        cvd=CVD(
            direction="BULLISH",
            strength=75.0,
        ),
        profile=Profile(
            location="BELOW_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="NEUTRAL"
        ),
    )

    assert result.vwap_points == 7.0
    assert result.grade in {
        "A+",
        "A",
        "B",
    }


def test_inside_value_area_is_partial_profile_confirmation():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        ),
        cvd=CVD(
            direction="BULLISH",
            strength=75.0,
        ),
        profile=Profile(
            location="INSIDE_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="BULLISH"
        ),
    )

    assert result.profile_points == 8.0
    assert result.actionable is True


def test_neutral_setup_is_not_actionable():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="NEUTRAL"
        )
    )

    assert result.direction == "NEUTRAL"
    assert result.score == 0.0
    assert result.grade == "REJECT"
    assert result.actionable is False


def test_missing_context_does_not_invent_confirmation():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        )
    )

    assert result.structure_points == 40.0
    assert result.cvd_points == 0.0
    assert result.profile_points == 0.0
    assert result.vwap_points == 0.0
    assert result.score == 40.0
    assert result.grade == "REJECT"
    assert result.actionable is False


def test_cvd_strength_below_threshold_gets_partial_points():
    result = ConfluenceEngine().evaluate(
        setup=Setup(
            direction="BULLISH"
        ),
        cvd=CVD(
            direction="BULLISH",
            strength=40.0,
        ),
        profile=Profile(
            location="BELOW_VALUE_AREA"
        ),
        vwap=VWAP(
            direction="BULLISH"
        ),
    )

    assert result.cvd_points == 8.0
    assert result.score == 83.0
    assert result.grade == "A"
    assert result.actionable is True
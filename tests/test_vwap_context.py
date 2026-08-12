import pytest

from indicators.vwap_context import (
    build_vwap_context,
)


def test_bullish_vwap_context():
    context = build_vwap_context(
        price=110.0,
        vwap=100.0,
        previous_vwap=99.0,
    )

    assert context.position == "ABOVE_VWAP"
    assert context.distance_pct == pytest.approx(
        10.0
    )
    assert context.slope == pytest.approx(
        1.0
    )
    assert context.trend == "BULLISH"


def test_bearish_vwap_context():
    context = build_vwap_context(
        price=90.0,
        vwap=100.0,
        previous_vwap=101.0,
    )

    assert context.position == "BELOW_VWAP"
    assert context.distance_pct == pytest.approx(
        -10.0
    )
    assert context.slope == pytest.approx(
        -1.0
    )
    assert context.trend == "BEARISH"


def test_price_above_vwap_but_falling_vwap_is_neutral():
    context = build_vwap_context(
        price=110.0,
        vwap=100.0,
        previous_vwap=101.0,
    )

    assert context.position == "ABOVE_VWAP"
    assert context.trend == "NEUTRAL"


def test_price_below_vwap_but_rising_vwap_is_neutral():
    context = build_vwap_context(
        price=90.0,
        vwap=100.0,
        previous_vwap=99.0,
    )

    assert context.position == "BELOW_VWAP"
    assert context.trend == "NEUTRAL"


def test_price_at_vwap():
    context = build_vwap_context(
        price=100.0,
        vwap=100.0,
        previous_vwap=100.0,
    )

    assert context.position == "AT_VWAP"
    assert context.distance_pct == pytest.approx(
        0.0
    )
    assert context.slope == pytest.approx(
        0.0
    )
    assert context.trend == "NEUTRAL"


def test_vwap_without_previous_value():
    context = build_vwap_context(
        price=105.0,
        vwap=100.0,
    )

    assert context.position == "ABOVE_VWAP"
    assert context.slope == pytest.approx(
        0.0
    )
    assert context.trend == "NEUTRAL"


def test_vwap_must_be_positive():
    with pytest.raises(
        ValueError,
        match="VWAP must be greater than zero",
    ):
        build_vwap_context(
            price=100.0,
            vwap=0.0,
        )


def test_price_cannot_be_negative():
    with pytest.raises(
        ValueError,
        match="Price cannot be negative",
    ):
        build_vwap_context(
            price=-1.0,
            vwap=100.0,
        )
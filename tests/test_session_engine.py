import pytest

from microstructure.session_engine import (
    SessionEngine,
)


def test_asia_session():
    # 04:00 UTC
    result = SessionEngine.analyze(
        timestamp=(
            4 * 60 * 60
        ),
        trade_count=1000,
        order_flow_strength=70.0,
        cvd_strength=70.0,
        liquidity_ratio=0.8,
    )

    assert result.name == "ASIA"
    assert result.is_overlap is False
    assert 0.0 <= result.quality <= 10.0


def test_london_session():
    # 09:00 UTC
    result = SessionEngine.analyze(
        timestamp=(
            9 * 60 * 60
        ),
        trade_count=1000,
        order_flow_strength=70.0,
        cvd_strength=70.0,
        liquidity_ratio=0.8,
    )

    assert result.name == "LONDON"
    assert result.is_overlap is False


def test_london_new_york_overlap():
    # 14:00 UTC
    result = SessionEngine.analyze(
        timestamp=(
            14 * 60 * 60
        ),
        trade_count=2000,
        order_flow_strength=80.0,
        cvd_strength=80.0,
        liquidity_ratio=0.9,
    )

    assert (
        result.name
        == "LONDON_NY_OVERLAP"
    )

    assert result.is_overlap is True

    assert result.quality >= 8.0

    assert (
        result.classification
        == "BEST"
    )

    assert result.execution_allowed is True


def test_new_york_session():
    # 18:00 UTC
    result = SessionEngine.analyze(
        timestamp=(
            18 * 60 * 60
        ),
        trade_count=1000,
        order_flow_strength=70.0,
        cvd_strength=70.0,
        liquidity_ratio=0.8,
    )

    assert result.name == "NEW_YORK"
    assert result.is_overlap is False


def test_off_hours():
    # 22:00 UTC
    result = SessionEngine.analyze(
        timestamp=(
            22 * 60 * 60
        ),
        trade_count=10,
        order_flow_strength=10.0,
        cvd_strength=10.0,
        liquidity_ratio=0.1,
    )

    assert result.name == "OFF_HOURS"
    assert result.quality < 5.0
    assert result.classification == "AVOID"
    assert result.execution_allowed is False


def test_quality_is_capped():
    result = SessionEngine.analyze(
        timestamp=(
            14 * 60 * 60
        ),
        trade_count=100000,
        order_flow_strength=100.0,
        cvd_strength=100.0,
        liquidity_ratio=1.0,
    )

    assert result.quality == pytest.approx(
        10.0
    )


def test_zero_activity_is_not_best():
    result = SessionEngine.analyze(
        timestamp=(
            14 * 60 * 60
        ),
        trade_count=0,
        order_flow_strength=0.0,
        cvd_strength=0.0,
        liquidity_ratio=0.0,
    )

    assert result.quality < 8.0
    assert result.execution_allowed is False
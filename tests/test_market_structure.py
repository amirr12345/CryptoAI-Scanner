from dataclasses import dataclass

import pytest

from microstructure.market_structure import (
    MarketStructureEngine,
)


@dataclass
class FakeCandle:
    timestamp: int
    high: float
    low: float


def candle(timestamp, high, low):
    return FakeCandle(
        timestamp=timestamp,
        high=high,
        low=low,
    )


def test_empty_input_returns_neutral_structure():
    result = MarketStructureEngine().calculate([])

    assert result.structure == "NEUTRAL"
    assert result.swings == []
    assert result.latest_high is None
    assert result.previous_high is None
    assert result.latest_low is None
    assert result.previous_low is None


def test_rejects_invalid_swing_window():
    with pytest.raises(
        ValueError,
        match="Swing window must be greater than zero",
    ):
        MarketStructureEngine().calculate(
            [],
            swing_window=0,
        )


def test_insufficient_candles_returns_neutral():
    candles = [
        candle(1, 101, 99),
        candle(2, 102, 100),
        candle(3, 103, 101),
        candle(4, 104, 102),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=2,
    )

    assert result.structure == "NEUTRAL"
    assert result.swings == []


def test_detects_swing_highs():
    candles = [
        candle(1, 100, 90),
        candle(2, 110, 95),
        candle(3, 102, 97),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    highs = [
        swing
        for swing in result.swings
        if swing.kind == "HIGH"
    ]

    assert len(highs) == 1
    assert highs[0].price == 110
    assert highs[0].label == "SWING_HIGH"


def test_detects_swing_lows():
    candles = [
        candle(1, 110, 100),
        candle(2, 102, 90),
        candle(3, 108, 98),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    lows = [
        swing
        for swing in result.swings
        if swing.kind == "LOW"
    ]

    assert len(lows) == 1
    assert lows[0].price == 90
    assert lows[0].label == "SWING_LOW"


def test_classifies_higher_high():
    candles = [
        candle(0, 100, 90),
        candle(1, 110, 95),
        candle(2, 102, 96),
        candle(3, 115, 100),
        candle(4, 105, 101),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    highs = [
        swing
        for swing in result.swings
        if swing.kind == "HIGH"
    ]

    assert len(highs) == 2
    assert highs[0].label == "SWING_HIGH"
    assert highs[1].label == "HH"


def test_classifies_lower_high():
    candles = [
        candle(0, 100, 90),
        candle(1, 115, 95),
        candle(2, 105, 97),
        candle(3, 110, 100),
        candle(4, 103, 101),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    highs = [
        swing
        for swing in result.swings
        if swing.kind == "HIGH"
    ]

    assert len(highs) == 2
    assert highs[1].label == "LH"


def test_classifies_higher_low():
    candles = [
        candle(0, 110, 100),
        candle(1, 120, 95),
        candle(2, 110, 103),
        candle(3, 125, 100),
        candle(4, 115, 108),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    lows = [
        swing
        for swing in result.swings
        if swing.kind == "LOW"
    ]

    assert len(lows) == 2
    assert lows[0].label == "SWING_LOW"
    assert lows[1].label == "HL"


def test_classifies_lower_low():
    candles = [
        candle(0, 110, 100),
        candle(1, 120, 95),
        candle(2, 110, 98),
        candle(3, 115, 90),
        candle(4, 105, 94),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    lows = [
        swing
        for swing in result.swings
        if swing.kind == "LOW"
    ]

    assert len(lows) == 2
    assert lows[0].label == "SWING_LOW"
    assert lows[1].label == "LL"


def test_detects_bullish_structure():
    candles = [
        candle(0, 110, 100),
        candle(1, 120, 95),
        candle(2, 112, 105),
        candle(3, 130, 100),
        candle(4, 118, 110),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    assert result.structure == "BULLISH"


def test_detects_bearish_structure():
    candles = [
        candle(0, 120, 110),
        candle(1, 130, 105),
        candle(2, 118, 108),
        candle(3, 125, 100),
        candle(4, 115, 103),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    assert result.structure == "BEARISH"


def test_detects_mixed_structure():
    candles = [
        candle(0, 110, 100),
        candle(1, 120, 95),
        candle(2, 112, 105),
        candle(3, 130, 90),
        candle(4, 118, 95),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    assert result.structure == "MIXED"


def test_swing_confirmation_index_matches_window():
    candles = [
        candle(0, 100, 90),
        candle(1, 110, 95),
        candle(2, 102, 96),
        candle(3, 115, 100),
        candle(4, 105, 101),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    assert result.swings

    for swing in result.swings:
        assert (
            swing.confirmation_index
            == swing.index + 1
        )


def test_swing_confirmation_index_matches_larger_window():
    candles = [
        candle(0, 100, 90),
        candle(1, 102, 91),
        candle(2, 110, 95),
        candle(3, 103, 97),
        candle(4, 101, 96),
        candle(5, 115, 100),
        candle(6, 105, 101),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=2,
    )

    assert result.swings

    for swing in result.swings:
        assert (
            swing.confirmation_index
            == swing.index + 2
        )


def test_swing_is_not_available_before_confirmation():
    candles = [
        candle(0, 100, 90),
        candle(1, 110, 95),
        candle(2, 102, 96),
        candle(3, 115, 100),
        candle(4, 105, 101),
    ]

    result = MarketStructureEngine().calculate(
        candles,
        swing_window=2,
    )

    for swing in result.swings:
        assert (
            swing.confirmation_index
            > swing.index
        )
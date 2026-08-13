from dataclasses import dataclass

import pytest

from microstructure.market_structure import (
    MarketStructureEngine,
)
from microstructure.structure_break import (
    StructureBreakEngine,
)
from models.market_structure import (
    MarketStructureResult,
    MarketSwing,
)


@dataclass
class FakeCandle:
    timestamp: int
    high: float
    low: float
    close: float


def candle(
    timestamp: int,
    high: float,
    low: float,
    close: float,
) -> FakeCandle:
    return FakeCandle(
        timestamp=timestamp,
        high=high,
        low=low,
        close=close,
    )


def make_structure(
    swings: list[MarketSwing],
    structure: str,
) -> MarketStructureResult:
    highs = [
        swing
        for swing in swings
        if swing.kind == "HIGH"
    ]

    lows = [
        swing
        for swing in swings
        if swing.kind == "LOW"
    ]

    return MarketStructureResult(
        swings=swings,
        latest_high=(
            highs[-1]
            if highs
            else None
        ),
        previous_high=(
            highs[-2]
            if len(highs) >= 2
            else None
        ),
        latest_low=(
            lows[-1]
            if lows
            else None
        ),
        previous_low=(
            lows[-2]
            if len(lows) >= 2
            else None
        ),
        structure=structure,
    )


def test_empty_input_returns_empty_result():
    structure = MarketStructureEngine().calculate([])

    result = StructureBreakEngine().calculate(
        candles=[],
        structure=structure,
    )

    assert result.events == []
    assert result.latest_event == "NONE"
    assert result.latest_direction == "NEUTRAL"


def test_rejects_negative_displacement():
    structure = MarketStructureEngine().calculate([])

    with pytest.raises(
        ValueError,
        match="Displacement percentage cannot be negative",
    ):
        StructureBreakEngine().calculate(
            candles=[],
            structure=structure,
            displacement_pct=-0.1,
        )


def test_no_structure_produces_no_break():
    candles = [
        candle(0, 100, 90, 95),
        candle(1, 101, 91, 96),
        candle(2, 102, 92, 97),
    ]

    structure = MarketStructureEngine().calculate(
        candles,
        swing_window=1,
    )

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    assert result.events == []


def test_bullish_bos():
    swings = [
        MarketSwing(
            1,
            1,
            100.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            90.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            110.0,
            "HIGH",
            "HH",
        ),
        MarketSwing(
            4,
            4,
            95.0,
            "LOW",
            "HL",
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 95, 90, 93),
        candle(1, 100, 92, 99),
        candle(2, 105, 94, 104),
        candle(3, 108, 96, 107),
        candle(4, 115, 100, 111),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    assert any(
        event.event == "BOS"
        and event.direction == "BULLISH"
        for event in result.events
    )


def test_bearish_bos():
    swings = [
        MarketSwing(
            1,
            1,
            110.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            90.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            105.0,
            "HIGH",
            "LH",
        ),
        MarketSwing(
            4,
            4,
            85.0,
            "LOW",
            "LL",
        ),
    ]

    structure = make_structure(
        swings,
        "BEARISH",
    )

    candles = [
        candle(0, 110, 95, 105),
        candle(1, 108, 92, 94),
        candle(2, 102, 88, 90),
        candle(3, 98, 84, 87),
        candle(4, 94, 80, 83),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    assert any(
        event.event == "BOS"
        and event.direction == "BEARISH"
        for event in result.events
    )


def test_bullish_choch():
    # Bearish regime:
    # 120 -> 110 = LH
    # 95  -> 90  = LL
    #
    # The 110 HIGH is already confirmed before candle 5,
    # therefore candle 5 can break it.
    swings = [
        MarketSwing(
            1,
            1,
            120.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            95.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            110.0,
            "HIGH",
            "LH",
        ),
        MarketSwing(
            4,
            4,
            90.0,
            "LOW",
            "LL",
        ),
    ]

    structure = make_structure(
        swings,
        "BEARISH",
    )

    candles = [
        candle(0, 118, 100, 110),
        candle(1, 116, 92, 100),
        candle(2, 113, 91, 96),
        candle(3, 111, 90, 92),
        candle(4, 108, 89, 91),
        candle(5, 116, 100, 110.05),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
        displacement_pct=1.0,
    )

    bullish_choch = [
        event
        for event in result.events
        if (
            event.event == "CHoCH"
            and event.direction == "BULLISH"
        )
    ]

    assert len(bullish_choch) >= 1

    event = bullish_choch[0]

    assert event.direction == "BULLISH"
    assert event.displacement > 0
    assert event.displacement_pct > 0


def test_bearish_choch():
    # Bullish regime:
    # 110 -> 120 = HH
    # 90  -> 100 = HL
    #
    # The 100 LOW is already confirmed before candle 5,
    # therefore candle 5 can break it.
    swings = [
        MarketSwing(
            1,
            1,
            110.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            90.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            120.0,
            "HIGH",
            "HH",
        ),
        MarketSwing(
            4,
            4,
            100.0,
            "LOW",
            "HL",
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 105, 92, 100),
        candle(1, 110, 95, 108),
        candle(2, 115, 98, 112),
        candle(3, 120, 100, 115),
        candle(4, 112, 99, 105),
        candle(5, 108, 96, 99.90),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
        displacement_pct=1.0,
    )

    bearish_choch = [
        event
        for event in result.events
        if (
            event.event == "CHoCH"
            and event.direction == "BEARISH"
        )
    ]

    assert len(bearish_choch) >= 1

    event = bearish_choch[0]

    assert event.direction == "BEARISH"
    assert event.displacement < 0
    assert event.displacement_pct > 0


def test_bullish_mss_requires_displacement():
    swings = [
        MarketSwing(
            1,
            1,
            120.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            95.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            110.0,
            "HIGH",
            "LH",
        ),
        MarketSwing(
            4,
            4,
            90.0,
            "LOW",
            "LL",
        ),
    ]

    structure = make_structure(
        swings,
        "BEARISH",
    )

    candles = [
        candle(0, 118, 100, 110),
        candle(1, 114, 94, 100),
        candle(2, 112, 92, 96),
        candle(3, 108, 90, 92),
        candle(4, 107, 88, 91),
        candle(5, 120, 100, 112),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
        displacement_pct=0.15,
    )

    bullish_mss = [
        event
        for event in result.events
        if (
            event.event == "MSS"
            and event.direction == "BULLISH"
        )
    ]

    assert len(bullish_mss) >= 1

    event = bullish_mss[0]

    assert event.direction == "BULLISH"
    assert event.displacement > 0
    assert event.displacement_pct >= 0.15


def test_bearish_mss_requires_displacement():
    swings = [
        MarketSwing(
            1,
            1,
            110.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            90.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            120.0,
            "HIGH",
            "HH",
        ),
        MarketSwing(
            4,
            4,
            100.0,
            "LOW",
            "HL",
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 108, 92, 100),
        candle(1, 112, 96, 108),
        candle(2, 118, 100, 115),
        candle(3, 121, 102, 117),
        candle(4, 115, 100, 105),
        candle(5, 95, 80, 82),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
        displacement_pct=0.15,
    )

    bearish_mss = [
        event
        for event in result.events
        if (
            event.event == "MSS"
            and event.direction == "BEARISH"
        )
    ]

    assert len(bearish_mss) >= 1

    event = bearish_mss[0]

    assert event.direction == "BEARISH"
    assert event.displacement < 0
    assert event.displacement_pct >= 0.15


def test_same_swing_is_not_broken_twice():
    swings = [
        MarketSwing(
            1,
            1,
            100.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            90.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            110.0,
            "HIGH",
            "HH",
        ),
        MarketSwing(
            4,
            4,
            95.0,
            "LOW",
            "HL",
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 100, 90, 95),
        candle(1, 105, 92, 99),
        candle(2, 108, 94, 107),
        candle(3, 112, 96, 111),
        candle(4, 114, 98, 113),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    bullish_breaks = [
        event
        for event in result.events
        if (
            event.direction == "BULLISH"
            and event.broken_index == 3
        )
    ]

    assert len(bullish_breaks) <= 1


def test_lookahead_is_not_used_for_regime():
    """
    Future swings must not retroactively affect earlier breaks.
    """

    swings = [
        MarketSwing(
            1,
            1,
            120.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            95.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            110.0,
            "HIGH",
            "LH",
        ),
        MarketSwing(
            4,
            4,
            90.0,
            "LOW",
            "LL",
        ),
        # Future swings.
        MarketSwing(
            8,
            8,
            130.0,
            "HIGH",
            "HH",
        ),
        MarketSwing(
            9,
            9,
            100.0,
            "LOW",
            "HL",
        ),
    ]

    structure = make_structure(
        swings,
        "MIXED",
    )

    candles = [
        candle(0, 100, 90, 95),
        candle(1, 115, 96, 105),
        candle(2, 112, 92, 100),
        candle(3, 110, 91, 95),
        candle(4, 109, 89, 92),
        candle(5, 116, 90, 111),
        candle(6, 120, 95, 115),
        candle(7, 125, 100, 120),
        candle(8, 135, 105, 130),
        candle(9, 140, 110, 135),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
        displacement_pct=1.0,
    )

    assert result.events

    assert all(
        event.index > event.broken_index
        for event in result.events
    )


def test_latest_event_matches_last_event():
    swings = [
        MarketSwing(
            1,
            1,
            100.0,
            "HIGH",
            "SWING_HIGH",
        ),
        MarketSwing(
            2,
            2,
            90.0,
            "LOW",
            "SWING_LOW",
        ),
        MarketSwing(
            3,
            3,
            110.0,
            "HIGH",
            "HH",
        ),
        MarketSwing(
            4,
            4,
            95.0,
            "LOW",
            "HL",
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 100, 90, 95),
        candle(1, 104, 92, 101),
        candle(2, 108, 94, 106),
        candle(3, 115, 96, 112),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    assert result.events

    assert result.latest_event == (
        result.events[-1].event
    )

    assert result.latest_direction == (
        result.events[-1].direction
    )
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
    timestamp,
    high,
    low,
    close,
):
    return FakeCandle(
        timestamp=timestamp,
        high=high,
        low=low,
        close=close,
    )


def make_swing(
    index,
    price,
    kind,
    label,
    confirmation_index,
):
    return MarketSwing(
        index=index,
        timestamp=index,
        price=float(price),
        kind=kind,
        label=label,
        confirmation_index=confirmation_index,
    )


def make_structure(
    swings,
    structure,
):
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
    structure = (
        MarketStructureEngine().calculate([])
    )

    result = StructureBreakEngine().calculate(
        candles=[],
        structure=structure,
    )

    assert result.events == []
    assert result.latest_event == "NONE"
    assert result.latest_direction == "NEUTRAL"


def test_rejects_negative_displacement():
    structure = (
        MarketStructureEngine().calculate([])
    )

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

    structure = (
        MarketStructureEngine().calculate(
            candles,
            swing_window=1,
        )
    )

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    assert result.events == []


def test_bullish_bos():
    swings = [
        make_swing(
            1,
            100,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            90,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            110,
            "HIGH",
            "HH",
            4,
        ),
        make_swing(
            4,
            95,
            "LOW",
            "HL",
            5,
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 95, 90, 93),
        candle(1, 98, 92, 96),
        candle(2, 105, 94, 103),
        candle(3, 108, 96, 107),
        candle(4, 115, 100, 111),
        candle(5, 118, 102, 113),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    bullish_bos = [
        event
        for event in result.events
        if (
            event.event == "BOS"
            and event.direction == "BULLISH"
        )
    ]

    assert bullish_bos

    event = bullish_bos[0]

    # First confirmed/broken swing is HIGH at index 1.
    assert event.broken_index == 1
    assert event.index == 2
    assert event.direction == "BULLISH"
    assert event.displacement > 0
    assert event.displacement_pct > 0


def test_bearish_bos():
    swings = [
        make_swing(
            1,
            110,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            90,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            105,
            "HIGH",
            "LH",
            4,
        ),
        make_swing(
            4,
            85,
            "LOW",
            "LL",
            5,
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
        candle(5, 90, 75, 78),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    bearish_bos = [
        event
        for event in result.events
        if (
            event.event == "BOS"
            and event.direction == "BEARISH"
        )
    ]

    assert bearish_bos

    event = bearish_bos[0]

    # First confirmed/broken swing is LOW at index 2.
    assert event.broken_index == 2
    assert event.index == 3
    assert event.direction == "BEARISH"
    assert event.displacement < 0
    assert event.displacement_pct > 0


def test_bullish_choch_respects_confirmation():
    swings = [
        make_swing(
            1,
            120,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            95,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            110,
            "HIGH",
            "LH",
            4,
        ),
        make_swing(
            4,
            90,
            "LOW",
            "LL",
            5,
        ),
    ]

    structure = make_structure(
        swings,
        "BEARISH",
    )

    candles = [
        candle(0, 118, 100, 110),
        candle(1, 116, 95, 103),
        candle(2, 114, 92, 98),
        candle(3, 112, 90, 92),
        candle(4, 111, 91, 95),
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

    assert bullish_choch

    event = bullish_choch[0]

    assert event.broken_index == 3
    assert event.index >= 5
    assert event.direction == "BULLISH"
    assert event.displacement > 0
    assert event.displacement_pct > 0


def test_bearish_choch_respects_confirmation():
    swings = [
        make_swing(
            1,
            110,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            90,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            120,
            "HIGH",
            "HH",
            4,
        ),
        make_swing(
            4,
            100,
            "LOW",
            "HL",
            5,
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
        candle(4, 115, 101, 106),
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

    assert bearish_choch

    event = bearish_choch[0]

    assert event.broken_index == 4
    assert event.index >= 5
    assert event.direction == "BEARISH"
    assert event.displacement < 0
    assert event.displacement_pct > 0


def test_bullish_mss_requires_displacement():
    swings = [
        make_swing(
            1,
            120,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            95,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            110,
            "HIGH",
            "LH",
            4,
        ),
        make_swing(
            4,
            90,
            "LOW",
            "LL",
            5,
        ),
    ]

    structure = make_structure(
        swings,
        "BEARISH",
    )

    candles = [
        candle(0, 118, 100, 110),
        candle(1, 114, 94, 101),
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

    assert bullish_mss

    event = bullish_mss[0]

    assert event.direction == "BULLISH"
    assert event.displacement > 0
    assert event.displacement_pct >= 0.15


def test_bearish_mss_requires_displacement():
    swings = [
        make_swing(
            1,
            110,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            90,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            120,
            "HIGH",
            "HH",
            4,
        ),
        make_swing(
            4,
            100,
            "LOW",
            "HL",
            5,
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

    assert bearish_mss

    event = bearish_mss[0]

    assert event.direction == "BEARISH"
    assert event.displacement < 0
    assert event.displacement_pct >= 0.15


def test_same_swing_is_not_broken_twice():
    swings = [
        make_swing(
            1,
            100,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            90,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            110,
            "HIGH",
            "HH",
            4,
        ),
        make_swing(
            4,
            95,
            "LOW",
            "HL",
            5,
        ),
    ]

    structure = make_structure(
        swings,
        "BULLISH",
    )

    candles = [
        candle(0, 95, 90, 93),
        candle(1, 99, 92, 97),
        candle(2, 105, 94, 103),
        candle(3, 108, 96, 107),
        candle(4, 115, 100, 111),
        candle(5, 118, 102, 114),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    broken_once = [
        event
        for event in result.events
        if event.broken_index == 1
    ]

    assert len(broken_once) <= 1


def test_break_before_confirmation_is_ignored():
    swing = make_swing(
        2,
        100,
        "HIGH",
        "HH",
        4,
    )

    structure = make_structure(
        [
            make_swing(
                0,
                90,
                "HIGH",
                "SWING_HIGH",
                2,
            ),
            make_swing(
                1,
                80,
                "LOW",
                "SWING_LOW",
                3,
            ),
            swing,
            make_swing(
                3,
                85,
                "LOW",
                "HL",
                5,
            ),
        ],
        "BULLISH",
    )

    candles = [
        candle(0, 90, 80, 85),
        candle(1, 95, 82, 90),
        candle(2, 105, 88, 101),
        candle(3, 110, 90, 108),
        candle(4, 112, 92, 111),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
    )

    assert all(
        not (
            event.broken_index == 2
            and event.index < 4
        )
        for event in result.events
    )


def test_lookahead_is_not_used():
    swings = [
        make_swing(
            1,
            120,
            "HIGH",
            "SWING_HIGH",
            3,
        ),
        make_swing(
            2,
            95,
            "LOW",
            "SWING_LOW",
            4,
        ),
        make_swing(
            3,
            110,
            "HIGH",
            "LH",
            5,
        ),
        make_swing(
            4,
            90,
            "LOW",
            "LL",
            6,
        ),
        make_swing(
            8,
            130,
            "HIGH",
            "HH",
            10,
        ),
        make_swing(
            9,
            100,
            "LOW",
            "HL",
            11,
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
        candle(10, 145, 115, 140),
        candle(11, 150, 120, 145),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
        displacement_pct=1.0,
    )

    assert result.events

    assert all(
        event.index
        > event.broken_index
        for event in result.events
    )


def test_latest_event_matches_last_event():
    swings = [
        make_swing(
            1,
            100,
            "HIGH",
            "SWING_HIGH",
            2,
        ),
        make_swing(
            2,
            90,
            "LOW",
            "SWING_LOW",
            3,
        ),
        make_swing(
            3,
            110,
            "HIGH",
            "HH",
            4,
        ),
        make_swing(
            4,
            95,
            "LOW",
            "HL",
            5,
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
        candle(3, 112, 96, 109),
        candle(4, 115, 98, 112),
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
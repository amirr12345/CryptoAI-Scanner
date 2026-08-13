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


def test_detects_bullish_bos():
    candles = [
        candle(0, 100, 90, 95),
        candle(1, 110, 95, 108),
        candle(2, 102, 96, 99),
        candle(3, 115, 100, 112),
        candle(4, 120, 105, 117),
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

    bullish_bos = [
        event
        for event in result.events
        if (
            event.event == "BOS"
            and event.direction == "BULLISH"
        )
    ]

    assert len(bullish_bos) >= 1
    assert result.bullish_bos_count >= 1

    event = bullish_bos[0]

    assert event.direction == "BULLISH"
    assert event.displacement > 0
    assert event.displacement_pct > 0


def test_detects_bearish_bos():
    candles = [
        candle(0, 120, 110, 115),
        candle(1, 130, 105, 108),
        candle(2, 118, 108, 116),
        candle(3, 125, 100, 102),
        candle(4, 115, 90, 94),
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

    bearish_bos = [
        event
        for event in result.events
        if (
            event.event == "BOS"
            and event.direction == "BEARISH"
        )
    ]

    assert len(bearish_bos) >= 1
    assert result.bearish_bos_count >= 1

    event = bearish_bos[0]

    assert event.direction == "BEARISH"
    assert event.displacement < 0
    assert event.displacement_pct > 0


def test_detects_bullish_choch_after_bearish_structure():
    structure = MarketStructureResult(
        swings=[
            MarketSwing(
                index=1,
                timestamp=1,
                price=120.0,
                kind="HIGH",
                label="SWING_HIGH",
            ),
            MarketSwing(
                index=2,
                timestamp=2,
                price=95.0,
                kind="LOW",
                label="SWING_LOW",
            ),
            MarketSwing(
                index=3,
                timestamp=3,
                price=110.0,
                kind="HIGH",
                label="LH",
            ),
            MarketSwing(
                index=4,
                timestamp=4,
                price=90.0,
                kind="LOW",
                label="LL",
            ),
        ],
        latest_high=MarketSwing(
            index=3,
            timestamp=3,
            price=110.0,
            kind="HIGH",
            label="LH",
        ),
        previous_high=MarketSwing(
            index=1,
            timestamp=1,
            price=120.0,
            kind="HIGH",
            label="SWING_HIGH",
        ),
        latest_low=MarketSwing(
            index=4,
            timestamp=4,
            price=90.0,
            kind="LOW",
            label="LL",
        ),
        previous_low=MarketSwing(
            index=2,
            timestamp=2,
            price=95.0,
            kind="LOW",
            label="SWING_LOW",
        ),
        structure="BEARISH",
    )

    candles = [
        candle(0, 100, 95, 98),
        candle(1, 120, 100, 115),
        candle(2, 110, 95, 96),
        candle(3, 110, 92, 100),
        candle(4, 105, 90, 91),
        candle(5, 116, 100, 110.05),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
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

    assert event.broken_index == 3
    assert event.broken_price == 110.0
    assert event.direction == "BULLISH"

    # Bullish break:
    # 110.05 - 110.00 = +0.05
    assert event.displacement > 0
    assert event.displacement_pct > 0


def test_detects_bearish_choch_after_bullish_structure():
    structure = MarketStructureResult(
        swings=[
            MarketSwing(
                index=1,
                timestamp=1,
                price=110.0,
                kind="HIGH",
                label="SWING_HIGH",
            ),
            MarketSwing(
                index=2,
                timestamp=2,
                price=90.0,
                kind="LOW",
                label="SWING_LOW",
            ),
            MarketSwing(
                index=3,
                timestamp=3,
                price=120.0,
                kind="HIGH",
                label="HH",
            ),
            MarketSwing(
                index=4,
                timestamp=4,
                price=100.0,
                kind="LOW",
                label="HL",
            ),
        ],
        latest_high=MarketSwing(
            index=3,
            timestamp=3,
            price=120.0,
            kind="HIGH",
            label="HH",
        ),
        previous_high=MarketSwing(
            index=1,
            timestamp=1,
            price=110.0,
            kind="HIGH",
            label="SWING_HIGH",
        ),
        latest_low=MarketSwing(
            index=4,
            timestamp=4,
            price=100.0,
            kind="LOW",
            label="HL",
        ),
        previous_low=MarketSwing(
            index=2,
            timestamp=2,
            price=90.0,
            kind="LOW",
            label="SWING_LOW",
        ),
        structure="BULLISH",
    )

    candles = [
        candle(0, 100, 90, 95),
        candle(1, 110, 95, 108),
        candle(2, 105, 90, 92),
        candle(3, 120, 100, 115),
        candle(4, 115, 100, 105),
        candle(5, 110, 98, 99.90),
    ]

    result = StructureBreakEngine().calculate(
        candles,
        structure,
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

    assert event.broken_index == 4
    assert event.broken_price == 100.0
    assert event.direction == "BEARISH"

    # Bearish break:
    # 99.90 - 100.00 = -0.10
    assert event.displacement < 0
    assert event.displacement_pct > 0


def test_detects_bullish_mss_with_strong_displacement():
    structure = MarketStructureResult(
        swings=[
            MarketSwing(
                index=1,
                timestamp=1,
                price=110.0,
                kind="HIGH",
                label="SWING_HIGH",
            ),
            MarketSwing(
                index=2,
                timestamp=2,
                price=90.0,
                kind="LOW",
                label="SWING_LOW",
            ),
            MarketSwing(
                index=3,
                timestamp=3,
                price=120.0,
                kind="HIGH",
                label="LH",
            ),
            MarketSwing(
                index=4,
                timestamp=4,
                price=100.0,
                kind="LOW",
                label="LL",
            ),
        ],
        latest_high=MarketSwing(
            index=3,
            timestamp=3,
            price=120.0,
            kind="HIGH",
            label="LH",
        ),
        previous_high=MarketSwing(
            index=1,
            timestamp=1,
            price=110.0,
            kind="HIGH",
            label="SWING_HIGH",
        ),
        latest_low=MarketSwing(
            index=4,
            timestamp=4,
            price=100.0,
            kind="LOW",
            label="LL",
        ),
        previous_low=MarketSwing(
            index=2,
            timestamp=2,
            price=90.0,
            kind="LOW",
            label="SWING_LOW",
        ),
        structure="BEARISH",
    )

    candles = [
        candle(0, 100, 95, 98),
        candle(1, 110, 100, 105),
        candle(2, 105, 90, 92),
        candle(3, 120, 100, 115),
        candle(4, 115, 90, 91),
        candle(5, 125, 95, 123),
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


def test_detects_bearish_mss_with_strong_displacement():
    structure = MarketStructureResult(
        swings=[
            MarketSwing(
                index=1,
                timestamp=1,
                price=110.0,
                kind="HIGH",
                label="SWING_HIGH",
            ),
            MarketSwing(
                index=2,
                timestamp=2,
                price=90.0,
                kind="LOW",
                label="SWING_LOW",
            ),
            MarketSwing(
                index=3,
                timestamp=3,
                price=120.0,
                kind="HH",
                label="HH",
            ),
            MarketSwing(
                index=4,
                timestamp=4,
                price=100.0,
                kind="LOW",
                label="HL",
            ),
        ],
        latest_high=MarketSwing(
            index=3,
            timestamp=3,
            price=120.0,
            kind="HIGH",
            label="HH",
        ),
        previous_high=MarketSwing(
            index=1,
            timestamp=1,
            price=110.0,
            kind="HIGH",
            label="SWING_HIGH",
        ),
        latest_low=MarketSwing(
            index=4,
            timestamp=4,
            price=100.0,
            kind="LOW",
            label="HL",
        ),
        previous_low=MarketSwing(
            index=2,
            timestamp=2,
            price=90.0,
            kind="LOW",
            label="SWING_LOW",
        ),
        structure="BULLISH",
    )

    candles = [
        candle(0, 100, 90, 95),
        candle(1, 110, 95, 108),
        candle(2, 105, 90, 92),
        candle(3, 120, 100, 115),
        candle(4, 115, 100, 105),
        candle(5, 110, 75, 70),
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


def test_latest_event_is_last_detected_event():
    candles = [
        candle(0, 100, 90, 95),
        candle(1, 110, 95, 108),
        candle(2, 102, 96, 99),
        candle(3, 115, 100, 112),
        candle(4, 120, 105, 117),
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

    assert result.events

    assert result.latest_event == (
        result.events[-1].event
    )

    assert result.latest_direction == (
        result.events[-1].direction
    )
from dataclasses import dataclass

from microstructure.liquidity_sweep import (
    LiquiditySweepEngine,
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


def swing(
    index: int,
    price: float,
    kind: str,
    label: str,
    confirmation_index: int,
) -> MarketSwing:
    return MarketSwing(
        index=index,
        timestamp=index,
        price=price,
        kind=kind,
        label=label,
        confirmation_index=confirmation_index,
    )


def make_structure(
    swings: list[MarketSwing],
) -> MarketStructureResult:

    highs = [
        item
        for item in swings
        if item.kind == "HIGH"
    ]

    lows = [
        item
        for item in swings
        if item.kind == "LOW"
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
        structure="MIXED",
    )


def test_empty_input_returns_empty_result():
    result = LiquiditySweepEngine().calculate(
        candles=[],
        structure=make_structure([]),
    )

    assert result.events == []
    assert result.latest_event == "NONE"
    assert result.latest_direction == "NEUTRAL"


def test_detects_bullish_liquidity_sweep():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "LOW",
                "SWING_LOW",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 105, 98, 102),
        candle(1, 104, 97, 101),
        candle(2, 103, 95, 100.8),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert len(result.events) == 1

    event = result.events[0]

    assert event.event == (
        "BULLISH_LIQUIDITY_SWEEP"
    )

    assert event.direction == "BULLISH"
    assert event.level_index == 1
    assert event.level_price == 100.0
    assert event.candle_low == 95.0
    assert event.candle_close == 100.8
    assert event.excursion > 0
    assert event.rejection > 0

    assert (
        result.bullish_sweep_count == 1
    )

    assert (
        result.bearish_sweep_count == 0
    )


def test_detects_bearish_liquidity_sweep():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "HIGH",
                "SWING_HIGH",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 102, 95, 98),
        candle(1, 103, 96, 101),
        candle(2, 105, 97, 99.2),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert len(result.events) == 1

    event = result.events[0]

    assert event.event == (
        "BEARISH_LIQUIDITY_SWEEP"
    )

    assert event.direction == "BEARISH"
    assert event.level_index == 1
    assert event.level_price == 100.0
    assert event.candle_high == 105.0
    assert event.candle_close == 99.2
    assert event.excursion > 0
    assert event.rejection > 0

    assert (
        result.bearish_sweep_count == 1
    )

    assert (
        result.bullish_sweep_count == 0
    )


def test_no_sweep_when_price_does_not_cross_level():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "LOW",
                "SWING_LOW",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 105, 98, 102),
        candle(1, 104, 97, 101),
        candle(2, 103, 100.1, 101),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert result.events == []


def test_no_sweep_when_price_crosses_but_does_not_reclaim():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "LOW",
                "SWING_LOW",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 105, 98, 102),
        candle(1, 104, 97, 101),
        candle(2, 103, 95, 98),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert result.events == []


def test_no_sweep_before_confirmation():
    structure = make_structure(
        [
            swing(
                3,
                100.0,
                "LOW",
                "SWING_LOW",
                5,
            ),
        ]
    )

    candles = [
        candle(0, 105, 98, 102),
        candle(1, 104, 97, 101),
        candle(2, 103, 95, 99),
        candle(3, 102, 94, 98),
        candle(4, 104, 96, 103),
        candle(5, 104, 95, 101),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert all(
        event.index >= 5
        for event in result.events
    )


def test_same_level_is_not_swept_twice():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "LOW",
                "SWING_LOW",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 105, 98, 102),
        candle(1, 104, 97, 101),
        candle(2, 103, 95, 101),
        candle(3, 104, 96, 100.5),
        candle(4, 105, 94, 101),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    level_events = [
        event
        for event in result.events
        if event.level_index == 1
    ]

    assert len(level_events) <= 1


def test_breaking_level_without_reclaim_is_not_sweep():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "HIGH",
                "SWING_HIGH",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 98, 90, 95),
        candle(1, 99, 91, 96),
        candle(2, 105, 95, 102),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert result.events == []


def test_latest_event_matches_last_event():
    structure = make_structure(
        [
            swing(
                1,
                100.0,
                "LOW",
                "SWING_LOW",
                2,
            ),
        ]
    )

    candles = [
        candle(0, 105, 98, 102),
        candle(1, 104, 97, 101),
        candle(2, 103, 95, 100.8),
    ]

    result = LiquiditySweepEngine().calculate(
        candles,
        structure,
    )

    assert result.events

    assert (
        result.latest_event
        == result.events[-1].event
    )

    assert (
        result.latest_direction
        == result.events[-1].direction
    )
import pytest

from microstructure.volume_profile import (
    VolumeProfileEngine,
)
from models.trade import Trade


def make_trade(
    timestamp: int,
    price: float,
    volume: float,
    side: str = "buy",
) -> Trade:
    return Trade(
        timestamp=timestamp,
        price=price,
        volume=volume,
        side=side,
        symbol="BTC",
    )


class FakeTrade:
    """
    Minimal trade-like object used to test validation inside
    VolumeProfileEngine without triggering Trade model validation.
    """

    def __init__(
        self,
        price: float,
        volume: float,
    ):
        self.price = price
        self.volume = volume


def test_volume_profile_calculates_total_volume():
    trades = [
        make_trade(1, 100.0, 2.0),
        make_trade(2, 101.0, 3.0),
        make_trade(3, 102.0, 5.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=3,
    )

    assert result.total_volume == pytest.approx(
        10.0
    )


def test_volume_profile_finds_poc():
    trades = [
        make_trade(1, 100.0, 1.0),
        make_trade(2, 101.0, 10.0),
        make_trade(3, 102.0, 2.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=3,
    )

    assert result.poc == pytest.approx(
        101.0,
        abs=0.1,
    )


def test_volume_profile_builds_levels():
    trades = [
        make_trade(1, 100.0, 1.0),
        make_trade(2, 101.0, 2.0),
        make_trade(3, 102.0, 3.0),
        make_trade(4, 103.0, 4.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=4,
    )

    assert len(result.levels) == 4

    assert sum(
        level.volume
        for level in result.levels
    ) == pytest.approx(10.0)


def test_volume_profile_detects_value_area():
    trades = [
        make_trade(1, 100.0, 1.0),
        make_trade(2, 101.0, 5.0),
        make_trade(3, 102.0, 4.0),
        make_trade(4, 103.0, 1.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=4,
        value_area_pct=70.0,
    )

    assert result.val is not None
    assert result.vah is not None
    assert result.poc is not None
    assert result.val <= result.poc <= result.vah


def test_volume_profile_detects_hvn():
    trades = [
        make_trade(1, 100.0, 1.0),
        make_trade(2, 101.0, 10.0),
        make_trade(3, 102.0, 1.0),
        make_trade(4, 103.0, 2.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=4,
    )

    assert len(result.hvn) >= 1


def test_volume_profile_detects_lvn():
    trades = [
        make_trade(1, 100.0, 10.0),
        make_trade(2, 101.0, 1.0),
        make_trade(3, 102.0, 10.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=3,
    )

    assert len(result.lvn) >= 1


def test_volume_profile_position_inside_value_area():
    trades = [
        make_trade(1, 100.0, 2.0),
        make_trade(2, 101.0, 10.0),
        make_trade(3, 102.0, 2.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=3,
        current_price=101.0,
    )

    assert result.position == "INSIDE_VALUE_AREA"


def test_volume_profile_position_above_value_area():
    trades = [
        make_trade(1, 100.0, 5.0),
        make_trade(2, 101.0, 10.0),
        make_trade(3, 102.0, 5.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=3,
        current_price=110.0,
    )

    assert result.position == "ABOVE_VALUE_AREA"


def test_volume_profile_position_below_value_area():
    trades = [
        make_trade(1, 100.0, 5.0),
        make_trade(2, 101.0, 10.0),
        make_trade(3, 102.0, 5.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades,
        bins=3,
        current_price=90.0,
    )

    assert result.position == "BELOW_VALUE_AREA"


def test_volume_profile_empty_trades():
    result = VolumeProfileEngine().calculate([])

    assert result.levels == []
    assert result.poc is None
    assert result.vah is None
    assert result.val is None
    assert result.total_volume == 0.0
    assert result.hvn == []
    assert result.lvn == []
    assert result.position == "UNKNOWN"


def test_volume_profile_rejects_invalid_bins():
    with pytest.raises(
        ValueError,
        match="Bins must be greater than zero",
    ):
        VolumeProfileEngine().calculate(
            [],
            bins=0,
        )


def test_volume_profile_rejects_invalid_value_area():
    with pytest.raises(
        ValueError,
        match="Value area percentage",
    ):
        VolumeProfileEngine().calculate(
            [],
            value_area_pct=0,
        )


def test_volume_profile_rejects_negative_price():
    trades = [
        FakeTrade(
            price=-100.0,
            volume=1.0,
        )
    ]

    with pytest.raises(
        ValueError,
        match="Trade price cannot be negative",
    ):
        VolumeProfileEngine().calculate(trades)


def test_volume_profile_rejects_negative_volume():
    trades = [
        FakeTrade(
            price=100.0,
            volume=-1.0,
        )
    ]

    with pytest.raises(
        ValueError,
        match="Trade volume cannot be negative",
    ):
        VolumeProfileEngine().calculate(trades)


def test_volume_profile_handles_zero_volume():
    trades = [
        make_trade(1, 100.0, 0.0),
        make_trade(2, 101.0, 0.0),
    ]

    result = VolumeProfileEngine().calculate(
        trades
    )

    assert result.total_volume == 0.0
    assert result.poc is None
    assert result.vah is None
    assert result.val is None
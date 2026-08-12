import pytest

from microstructure.cvd_engine import CVDEngine
from models.trade import Trade


def make_trade(
    timestamp: int,
    price: float,
    volume: float,
    side: str,
) -> Trade:
    return Trade(
        timestamp=timestamp,
        price=price,
        volume=volume,
        side=side,
        symbol="BTC",
    )


def test_cvd_calculates_buy_and_sell_volume():
    trades = [
        make_trade(1, 100.0, 2.0, "buy"),
        make_trade(2, 101.0, 1.0, "sell"),
        make_trade(3, 102.0, 3.0, "buy"),
    ]

    result = CVDEngine().calculate(trades)

    assert result.buy_volume == pytest.approx(5.0)
    assert result.sell_volume == pytest.approx(1.0)
    assert result.delta == pytest.approx(4.0)
    assert result.cumulative_delta == pytest.approx(4.0)


def test_cvd_points_track_cumulative_delta():
    trades = [
        make_trade(1, 100.0, 2.0, "buy"),
        make_trade(2, 101.0, 1.0, "sell"),
        make_trade(3, 102.0, 3.0, "buy"),
    ]

    result = CVDEngine().calculate(trades)

    assert len(result.points) == 3

    assert result.points[0].delta == pytest.approx(2.0)
    assert result.points[0].cumulative_delta == pytest.approx(2.0)

    assert result.points[1].delta == pytest.approx(-1.0)
    assert result.points[1].cumulative_delta == pytest.approx(1.0)

    assert result.points[2].delta == pytest.approx(3.0)
    assert result.points[2].cumulative_delta == pytest.approx(4.0)


def test_cvd_supports_starting_cvd():
    trades = [
        make_trade(1, 100.0, 2.0, "buy"),
        make_trade(2, 101.0, 1.0, "sell"),
    ]

    result = CVDEngine().calculate(
        trades,
        starting_cvd=10.0,
    )

    assert result.starting_cvd == pytest.approx(10.0)
    assert result.delta == pytest.approx(1.0)
    assert result.cumulative_delta == pytest.approx(11.0)


def test_cvd_detects_bullish_trend():
    trades = [
        make_trade(1, 100.0, 1.0, "buy"),
        make_trade(2, 102.0, 2.0, "buy"),
    ]

    result = CVDEngine().calculate(trades)

    assert result.price_change == pytest.approx(2.0)
    assert result.cvd_change == pytest.approx(3.0)
    assert result.trend == "BULLISH"
    assert result.divergence == "NONE"


def test_cvd_detects_bearish_trend():
    trades = [
        make_trade(1, 102.0, 1.0, "sell"),
        make_trade(2, 100.0, 2.0, "sell"),
    ]

    result = CVDEngine().calculate(trades)

    assert result.price_change == pytest.approx(-2.0)
    assert result.cvd_change == pytest.approx(-3.0)
    assert result.trend == "BEARISH"
    assert result.divergence == "NONE"


def test_cvd_detects_bullish_divergence():
    trades = [
        make_trade(1, 102.0, 1.0, "sell"),
        make_trade(2, 100.0, 1.0, "buy"),
        make_trade(3, 99.0, 2.0, "buy"),
    ]

    result = CVDEngine().calculate(trades)

    assert result.price_change < 0
    assert result.cvd_change > 0
    assert result.trend == "NEUTRAL"
    assert result.divergence == "BULLISH_DIVERGENCE"


def test_cvd_detects_bearish_divergence():
    trades = [
        make_trade(1, 100.0, 1.0, "buy"),
        make_trade(2, 102.0, 2.0, "sell"),
        make_trade(3, 103.0, 3.0, "sell"),
    ]

    result = CVDEngine().calculate(trades)

    assert result.price_change > 0
    assert result.cvd_change < 0
    assert result.trend == "NEUTRAL"
    assert result.divergence == "BEARISH_DIVERGENCE"


def test_cvd_empty_trades():
    result = CVDEngine().calculate([])

    assert result.buy_volume == 0.0
    assert result.sell_volume == 0.0
    assert result.delta == 0.0
    assert result.starting_cvd == 0.0
    assert result.cumulative_delta == 0.0
    assert result.price_change == 0.0
    assert result.cvd_change == 0.0
    assert result.trend == "NEUTRAL"
    assert result.divergence == "NONE"
    assert result.points == []



def test_cvd_supports_negative_starting_cvd():
    trades = [
        make_trade(1, 100.0, 2.0, "buy"),
        make_trade(2, 101.0, 1.0, "sell"),
    ]

    result = CVDEngine().calculate(
        trades,
        starting_cvd=-10.0,
    )

    assert result.starting_cvd == pytest.approx(-10.0)
    assert result.delta == pytest.approx(1.0)
    assert result.cumulative_delta == pytest.approx(-9.0)
    assert result.cvd_change == pytest.approx(1.0)
from indicators.vwap_context import (
    build_vwap_context,
)
from microstructure.market_context_engine import (
    MarketContextEngine,
)
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


def test_market_context_engine_builds_snapshot():
    trades = [
        make_trade(1000, 100.0, 5.0, "buy"),
        make_trade(1010, 101.0, 2.0, "buy"),
        make_trade(1020, 99.0, 1.0, "sell"),
        make_trade(1030, 102.0, 4.0, "buy"),
    ]

    result = MarketContextEngine().build(
        trades=trades,
        current_price=102.0,
        vwap=100.0,
        previous_vwap=99.0,
    )

    assert result.cvd is not None
    assert result.vwap is not None
    assert result.volume_profile is not None
    assert result.fusion is not None

    assert result.vwap.position == "ABOVE_VWAP"
    assert result.vwap.trend == "BULLISH"

    assert result.volume_profile.total_volume == 12.0


def test_market_context_engine_rejects_empty_trades():
    try:
        MarketContextEngine().build(
            trades=[],
            current_price=100.0,
            vwap=99.0,
        )
    except ValueError as exc:
        assert (
            "Trades are required for market context"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError for empty trades."
        )
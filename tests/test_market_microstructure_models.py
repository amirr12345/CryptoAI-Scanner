import pytest

from models.order_book import OrderBook
from models.order_book_level import OrderBookLevel
from models.trade import Trade


def test_trade_creation():
    trade = Trade(
        timestamp=1_700_000_000,
        price=100.0,
        volume=2.5,
        side="buy",
        symbol="BTC",
    )

    assert trade.timestamp == 1_700_000_000
    assert trade.price == 100.0
    assert trade.volume == 2.5
    assert trade.side == "buy"
    assert trade.symbol == "BTC"


def test_trade_accepts_sell_side():
    trade = Trade(
        timestamp=1_700_000_000,
        price=100.0,
        volume=1.0,
        side="SELL",
        symbol="BTC",
    )

    assert trade.side == "SELL"


def test_trade_rejects_negative_price():
    with pytest.raises(
        ValueError,
        match="Trade price cannot be negative",
    ):
        Trade(
            timestamp=1_700_000_000,
            price=-1.0,
            volume=1.0,
            side="buy",
            symbol="BTC",
        )


def test_trade_rejects_negative_volume():
    with pytest.raises(
        ValueError,
        match="Trade volume cannot be negative",
    ):
        Trade(
            timestamp=1_700_000_000,
            price=100.0,
            volume=-1.0,
            side="buy",
            symbol="BTC",
        )


def test_trade_rejects_invalid_side():
    with pytest.raises(
        ValueError,
        match="Trade side must be 'buy' or 'sell'",
    ):
        Trade(
            timestamp=1_700_000_000,
            price=100.0,
            volume=1.0,
            side="unknown",
            symbol="BTC",
        )


def test_order_book_level_creation():
    level = OrderBookLevel(
        price=100.0,
        volume=5.0,
    )

    assert level.price == 100.0
    assert level.volume == 5.0


def test_order_book_level_rejects_negative_price():
    with pytest.raises(
        ValueError,
        match="Order book price cannot be negative",
    ):
        OrderBookLevel(
            price=-1.0,
            volume=5.0,
        )


def test_order_book_level_rejects_negative_volume():
    with pytest.raises(
        ValueError,
        match="Order book volume cannot be negative",
    ):
        OrderBookLevel(
            price=100.0,
            volume=-1.0,
        )


def test_order_book_best_bid_and_ask():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
        bids=[
            OrderBookLevel(price=99.0, volume=5.0),
            OrderBookLevel(price=100.0, volume=3.0),
            OrderBookLevel(price=98.0, volume=10.0),
        ],
        asks=[
            OrderBookLevel(price=101.0, volume=4.0),
            OrderBookLevel(price=102.0, volume=8.0),
            OrderBookLevel(price=103.0, volume=2.0),
        ],
    )

    assert order_book.best_bid().price == 100.0
    assert order_book.best_ask().price == 101.0


def test_order_book_empty_best_levels():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
    )

    assert order_book.best_bid() is None
    assert order_book.best_ask() is None


def test_order_book_bid_and_ask_volume():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
        bids=[
            OrderBookLevel(price=100.0, volume=5.0),
            OrderBookLevel(price=99.0, volume=7.0),
            OrderBookLevel(price=98.0, volume=10.0),
        ],
        asks=[
            OrderBookLevel(price=101.0, volume=4.0),
            OrderBookLevel(price=102.0, volume=6.0),
            OrderBookLevel(price=103.0, volume=8.0),
        ],
    )

    assert order_book.bid_volume() == 22.0
    assert order_book.ask_volume() == 18.0


def test_order_book_bid_and_ask_volume_with_level_limit():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
        bids=[
            OrderBookLevel(price=100.0, volume=5.0),
            OrderBookLevel(price=99.0, volume=7.0),
            OrderBookLevel(price=98.0, volume=10.0),
        ],
        asks=[
            OrderBookLevel(price=101.0, volume=4.0),
            OrderBookLevel(price=102.0, volume=6.0),
            OrderBookLevel(price=103.0, volume=8.0),
        ],
    )

    assert order_book.bid_volume(2) == 12.0
    assert order_book.ask_volume(2) == 10.0


def test_order_book_imbalance():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
        bids=[
            OrderBookLevel(price=100.0, volume=15.0),
        ],
        asks=[
            OrderBookLevel(price=101.0, volume=5.0),
        ],
    )

    assert order_book.imbalance() == pytest.approx(0.5)


def test_order_book_imbalance_can_be_negative():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
        bids=[
            OrderBookLevel(price=100.0, volume=5.0),
        ],
        asks=[
            OrderBookLevel(price=101.0, volume=15.0),
        ],
    )

    assert order_book.imbalance() == pytest.approx(-0.5)


def test_order_book_zero_imbalance_when_empty():
    order_book = OrderBook(
        symbol="BTC",
        timestamp=1_700_000_000,
    )

    assert order_book.imbalance() == 0.0
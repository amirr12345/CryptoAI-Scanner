from __future__ import annotations

from unittest.mock import Mock, patch

from api.okx import OKXExchange
from models.candle import Candle
from models.order_book import OrderBook
from models.ticker import Ticker
from models.trade import Trade


def test_normalize_symbol():
    assert (
        OKXExchange.normalize_symbol(
            "btc-usdt"
        )
        == "BTCUSDT"
    )

    assert (
        OKXExchange.normalize_symbol(
            "BTCUSDT"
        )
        == "BTCUSDT"
    )


def test_normalize_symbol_rejects_irt():
    try:
        OKXExchange.normalize_symbol(
            "BTCIRT"
        )
    except ValueError as exc:
        assert "USDT" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_get_ticker():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "last": "63000",
                "high24h": "64000",
                "low24h": "62000",
                "vol24h": "1000",
            }
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        ticker = OKXExchange().get_ticker(
            "BTCUSDT"
        )

    assert isinstance(
        ticker,
        Ticker,
    )

    assert ticker.symbol == "BTCUSDT"
    assert ticker.last_price == 63000
    assert ticker.high == 64000
    assert ticker.low == 62000
    assert ticker.volume == 1000


def test_get_markets_usdt_only():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "quoteCcy": "USDT",
                "state": "live",
            },
            {
                "instId": "ETH-USDT",
                "quoteCcy": "USDT",
                "state": "live",
            },
            {
                "instId": "BTC-USDC",
                "quoteCcy": "USDC",
                "state": "live",
            },
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        markets = (
            OKXExchange().get_markets()
        )

    assert set(
        markets["stats"].keys()
    ) == {
        "btc-usdt",
        "eth-usdt",
    }


def test_get_history():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            [
                "1700000120000",
                "102",
                "104",
                "100",
                "103",
                "20",
                "2000",
                "2000",
                "1",
            ],
            [
                "1700000060000",
                "101",
                "103",
                "99",
                "102",
                "10",
                "1000",
                "1000",
                "1",
            ],
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        candles = (
            OKXExchange().get_history(
                "BTCUSDT",
                resolution="60",
                countback=2,
            )
        )

    assert len(candles) == 2

    assert all(
        isinstance(
            candle,
            Candle,
        )
        for candle in candles
    )

    assert (
        candles[0].timestamp
        == 1700000060
    )

    assert (
        candles[1].timestamp
        == 1700000120
    )


def test_get_history_passes_explicit_range():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ) as mock_get:
        OKXExchange().get_history(
            "BTCUSDT",
            resolution="60",
            countback=100,
            start_timestamp_ms=1700000000000,
            end_timestamp_ms=1700003600000,
        )

    params = (
        mock_get.call_args.kwargs[
            "params"
        ]
    )

    assert (
        params["instId"]
        == "BTC-USDT"
    )

    assert (
        params["bar"]
        == "1H"
    )

    assert (
        params["limit"]
        == "100"
    )

    assert (
        params["after"]
        == "1700003600000"
    )

    assert (
        params["before"]
        == "1700000000000"
    )


def test_get_trades():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "tradeId": "2",
                "side": "sell",
                "sz": "0.5",
                "px": "63010",
                "ts": "1700000001123",
            },
            {
                "instId": "BTC-USDT",
                "tradeId": "1",
                "side": "buy",
                "sz": "0.25",
                "px": "63000",
                "ts": "1700000000123",
            },
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        trades = (
            OKXExchange().get_trades(
                "BTCUSDT",
                limit=100,
            )
        )

    assert len(trades) == 2

    assert all(
        isinstance(
            trade,
            Trade,
        )
        for trade in trades
    )

    assert (
        trades[0].symbol
        == "BTC"
    )

    assert (
        trades[0].timestamp
        == 1700000000123
    )

    assert (
        trades[0].side
        == "buy"
    )

    assert (
        trades[1].symbol
        == "BTC"
    )

    assert (
        trades[1].timestamp
        == 1700000001123
    )

    assert (
        trades[1].side
        == "sell"
    )


def test_get_trades_limit():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ) as mock_get:
        OKXExchange().get_trades(
            "BTCUSDT",
            limit=100,
        )

    params = (
        mock_get.call_args.kwargs[
            "params"
        ]
    )

    assert (
        params["instId"]
        == "BTC-USDT"
    )

    assert (
        params["limit"]
        == "100"
    )


def test_get_historical_trades_paginates():
    first = Mock()
    first.raise_for_status.return_value = None
    first.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "tradeId": "200",
                "side": "buy",
                "sz": "0.1",
                "px": "63000",
                "ts": "1700000002000",
            },
            {
                "instId": "BTC-USDT",
                "tradeId": "199",
                "side": "sell",
                "sz": "0.2",
                "px": "62990",
                "ts": "1700000001000",
            },
        ],
    }

    second = Mock()
    second.raise_for_status.return_value = None
    second.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "tradeId": "198",
                "side": "buy",
                "sz": "0.3",
                "px": "62980",
                "ts": "1699999996000",
            },
        ],
    }

    with patch(
        "api.okx.requests.get",
        side_effect=[
            first,
            second,
        ],
    ) as mock_get:
        trades = (
            OKXExchange().get_historical_trades(
                "BTCUSDT",
                end_timestamp_ms=1700000002000,
                lookback_seconds=5,
                max_pages=5,
            )
        )

    assert len(trades) == 2

    assert (
        trades[0].timestamp
        == 1700000001000
    )

    assert (
        trades[1].timestamp
        == 1700000002000
    )

    assert (
        mock_get.call_count
        == 2
    )

    second_params = (
        mock_get.call_args_list[1]
        .kwargs["params"]
    )

    assert (
        second_params["after"]
        == "199"
    )


def test_get_historical_trades_respects_as_of():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "tradeId": "3",
                "side": "buy",
                "sz": "0.1",
                "px": "63000",
                "ts": "1700000003000",
            },
            {
                "instId": "BTC-USDT",
                "tradeId": "2",
                "side": "sell",
                "sz": "0.2",
                "px": "62990",
                "ts": "1700000002000",
            },
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        trades = (
            OKXExchange().get_historical_trades(
                "BTCUSDT",
                end_timestamp_ms=1700000002000,
                lookback_seconds=5,
                max_pages=1,
            )
        )

    assert len(trades) == 1

    assert (
        trades[0].timestamp
        == 1700000002000
    )

    assert (
        trades[0].symbol
        == "BTC"
    )


def test_get_historical_trades_stops_at_boundary():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "tradeId": "3",
                "side": "buy",
                "sz": "0.1",
                "px": "63000",
                "ts": "1700000003000",
            },
            {
                "instId": "BTC-USDT",
                "tradeId": "2",
                "side": "sell",
                "sz": "0.2",
                "px": "62990",
                "ts": "1699999980000",
            },
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ) as mock_get:
        trades = (
            OKXExchange().get_historical_trades(
                "BTCUSDT",
                end_timestamp_ms=1700000002000,
                lookback_seconds=5,
                max_pages=5,
            )
        )

    assert trades == []

    assert (
        mock_get.call_count
        == 1
    )


def test_get_orderbook():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT",
                "ts": "1700000000123",
                "bids": [
                    [
                        "63000",
                        "1.5",
                        "0",
                        "2",
                    ],
                    [
                        "62990",
                        "2.0",
                        "0",
                        "3",
                    ],
                ],
                "asks": [
                    [
                        "63010",
                        "1.0",
                        "0",
                        "1",
                    ],
                    [
                        "63020",
                        "3.0",
                        "0",
                        "2",
                    ],
                ],
            }
        ],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        orderbook = (
            OKXExchange().get_orderbook(
                "BTCUSDT",
                depth=2,
            )
        )

    assert isinstance(
        orderbook,
        OrderBook,
    )

    assert (
        orderbook.symbol
        == "BTC"
    )

    assert (
        orderbook.timestamp
        == 1700000000123
    )

    assert len(
        orderbook.bids
    ) == 2

    assert len(
        orderbook.asks
    ) == 2

    assert (
        orderbook.bids[0].price
        == 63000
    )

    assert (
        orderbook.asks[0].price
        == 63010
    )


def test_api_error():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "50001",
        "msg": "error",
        "data": [],
    }

    with patch(
        "api.okx.requests.get",
        return_value=response,
    ):
        try:
            OKXExchange().get_ticker(
                "BTCUSDT"
            )
        except ValueError as exc:
            assert (
                "OKX request failed"
                in str(exc)
            )
        else:
            raise AssertionError(
                "Expected ValueError."
            )
from __future__ import annotations

from unittest.mock import Mock, patch

from api.gateio import GateIOExchange
from models.candle import Candle
from models.order_book import OrderBook
from models.ticker import Ticker
from models.trade import Trade


def test_normalize_symbol():
    assert (
        GateIOExchange.normalize_symbol(
            "btc-usdt"
        )
        == "BTCUSDT"
    )

    assert (
        GateIOExchange.normalize_symbol(
            "BTC_USDT"
        )
        == "BTCUSDT"
    )

    assert (
        GateIOExchange.normalize_symbol(
            "BTCUSDT"
        )
        == "BTCUSDT"
    )


def test_normalize_symbol_rejects_irt():
    try:
        GateIOExchange.normalize_symbol(
            "BTCIRT"
        )
    except ValueError as exc:
        assert "USDT" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_gate_symbol():
    assert (
        GateIOExchange._gate_symbol(
            "BTCUSDT"
        )
        == "BTC_USDT"
    )


def test_base_symbol():
    assert (
        GateIOExchange._base_symbol(
            "BTCUSDT"
        )
        == "BTC"
    )


def test_get_ticker():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "currency_pair": "BTC_USDT",
            "last": "63123.8",
            "high_24h": "63187.6",
            "low_24h": "62801.1",
            "base_volume": "1010.142788",
            "quote_volume": "63653495",
        }
    ]

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        ticker = (
            GateIOExchange()
            .get_ticker("BTCUSDT")
        )

    assert isinstance(
        ticker,
        Ticker,
    )

    assert (
        ticker.symbol
        == "BTCUSDT"
    )

    assert (
        ticker.last_price
        == 63123.8
    )

    assert (
        ticker.high
        == 63187.6
    )

    assert (
        ticker.low
        == 62801.1
    )


def test_get_markets_usdt_only():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "currency_pair": "BTC_USDT",
            "last": "63000",
            "base_volume": "100",
        },
        {
            "currency_pair": "ETH_USDT",
            "last": "1800",
            "base_volume": "200",
        },
        {
            "currency_pair": "BTC_USDC",
            "last": "63000",
            "base_volume": "100",
        },
    ]

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        markets = (
            GateIOExchange()
            .get_markets()
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
    response.json.return_value = [
        [
            "1786809600",
            "1694913.42217450",
            "63125.8",
            "63125.8",
            "63066.4",
            "63097.7",
            "26.86387400",
            "true",
        ],
        [
            "1786806000",
            "1000000",
            "63100",
            "63110",
            "63000",
            "63050",
            "15",
            "true",
        ],
    ]

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        candles = (
            GateIOExchange()
            .get_history(
                "BTCUSDT",
                resolution="60",
                countback=2,
            )
        )

    assert len(
        candles
    ) == 2

    assert all(
        isinstance(
            candle,
            Candle,
        )
        for candle in candles
    )

    assert (
        candles[0].timestamp
        == 1786806000
    )

    assert (
        candles[0].open
        == 63050
    )

    assert (
        candles[0].close
        == 63100
    )

    assert (
        candles[1].timestamp
        == 1786809600
    )

    assert (
        candles[1].open
        == 63097.7
    )

    assert (
        candles[1].close
        == 63125.8
    )


def test_get_history_explicit_range():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = []

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ) as mock_get:
        GateIOExchange().get_history(
            "BTCUSDT",
            resolution="60",
            countback=10,
            start_timestamp=1786700000,
            end_timestamp=1786800000,
        )

    params = (
        mock_get.call_args.kwargs[
            "params"
        ]
    )

    assert (
        params["currency_pair"]
        == "BTC_USDT"
    )

    assert (
        params["interval"]
        == "1h"
    )

    assert (
        params["from"]
        == 1786700000
    )

    assert (
        params["to"]
        == 1786800000
    )

    assert "limit" not in params


def test_get_trades():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "id": "215168497",
            "create_time": "1786824084",
            "create_time_ms": "1786824084512.238000",
            "currency_pair": "BTC_USDT",
            "side": "buy",
            "amount": "0.001057",
            "price": "63116",
            "sequence_id": "215168497",
        },
        {
            "id": "215168496",
            "create_time": "1786824082",
            "create_time_ms": "1786824082080.050000",
            "currency_pair": "BTC_USDT",
            "side": "sell",
            "amount": "0.002376",
            "price": "63116",
            "sequence_id": "215168496",
        },
    ]

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        trades = (
            GateIOExchange()
            .get_trades(
                "BTCUSDT",
                limit=100,
            )
        )

    assert len(
        trades
    ) == 2

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
        trades[0].side
        == "sell"
    )

    assert (
        trades[0].timestamp
        == 1786824082080
    )

    assert (
        trades[1].symbol
        == "BTC"
    )

    assert (
        trades[1].side
        == "buy"
    )

    assert (
        trades[1].timestamp
        == 1786824084512
    )


def test_get_historical_trades_paginates():
    first = Mock()
    first.raise_for_status.return_value = None
    first.json.return_value = [
        {
            "id": "215168497",
            "create_time": "1786824084",
            "create_time_ms": "1786824084512.000",
            "currency_pair": "BTC_USDT",
            "side": "buy",
            "amount": "0.1",
            "price": "63116",
            "sequence_id": "215168497",
        },
        {
            "id": "215168496",
            "create_time": "1786824082",
            "create_time_ms": "1786824082080.000",
            "currency_pair": "BTC_USDT",
            "side": "sell",
            "amount": "0.2",
            "price": "63115",
            "sequence_id": "215168496",
        },
    ]

    second = Mock()
    second.raise_for_status.return_value = None
    second.json.return_value = [
        {
            "id": "215168495",
            "create_time": "1786824077",
            "create_time_ms": "1786824077604.000",
            "currency_pair": "BTC_USDT",
            "side": "sell",
            "amount": "0.3",
            "price": "63114",
            "sequence_id": "215168495",
        },
        {
            "id": "215168494",
            "create_time": "1786824071",
            "create_time_ms": "1786824071975.000",
            "currency_pair": "BTC_USDT",
            "side": "buy",
            "amount": "0.4",
            "price": "63113",
            "sequence_id": "215168494",
        },
        {
            "id": "215168493",
            "create_time": "1786800000",
            "create_time_ms": "1786800000000.000",
            "currency_pair": "BTC_USDT",
            "side": "buy",
            "amount": "0.5",
            "price": "63000",
            "sequence_id": "215168493",
        },
    ]

    with patch(
        "api.gateio.requests.get",
        side_effect=[
            first,
            second,
        ],
    ) as mock_get:
        trades = (
            GateIOExchange()
            .get_historical_trades(
                "BTCUSDT",
                end_timestamp_ms=1786824084512,
                lookback_seconds=3600,
                max_pages=5,
            )
        )

    assert len(
        trades
    ) == 4

    assert (
        trades[0].timestamp
        == 1786824071975
    )

    assert (
        trades[-1].timestamp
        == 1786824084512
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
        second_params["last_id"]
        == "215168496"
    )

    assert (
        second_params["reverse"]
        == "true"
    )


def test_get_historical_trades_never_includes_future():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "id": "3",
            "create_time": "1786825000",
            "create_time_ms": "1786825000000",
            "currency_pair": "BTC_USDT",
            "side": "buy",
            "amount": "0.1",
            "price": "63200",
        },
        {
            "id": "2",
            "create_time": "1786824000",
            "create_time_ms": "1786824000000",
            "currency_pair": "BTC_USDT",
            "side": "sell",
            "amount": "0.2",
            "price": "63100",
        },
    ]

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        trades = (
            GateIOExchange()
            .get_historical_trades(
                "BTCUSDT",
                end_timestamp_ms=1786824000000,
                lookback_seconds=3600,
                max_pages=1,
            )
        )

    assert len(
        trades
    ) == 1

    assert (
        trades[0].timestamp
        == 1786824000000
    )


def test_get_orderbook():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "id": 123456,
        "current": 1786824085000,
        "update": 1786824084999,
        "bids": [
            [
                "63115.9",
                "1.5",
            ],
            [
                "63115.8",
                "2.0",
            ],
        ],
        "asks": [
            [
                "63116.0",
                "1.0",
            ],
            [
                "63116.1",
                "3.0",
            ],
        ],
    }

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        orderbook = (
            GateIOExchange()
            .get_orderbook(
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
        == 1786824085000
    )

    assert (
        len(orderbook.bids)
        == 2
    )

    assert (
        len(orderbook.asks)
        == 2
    )

    assert (
        orderbook.bids[0].price
        == 63115.9
    )

    assert (
        orderbook.asks[0].price
        == 63116.0
    )


def test_rejects_non_usdt():
    try:
        GateIOExchange().get_ticker(
            "BTCIRT"
        )
    except ValueError as exc:
        assert "USDT" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_api_request_error():
    response = Mock()
    response.raise_for_status.return_value = None

    def raise_json_error():
        raise ValueError(
            "invalid json"
        )

    response.json.side_effect = (
        raise_json_error
    )

    with patch(
        "api.gateio.requests.get",
        return_value=response,
    ):
        try:
            GateIOExchange().get_ticker(
                "BTCUSDT"
            )
        except ValueError as exc:
            assert (
                "invalid json"
                in str(exc)
            )
        else:
            raise AssertionError(
                "Expected ValueError."
            )
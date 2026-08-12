from unittest.mock import Mock, patch

import pytest

from api.nobitex import NobitexExchange
from models.candle import Candle


def test_get_ticker():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "status": "ok",
        "stats": {
            "btc-rls": {
                "latest": "100000",
                "dayHigh": "110000",
                "dayLow": "90000",
                "volumeSrc": "12.5",
            }
        },
    }

    with patch(
        "api.nobitex.requests.get",
        return_value=response,
    ) as mock_get:

        ticker = NobitexExchange().get_ticker("btc")

    assert ticker.symbol == "BTC"
    assert ticker.last_price == 100000
    assert ticker.high == 110000
    assert ticker.low == 90000
    assert ticker.volume == 12.5

    mock_get.assert_called_once()

    request_params = mock_get.call_args.kwargs["params"]

    assert request_params["srcCurrency"] == "btc"
    assert request_params["dstCurrency"] == "rls"


def test_get_markets():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "status": "ok",
        "stats": {
            "btc-rls": {},
            "eth-rls": {},
        },
    }

    with patch(
        "api.nobitex.requests.get",
        return_value=response,
    ) as mock_get:

        data = NobitexExchange().get_markets()

    assert data["status"] == "ok"
    assert "btc-rls" in data["stats"]
    assert "eth-rls" in data["stats"]

    mock_get.assert_called_once()


def test_get_history():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "ok",
        "t": [1000, 1060],
        "o": [100, 101],
        "h": [102, 103],
        "l": [99, 100],
        "c": [101, 102],
        "v": [10, 12],
    }

    with patch(
        "api.nobitex.requests.get",
        return_value=response,
    ) as mock_get:

        candles = NobitexExchange().get_history(
            symbol="BTC",
            resolution="60",
            countback=2,
        )

    assert len(candles) == 2
    assert all(
        isinstance(candle, Candle)
        for candle in candles
    )

    assert candles[0].timestamp == 1000
    assert candles[0].open == 100
    assert candles[0].high == 102
    assert candles[0].low == 99
    assert candles[0].close == 101
    assert candles[0].volume == 10

    request_params = mock_get.call_args.kwargs["params"]

    assert request_params["symbol"] == "BTCIRT"
    assert request_params["resolution"] == "60"
    assert request_params["countback"] == 2
    assert "to" in request_params
    assert isinstance(request_params["to"], int)


def test_get_history_accepts_irt_symbol():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "ok",
        "t": [1000],
        "o": [100],
        "h": [102],
        "l": [99],
        "c": [101],
        "v": [10],
    }

    with patch(
        "api.nobitex.requests.get",
        return_value=response,
    ) as mock_get:

        NobitexExchange().get_history(
            symbol="BTCIRT",
            resolution="60",
            countback=1,
        )

    request_params = mock_get.call_args.kwargs["params"]

    assert request_params["symbol"] == "BTCIRT"


def test_get_history_rejects_empty_symbol():
    with pytest.raises(
        ValueError,
        match="Symbol cannot be empty",
    ):
        NobitexExchange().get_history("")


def test_get_history_rejects_empty_resolution():
    with pytest.raises(
        ValueError,
        match="Resolution cannot be empty",
    ):
        NobitexExchange().get_history(
            symbol="BTC",
            resolution="",
        )


def test_get_history_rejects_invalid_countback():
    with pytest.raises(
        ValueError,
        match="Countback must be greater than zero",
    ):
        NobitexExchange().get_history(
            symbol="BTC",
            countback=0,
        )


def test_get_history_rejects_large_countback():
    with pytest.raises(
        ValueError,
        match="Countback cannot be greater than 500",
    ):
        NobitexExchange().get_history(
            symbol="BTC",
            countback=501,
        )


def test_get_history_rejects_invalid_response():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "error",
        "errmsg": "Invalid resolution!",
    }

    with patch(
        "api.nobitex.requests.get",
        return_value=response,
    ):
        with pytest.raises(
            ValueError,
            match="history request failed",
        ):
            NobitexExchange().get_history(
                symbol="BTC",
                resolution="invalid",
                countback=10,
            )


def test_get_history_rejects_inconsistent_arrays():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "ok",
        "t": [1000, 1060],
        "o": [100],
        "h": [102, 103],
        "l": [99, 100],
        "c": [101, 102],
        "v": [10, 12],
    }

    with patch(
        "api.nobitex.requests.get",
        return_value=response,
    ):
        with pytest.raises(
            ValueError,
            match="array lengths are inconsistent",
        ):
            NobitexExchange().get_history(
                symbol="BTC",
                resolution="60",
                countback=2,
            )
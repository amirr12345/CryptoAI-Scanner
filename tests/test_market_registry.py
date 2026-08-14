from core.market_registry import (
    MarketRegistry,
)


def test_btc_irt_descriptor():
    registry = MarketRegistry()

    descriptor = (
        registry.build_descriptor(
            "BTCIRT"
        )
    )

    assert descriptor.market_symbol == "BTCIRT"
    assert descriptor.base_asset == "BTC"
    assert descriptor.quote_asset == "IRT"
    assert descriptor.analysis_market == "BTCUSDT"
    assert descriptor.execution_market == "BTCIRT"


def test_btc_usdt_descriptor():
    registry = MarketRegistry()

    descriptor = (
        registry.build_descriptor(
            "BTCUSDT"
        )
    )

    assert descriptor.market_symbol == "BTCUSDT"
    assert descriptor.base_asset == "BTC"
    assert descriptor.quote_asset == "USDT"
    assert descriptor.analysis_market == "BTCUSDT"
    assert descriptor.execution_market == "BTCUSDT"


def test_usdt_irt_is_bridge_market():
    registry = MarketRegistry()

    descriptor = (
        registry.build_descriptor(
            "USDTIRT"
        )
    )

    assert descriptor.market_symbol == "USDTIRT"
    assert descriptor.base_asset == "USDT"
    assert descriptor.quote_asset == "IRT"
    assert descriptor.analysis_market == "USDTIRT"
    assert descriptor.execution_market == "USDTIRT"


def test_normalization():
    registry = MarketRegistry()

    descriptor = (
        registry.register_symbol(
            "btCirt"
        )
    )

    assert descriptor.market_symbol == "BTCIRT"

    assert (
        registry.analysis_market(
            "btCirt"
        )
        == "BTCUSDT"
    )


def test_usdt_market():
    registry = MarketRegistry()

    assert (
        registry.usdt_market("btc")
        == "BTCUSDT"
    )

    assert (
        registry.usdt_market("ETH")
        == "ETHUSDT"
    )


def test_irt_market():
    registry = MarketRegistry()

    assert (
        registry.irt_market("btc")
        == "BTCIRT"
    )


def test_implicit_usdt_price():
    registry = MarketRegistry()

    result = (
        registry.implicit_usdt_price(
            base_irt_price=11_830_000_000,
            usdt_irt_price=187_000,
        )
    )

    expected = (
        11_830_000_000
        / 187_000
    )

    assert result == expected


def test_require_auto_registers():
    registry = MarketRegistry()

    assert registry.get("BTCIRT") is None

    descriptor = registry.require(
        "BTCIRT"
    )

    assert descriptor.market_symbol == "BTCIRT"

    assert (
        registry.get("BTCIRT")
        == descriptor
    )


def test_registry_contains_registered_markets():
    registry = MarketRegistry()

    registry.register_symbol(
        "BTCIRT"
    )

    registry.register_symbol(
        "BTCUSDT"
    )

    symbols = registry.symbols()

    assert symbols == [
        "BTCIRT",
        "BTCUSDT",
    ]
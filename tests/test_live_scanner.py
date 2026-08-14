from __future__ import annotations

from core.market_registry import MarketRegistry
from models.candle import Candle
from services.live_confluence_service import (
    LiveConfluenceResult,
)
from tools.live_scanner import LiveScanner


class FakeMarketService:
    def __init__(self):
        self.history_calls = []

    def markets(self):
        return {
            "stats": {
                "BTC-usdt": {},
                "ETH-usdt": {},
                "BTC-rls": {},
                "ETH-rls": {},
            }
        }

    def history(
        self,
        symbol,
        resolution="60",
        countback=200,
    ):
        self.history_calls.append(
            (
                symbol,
                resolution,
                countback,
            )
        )

        return [
            Candle(
                timestamp=1000,
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=100.0,
            )
        ]


class FakeTradeStore:
    def latest_timestamp(
        self,
        symbol,
    ):
        return 1300


class FakeCandleStore:
    def get_recent(
        self,
        symbol,
        timeframe="60",
        limit=200,
    ):
        return []

    def latest(
        self,
        symbol,
        timeframe="60",
    ):
        return None


class FakeConfluenceService:
    def __init__(self):
        self.calls = []

    def evaluate(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        return LiveConfluenceResult(
            symbol=kwargs["symbol"],
            setup=None,
            confluence=None,
            status="NO_STRUCTURE_SETUP",
            reason="No setup.",
        )


def test_extract_usdt_markets():
    symbols = (
        LiveScanner._extract_usdt_markets(
            {
                "stats": {
                    "BTC-usdt": {},
                    "ETH-usdt": {},
                    "BTC-rls": {},
                    "ETH-rls": {},
                    "INVALID": {},
                }
            }
        )
    )

    assert symbols == [
        "BTCUSDT",
        "ETHUSDT",
    ]


def test_scan_uses_usdt_market_directly():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()
    registry.register_symbol(
        "BTCUSDT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    result = scanner.scan_market(
        "BTCUSDT"
    )

    assert (
        result.status
        == "NO_STRUCTURE_SETUP"
    )

    assert market.history_calls == [
        (
            "BTCUSDT",
            "60",
            200,
        )
    ]

    assert len(
        confluence.calls
    ) == 1

    assert (
        confluence.calls[0]["symbol"]
        == "BTC"
    )

    assert (
        confluence.calls[0][
            "latest_trade_timestamp"
        ]
        == 1300
    )


def test_scan_discovers_only_usdt_markets():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()
    registry.register_symbol(
        "BTCUSDT"
    )
    registry.register_symbol(
        "ETHUSDT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    results, summary = (
        scanner.scan()
    )

    assert len(results) == 2

    assert (
        summary.total_symbols
        == 2
    )

    assert (
        summary.no_structure_setup
        == 2
    )

    assert (
        summary.errors
        == 0
    )

    for (
        base,
        descriptor,
        result,
    ) in results:
        assert (
            descriptor.analysis_market
            == f"{base}USDT"
        )

        assert (
            descriptor.execution_market
            == f"{base}USDT"
        )

        assert (
            result.status
            == "NO_STRUCTURE_SETUP"
        )


def test_irt_market_can_be_execution_fallback():
    registry = MarketRegistry()

    registry.register_symbol(
        "BTCIRT"
    )

    descriptor = (
        registry.build_descriptor(
            "BTCIRT"
        )
    )

    assert (
        descriptor.base_asset
        == "BTC"
    )

    assert (
        descriptor.quote_asset
        == "IRT"
    )

    assert (
        descriptor.analysis_market
        == "BTCUSDT"
    )

    assert (
        descriptor.execution_market
        == "BTCIRT"
    )


def test_btc_uses_btcusdt_for_analysis():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()

    registry.register_symbol(
        "BTCIRT"
    )

    registry.register_symbol(
        "BTCUSDT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    result = scanner.scan_market(
        "BTCUSDT"
    )

    assert (
        result.status
        == "NO_STRUCTURE_SETUP"
    )

    assert market.history_calls == [
        (
            "BTCUSDT",
            "60",
            200,
        )
    ]

    assert len(
        confluence.calls
    ) == 1

    assert (
        confluence.calls[0]["symbol"]
        == "BTC"
    )


def test_eth_uses_ethusdt_for_analysis():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()

    registry.register_symbol(
        "ETHIRT"
    )

    registry.register_symbol(
        "ETHUSDT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    result = scanner.scan_market(
        "ETHUSDT"
    )

    assert (
        result.status
        == "NO_STRUCTURE_SETUP"
    )

    assert market.history_calls == [
        (
            "ETHUSDT",
            "60",
            200,
        )
    ]

    assert len(
        confluence.calls
    ) == 1

    assert (
        confluence.calls[0]["symbol"]
        == "ETH"
    )


def test_usdt_bridge_is_not_converted_to_usdtusdt():
    registry = MarketRegistry()

    descriptor = (
        registry.register_symbol(
            "USDTIRT"
        )
    )

    assert (
        descriptor.analysis_market
        == "USDTIRT"
    )

    assert (
        descriptor.execution_market
        == "USDTIRT"
    )


def test_scan_returns_market_descriptor():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()

    registry.register_symbol(
        "BTCUSDT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    results, _ = scanner.scan(
        symbols=["BTCUSDT"]
    )

    assert len(results) == 1

    base, descriptor, result = (
        results[0]
    )

    assert base == "BTC"

    assert (
        descriptor.market_symbol
        == "BTCUSDT"
    )

    assert (
        descriptor.base_asset
        == "BTC"
    )

    assert (
        descriptor.quote_asset
        == "USDT"
    )

    assert (
        descriptor.analysis_market
        == "BTCUSDT"
    )

    assert (
        descriptor.execution_market
        == "BTCUSDT"
    )

    assert (
        result.status
        == "NO_STRUCTURE_SETUP"
    )


def test_scan_custom_usdt_symbols():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()

    registry.register_symbol(
        "BTCUSDT"
    )

    registry.register_symbol(
        "ETHUSDT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    results, summary = scanner.scan(
        symbols=[
            "BTCUSDT",
            "ETHUSDT",
        ]
    )

    assert len(results) == 2

    assert (
        summary.total_symbols
        == 2
    )

    assert (
        summary.errors
        == 0
    )

    assert (
        summary.no_structure_setup
        == 2
    )
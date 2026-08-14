from __future__ import annotations

from core.market_registry import (
    MarketRegistry,
)
from models.candle import Candle
from services.live_confluence_service import (
    LiveConfluenceResult,
)
from tools.live_scanner import (
    LiveScanner,
)


class FakeMarketService:
    def __init__(self):
        self.history_calls = []

    def markets(self):
        return {
            "stats": {
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
            ),
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


def test_extract_symbols():
    symbols = (
        LiveScanner._extract_symbols(
            {
                "stats": {
                    "BTC-rls": {},
                    "ETH-rls": {},
                    "INVALID": {},
                }
            }
        )
    )

    assert symbols == [
        "BTC",
        "ETH",
    ]


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

    result = scanner.scan_symbol(
        "BTC"
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

    assert (
        len(confluence.calls)
        == 1
    )

    assert (
        confluence.calls[0][
            "latest_trade_timestamp"
        ]
        == 1300
    )


def test_btcirt_falls_back_to_usdt_reference():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()

    registry.register_symbol(
        "BTCIRT"
    )

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
        market_registry=registry,
    )

    descriptor = (
        scanner._resolve_market(
            "BTC"
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


def test_scan_all_symbols():
    market = FakeMarketService()
    confluence = (
        FakeConfluenceService()
    )

    registry = MarketRegistry()

    registry.register_symbol(
        "BTCIRT"
    )

    registry.register_symbol(
        "ETHIRT"
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
        summary.evaluated
        == 0
    )

    assert (
        summary.errors
        == 0
    )

    btc = next(
        item
        for item in results
        if item[0] == "BTC"
    )

    assert (
        btc[1].analysis_market
        == "BTCUSDT"
    )

    assert (
        btc[1].execution_market
        == "BTCIRT"
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
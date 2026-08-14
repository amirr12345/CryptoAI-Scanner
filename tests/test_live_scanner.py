from __future__ import annotations

from dataclasses import dataclass

from core.candle_store import CandleStore
from core.trade_store import TradeStore
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
    def __init__(self):
        pass


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
    symbols = LiveScanner._extract_symbols(
        {
            "stats": {
                "BTC-rls": {},
                "ETH-rls": {},
                "INVALID": {},
            }
        }
    )

    assert symbols == [
        "BTC",
        "ETH",
    ]


def test_scan_symbol():
    market = FakeMarketService()
    confluence = FakeConfluenceService()

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
    )

    result = scanner.scan_symbol(
        "BTC"
    )

    assert result.status == (
        "NO_STRUCTURE_SETUP"
    )

    assert market.history_calls == [
        ("BTC", "60", 200)
    ]

    assert len(
        confluence.calls
    ) == 1

    assert (
        confluence.calls[0]
        ["latest_trade_timestamp"]
        == 1300
    )


def test_scan_all_symbols():
    market = FakeMarketService()
    confluence = FakeConfluenceService()

    scanner = LiveScanner(
        market_service=market,
        candle_store=FakeCandleStore(),
        trade_store=FakeTradeStore(),
        confluence_service=confluence,
    )

    results, summary = scanner.scan()

    assert len(results) == 2
    assert summary.total_symbols == 2
    assert summary.no_structure_setup == 2
    assert summary.evaluated == 0
    assert summary.errors == 0
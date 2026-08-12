from models.analysis_result import AnalysisResult
from services.scanner_service import ScannerService


class FakeExchange:

    def get_markets(self):
        return {
            "status": "ok",
            "stats": {
                "btc-rls": {},
                "eth-rls": {},
                "xrp-rls": {},
                "btc-usdt": {},
            },
        }


class FakeMarketService:

    def __init__(self):
        self.exchange = FakeExchange()

    def markets(self):
        return self.exchange.get_markets()


class FakeAnalysisService:

    def analyze(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ):
        scores = {
            "BTC": 60,
            "ETH": 30,
            "XRP": -20,
        }

        return AnalysisResult(
            symbol=symbol,
            timestamp=1_700_000_000,
            price=100.0,
            total_score=scores[symbol],
            confidence=0.90,
            signal=(
                "STRONG_BUY"
                if scores[symbol] >= 60
                else "BUY"
                if scores[symbol] >= 30
                else "SELL"
            ),
            reasons=[],
            indicators={},
        )


def test_extract_rls_symbols():
    data = {
        "stats": {
            "btc-rls": {},
            "eth-rls": {},
            "btc-usdt": {},
        }
    }

    symbols = ScannerService._extract_rls_symbols(data)

    assert symbols == ["BTC", "ETH"]


def test_scan_multiple_markets():
    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=FakeAnalysisService(),
    )

    result = scanner.scan()

    assert result.successful_count == 3
    assert result.failed_count == 0

    ranked = result.ranked_results

    assert ranked[0].symbol == "BTC"
    assert ranked[0].total_score == 60

    assert ranked[1].symbol == "ETH"
    assert ranked[2].symbol == "XRP"


def test_scan_specific_symbols():
    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=FakeAnalysisService(),
    )

    result = scanner.scan(
        symbols=["BTC", "ETH"],
    )

    assert result.successful_count == 2
    assert result.failed_count == 0


def test_scan_continues_after_symbol_failure():

    class FailingAnalysisService:

        def analyze(
            self,
            symbol: str,
            resolution: str = "60",
            countback: int = 200,
        ):
            if symbol == "ETH":
                raise RuntimeError("analysis failed")

            return AnalysisResult(
                symbol=symbol,
                timestamp=1_700_000_000,
                price=100.0,
                total_score=20,
                confidence=0.80,
                signal="BUY",
                reasons=[],
                indicators={},
            )

    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=FailingAnalysisService(),
    )

    result = scanner.scan(
        symbols=["BTC", "ETH", "XRP"],
    )

    assert result.successful_count == 2
    assert result.failed_count == 1

    assert "ETH" in result.failed_symbols
    assert result.failed_symbols["ETH"] == "analysis failed"
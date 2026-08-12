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

    symbols = ScannerService._extract_rls_symbols(
        data
    )

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
    assert ranked[1].total_score == 30

    assert ranked[2].symbol == "XRP"
    assert ranked[2].total_score == -20


def test_ranked_results_use_confidence_as_tiebreaker():
    class TieAnalysisService:
        def analyze(
            self,
            symbol: str,
            resolution: str = "60",
            countback: int = 200,
        ):
            values = {
                "BTC": (35, 0.45, "BUY"),
                "ETH": (35, 0.60, "BUY"),
                "XRP": (-20, 0.90, "SELL"),
            }

            score, confidence, signal = values[symbol]

            return AnalysisResult(
                symbol=symbol,
                timestamp=1_700_000_000,
                price=100.0,
                total_score=score,
                confidence=confidence,
                signal=signal,
                reasons=[],
                indicators={},
            )

    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=TieAnalysisService(),
    )

    result = scanner.scan(
        symbols=["BTC", "ETH", "XRP"],
    )

    ranked = result.ranked_results

    assert ranked[0].symbol == "ETH"
    assert ranked[0].total_score == 35
    assert ranked[0].confidence == 0.60

    assert ranked[1].symbol == "BTC"
    assert ranked[1].total_score == 35
    assert ranked[1].confidence == 0.45

    assert ranked[2].symbol == "XRP"
    assert ranked[2].total_score == -20


def test_actionable_results_exclude_zero_score():
    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=FakeAnalysisService(),
    )

    result = scanner.scan(
        symbols=["BTC", "ETH", "XRP"],
    )

    actionable = result.actionable_results

    assert len(actionable) == 3

    assert all(
        item.total_score != 0
        for item in actionable
    )

    assert actionable[0].symbol == "BTC"
    assert actionable[1].symbol == "ETH"
    assert actionable[2].symbol == "XRP"


def test_actionable_results_remove_zero_score_markets():
    class MixedScoreAnalysisService:
        def analyze(
            self,
            symbol: str,
            resolution: str = "60",
            countback: int = 200,
        ):
            scores = {
                "BTC": 60,
                "ETH": 0,
                "XRP": -20,
            }

            return AnalysisResult(
                symbol=symbol,
                timestamp=1_700_000_000,
                price=100.0,
                total_score=scores[symbol],
                confidence=(
                    0.90
                    if scores[symbol] != 0
                    else 0.0
                ),
                signal=(
                    "STRONG_BUY"
                    if scores[symbol] >= 40
                    else "BUY"
                    if scores[symbol] >= 20
                    else "SELL"
                    if scores[symbol] <= -20
                    else "HOLD"
                ),
                reasons=[],
                indicators={},
            )

    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=MixedScoreAnalysisService(),
    )

    result = scanner.scan(
        symbols=["BTC", "ETH", "XRP"],
    )

    assert result.successful_count == 3
    assert len(result.results) == 3

    actionable = result.actionable_results

    assert len(actionable) == 2

    assert actionable[0].symbol == "BTC"
    assert actionable[1].symbol == "XRP"

    assert all(
        item.total_score != 0
        for item in actionable
    )


def test_actionable_results_exclude_hold_signals():
    class MixedSignalAnalysisService:
        def analyze(
            self,
            symbol: str,
            resolution: str = "60",
            countback: int = 200,
        ):
            values = {
                "BTC": (35, 0.45, "BUY"),
                "ETH": (15, 0.90, "HOLD"),
                "XRP": (-20, 0.50, "SELL"),
            }

            score, confidence, signal = values[symbol]

            return AnalysisResult(
                symbol=symbol,
                timestamp=1_700_000_000,
                price=100.0,
                total_score=score,
                confidence=confidence,
                signal=signal,
                reasons=[],
                indicators={},
            )

    scanner = ScannerService(
        market_service=FakeMarketService(),
        analysis_service=MixedSignalAnalysisService(),
    )

    result = scanner.scan(
        symbols=["BTC", "ETH", "XRP"],
    )

    actionable = result.actionable_results

    assert len(actionable) == 2

    assert actionable[0].symbol == "BTC"
    assert actionable[1].symbol == "XRP"

    assert all(
        item.signal != "HOLD"
        for item in actionable
    )


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
                raise RuntimeError(
                    "analysis failed"
                )

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

    assert (
        result.failed_symbols["ETH"]
        == "analysis failed"
    )

    assert len(result.actionable_results) == 2
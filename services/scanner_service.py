from __future__ import annotations

from models.scan_result import ScanResult
from services.analysis_service import AnalysisService
from services.market_service import MarketService


class ScannerService:
    """
    Scan multiple markets and rank their analysis results.
    """

    def __init__(
        self,
        market_service: MarketService | None = None,
        analysis_service: AnalysisService | None = None,
    ):
        self.market_service = market_service or MarketService()

        self.analysis_service = (
            analysis_service
            or AnalysisService(
                market_service=self.market_service,
            )
        )

    @staticmethod
    def _extract_rls_symbols(data: dict) -> list[str]:
        """
        Extract source symbols from Nobitex RLS market keys.

        Example:
            btc-rls -> BTC
        """

        stats = data.get("stats", {})

        symbols: list[str] = []

        for market_key in stats:
            if not market_key.endswith("-rls"):
                continue

            symbol = market_key[:-4].strip()

            if symbol:
                symbols.append(symbol.upper())

        return sorted(set(symbols))

    def scan(
        self,
        resolution: str = "60",
        countback: int = 200,
        symbols: list[str] | None = None,
    ) -> ScanResult:
        """
        Analyze multiple markets.

        If symbols is None, all RLS markets are scanned.

        A failure in one symbol does not stop the scan.
        """

        market_data = self.market_service.exchange.get_markets()

        if symbols is None:
            target_symbols = self._extract_rls_symbols(market_data)
        else:
            target_symbols = [
                symbol.upper()
                for symbol in symbols
                if symbol.strip()
            ]

        results = []
        failed_symbols: dict[str, str] = {}

        for symbol in target_symbols:
            try:
                result = self.analysis_service.analyze(
                    symbol=symbol,
                    resolution=resolution,
                    countback=countback,
                )

                results.append(result)

            except Exception as exc:
                failed_symbols[symbol] = str(exc)

        return ScanResult(
            results=results,
            failed_symbols=failed_symbols,
        )
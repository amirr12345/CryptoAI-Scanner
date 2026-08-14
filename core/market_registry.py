from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MarketDescriptor:
    """
    Canonical description of one market.

    Examples:

        BTCIRT
            base_asset       = BTC
            quote_asset      = IRT
            analysis_market  = BTCUSDT
            execution_market = BTCIRT

        BTCUSDT
            base_asset       = BTC
            quote_asset      = USDT
            analysis_market  = BTCUSDT
            execution_market = BTCUSDT

        USDTIRT
            base_asset       = USDT
            quote_asset      = IRT
            analysis_market  = USDTIRT
            execution_market = USDTIRT
    """

    market_symbol: str
    base_asset: str
    quote_asset: str
    analysis_market: str
    execution_market: str


class MarketRegistry:
    """
    Central market identity registry.

    Project rule:

        USDT is the primary analysis quote.

    IRT is allowed as:
        - local execution quote
        - local price quote

    USDTIRT is the quote bridge.
    """

    ANALYSIS_QUOTE = "USDT"
    LOCAL_QUOTE = "IRT"

    def __init__(
        self,
        descriptors: list[MarketDescriptor] | None = None,
    ) -> None:
        self._markets: dict[str, MarketDescriptor] = {}

        for descriptor in descriptors or []:
            self.register(descriptor)

    @staticmethod
    def normalize_market_symbol(
        market_symbol: str,
    ) -> str:
        value = market_symbol.strip().upper()

        if not value:
            raise ValueError(
                "Market symbol cannot be empty."
            )

        return value

    @staticmethod
    def _parse_market_symbol(
        market_symbol: str,
    ) -> tuple[str, str]:
        """
        Parse supported market quote suffixes.

        Longest suffixes are checked first.
        """

        symbol = (
            market_symbol.strip().upper()
        )

        if not symbol:
            raise ValueError(
                "Market symbol cannot be empty."
            )

        known_quotes = (
            "USDT",
            "USDC",
            "IRT",
            "BTC",
            "ETH",
        )

        for quote in known_quotes:
            if symbol.endswith(quote):
                base = symbol[: -len(quote)]

                if base:
                    return base, quote

        raise ValueError(
            f"Unsupported market symbol: "
            f"{market_symbol}"
        )

    @classmethod
    def build_descriptor(
        cls,
        market_symbol: str,
    ) -> MarketDescriptor:
        normalized = (
            cls.normalize_market_symbol(
                market_symbol
            )
        )

        base, quote = (
            cls._parse_market_symbol(
                normalized
            )
        )

        # USDT/IRT is the bridge market itself.
        if (
            base == cls.ANALYSIS_QUOTE
            and quote == cls.LOCAL_QUOTE
        ):
            analysis_market = normalized

        # BASE/USDT is already the canonical
        # analysis market.
        elif quote == cls.ANALYSIS_QUOTE:
            analysis_market = normalized

        # BASE/IRT should be analyzed against
        # BASE/USDT.
        elif quote == cls.LOCAL_QUOTE:
            analysis_market = (
                f"{base}{cls.ANALYSIS_QUOTE}"
            )

        # Other quote assets currently map to
        # BASE/USDT as the analysis reference.
        else:
            analysis_market = (
                f"{base}{cls.ANALYSIS_QUOTE}"
            )

        return MarketDescriptor(
            market_symbol=normalized,
            base_asset=base,
            quote_asset=quote,
            analysis_market=analysis_market,
            execution_market=normalized,
        )

    def register(
        self,
        descriptor: MarketDescriptor,
    ) -> None:
        normalized = (
            self.normalize_market_symbol(
                descriptor.market_symbol
            )
        )

        if normalized != descriptor.market_symbol:
            raise ValueError(
                "Market descriptor must use "
                "normalized market_symbol."
            )

        self._markets[normalized] = descriptor

    def register_symbol(
        self,
        market_symbol: str,
    ) -> MarketDescriptor:
        descriptor = (
            self.build_descriptor(
                market_symbol
            )
        )

        self.register(descriptor)

        return descriptor

    def get(
        self,
        market_symbol: str,
    ) -> MarketDescriptor | None:
        normalized = (
            self.normalize_market_symbol(
                market_symbol
            )
        )

        return self._markets.get(normalized)

    def require(
        self,
        market_symbol: str,
    ) -> MarketDescriptor:
        descriptor = self.get(
            market_symbol
        )

        if descriptor is None:
            descriptor = self.register_symbol(
                market_symbol
            )

        return descriptor

    def all(
        self,
    ) -> list[MarketDescriptor]:
        return sorted(
            self._markets.values(),
            key=lambda item: (
                item.base_asset,
                item.quote_asset,
                item.market_symbol,
            ),
        )

    def symbols(
        self,
    ) -> list[str]:
        return [
            item.market_symbol
            for item in self.all()
        ]

    def analysis_market(
        self,
        market_symbol: str,
    ) -> str:
        return self.require(
            market_symbol
        ).analysis_market

    def execution_market(
        self,
        market_symbol: str,
    ) -> str:
        return self.require(
            market_symbol
        ).execution_market

    def base_asset(
        self,
        market_symbol: str,
    ) -> str:
        return self.require(
            market_symbol
        ).base_asset

    def quote_asset(
        self,
        market_symbol: str,
    ) -> str:
        return self.require(
            market_symbol
        ).quote_asset

    def usdt_market(
        self,
        base_asset: str,
    ) -> str:
        base = base_asset.strip().upper()

        if not base:
            raise ValueError(
                "Base asset cannot be empty."
            )

        return (
            f"{base}"
            f"{self.ANALYSIS_QUOTE}"
        )

    def irt_market(
        self,
        base_asset: str,
    ) -> str:
        base = base_asset.strip().upper()

        if not base:
            raise ValueError(
                "Base asset cannot be empty."
            )

        return (
            f"{base}"
            f"{self.LOCAL_QUOTE}"
        )

    @staticmethod
    def implicit_usdt_price(
        base_irt_price: float,
        usdt_irt_price: float,
    ) -> float:
        """
        Convert BASE/IRT to implicit BASE/USDT.

        BASE/USDT =
            BASE/IRT / USDT/IRT
        """

        base_price = float(
            base_irt_price
        )

        bridge_price = float(
            usdt_irt_price
        )

        if base_price < 0:
            raise ValueError(
                "base_irt_price cannot be negative."
            )

        if bridge_price <= 0:
            raise ValueError(
                "usdt_irt_price must be "
                "greater than zero."
            )

        return base_price / bridge_price
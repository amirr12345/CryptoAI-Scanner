from __future__ import annotations

import requests

from api.base import ExchangeBase
from api.models import Ticker
from models.candle import Candle


class NobitexExchange(ExchangeBase):

    BASE_URL = "https://apiv2.nobitex.ir"

    def get_ticker(self, symbol: str) -> Ticker:
        symbol = symbol.lower()

        response = requests.get(
            self.BASE_URL + "/market/stats",
            params={
                "srcCurrency": symbol,
                "dstCurrency": "rls",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                f"Nobitex market stats failed: {data}"
            )

        market_key = f"{symbol}-rls"

        try:
            market = data["stats"][market_key]
        except KeyError as exc:
            raise ValueError(
                f"Market not found in Nobitex response: {market_key}"
            ) from exc

        return Ticker(
            symbol=symbol.upper(),
            last_price=float(market["latest"]),
            high=float(market["dayHigh"]),
            low=float(market["dayLow"]),
            volume=float(market["volumeSrc"]),
        )

    def get_markets(self):
        response = requests.get(
            self.BASE_URL + "/market/stats",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                f"Nobitex market stats failed: {data}"
            )

        return data

    def get_history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        if not resolution:
            raise ValueError("Resolution cannot be empty.")

        if countback <= 0:
            raise ValueError("Countback must be greater than zero.")

        params = {
            "symbol": symbol.upper(),
            "resolution": resolution,
            "countback": countback,
        }

        response = requests.get(
            self.BASE_URL + "/market/udf/history",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("s") != "ok":
            raise ValueError(
                f"Nobitex history request failed: {data}"
            )

        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        lengths = {
            len(timestamps),
            len(opens),
            len(highs),
            len(lows),
            len(closes),
            len(volumes),
        }

        if len(lengths) != 1:
            raise ValueError(
                "Invalid Nobitex OHLC response: "
                "array lengths are inconsistent."
            )

        return [
            Candle(
                timestamp=int(timestamps[i]),
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=float(volumes[i]),
            )
            for i in range(len(timestamps))
        ]
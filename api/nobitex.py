import requests

from api.base import ExchangeBase
from api.models import Ticker


class NobitexExchange(ExchangeBase):

    BASE_URL = "https://apiv2.nobitex.ir"

    def get_ticker(self, symbol):

        response = requests.get(
            self.BASE_URL + "/market/stats",
            params={
                "srcCurrency": symbol,
                "dstCurrency": "rls"
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        market = data["stats"][f"{symbol}-rls"]

        return Ticker(
            symbol=symbol.upper(),
            last_price=float(market["latest"]),
            high=float(market["dayHigh"]),
            low=float(market["dayLow"]),
            volume=float(market["volumeSrc"])
        )

    def get_markets(self):

        response = requests.get(
            self.BASE_URL + "/market/stats",
            timeout=10
        )

        response.raise_for_status()

        return response.json()
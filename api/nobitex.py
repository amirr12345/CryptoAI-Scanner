import requests

from base import ExchangeBase


class NobitexExchange(ExchangeBase):

    BASE_URL = "https://apiv2.nobitex.ir"

    def get_markets(self):

        url = self.BASE_URL + "/market/stats"

        response = requests.get(url, timeout=10)

        response.raise_for_status()

        return response.json()

    def get_ticker(self, symbol):

        url = self.BASE_URL + "/market/stats"

        response = requests.get(
            url,
            params={
                "srcCurrency": symbol,
                "dstCurrency": "rls"
            },
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    def get_orderbook(self, symbol):
        return {}
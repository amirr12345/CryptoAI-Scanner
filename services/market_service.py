from api.nobitex import NobitexExchange


class MarketService:

    def __init__(self):
        self.exchange = NobitexExchange()

    def get_btc_price(self):

        data = self.exchange.get_ticker("btc")

        stats = data["stats"]["btc-rls"]

        return float(stats["latest"])
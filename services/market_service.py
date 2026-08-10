from api.nobitex import NobitexExchange


class MarketService:

    def __init__(self):

        self.exchange = NobitexExchange()

    def btc(self):

        return self.exchange.get_ticker("btc")

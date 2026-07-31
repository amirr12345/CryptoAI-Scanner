from api.nobitex import NobitexExchange


class MarketRepository:
    """
    ارتباط با صرافی نوبیتکس
    """

    def __init__(self):
        self.exchange = NobitexExchange()

    def get_ticker(self, symbol: str):
        return self.exchange.get_ticker(symbol)

    def get_markets(self):
        return self.exchange.get_markets()
from api.nobitex import NobitexExchange


class MarketRepository:
    """
    Repository مسئول دریافت داده از صرافی است.
    سایر بخش‌های پروژه نباید مستقیماً api را صدا بزنند.
    """

    def __init__(self):
        self.exchange = NobitexExchange()

    def get_ticker(self, symbol: str):
        return self.exchange.get_ticker(symbol)

    def get_markets(self):
        return self.exchange.get_markets()
from repositories.market_repository import MarketRepository


class MarketService:

    def __init__(self):
        self.repository = MarketRepository()

    def get_ticker(self, symbol: str):
        return self.repository.get_ticker(symbol)

    def get_markets(self):
        return self.repository.get_markets()
from api.history import HistoryAPI


class HistoryRepository:

    def __init__(self):

        self.api = HistoryAPI()

    def load(self, symbol="BTCIRT", resolution="60", bars=200):

        return self.api.get_history(symbol, resolution, bars)

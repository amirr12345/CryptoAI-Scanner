from repositories.history_repository import HistoryRepository


class HistoryService:

    def __init__(self):

        self.repo = HistoryRepository()

    def get_history(
            self,
            symbol="BTCIRT",
            resolution="60",
            bars=200):

        return self.repo.load(
            symbol,
            resolution,
            bars
        )
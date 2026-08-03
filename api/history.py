import requests
import time


class HistoryAPI:

    BASE_URL = "https://apiv2.nobitex.ir/market/udf/history"

    def get_history(self, symbol="BTCIRT", resolution="60", bars=200):

        now = int(time.time())

        params = {
            "symbol": symbol,
            "resolution": resolution,
            "to": now,
            "countback": bars,
        }

        response = requests.get(self.BASE_URL, params=params, timeout=20)

        response.raise_for_status()

        return response.json()

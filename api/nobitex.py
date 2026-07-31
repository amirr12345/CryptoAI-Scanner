import requests

BASE_URL = "https://apiv2.nobitex.ir"

def get_stats(symbol="btc", market="rls"):
    url = f"{BASE_URL}/market/stats"

    params = {
        "srcCurrency": symbol,
        "dstCurrency": market
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(e)
        return None
from config import APP_NAME, VERSION

from core.logger import get_logger
from core.database import initialize
from services.market_service import MarketService

logger = get_logger()

print("=" * 55)
print(APP_NAME)
print(f"Version : {VERSION}")
print("=" * 55)

logger.info("Program Started")

initialize()

logger.info("Database Ready")

print("✓ Logger Ready")
print("✓ Database Ready")
print()

print("Connecting to Nobitex...")

service = MarketService()

btc = service.get_ticker("btc")

print()
print("=" * 50)
print("BTC Market")
print("=" * 50)
print(f"Price : {btc.last_price}")
print(f"High  : {btc.high}")
print(f"Low   : {btc.low}")
print(f"Volume: {btc.volume}")

print()
print("Scanner Ready")

from services.history_service import HistoryService

history = HistoryService()

analysis = AnalysisService()

result = analysis.run()

print()
print("=" * 50)
print("BTC ANALYSIS")
print("=" * 50)

print(f"Price : {result['price']:.2f}")
print(f"EMA20 : {result['ema20']:.2f}")
print(f"EMA50 : {result['ema50']:.2f}")

import pandas as pd
from indicators.ema import EMAIndicator

df = pd.DataFrame({
    "time": data["t"],
    "open": data["o"],
    "high": data["h"],
    "low": data["l"],
    "close": data["c"],
    "volume": data["v"]
})

print(df.tail())
print(data["c"][-5:])

ema20 = EMAIndicator(20).calculate(df)
ema50 = EMAIndicator(50).calculate(df)

print()
print("=" * 50)
print("EMA")
print("=" * 50)

print("Last Close :", df["close"].iloc[-1])
print("EMA20      :", round(float(ema20.iloc[-1]), 2))
print("EMA50      :", round(float(ema50.iloc[-1]), 2))
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
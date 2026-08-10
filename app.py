from config import APP_NAME, VERSION

from core.logger import get_logger
from core.database import initialize

logger = get_logger()

from services.market_service import MarketService

service = MarketService()

btc = service.btc()

print()
print("=" * 50)
print("BTC Market")
print("=" * 50)

print("Price :", btc.last_price)
print("High  :", btc.high)
print("Low   :", btc.low)
print("Volume:", btc.volume)

print("=" * 55)
print(APP_NAME)
print("Version :", VERSION)
print("=" * 55)

logger.info("Program Started")

initialize()

logger.info("Database Ready")

print("✓ Logger Ready")
print("✓ Database Ready")
print("Scanner Starting...")

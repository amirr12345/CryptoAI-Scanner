from config import APP_NAME, VERSION

from core.logger import get_logger
from core.database import initialize

logger = get_logger()

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
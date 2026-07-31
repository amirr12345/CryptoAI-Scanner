from config import *

from Core.logger import get_logger

from Core.database import initialize

logger = get_logger()

print("="*55)
print(APP_NAME)
print("Version :", VERSION)
print("="*55)

logger.info("Program Started")

initialize()

logger.info("Database Ready")

print("✓ Logger Ready")

print("✓ Database Ready")

print("Scanner Starting ...")

from api.nobitex import get_stats

print("Connecting...")

data = get_stats()

if data:

    print("Connected")

    print(data["stats"]["btc-rls"]["latest"])

else:

    print("Connection Failed")
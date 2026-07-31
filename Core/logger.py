from loguru import logger
import os

os.makedirs("logs", exist_ok=True)

logger.add(
    "logs/scanner.log",
    rotation="5 MB",
    retention="30 days",
    level="INFO",
    encoding="utf-8"
)

def get_logger():
    return logger
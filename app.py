from config import APP_NAME, VERSION

from core.database import initialize
from core.logger import get_logger

from services.market_service import MarketService
from services.analysis_service import AnalysisService

logger = get_logger()


def print_header():
    print("=" * 55)
    print(APP_NAME)
    print(f"Version : {VERSION}")
    print("=" * 55)


def main():

    print_header()

    logger.info("Program Started")

    initialize()

    logger.info("Database Ready")

    print("✓ Logger Ready")
    print("✓ Database Ready")
    print()

    print("Connecting to Nobitex...")

    market = MarketService()

    btc = market.get_ticker("btc")

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

    analysis = AnalysisService()

    result = analysis.run(
        symbol="BTCIRT",
        resolution="60",
        bars=200,
    )

    print()
    print("=" * 50)
    print("BTC ANALYSIS")
    print("=" * 50)

    print(f"Symbol : {result.symbol}")
    print(f"Price  : {result.price:.2f}")
    print(f"EMA20  : {result.ema20:.2f}")
    print(f"EMA50  : {result.ema50:.2f}")
    print(f"RSI    : {result.rsi:.2f}")
    print(f"MACD   : {result.macd:.2f}")
    print(f"Trend  : {result.trend}")
    print(f"Signal : {result.signal}")
    print(f"Score  : {result.score}")
    print(f"ATR    : {result.atr:.2f}")

    print()
    print("Analysis Completed")


if __name__ == "__main__":
    main()

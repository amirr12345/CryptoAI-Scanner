from config import APP_NAME, VERSION

from core.database import initialize
from core.logger import get_logger
from services.scanner_service import ScannerService


logger = get_logger()


def print_scan_results(scan_result):
    print()
    print("=" * 70)
    print("MULTI-MARKET SCAN RESULTS")
    print("=" * 70)

    if not scan_result.results:
        print("No successful market analysis.")
    else:
        for rank, result in enumerate(
            scan_result.ranked_results,
            start=1,
        ):
            print(
                f"{rank}. "
                f"{result.symbol:<10} "
                f"Signal={result.signal:<12} "
                f"Score={result.total_score:>4} "
                f"Confidence={result.confidence:.2f} "
                f"Price={result.price:.2f}"
            )

    print("-" * 70)

    if scan_result.failed_symbols:
        print("FAILED SYMBOLS")
        for symbol, error in scan_result.failed_symbols.items():
            print(f"{symbol}: {error}")

    print("=" * 70)


def main():
    logger.info("Program Started")

    initialize()
    logger.info("Database Ready")

    print("=" * 70)
    print(APP_NAME)
    print("Version :", VERSION)
    print("=" * 70)

    print("Logger Ready")
    print("Database Ready")
    print("Scanner Starting...")

    scanner = ScannerService()

    try:
        scan_result = scanner.scan(
            resolution="60",
            countback=200,
        )

        print_scan_results(scan_result)

        logger.info(
            "Scanner completed: %s successful, %s failed",
            scan_result.successful_count,
            scan_result.failed_count,
        )

    except Exception:
        logger.exception("Scanner failed.")
        raise


if __name__ == "__main__":
    main()
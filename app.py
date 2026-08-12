from config import APP_NAME, VERSION

from core.database import initialize
from core.logger import get_logger
from services.scanner_service import ScannerService


logger = get_logger()


def print_scan_results(scan_result):
    """
    Print concise multi-market scanner results.

    All successful analysis results remain available through
    scan_result.results, but the main console output focuses
    on actionable signals (score != 0).
    """

    print()
    print("=" * 70)
    print("MULTI-MARKET SCAN SUMMARY")
    print("=" * 70)

    print(
        f"Total Markets       : "
        f"{scan_result.successful_count + scan_result.failed_count}"
    )

    print(
        f"Successful Analyses : "
        f"{scan_result.successful_count}"
    )

    print(
        f"Actionable Signals  : "
        f"{len(scan_result.actionable_results)}"
    )

    print(
        f"Failed Markets      : "
        f"{scan_result.failed_count}"
    )

    print("=" * 70)

    actionable = scan_result.actionable_results

    if not actionable:
        print("No actionable signals found.")
    else:
        print("TOP ACTIONABLE SIGNALS")
        print("-" * 70)

        for rank, result in enumerate(
            actionable,
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

    print("=" * 70)

    if scan_result.failed_symbols:
        print("FAILED MARKETS")
        print("-" * 70)

        for symbol, error in (
            scan_result.failed_symbols.items()
        ):
            print(
                f"{symbol:<12}: {error}"
            )

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
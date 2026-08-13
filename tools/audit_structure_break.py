from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from collections import Counter

from microstructure.market_structure import (
    MarketStructureEngine,
)
from microstructure.structure_break import (
    StructureBreakEngine,
)
from services.market_service import MarketService


def main() -> None:
    market_service = MarketService()

    market_data = market_service.markets()
    stats = market_data.get("stats", {})

    symbols = sorted(
        {
            key[:-4].upper()
            for key in stats
            if key.endswith("-rls")
        }
    )

    structure_engine = MarketStructureEngine()
    break_engine = StructureBreakEngine()

    structure_counter = Counter()
    event_counter = Counter()

    results = []
    failed = {}

    for symbol in symbols:
        try:
            candles = market_service.history(
                symbol=symbol,
                resolution="60",
                countback=200,
            )

            structure = structure_engine.calculate(
                candles,
                swing_window=2,
            )

            breaks = break_engine.calculate(
                candles=candles,
                structure=structure,
                displacement_pct=0.15,
            )

            structure_counter[
                structure.structure
            ] += 1

            event_counter[
                breaks.latest_event
            ] += 1

            results.append(
                {
                    "symbol": symbol,
                    "structure": structure.structure,
                    "swings": len(structure.swings),
                    "latest_event": breaks.latest_event,
                    "latest_direction": (
                        breaks.latest_direction
                    ),
                    "events": len(breaks.events),
                    "bullish_bos": (
                        breaks.bullish_bos_count
                    ),
                    "bearish_bos": (
                        breaks.bearish_bos_count
                    ),
                    "bullish_choch": (
                        breaks.bullish_choch_count
                    ),
                    "bearish_choch": (
                        breaks.bearish_choch_count
                    ),
                    "bullish_mss": (
                        breaks.bullish_mss_count
                    ),
                    "bearish_mss": (
                        breaks.bearish_mss_count
                    ),
                }
            )

        except Exception as exc:
            failed[symbol] = str(exc)

    print()
    print("=" * 110)
    print("MARKET STRUCTURE / BOS / CHoCH / MSS AUDIT")
    print("=" * 110)

    print(
        f"Total symbols      : {len(symbols)}"
    )

    print(
        f"Successful         : {len(results)}"
    )

    print(
        f"Failed             : {len(failed)}"
    )

    print("-" * 110)

    print("STRUCTURE DISTRIBUTION")

    for name in (
        "BULLISH",
        "BEARISH",
        "MIXED",
        "NEUTRAL",
    ):
        print(
            f"{name:<12}: "
            f"{structure_counter[name]}"
        )

    print()
    print("LATEST EVENT DISTRIBUTION")

    for name in (
        "BOS",
        "CHoCH",
        "MSS",
        "NONE",
    ):
        print(
            f"{name:<12}: "
            f"{event_counter[name]}"
        )

    print()
    print("-" * 110)
    print("LATEST STRUCTURE-BREAK EVENTS")
    print("-" * 110)

    event_results = [
        result
        for result in results
        if result["latest_event"] != "NONE"
    ]

    event_results.sort(
        key=lambda item: (
            item["latest_event"] != "MSS",
            item["latest_event"] != "CHoCH",
            item["symbol"],
        )
    )

    for rank, result in enumerate(
        event_results[:30],
        start=1,
    ):
        print(
            f"{rank:>2}. "
            f"{result['symbol']:<10} "
            f"Structure={result['structure']:<8} "
            f"Event={result['latest_event']:<6} "
            f"Direction={result['latest_direction']:<8} "
            f"Swings={result['swings']:<3} "
            f"Events={result['events']:<3}"
        )

    print()
    print("-" * 110)
    print("BOS / CHoCH / MSS COUNTS")
    print("-" * 110)

    for rank, result in enumerate(
        sorted(
            results,
            key=lambda item: (
                item["bullish_mss"]
                + item["bearish_mss"]
                + item["bullish_choch"]
                + item["bearish_choch"]
            ),
            reverse=True,
        )[:20],
        start=1,
    ):
        print(
            f"{rank:>2}. "
            f"{result['symbol']:<10} "
            f"BOS={(
                result['bullish_bos']
                + result['bearish_bos']
            ):>2} "
            f"CHoCH={(
                result['bullish_choch']
                + result['bearish_choch']
            ):>2} "
            f"MSS={(
                result['bullish_mss']
                + result['bearish_mss']
            ):>2}"
        )

    print()
    print("-" * 110)
    print("FAILED MARKETS")
    print("-" * 110)

    for symbol, error in list(
        failed.items()
    )[:20]:
        print(
            f"{symbol:<12}: {error}"
        )

    print("=" * 110)


if __name__ == "__main__":
    main()
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from microstructure.liquidity_sweep import (
    LiquiditySweepEngine,
)
from microstructure.market_structure import (
    MarketStructureEngine,
)
from microstructure.structure_break import (
    StructureBreakEngine,
)
from microstructure.structure_setup import (
    StructureSetupEngine,
)
from services.market_service import MarketService


def main() -> None:
    market_service = MarketService()

    market_data = market_service.markets()

    stats = market_data.get(
        "stats",
        {},
    )

    symbols = sorted(
        {
            key[:-4].upper()
            for key in stats
            if key.endswith("-rls")
        }
    )

    structure_engine = (
        MarketStructureEngine()
    )

    break_engine = (
        StructureBreakEngine()
    )

    sweep_engine = (
        LiquiditySweepEngine()
    )

    setup_engine = (
        StructureSetupEngine()
    )

    structure_counter = Counter()
    setup_counter = Counter()
    confluence_counter = Counter()

    results = []
    failed = {}

    for symbol in symbols:
        try:
            candles = market_service.history(
                symbol=symbol,
                resolution="60",
                countback=200,
            )

            structure = (
                structure_engine.calculate(
                    candles,
                    swing_window=2,
                )
            )

            structure_breaks = (
                break_engine.calculate(
                    candles=candles,
                    structure=structure,
                    displacement_pct=0.15,
                )
            )

            liquidity_sweeps = (
                sweep_engine.calculate(
                    candles=candles,
                    structure=structure,
                )
            )

            setups = (
                setup_engine.calculate(
                    sweeps=liquidity_sweeps.events,
                    structure_breaks=(
                        structure_breaks.events
                    ),
                    max_bars_after_sweep=10,
                )
            )

            structure_counter[
                structure.structure
            ] += 1

            setup_counter[
                "TOTAL"
            ] += len(setups.setups)

            setup_counter[
                "BULLISH"
            ] += setups.bullish_setup_count

            setup_counter[
                "BEARISH"
            ] += setups.bearish_setup_count

            results.append(
                {
                    "symbol": symbol,
                    "structure": structure.structure,
                    "swings": len(
                        structure.swings
                    ),
                    "sweeps": len(
                        liquidity_sweeps.events
                    ),
                    "mss": (
                        structure_breaks.bullish_mss_count
                        + structure_breaks.bearish_mss_count
                    ),
                    "setups": len(
                        setups.setups
                    ),
                    "bullish_setups": (
                        setups.bullish_setup_count
                    ),
                    "bearish_setups": (
                        setups.bearish_setup_count
                    ),
                    "latest_setup": (
                        setups.latest_setup
                    ),
                    "latest_direction": (
                        setups.latest_direction
                    ),
                }
            )

        except Exception as exc:
            failed[symbol] = str(exc)

    print()
    print("=" * 110)
    print("STRUCTURE SETUP AUDIT")
    print("=" * 110)

    print(
        f"Total symbols : {len(symbols)}"
    )

    print(
        f"Successful    : {len(results)}"
    )

    print(
        f"Failed        : {len(failed)}"
    )

    print()
    print("STRUCTURE DISTRIBUTION")
    print("-" * 110)

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
    print("SETUP DISTRIBUTION")
    print("-" * 110)

    print(
        f"Total setups  : "
        f"{setup_counter['TOTAL']}"
    )

    print(
        f"Bullish       : "
        f"{setup_counter['BULLISH']}"
    )

    print(
        f"Bearish       : "
        f"{setup_counter['BEARISH']}"
    )

    print()
    print("MARKETS WITH SETUPS")
    print("-" * 110)

    setup_results = [
        result
        for result in results
        if result["setups"] > 0
    ]

    setup_results.sort(
        key=lambda item: (
            item["setups"],
            item["mss"],
            item["swings"],
        ),
        reverse=True,
    )

    for rank, result in enumerate(
        setup_results[:40],
        start=1,
    ):
        print(
            f"{rank:>2}. "
            f"{result['symbol']:<10} "
            f"Structure={result['structure']:<8} "
            f"Swings={result['swings']:<3} "
            f"Sweeps={result['sweeps']:<3} "
            f"MSS={result['mss']:<3} "
            f"Setups={result['setups']:<3} "
            f"Bull={result['bullish_setups']:<2} "
            f"Bear={result['bearish_setups']:<2} "
            f"Latest={result['latest_direction']}"
        )

    print()
    print("LATEST ACTIVE SETUPS")
    print("-" * 110)

    latest_results = [
        result
        for result in results
        if result["latest_setup"] != "NONE"
    ]

    latest_results.sort(
        key=lambda item: item["symbol"]
    )

    for rank, result in enumerate(
        latest_results[:40],
        start=1,
    ):
        print(
            f"{rank:>2}. "
            f"{result['symbol']:<10} "
            f"Structure={result['structure']:<8} "
            f"Setup={result['latest_setup']:<28} "
            f"Direction={result['latest_direction']}"
        )

    print()
    print("FAILED MARKETS")
    print("-" * 110)

    for symbol, error in list(
        failed.items()
    )[:30]:
        print(
            f"{symbol:<12}: {error}"
        )

    print("=" * 110)


if __name__ == "__main__":
    main()
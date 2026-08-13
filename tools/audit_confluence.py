from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from microstructure.confluence_engine import (
    ConfluenceEngine,
)
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
    sweep_engine = LiquiditySweepEngine()
    setup_engine = StructureSetupEngine()
    confluence_engine = ConfluenceEngine()

    grade_counter = Counter()
    direction_counter = Counter()

    results: list[dict] = []
    failed: dict[str, str] = {}

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

            structure_breaks = break_engine.calculate(
                candles=candles,
                structure=structure,
                displacement_pct=0.15,
            )

            sweeps = sweep_engine.calculate(
                candles=candles,
                structure=structure,
            )

            setups = setup_engine.calculate(
                sweeps=sweeps.events,
                structure_breaks=structure_breaks.events,
                max_bars_after_sweep=10,
            )

            symbol_setups: list[dict] = []

            for setup in setups.setups:
                # فعلاً فقط ساختار Setup را ارزیابی می‌کنیم.
                # Context تاریخی هم‌زمان CVD / Profile / VWAP
                # هنوز به این Audit متصل نشده است.
                confluence = confluence_engine.evaluate(
                    setup=setup,
                    cvd=None,
                    profile=None,
                    vwap=None,
                )

                grade_counter[confluence.grade] += 1
                direction_counter[confluence.direction] += 1

                symbol_setups.append(
                    {
                        "setup": setup,
                        "confluence": confluence,
                    }
                )

            latest = (
                symbol_setups[-1]
                if symbol_setups
                else None
            )

            results.append(
                {
                    "symbol": symbol,
                    "structure": structure.structure,
                    "swings": len(structure.swings),
                    "sweeps": len(sweeps.events),
                    "mss": (
                        structure_breaks.bullish_mss_count
                        + structure_breaks.bearish_mss_count
                    ),
                    "setups": len(setups.setups),
                    "bullish_setups": setups.bullish_setup_count,
                    "bearish_setups": setups.bearish_setup_count,
                    "latest_setup": setups.latest_setup,
                    "latest_direction": setups.latest_direction,
                    "latest_grade": (
                        latest["confluence"].grade
                        if latest is not None
                        else "NONE"
                    ),
                    "latest_score": (
                        latest["confluence"].score
                        if latest is not None
                        else 0.0
                    ),
                }
            )

        except Exception as exc:
            failed[symbol] = str(exc)

    print()
    print("=" * 110)
    print("CONFLUENCE AUDIT")
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
    print("CONFLUENCE GRADE DISTRIBUTION")
    print("-" * 110)

    for grade in (
        "A+",
        "A",
        "B",
        "CONFLICT",
        "REJECT",
    ):
        print(
            f"{grade:<12}: "
            f"{grade_counter[grade]}"
        )

    print()
    print("CONFLUENCE DIRECTION DISTRIBUTION")
    print("-" * 110)

    for direction in (
        "BULLISH",
        "BEARISH",
        "NEUTRAL",
    ):
        print(
            f"{direction:<12}: "
            f"{direction_counter[direction]}"
        )

    print()
    print("MARKETS WITH STRUCTURE SETUPS")
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
        setup_results[:50],
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
            f"Latest={result['latest_direction']:<8} "
            f"Grade={result['latest_grade']:<8} "
            f"Score={result['latest_score']:>5.1f}"
        )

    print()
    print("LATEST CONFLUENCE RESULTS")
    print("-" * 110)

    latest_results = [
        result
        for result in results
        if result["latest_setup"] != "NONE"
    ]

    latest_results.sort(
        key=lambda item: (
            item["latest_score"],
            item["symbol"],
        ),
        reverse=True,
    )

    for rank, result in enumerate(
        latest_results[:50],
        start=1,
    ):
        print(
            f"{rank:>2}. "
            f"{result['symbol']:<10} "
            f"Setup={result['latest_setup']:<28} "
            f"Direction={result['latest_direction']:<8} "
            f"Grade={result['latest_grade']:<8} "
            f"Score={result['latest_score']:>5.1f}"
        )

    print()
    print("FAILED MARKETS")
    print("-" * 110)

    if not failed:
        print("No failed markets.")
    else:
        for symbol, error in failed.items():
            print(
                f"{symbol:<12}: {error}"
            )

    print("=" * 110)

    print()
    print(
        "NOTE: This audit currently evaluates "
        "Structure Setup only."
    )

    print(
        "Historical event-aligned CVD / Volume Profile / VWAP "
        "are not yet supplied."
    )


if __name__ == "__main__":
    main()
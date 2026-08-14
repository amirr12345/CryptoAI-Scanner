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
from microstructure.historical_confluence import (
    HistoricalConfluenceEngine,
)
from microstructure.historical_context import (
    HistoricalContextEngine,
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

    historical_context_engine = (
        HistoricalContextEngine()
    )

    historical_confluence_engine = (
        HistoricalConfluenceEngine(
            confluence_engine=ConfluenceEngine()
        )
    )

    grade_counter = Counter()
    direction_counter = Counter()
    status_counter = Counter()

    all_results: list[dict] = []
    failed_markets: dict[str, str] = {}

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

            structure_breaks = (
                break_engine.calculate(
                    candles=candles,
                    structure=structure,
                    displacement_pct=0.15,
                )
            )

            sweeps = sweep_engine.calculate(
                candles=candles,
                structure=structure,
            )

            setups = setup_engine.calculate(
                sweeps=sweeps.events,
                structure_breaks=(
                    structure_breaks.events
                ),
                max_bars_after_sweep=10,
            )

            market_setup_results: list[dict] = []

            for setup in setups.setups:
                setup_timestamp = int(
                    setup.timestamp
                )

                try:
                    context = (
                        historical_context_engine.calculate(
                            symbol=symbol,
                            timestamp=setup_timestamp,
                            lookback_seconds=3600,
                        )
                    )

                except ValueError as exc:
                    status_counter[
                        "NO_HISTORICAL_DATA"
                    ] += 1

                    market_setup_results.append(
                        {
                            "setup": setup,
                            "status": "NO_HISTORICAL_DATA",
                            "grade": "NONE",
                            "score": 0.0,
                            "direction": setup.direction,
                            "error": str(exc),
                        }
                    )

                    continue

                except Exception as exc:
                    status_counter[
                        "FAILED"
                    ] += 1

                    market_setup_results.append(
                        {
                            "setup": setup,
                            "status": "FAILED",
                            "grade": "NONE",
                            "score": 0.0,
                            "direction": setup.direction,
                            "error": str(exc),
                        }
                    )

                    continue

                try:
                    confluence = (
                        historical_confluence_engine.evaluate(
                            setup=setup,
                            context=context,
                        )
                    )

                except Exception as exc:
                    status_counter[
                        "FAILED"
                    ] += 1

                    market_setup_results.append(
                        {
                            "setup": setup,
                            "status": "FAILED",
                            "grade": "NONE",
                            "score": 0.0,
                            "direction": setup.direction,
                            "error": str(exc),
                        }
                    )

                    continue

                grade = confluence.grade

                status_counter["EVALUATED"] += 1
                grade_counter[grade] += 1
                direction_counter[
                    confluence.direction
                ] += 1

                market_setup_results.append(
                    {
                        "setup": setup,
                        "status": "EVALUATED",
                        "grade": grade,
                        "score": confluence.score,
                        "direction": confluence.direction,
                        "actionable": (
                            confluence.actionable
                        ),
                        "context": context,
                        "confluence": confluence,
                    }
                )

            latest = (
                market_setup_results[-1]
                if market_setup_results
                else None
            )

            evaluated_count = sum(
                1
                for result in market_setup_results
                if result["status"] == "EVALUATED"
            )

            no_data_count = sum(
                1
                for result in market_setup_results
                if result["status"]
                == "NO_HISTORICAL_DATA"
            )

            failed_count = sum(
                1
                for result in market_setup_results
                if result["status"] == "FAILED"
            )

            all_results.append(
                {
                    "symbol": symbol,
                    "structure": structure.structure,
                    "swings": len(
                        structure.swings
                    ),
                    "sweeps": len(
                        sweeps.events
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
                    "evaluated": evaluated_count,
                    "no_historical_data": no_data_count,
                    "failed": failed_count,
                    "latest": latest,
                    "setup_results": market_setup_results,
                }
            )

        except Exception as exc:
            failed_markets[symbol] = str(exc)
            status_counter["MARKET_FAILED"] += 1

    print()
    print("=" * 120)
    print("HISTORICAL CONFLUENCE AUDIT")
    print("=" * 120)

    print(
        f"Total symbols       : {len(symbols)}"
    )

    print(
        f"Successful markets  : "
        f"{len(all_results)}"
    )

    print(
        f"Failed markets      : "
        f"{len(failed_markets)}"
    )

    print()
    print("SETUP STATUS")
    print("-" * 120)

    for status in (
        "EVALUATED",
        "NO_HISTORICAL_DATA",
        "FAILED",
    ):
        print(
            f"{status:<22}: "
            f"{status_counter[status]}"
        )

    print()
    print("GRADE DISTRIBUTION")
    print("-" * 120)

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
    print("DIRECTION DISTRIBUTION")
    print("-" * 120)

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
    print("MARKETS WITH EVALUATED HISTORICAL CONFLUENCE")
    print("-" * 120)

    market_rows = [
        result
        for result in all_results
        if result["evaluated"] > 0
    ]

    market_rows.sort(
        key=lambda item: (
            item["latest"]["score"]
            if item["latest"]
            and item["latest"]["status"]
            == "EVALUATED"
            else -1.0,
            item["symbol"],
        ),
        reverse=True,
    )

    for rank, result in enumerate(
        market_rows[:50],
        start=1,
    ):
        latest = result["latest"]

        if (
            latest is not None
            and latest["status"] == "EVALUATED"
        ):
            latest_grade = latest["grade"]
            latest_score = latest["score"]
            latest_direction = (
                latest["direction"]
            )

        else:
            latest_grade = "NONE"
            latest_score = 0.0
            latest_direction = "NONE"

        print(
            f"{rank:>2}. "
            f"{result['symbol']:<12} "
            f"Structure={result['structure']:<8} "
            f"Setups={result['setups']:<3} "
            f"Eval={result['evaluated']:<3} "
            f"NoData={result['no_historical_data']:<3} "
            f"Latest={latest_direction:<8} "
            f"Grade={latest_grade:<9} "
            f"Score={latest_score:>5.1f}"
        )

    print()
    print("LATEST EVALUATED SETUPS")
    print("-" * 120)

    latest_evaluated = []

    for result in all_results:
        latest = result["latest"]

        if (
            latest is not None
            and latest["status"] == "EVALUATED"
        ):
            latest_evaluated.append(
                (
                    result["symbol"],
                    result,
                    latest,
                )
            )

    latest_evaluated.sort(
        key=lambda item: (
            item[2]["score"],
            item[0],
        ),
        reverse=True,
    )

    for rank, (
        symbol,
        result,
        latest,
    ) in enumerate(
        latest_evaluated[:50],
        start=1,
    ):
        setup = latest["setup"]
        context = latest["context"]

        print(
            f"{rank:>2}. "
            f"{symbol:<12} "
            f"Setup={setup.setup:<28} "
            f"Direction={setup.direction:<8} "
            f"Grade={latest['grade']:<9} "
            f"Score={latest['score']:>5.1f} "
            f"CVD={context.cvd_direction:<8} "
            f"VWAP={context.vwap_position:<12} "
            f"Profile={context.profile_position:<18}"
        )

    print()
    print("A+ / A ACTIONABLE SETUPS")
    print("-" * 120)

    actionable_results = []

    for result in all_results:
        for item in result["setup_results"]:
            if (
                item["status"] == "EVALUATED"
                and item.get("actionable") is True
            ):
                actionable_results.append(
                    (
                        result["symbol"],
                        item,
                    )
                )

    actionable_results.sort(
        key=lambda item: (
            item[1]["score"],
            item[0],
        ),
        reverse=True,
    )

    for rank, (
        symbol,
        item,
    ) in enumerate(
        actionable_results[:50],
        start=1,
    ):
        setup = item["setup"]
        context = item["context"]

        print(
            f"{rank:>2}. "
            f"{symbol:<12} "
            f"Setup={setup.setup:<28} "
            f"Direction={setup.direction:<8} "
            f"Grade={item['grade']:<5} "
            f"Score={item['score']:>5.1f} "
            f"CVD={context.cvd_direction:<8} "
            f"CVDStr={context.cvd_strength:>5.1f} "
            f"VWAP={context.vwap_position:<12} "
            f"Profile={context.profile_position:<18}"
        )

    print()
    print("FAILED MARKETS")
    print("-" * 120)

    if not failed_markets:
        print("No failed markets.")

    else:
        for symbol, error in list(
            failed_markets.items()
        )[:50]:
            print(
                f"{symbol:<14}: {error}"
            )

    print()
    print("=" * 120)


if __name__ == "__main__":
    main()
from __future__ import annotations

import sqlite3
import sys
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


DB_PATH = PROJECT_ROOT / "data" / "crypto.db"


def get_trade_range(
    symbol: str,
):
    connection = sqlite3.connect(DB_PATH)

    row = connection.execute(
        """
        SELECT
            MIN(timestamp),
            MAX(timestamp),
            COUNT(*)
        FROM market_trades
        WHERE symbol = ?
        """,
        (
            symbol,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return None, None, 0

    return (
        row[0],
        row[1],
        int(row[2] or 0),
    )


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

    print()
    print("=" * 120)
    print("HISTORICAL TRADE COVERAGE AUDIT")
    print("=" * 120)

    rows = []

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

            if not setups.setups:
                continue

            trade_min_ms, trade_max_ms, trade_count = (
                get_trade_range(symbol)
            )

            if trade_count == 0:
                rows.append(
                    {
                        "symbol": symbol,
                        "setups": len(setups.setups),
                        "first_setup": setups.setups[0].timestamp,
                        "last_setup": setups.setups[-1].timestamp,
                        "trade_count": 0,
                        "trade_min": None,
                        "trade_max": None,
                        "covered": 0,
                    }
                )

                continue

            # Setup timestamps are seconds.
            trade_min_sec = int(
                trade_min_ms / 1000
            )

            trade_max_sec = int(
                trade_max_ms / 1000
            )

            covered = sum(
                1
                for setup in setups.setups
                if (
                    trade_min_sec
                    <= int(setup.timestamp)
                    <= trade_max_sec
                )
            )

            rows.append(
                {
                    "symbol": symbol,
                    "setups": len(setups.setups),
                    "first_setup": setups.setups[0].timestamp,
                    "last_setup": setups.setups[-1].timestamp,
                    "trade_count": trade_count,
                    "trade_min": trade_min_sec,
                    "trade_max": trade_max_sec,
                    "covered": covered,
                }
            )

        except Exception:
            continue

    rows.sort(
        key=lambda row: (
            row["covered"],
            row["trade_count"],
            row["setups"],
        ),
        reverse=True,
    )

    total_setups = sum(
        row["setups"]
        for row in rows
    )

    total_covered = sum(
        row["covered"]
        for row in rows
    )

    print(
        f"Markets with setups : {len(rows)}"
    )

    print(
        f"Total setups        : {total_setups}"
    )

    print(
        f"Currently covered   : {total_covered}"
    )

    if total_setups:
        print(
            f"Coverage            : "
            f"{total_covered / total_setups * 100:.2f}%"
        )

    print()
    print(
        "TOP MARKETS BY HISTORICAL COVERAGE"
    )
    print("-" * 120)

    for index, row in enumerate(
        rows[:50],
        start=1,
    ):
        print(
            f"{index:>2}. "
            f"{row['symbol']:<12} "
            f"Setups={row['setups']:<3} "
            f"Covered={row['covered']:<3} "
            f"Trades={row['trade_count']:<5} "
            f"FirstSetup={row['first_setup']} "
            f"LastSetup={row['last_setup']} "
            f"TradeMin={row['trade_min']} "
            f"TradeMax={row['trade_max']}"
        )

    print()
    print("=" * 120)


if __name__ == "__main__":
    main()
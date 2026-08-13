from __future__ import annotations

import sqlite3
from pathlib import Path

from models.trade import Trade


DEFAULT_DB_PATH = Path("data/crypto.db")


class TradeStore:
    """
    Persistent storage for public market trades.

    Trades are stored chronologically and can later be queried
    with an as-of timestamp for historical context calculation.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path
        )

        connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        return connection

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,

                    price REAL NOT NULL,
                    volume REAL NOT NULL,

                    side TEXT NOT NULL,

                    UNIQUE (
                        symbol,
                        timestamp,
                        price,
                        volume,
                        side
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_market_trades_symbol_timestamp
                ON market_trades (
                    symbol,
                    timestamp
                )
                """
            )

            connection.commit()

    def save_trade(
        self,
        trade: Trade,
    ) -> bool:
        """
        Save one trade.

        Returns:
            True  -> inserted
            False -> duplicate
        """

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO market_trades (
                    symbol,
                    timestamp,
                    price,
                    volume,
                    side
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    trade.symbol.upper(),
                    int(trade.timestamp),
                    float(trade.price),
                    float(trade.volume),
                    trade.side.strip().lower(),
                ),
            )

            connection.commit()

            return cursor.rowcount == 1

    def save_trades(
        self,
        trades: list[Trade],
    ) -> int:
        """
        Save multiple trades.

        Returns:
            Number of newly inserted trades.
        """

        if not trades:
            return 0

        rows = [
            (
                trade.symbol.upper(),
                int(trade.timestamp),
                float(trade.price),
                float(trade.volume),
                trade.side.strip().lower(),
            )
            for trade in trades
        ]

        with self._connect() as connection:
            before = connection.total_changes

            connection.executemany(
                """
                INSERT OR IGNORE INTO market_trades (
                    symbol,
                    timestamp,
                    price,
                    volume,
                    side
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

            connection.commit()

            return (
                connection.total_changes
                - before
            )

    def get_trades(
        self,
        symbol: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[Trade]:
        """
        Return trades ordered chronologically.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        query = """
            SELECT
                timestamp,
                price,
                volume,
                side
            FROM market_trades
            WHERE symbol = ?
        """

        params: list[object] = [
            normalized_symbol
        ]

        if start_timestamp is not None:
            query += """
                AND timestamp >= ?
            """
            params.append(
                int(start_timestamp)
            )

        if end_timestamp is not None:
            query += """
                AND timestamp <= ?
            """
            params.append(
                int(end_timestamp)
            )

        query += """
            ORDER BY timestamp ASC, id ASC
        """

        with self._connect() as connection:
            rows = connection.execute(
                query,
                tuple(params),
            ).fetchall()

        return [
            Trade(
                timestamp=int(row[0]),
                price=float(row[1]),
                volume=float(row[2]),
                side=str(row[3]),
                symbol=normalized_symbol,
            )
            for row in rows
        ]

    def get_trades_as_of(
        self,
        symbol: str,
        end_timestamp: int,
        lookback_seconds: int | None = None,
    ) -> list[Trade]:
        """
        Return only trades that were available at the given
        historical timestamp.

        This is the key method for preventing look-ahead bias.
        """

        start_timestamp = None

        if lookback_seconds is not None:
            if lookback_seconds <= 0:
                raise ValueError(
                    "Lookback seconds must be greater than zero."
                )

            start_timestamp = (
                int(end_timestamp)
                - int(lookback_seconds)
            )

        return self.get_trades(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

    def count(
        self,
        symbol: str | None = None,
    ) -> int:
        """
        Return stored trade count.
        """

        with self._connect() as connection:
            if symbol is None:
                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM market_trades
                    """
                ).fetchone()

            else:
                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM market_trades
                    WHERE symbol = ?
                    """,
                    (
                        symbol.strip().upper(),
                    ),
                ).fetchone()

        return int(row[0])

    def latest_timestamp(
        self,
        symbol: str,
    ) -> int | None:
        """
        Return latest stored trade timestamp.
        """

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(timestamp)
                FROM market_trades
                WHERE symbol = ?
                """,
                (
                    symbol.strip().upper(),
                ),
            ).fetchone()

        if row is None or row[0] is None:
            return None

        return int(row[0])
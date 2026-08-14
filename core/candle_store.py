from __future__ import annotations

import sqlite3
from pathlib import Path

from models.candle import Candle


DEFAULT_DB_PATH = Path("data/crypto.db")


class CandleStore:
    """
    Persistent storage for live OHLCV candles.

    Unique key:

        (symbol, timeframe, timestamp)

    Repeated WebSocket updates for the same candle update
    the existing row instead of creating duplicates.
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
                CREATE TABLE IF NOT EXISTS live_candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,

                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,

                    UNIQUE (
                        symbol,
                        timeframe,
                        timestamp
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_live_candles_symbol_timeframe_timestamp
                ON live_candles (
                    symbol,
                    timeframe,
                    timestamp
                )
                """
            )

            connection.commit()

    def save(
        self,
        symbol: str,
        candle: Candle,
        timeframe: str = "60",
    ) -> bool:
        """
        Insert or update one candle.

        Symbol belongs to the storage record, not the Candle model.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if not timeframe:
            raise ValueError(
                "Timeframe cannot be empty."
            )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO live_candles (
                    symbol,
                    timeframe,
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    symbol,
                    timeframe,
                    timestamp
                )
                DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
                """,
                (
                    normalized_symbol,
                    str(timeframe),
                    int(candle.timestamp),
                    float(candle.open),
                    float(candle.high),
                    float(candle.low),
                    float(candle.close),
                    float(candle.volume),
                ),
            )

            connection.commit()

        return True

    def get(
        self,
        symbol: str,
        timestamp: int,
        timeframe: str = "60",
    ) -> Candle | None:
        """
        Return one candle by unique key.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM live_candles
                WHERE symbol = ?
                  AND timeframe = ?
                  AND timestamp = ?
                LIMIT 1
                """,
                (
                    normalized_symbol,
                    str(timeframe),
                    int(timestamp),
                ),
            ).fetchone()

        if row is None:
            return None

        return Candle(
            timestamp=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )

    def latest(
        self,
        symbol: str,
        timeframe: str = "60",
    ) -> Candle | None:
        """
        Return the latest stored candle.
        """

        normalized_symbol = (
            symbol.strip().upper()
        )

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM live_candles
                WHERE symbol = ?
                  AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (
                    normalized_symbol,
                    str(timeframe),
                ),
            ).fetchone()

        if row is None:
            return None

        return Candle(
            timestamp=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )

    def get_recent(
        self,
        symbol: str,
        timeframe: str = "60",
        limit: int = 200,
    ) -> list[Candle]:
        """
        Return recent candles in chronological order.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        normalized_symbol = (
            symbol.strip().upper()
        )

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM live_candles
                WHERE symbol = ?
                  AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (
                    normalized_symbol,
                    str(timeframe),
                    int(limit),
                ),
            ).fetchall()

        rows.reverse()

        return [
            Candle(
                timestamp=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in rows
        ]

    def count(
        self,
        symbol: str | None = None,
        timeframe: str = "60",
    ) -> int:
        """
        Return stored candle count.
        """

        with self._connect() as connection:
            if symbol is None:
                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM live_candles
                    WHERE timeframe = ?
                    """,
                    (
                        str(timeframe),
                    ),
                ).fetchone()

            else:
                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM live_candles
                    WHERE symbol = ?
                      AND timeframe = ?
                    """,
                    (
                        symbol.strip().upper(),
                        str(timeframe),
                    ),
                ).fetchone()

        return int(row[0])

    def latest_timestamp(
        self,
        symbol: str,
        timeframe: str = "60",
    ) -> int | None:
        """
        Return latest stored candle timestamp.
        """

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(timestamp)
                FROM live_candles
                WHERE symbol = ?
                  AND timeframe = ?
                """,
                (
                    symbol.strip().upper(),
                    str(timeframe),
                ),
            ).fetchone()

        if row is None or row[0] is None:
            return None

        return int(row[0])
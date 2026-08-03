from core.database import db
from models.candle import Candle


class CandleRepository:

    def save(self, candle: Candle):

        db.execute(
            """
            INSERT INTO candles(
                symbol,
                timeframe,
                timestamp,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                candle.symbol,
                candle.timeframe,
                candle.timestamp.isoformat(),
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume
            )
        )

    def all(self):

        return db.fetchall(
            """
            SELECT *
            FROM candles
            ORDER BY timestamp DESC
            """
        )
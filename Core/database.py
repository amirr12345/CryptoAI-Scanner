import sqlite3
from pathlib import Path

DB_PATH = Path("data/crypto.db")


class Database:

    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)

        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()

        self.create_tables()

    def create_tables(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            timeframe TEXT NOT NULL,

            timestamp TEXT NOT NULL,

            open REAL,

            high REAL,

            low REAL,

            close REAL,

            volume REAL
        )
        """)

        self.conn.commit()

    def execute(self, sql, params=()):
        self.cursor.execute(sql, params)
        self.conn.commit()

    def fetchall(self, sql, params=()):
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


db = Database()

def initialize():
    """
    Initialize database singleton.
    """
    return db
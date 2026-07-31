import sqlite3
import os

os.makedirs("data", exist_ok=True)

DB_PATH = "data/crypto.db"

def connect():
    return sqlite3.connect(DB_PATH)

def initialize():

    conn = connect()

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prices(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT,

            price REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.commit()

    conn.close()
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "database" / "messages.db"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

URL = "https://api.binance.com/api/v3/klines"


def fetch(symbol):
    r = requests.get(URL, params={
        "symbol": symbol,
        "interval": "1m",
        "limit": 200
    })
    return r.json()


def insert_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_data_multi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        close REAL,
        volume REAL
    )
    """)

    total = 0

    for symbol in SYMBOLS:
        data = fetch(symbol)

        for k in data:
            ts = datetime.fromtimestamp(k[0]/1000, timezone.utc).isoformat()
            close = float(k[4])
            vol = float(k[5])

            cur.execute("""
            INSERT OR IGNORE INTO market_data_multi
            (timestamp, symbol, close, volume)
            VALUES (?, ?, ?, ?)
            """, (ts, symbol, close, vol))

            total += 1

    conn.commit()
    conn.close()

    print(f"Inserted {total} rows")


if __name__ == "__main__":
    insert_data()
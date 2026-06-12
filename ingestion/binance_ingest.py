import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests

# Use the existing SQLite database under database/messages.db
DB_PATH = Path(__file__).resolve().parents[1] / "database" / "messages.db"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
LIMIT = 500


def ensure_market_data_table(conn: sqlite3.Connection) -> None:
    """Create the market_data table and a unique index for duplicate protection."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            close_price REAL,
            volume REAL
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp
        ON market_data (symbol, timestamp)
        """
    )
    conn.commit()


def fetch_binance_klines() -> list:
    """Fetch recent 1-minute BTCUSDT klines from Binance public REST API."""
    response = requests.get(
        BINANCE_KLINES_URL,
        params={"symbol": SYMBOL, "interval": INTERVAL, "limit": LIMIT},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def format_timestamp(timestamp_ms: int) -> str:
    """Convert Binance millisecond timestamp to an ISO 8601 UTC string."""
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat()


def ingest_market_data() -> int:
    """Download Binance klines and insert new rows into market_data."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        ensure_market_data_table(conn)
        cur = conn.cursor()

        klines = fetch_binance_klines()
        rows = []
        for kline in klines:
            timestamp_ms = int(kline[0])
            close_price = float(kline[4])
            volume = float(kline[5])
            rows.append(
                (
                    format_timestamp(timestamp_ms),
                    SYMBOL,
                    close_price,
                    volume,
                )
            )

        before_changes = conn.total_changes
        cur.executemany(
            "INSERT OR IGNORE INTO market_data (timestamp, symbol, close_price, volume) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        inserted = conn.total_changes - before_changes

    return inserted


if __name__ == "__main__":
    inserted_count = ingest_market_data()
    print(f"Inserted {inserted_count} new rows into market_data")

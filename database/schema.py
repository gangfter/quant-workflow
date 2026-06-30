"""Single source of truth for the SQLite schema.

Every table used by ingestion / engine / research is defined here.
`ensure_schema(conn)` is idempotent and migration-safe: it creates missing
tables, adds missing columns to legacy tables, and builds indexes.

Run directly to (re)initialize:  python database/schema.py
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = str(ROOT / "database" / "messages.db")

_TABLES = {
    "market_data": """CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        close_price REAL NOT NULL,
        volume REAL NOT NULL)""",
    "premium_data": """CREATE TABLE IF NOT EXISTS premium_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        premium REAL NOT NULL)""",
    "etf_flows": """CREATE TABLE IF NOT EXISTS etf_flows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        net_inflow REAL NOT NULL,
        created_at TEXT)""",
    "funding_data": """CREATE TABLE IF NOT EXISTS funding_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        kind TEXT NOT NULL,
        funding_rate REAL,
        open_interest REAL)""",
    "signals": """CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL DEFAULT 'BTCUSDT',
        r_t INTEGER,
        v_t INTEGER,
        m_t INTEGER,
        score REAL,
        signal TEXT NOT NULL,
        regime TEXT,
        price REAL,
        source TEXT NOT NULL DEFAULT 'live')""",
    "positions": """CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        position_size REAL,
        entry_price REAL NOT NULL,
        exit_price REAL,
        realized_pnl REAL,
        stop_loss REAL,
        take_profit REAL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        idempotency_key TEXT UNIQUE,
        created_at TEXT NOT NULL,
        closed_at TEXT)""",
    "trades_log": """CREATE TABLE IF NOT EXISTS trades_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        regime TEXT,
        action TEXT NOT NULL,
        entry_price REAL,
        exit_price REAL,
        position_size REAL,
        realized_pnl REAL,
        confidence REAL,
        exit_reason TEXT,
        hold_minutes REAL,
        timestamp TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'live')""",
    "signal_performance": """CREATE TABLE IF NOT EXISTS signal_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        signal TEXT NOT NULL,
        entry_price REAL,
        exit_price REAL,
        pnl_pct REAL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        closed_at TEXT)""",
}

# Columns added to tables that may pre-exist with the legacy schema.
_MIGRATIONS = [
    ("signals", "symbol", "TEXT DEFAULT 'BTCUSDT'"),
    ("signals", "regime", "TEXT"),
    ("signals", "price", "REAL"),
    ("signals", "source", "TEXT DEFAULT 'live'"),
    ("positions", "exit_price", "REAL"),
    ("positions", "realized_pnl", "REAL"),
    ("trades_log", "source", "TEXT DEFAULT 'live'"),
    ("signal_performance", "closed_at", "TEXT"),
]

_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data (symbol, timestamp)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_funding_symbol_ts_kind ON funding_data (symbol, timestamp, kind)",
    "CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals (timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_trades_log_timestamp ON trades_log (timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_premium_timestamp ON premium_data (timestamp)",
]


def _existing_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for ddl in _TABLES.values():
        cur.execute(ddl)
    for table, column, decl in _MIGRATIONS:
        if column not in _existing_columns(cur, table):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    for ddl in _INDEXES:
        cur.execute(ddl)
    conn.commit()


def main():
    conn = sqlite3.connect(DB)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print("[SCHEMA OK]", [r[0] for r in cur.fetchall()])
    conn.close()


if __name__ == "__main__":
    main()

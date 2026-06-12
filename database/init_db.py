import sqlite3

conn = sqlite3.connect("database/messages.db")

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS etf_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    net_inflow REAL,
    created_at TEXT
)
""")

# --- State Recovery schema (positions + trades_log) ---
cur.execute("""
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    position_size REAL NOT NULL,
    entry_price REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT DEFAULT 'OPEN',
    idempotency_key TEXT UNIQUE,
    created_at TEXT NOT NULL,
    closed_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS trades_log (
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
    timestamp TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("etf_flows + positions/trades_log created")

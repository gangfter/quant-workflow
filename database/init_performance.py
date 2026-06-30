import sqlite3

conn = sqlite3.connect("database/messages.db")

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS signal_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT,
    signal TEXT,
    entry_price REAL,
    exit_price REAL,
    pnl_pct REAL,
    status TEXT
)
""")

conn.commit()
conn.close()

print("signal_performance table created")
import sqlite3
from datetime import datetime

DB = "database/messages.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    symbol TEXT,
    side TEXT,
    entry_price REAL,
    status TEXT
)
""")

conn.commit()
conn.close()

print("positions table ready")
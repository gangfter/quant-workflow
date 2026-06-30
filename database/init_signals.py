import sqlite3

conn = sqlite3.connect("database/messages.db")

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    r_t INTEGER,
    m_t INTEGER,
    v_t INTEGER,
    score INTEGER,
    signal TEXT
)
""")

conn.commit()
conn.close()

print("signals table created")

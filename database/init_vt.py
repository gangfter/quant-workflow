import sqlite3

conn = sqlite3.connect("database/messages.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS premium_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    premium REAL
)
""")

conn.commit()
conn.close()

print("premium_data created")
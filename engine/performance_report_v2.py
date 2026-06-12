import sqlite3

DB = "database/messages.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
SELECT side, entry_price, status
FROM positions
""")

rows = cur.fetchall()

total = len(rows)
closed = sum(1 for r in rows if r[2] == "CLOSED")

print("\n=== REPORT ===")
print("Total Trades:", total)
print("Closed Trades:", closed)
print("Open Trades:", total - closed)
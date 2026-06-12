import sqlite3

conn = sqlite3.connect("database/messages.db")

cur = conn.cursor()

cur.execute("""
SELECT *
FROM etf_flows
ORDER BY id DESC
LIMIT 5
""")

rows = cur.fetchall()

for row in rows:
    print(row)

conn.close()
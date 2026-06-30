import sqlite3

conn = sqlite3.connect("database/messages.db")

cur = conn.cursor()

cur.execute("""
SELECT *
FROM signals
ORDER BY id DESC
LIMIT 10
""")

for row in cur.fetchall():
    print(row)

conn.close()
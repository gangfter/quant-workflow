import sqlite3
import matplotlib.pyplot as plt

DB = "database/messages.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT created_at, pnl_pct
FROM signal_performance
WHERE pnl_pct IS NOT NULL
ORDER BY created_at
""")

rows = cur.fetchall()

equity = 100
curve = [equity]

for _, pnl in rows:
    equity *= (1 + pnl / 100)
    curve.append(equity)

plt.plot(curve)
plt.title("Equity Curve")
plt.show()

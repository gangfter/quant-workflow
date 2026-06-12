import sqlite3

conn = sqlite3.connect("database/messages.db")
cur = conn.cursor()

cur.execute("""
SELECT close_price, volume
FROM market_data
ORDER BY timestamp DESC
LIMIT 100
""")

rows = cur.fetchall()

prices = [row[0] for row in rows]
volumes = [row[1] for row in rows]

vwap = sum(p * v for p, v in zip(prices, volumes)) / sum(volumes)

current_price = prices[0]

deviation = (current_price - vwap) / vwap

print(f"Current Price: {current_price}")
print(f"VWAP: {vwap}")
print(f"Deviation: {deviation:.4%}")

if deviation > 0.0003:
    m_t = 1
elif deviation < -0.0003:
    m_t = -1
else:
    m_t = 0

print(f"M_t = {m_t}")
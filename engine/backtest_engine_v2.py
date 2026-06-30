from engine.trade_executor import open_position, close_positions
import sqlite3

DB = "database/messages.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()


# latest price
cur.execute("""
SELECT close FROM market_data_multi
ORDER BY timestamp DESC LIMIT 1
""")

price = cur.fetchone()[0]


# latest signal
cur.execute("""
SELECT signal FROM signals
ORDER BY timestamp DESC LIMIT 1
""")

signal = cur.fetchone()[0]


print("Signal:", signal)
print("Price:", price)


# close old trades first
close_positions(price)


# open new trade
if signal in ["LONG", "SHORT"]:
    open_position("BTC", signal, price)
else:
    print("No trade opened")
    
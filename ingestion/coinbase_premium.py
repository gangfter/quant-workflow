import sqlite3
from datetime import datetime

import requests

coinbase = requests.get(
    "https://api.coinbase.com/v2/prices/BTC-USD/spot"
).json()

binance = requests.get(
    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
).json()

coinbase_price = float(coinbase["data"]["amount"])
binance_price = float(binance["price"])

premium = coinbase_price - binance_price

conn = sqlite3.connect("database/messages.db")
cur = conn.cursor()

cur.execute("""
INSERT INTO premium_data (
    timestamp,
    premium
)
VALUES (?, ?)
""", (
    datetime.now().isoformat(),
    premium
))

conn.commit()
conn.close()

print(f"Coinbase: {coinbase_price}")
print(f"Binance: {binance_price}")
print(f"Premium: {premium}")
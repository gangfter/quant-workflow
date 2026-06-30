import sqlite3
from datetime import datetime, timedelta

DB = "database/messages.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()


# =========================
# 1. OPEN trades 가져오기
# =========================
cur.execute("""
SELECT id, created_at, signal, entry_price
FROM signal_performance
WHERE status = 'OPEN'
ORDER BY id ASC
""")

trades = cur.fetchall()


# =========================
# 2. price data 가져오기
# =========================
cur.execute("""
SELECT timestamp, close_price
FROM market_data
ORDER BY timestamp ASC
""")

prices = cur.fetchall()


# timestamp → index map
price_map = {t: p for t, p in prices}

from datetime import timezone

# =========================
# 3. helper: 미래 가격 찾기
# =========================
def get_future_price(entry_time, minutes=5):
    entry_dt = datetime.fromisoformat(entry_time).replace(tzinfo=None)

    target_time = entry_dt + timedelta(minutes=minutes)

    closest = None
    min_diff = float("inf")

    for t, price in prices:
        dt = datetime.fromisoformat(t).replace(tzinfo=None)
        diff = abs((dt - target_time).total_seconds())

        if diff < min_diff:
            min_diff = diff
            closest = price

    return closest


# =========================
# 4. backtest loop
# =========================
equity = 100.0
equity_curve = []

for trade_id, created_at, signal, entry_price in trades:

    exit_price = get_future_price(created_at, minutes=5)

    if not exit_price:
        continue

    pnl = 0

    if signal == "LONG":
        pnl = (exit_price - entry_price) / entry_price * 100

    elif signal == "SHORT":
        pnl = (entry_price - exit_price) / entry_price * 100

    equity += equity * (pnl / 100)
    equity_curve.append(equity)

    cur.execute("""
    UPDATE signal_performance
    SET exit_price = ?, pnl_pct = ?, status = 'CLOSED'
    WHERE id = ?
    """, (exit_price, pnl, trade_id))

    print(f"[TRADE] {signal} | PnL: {pnl:.3f}%")


conn.commit()
conn.close()


# =========================
# 5. 결과
# =========================
print("\n=== RESULT ===")
print(f"Final Equity: {equity:.2f}")
print(f"Trades: {len(trades)}")
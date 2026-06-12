import sqlite3

conn = sqlite3.connect("database/messages.db")
cur = conn.cursor()


# =========================
# 1. closed trades
# =========================
cur.execute("""
SELECT signal, pnl_pct
FROM signal_performance
WHERE status = 'CLOSED'
""")

rows = cur.fetchall()

if not rows:
    print("No closed trades")
    exit()


# =========================
# 2. metrics
# =========================
wins = 0
losses = 0
total_pnl = 0

long_pnl = []
short_pnl = []

for signal, pnl in rows:

    total_pnl += pnl

    if pnl > 0:
        wins += 1
    else:
        losses += 1

    if signal == "LONG":
        long_pnl.append(pnl)
    elif signal == "SHORT":
        short_pnl.append(pnl)


# =========================
# 3. results
# =========================
win_rate = wins / len(rows) * 100
avg_pnl = total_pnl / len(rows)

print("\n=== PERFORMANCE REPORT ===")
print(f"Trades: {len(rows)}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Avg PnL: {avg_pnl:.4f}%")
print(f"Long Trades: {len(long_pnl)}")
print(f"Short Trades: {len(short_pnl)}")

conn.close()
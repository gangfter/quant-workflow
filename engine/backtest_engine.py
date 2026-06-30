import sqlite3
from datetime import datetime

DB_PATH = "database/messages.db"


# =========================
# 1. DB 연결
# =========================
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


# =========================
# 2. OPEN trades 가져오기
# =========================
cur.execute("""
SELECT id, created_at, signal, entry_price
FROM signal_performance
WHERE status = 'OPEN'
ORDER BY id ASC
""")

trades = cur.fetchall()


if not trades:
    print("No OPEN trades")
    conn.close()
    exit()


# =========================
# 3. 가격 데이터 (최신 기준)
# =========================
cur.execute("""
SELECT timestamp, close_price
FROM market_data
ORDER BY timestamp ASC
""")

price_data = cur.fetchall()


# =========================
# 4. 간단 백테스트
# =========================
equity = 100.0
equity_curve = []


for trade_id, created_at, signal, entry_price in trades:

    if not entry_price:
        continue

    exit_price = price_data[-1][1]  # 가장 최신 가격

    pnl = 0

    if signal == "LONG":
        pnl = (exit_price - entry_price) / entry_price * 100

    elif signal == "SHORT":
        pnl = (entry_price - exit_price) / entry_price * 100

    equity += equity * (pnl / 100)

    equity_curve.append(equity)

    # =========================
    # DB 업데이트
    # =========================
    cur.execute("""
    UPDATE signal_performance
    SET
        exit_price = ?,
        pnl_pct = ?,
        status = 'CLOSED'
    WHERE id = ?
    """, (
        exit_price,
        pnl,
        trade_id
    ))

    print(f"[TRADE CLOSED] {signal} | PnL: {pnl:.3f}%")


# =========================
# 5. 결과 출력
# =========================
conn.commit()
conn.close()

print("\n=== BACKTEST SUMMARY ===")
print(f"Final Equity: {equity:.2f}")
print(f"Total Trades: {len(trades)}")
print(f"Avg Equity Step: {sum(equity_curve)/len(equity_curve):.2f}")
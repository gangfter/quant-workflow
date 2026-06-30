import sqlite3
from datetime import datetime

DB_PATH = "database/messages.db"


# =========================
# 1. DB 연결
# =========================
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


# =========================
# 2. OPEN SIGNAL 조회
# =========================
cur.execute("""
SELECT id, created_at, signal, entry_price
FROM signal_performance
WHERE status = 'OPEN'
ORDER BY id ASC
""")

open_signals = cur.fetchall()


if not open_signals:
    print("No OPEN signals to evaluate")
    conn.close()
    exit()


# =========================
# 3. 최신 가격 조회
# =========================
cur.execute("""
SELECT close_price
FROM market_data
ORDER BY timestamp DESC
LIMIT 1
""")

current_price = cur.fetchone()[0]


# =========================
# 4. 평가 루프
# =========================
for signal_id, created_at, signal, entry_price in open_signals:

    if entry_price is None:
        continue

    pnl = 0

    if signal == "LONG":
        pnl = (current_price - entry_price) / entry_price * 100

    elif signal == "SHORT":
        pnl = (entry_price - current_price) / entry_price * 100

    else:
        pnl = 0


    # =========================
    # 5. UPDATE
    # =========================
    cur.execute("""
    UPDATE signal_performance
    SET
        exit_price = ?,
        pnl_pct = ?,
        status = 'CLOSED'
    WHERE id = ?
    """, (
        current_price,
        pnl,
        signal_id
    ))

    print(f"[CLOSED] {signal} | PnL: {pnl:.4f}%")


# =========================
# 6. COMMIT
# =========================
conn.commit()
conn.close()
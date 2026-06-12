import sqlite3
from datetime import datetime

DB = "database/messages.db"


def open_position(symbol, side, price):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO positions (timestamp, symbol, side, entry_price, status)
    VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        symbol,
        side,
        price,
        "OPEN"
    ))

    conn.commit()
    conn.close()


def close_positions(exit_price):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    SELECT id, entry_price, side FROM positions WHERE status='OPEN'
    """)

    rows = cur.fetchall()

    for pid, entry, side in rows:
        pnl = (exit_price - entry) / entry * 100
        if side == "SHORT":
            pnl *= -1

        cur.execute("""
        UPDATE positions
        SET status='CLOSED'
        WHERE id=?
        """, (pid,))

        print(f"[CLOSED] {side} | PnL: {pnl:.3f}%")

    conn.commit()
    conn.close()
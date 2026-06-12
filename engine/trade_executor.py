import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = str(ROOT / "database" / "messages.db")


def _now():
    return datetime.now(timezone.utc).isoformat()


def open_position(symbol, side, price, position_size=None):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO positions (symbol, side, position_size, entry_price, status, created_at)
        VALUES (?, ?, ?, ?, 'OPEN', ?)
        """,
        (symbol, side, position_size, price, _now()),
    )
    conn.commit()
    conn.close()


def close_positions(exit_price):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, symbol, side, entry_price, position_size FROM positions WHERE status='OPEN'"
    )
    rows = cur.fetchall()
    now = _now()
    for pid, symbol, side, entry, size in rows:
        direction = 1.0 if side == "LONG" else -1.0
        pnl_pct = direction * (exit_price - entry) / entry
        realized = direction * (exit_price - entry) * (size or 0.0)
        cur.execute(
            "UPDATE positions SET status='CLOSED', exit_price=?, realized_pnl=?, closed_at=? WHERE id=?",
            (exit_price, realized, now, pid),
        )
        cur.execute(
            """
            INSERT INTO trades_log (symbol, action, entry_price, exit_price, position_size,
                                    realized_pnl, exit_reason, timestamp, source)
            VALUES (?, ?, ?, ?, ?, ?, 'MANUAL_CLOSE', ?, 'live')
            """,
            (symbol, side, entry, exit_price, size, realized, now),
        )
        print(f"[CLOSED] {side} | PnL: {pnl_pct:.3%}")
    conn.commit()
    conn.close()

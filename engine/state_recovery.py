import sqlite3
from datetime import datetime
from typing import Dict, Any, List

DB = "database/messages.db"


def _fetch_latest_price(symbol: str, conn: sqlite3.Connection) -> float:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT close_price
        FROM market_data
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (symbol,),
    )
    row = cur.fetchone()
    return float(row[0]) if row else 0.0


def recover_state() -> Dict[str, Any]:
    """Recover system state after restart.

    No replay execution is performed.
    Returns recovered snapshots for callers (offline logic only).
    """
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- POSITIONS recovery (best-effort based on current schema) ---
    cur.execute("SELECT id, symbol, side, entry_price, status FROM positions")
    rows = cur.fetchall()

    open_positions: List[Dict[str, Any]] = []
    for r in rows:
        if (r["status"] or "").upper() == "CLOSED":
            continue
        current_price = _fetch_latest_price(r["symbol"], conn)
        # size may not exist in current DB schema; keep as None if absent
        size = None
        open_positions.append(
            {
                "symbol": r["symbol"],
                "side": r["side"],
                "size": size,
                "entry_price": r["entry_price"],
                "current_price": current_price,
                "status": r["status"],
            }
        )

    # --- DAILY PNL recovery (requires trades_log table) ---
    daily_pnl = None
    try:
        cur.execute(
            """
            SELECT COALESCE(SUM(realized_pnl + unrealized_pnl), 0)
            FROM trades_log
            """
        )
        daily_pnl = float(cur.fetchone()[0])
    except sqlite3.OperationalError:
        daily_pnl = None

    # --- EXPOSURE recovery (requires position_size/size in positions) ---
    exposure = None
    try:
        cur.execute(
            """
            SELECT COALESCE(SUM(position_size), 0)
            FROM positions
            WHERE (status IS NULL OR status != 'CLOSED')
            """
        )
        exposure = float(cur.fetchone()[0])
    except sqlite3.OperationalError:
        exposure = None

    conn.close()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "positions": open_positions,
        "daily_pnl": daily_pnl,
        "exposure": exposure,
        "signal_state": None,
        "duplicate_order_guard": {"enabled": False, "note": "No idempotency_key schema present"},
    }

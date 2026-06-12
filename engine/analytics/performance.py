import sqlite3
from typing import Dict, Any

DB = "database/messages.db"


def update_performance_metrics(db_path: str = DB) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Only use columns that are confirmed to exist in current schema:
    # realized_pnl, entry_price, exit_price, regime, confidence
    cur.execute("SELECT realized_pnl, regime FROM trades_log")
    rows = cur.fetchall()

    realized = [float(r[0]) for r in rows if r[0] is not None]

    total_trades = len(realized)
    win_mask = [p > 0 for p in realized]
    loss_mask = [p <= 0 for p in realized]

    wins = [p for p, is_win in zip(realized, win_mask) if is_win]
    losses = [p for p, is_loss in zip(realized, loss_mask) if is_loss]

    total_win = sum(wins) if wins else 0.0
    total_loss_abs = abs(sum(losses)) if losses else 0.0

    profit_factor = (total_win / total_loss_abs) if total_loss_abs > 0 else None
    win_rate = (len(wins) / total_trades) if total_trades > 0 else None
    avg_pnl = (sum(realized) / total_trades) if total_trades > 0 else None

    # max_drawdown from cumulative pnl equity curve
    # equity(t) = cumulative sum(realized_pnl)
    peak = float("-inf")
    max_dd = 0.0
    cum = 0.0
    for p in realized:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    conn.close()
    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_pnl": avg_pnl,
        "max_drawdown": max_dd,
    }

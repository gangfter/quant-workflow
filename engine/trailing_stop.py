import sqlite3

DB = "database/messages.db"


def check_trailing_stop():
    """Compute trailing-stop actions for OPEN positions.

    Rule (paper-logic):
    - If take_profit is not set, no action.
    - If price reaches 50% of the distance from entry to take_profit,
      move stop_loss to entry (break-even).
    - If current price falls below stop_loss after break-even move,
      return CLOSE_POSITION for that position.

    Returns a list of actions:
    [{"position_id": int, "action": "UPDATE_STOP"|"CLOSE_POSITION",
      "new_stop_loss": float|None, "reason": "TRAILING_STOP"}, ...]
    """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Current price approximation from market_data
    cur.execute(
        """
        SELECT symbol, close_price
        FROM market_data
        ORDER BY timestamp DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    current_symbol = row[0] if row else None
    current_price = float(row[1]) if row and row[1] is not None else 0.0

    cur.execute(
        """
        SELECT id, symbol, side, entry_price, stop_loss, take_profit
        FROM positions
        WHERE status='OPEN'
        """
    )
    positions = cur.fetchall()

    actions = []

    for pid, sym, side, entry_price, stop_loss, take_profit in positions:
        if take_profit is None:
            continue

        # Determine 50% target along move from entry to take_profit
        tp_50 = entry_price + 0.5 * (take_profit - entry_price)

        # If first time reaching tp_50, set stop to break-even (entry)
        # For LONG, price increase indicates reached. For SHORT, reverse.
        reached = False
        if side == "LONG":
            reached = current_price >= tp_50
        else:
            reached = current_price <= tp_50

        if reached and (stop_loss is None or stop_loss < entry_price):
            actions.append(
                {
                    "position_id": pid,
                    "action": "UPDATE_STOP",
                    "new_stop_loss": float(entry_price),
                    "reason": "TRAILING_STOP",
                }
            )
            # Update in-memory state only; caller can persist.

        # If stop_loss is at/beyond break-even, close if price crosses below stop
        # For LONG: close if current_price < stop_loss
        if stop_loss is not None and current_price > 0:
            if side == "LONG" and current_price < stop_loss:
                actions.append(
                    {
                        "position_id": pid,
                        "action": "CLOSE_POSITION",
                        "new_stop_loss": None,
                        "reason": "TRAILING_STOP",
                    }
                )
            if side == "SHORT" and current_price > stop_loss:
                actions.append(
                    {
                        "position_id": pid,
                        "action": "CLOSE_POSITION",
                        "new_stop_loss": None,
                        "reason": "TRAILING_STOP",
                    }
                )

    conn.close()
    return actions

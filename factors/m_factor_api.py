import sqlite3

DB = "database/messages.db"


def get_m_factor() -> int:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT close_price, volume
        FROM market_data
        ORDER BY timestamp DESC
        LIMIT 100
        """,
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return 0

    prices = [row[0] for row in rows]
    volumes = [row[1] for row in rows]

    denom = sum(volumes)
    if denom == 0:
        return 0

    vwap = sum(p * v for p, v in zip(prices, volumes)) / denom
    current_price = prices[0]
    deviation = (current_price - vwap) / vwap if vwap else 0.0

    if deviation > 0.0005:
        return 1
    if deviation < -0.0005:
        return -1
    return 0

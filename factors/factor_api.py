import sqlite3
import pandas as pd


DB = "database/messages.db"


def _connect():
    return sqlite3.connect(DB)


def get_r_factor() -> int:
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT date, net_inflow
        FROM etf_flows
        ORDER BY date
        """,
        conn,
    )
    conn.close()
    if len(df) < 2:
        return 0
    mean = df["net_inflow"].mean()
    std = df["net_inflow"].std()
    if std == 0:
        return 0
    latest = df["net_inflow"].iloc[-1]
    z_score = (latest - mean) / std
    if z_score > 1.5:
        return 1
    if z_score < -1.5:
        return -1
    return 0


def get_m_factor() -> int:
    conn = _connect()
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
    deviation = (current_price - vwap) / vwap if vwap else 0

    if deviation > 0.0005:
        return 1
    if deviation < -0.0005:
        return -1
    return 0


def get_v_factor() -> int:
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT premium
        FROM premium_data
        ORDER BY id
        """,
        conn,
    )
    conn.close()
    if len(df) < 2:
        return 0
    mean = df["premium"].mean()
    std = df["premium"].std()
    if std == 0:
        return 0
    latest = df["premium"].iloc[-1]
    z_score = (latest - mean) / std
    if z_score > 1.0:
        return 1
    if z_score < -1.0:
        return -1
    return 0

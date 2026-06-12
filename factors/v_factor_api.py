import sqlite3
import pandas as pd

DB = "database/messages.db"


def get_v_factor(candle_timestamp=None) -> int:
    conn = sqlite3.connect(DB)
    if candle_timestamp is None:
        df = pd.read_sql_query(
            """
            SELECT premium, timestamp
            FROM premium_data
            ORDER BY id
            """,
            conn,
        )
    else:
        df = pd.read_sql_query(
            """
            SELECT premium, timestamp
            FROM premium_data
            WHERE timestamp <= ?
            ORDER BY id
            """,
            conn,
            params=[candle_timestamp],
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

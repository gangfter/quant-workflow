import sqlite3
import pandas as pd

DB = "database/messages.db"


def get_r_factor() -> int:
    conn = sqlite3.connect(DB)
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

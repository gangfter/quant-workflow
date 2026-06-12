import sqlite3
import math
from datetime import datetime, timezone

DB = "database/messages.db"


def _mean_std(values):
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(var)
    return mean, std


def get_market_regime(symbol: str = "BTCUSDT", window: int = 48) -> dict:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT close_price, volume
        FROM market_data
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (symbol, window),
    )
    rows = cur.fetchall()
    conn.close()

    if len(rows) < 2:
        # Not enough data; default to RANGE deterministically.
        return {
            "regime": "RANGE",
            "volume_z": 0.0,
            "atr_z": 0.0,
            "action": "FLAT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # rows are newest->oldest; keep aligned with diffs
    close = [r[0] for r in rows][::-1]
    vol = [r[1] for r in rows][::-1]

    current_volume = vol[-1]
    vols_for_stats = vol
    mean_vol, std_vol = _mean_std(vols_for_stats)
    volume_z = 0.0 if std_vol == 0 else (current_volume - mean_vol) / std_vol

    # ATR proxy: abs(diff(close)) using available closes
    atr_proxy = [abs(close[i] - close[i - 1]) for i in range(1, len(close))]
    current_atr = atr_proxy[-1]
    mean_atr, std_atr = _mean_std(atr_proxy)
    atr_z = 0.0 if std_atr == 0 else (current_atr - mean_atr) / std_atr

    if volume_z > 3.0 and atr_z > 2.5:
        regime = "SHOCK"
        action = "FLAT"
    elif volume_z > 1.5 and atr_z > 1.0:
        regime = "TREND"
        action = "CONTINUE"
    else:
        regime = "RANGE"
        action = "CONTINUE"

    return {
        "regime": regime,
        "volume_z": float(volume_z),
        "atr_z": float(atr_z),
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

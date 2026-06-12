from pathlib import Path
import sys
import sqlite3
import subprocess
import re
from datetime import datetime, timezone

# project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from notifications.telegram_alert import send_message


def generate_signal(features: dict) -> dict:
    """Pure mapping from extracted features to a deterministic trading action.

    This function has no side effects and does not call the risk/execution engines.
    """
    score = features.get("score", 0)

    if score >= 2:
        action = "BUY_LONG"
    elif score <= -2:
        action = "SELL_SHORT"
    else:
        return {"action": "FLAT"}

    if action == "FLAT":
        return {"action": "FLAT"}

    return {
        "symbol": features.get("symbol", "BTCUSDT"),
        "action": action,
        "position_size": None,
        "confidence": abs(score) / 3,
        "regime": features.get("regime"),
    }


# =========================
# 0. DATA FRESHNESS GATE
# =========================

_conn = sqlite3.connect(str(ROOT / "database/messages.db"))
_cur = _conn.cursor()
_cur.execute("SELECT timestamp FROM market_data ORDER BY timestamp DESC LIMIT 1")
_row = _cur.fetchone()
_conn.close()

# In backtest mode, staleness gate can be bypassed by setting BACKTEST_MODE.
if not _row:
    print("[ERROR] No market data in DB. Aborting.")
    sys.exit(1)

import os
if not os.getenv("BACKTEST_MODE"):
    _latest_dt = datetime.fromisoformat(_row[0])
    _age_seconds = (datetime.now(timezone.utc) - _latest_dt.replace(tzinfo=timezone.utc)).total_seconds()
    if _age_seconds > 300:
        print(f"[ERROR] Market data is stale ({int(_age_seconds)}s old, max 300s). Aborting.")
        sys.exit(1)


# =========================
# 1. RUN FACTORS
# =========================

def run_factor(script_path):
    return subprocess.check_output(
        ["python", script_path],
        text=True
    )


r_output = run_factor("factors/regime.py")
m_output = run_factor("factors/m_factor.py")
v_output = run_factor("factors/v_factor.py")


# =========================
# 2. PARSE OUTPUT
# =========================

r_match = re.search(r"R_t = (-?\d+)", r_output)
m_match = re.search(r"M_t = (-?\d+)", m_output)
v_match = re.search(r"V_t = (-?\d+)", v_output)

r_t = int(r_match.group(1)) if r_match else 0
m_t = int(m_match.group(1)) if m_match else 0
v_t = int(v_match.group(1)) if v_match else 0


# =========================
# 3. SIGNAL
# =========================

score = r_t + m_t + v_t

if score >= 2:
    signal = "LONG"
elif score <= -2:
    signal = "SHORT"
else:
    signal = "FLAT"


# =========================
# 4. GET CURRENT PRICE (CRITICAL FIX)
# =========================

conn = sqlite3.connect("database/messages.db")
cur = conn.cursor()

cur.execute("""
SELECT close_price
FROM market_data
ORDER BY timestamp DESC
LIMIT 1
""")

row = cur.fetchone()
current_price = row[0] if row else 0


# =========================
# 5. PRINT
# =========================

print(f"R_t = {r_t}")
print(f"M_t = {m_t}")
print(f"V_t = {v_t}")
print(f"Signal = {signal}")
print(f"Price = {current_price}")


# =========================
# 6. SAVE SIGNAL
# =========================

cur.execute("""
INSERT INTO signals (
    timestamp,
    r_t,
    m_t,
    v_t,
    score,
    signal
)
VALUES (?, ?, ?, ?, ?, ?)
""", (
    datetime.now().isoformat(),
    r_t,
    m_t,
    v_t,
    score,
    signal
))


# =========================
# 7. SAVE PERFORMANCE ENTRY
# =========================

cur.execute("""
INSERT INTO signal_performance (
    created_at,
    signal,
    entry_price,
    status
)
VALUES (?, ?, ?, ?)
""", (
    datetime.now().isoformat(),
    signal,
    current_price,
    "OPEN"
))

conn.commit()
conn.close()


# =========================
# 8. TELEGRAM ALERT
# =========================

if signal != "FLAT":
    send_message(
        f"""
Signal: {signal}

Score: {score}

R_t = {r_t}
M_t = {m_t}
V_t = {v_t}

Price = {current_price}
"""
    )
    
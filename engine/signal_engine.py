"""Signal engine.

Importing this module has NO side effects. All runtime behaviour lives in
run_signal_cycle() / main() and executes only under __main__ or when called
explicitly by the orchestrator (run_workflow.py).
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB = str(ROOT / "database" / "messages.db")
MAX_STALENESS_SECONDS = 300


def generate_signal(features: dict) -> dict:
    """Pure mapping from features to a deterministic action. No side effects."""
    score = features.get("score", 0)
    if score >= 2:
        action = "BUY_LONG"
    elif score <= -2:
        action = "SELL_SHORT"
    else:
        return {"action": "FLAT"}
    return {
        "symbol": features.get("symbol", "BTCUSDT"),
        "action": action,
        "position_size": None,
        "confidence": abs(score) / 3,
        "regime": features.get("regime"),
    }


def compute_factors(as_of=None) -> dict:
    from factors.factor_api import get_m_factor, get_r_factor, get_v_factor

    r_t = get_r_factor(as_of)
    v_t = get_v_factor(as_of)
    m_t = get_m_factor(as_of)
    return {"r_t": r_t, "v_t": v_t, "m_t": m_t, "score": r_t + v_t + m_t}


def _latest_market_row(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, close_price FROM market_data ORDER BY timestamp DESC LIMIT 1"
    )
    return cur.fetchone()


def run_signal_cycle(notify: bool = True) -> dict:
    """One live cycle: freshness gate -> factors -> persist -> alert."""
    from database.schema import ensure_schema

    conn = sqlite3.connect(DB)
    ensure_schema(conn)

    row = _latest_market_row(conn)
    if not row:
        conn.close()
        raise RuntimeError("No market data in DB. Run ingestion first.")

    if not os.getenv("BACKTEST_MODE"):
        latest = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - latest).total_seconds()
        if age > MAX_STALENESS_SECONDS:
            conn.close()
            raise RuntimeError(
                f"Market data is stale ({int(age)}s old, max {MAX_STALENESS_SECONDS}s)."
            )

    parts = compute_factors()
    score = parts["score"]
    signal = "LONG" if score >= 2 else "SHORT" if score <= -2 else "FLAT"
    price = row[1]
    now = datetime.now(timezone.utc).isoformat()

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO signals (timestamp, symbol, r_t, v_t, m_t, score, signal, price, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'live')",
        (now, "BTCUSDT", parts["r_t"], parts["v_t"], parts["m_t"], score, signal, price),
    )
    cur.execute(
        "INSERT INTO signal_performance (created_at, signal, entry_price, status) "
        "VALUES (?, ?, ?, 'OPEN')",
        (now, signal, price),
    )
    conn.commit()
    conn.close()

    print(f"R_t = {parts['r_t']}")
    print(f"V_t = {parts['v_t']}")
    print(f"M_t = {parts['m_t']}")
    print(f"Signal = {signal}")
    print(f"Price = {price}")

    if notify and signal != "FLAT":
        try:
            from notifications.telegram_alert import send_message

            send_message(
                f"Signal: {signal}\nScore: {score}\n"
                f"R={parts['r_t']} V={parts['v_t']} M={parts['m_t']}\nPrice={price}"
            )
        except Exception as e:
            print(f"[WARN] telegram alert failed: {e}")

    return {"signal": signal, "price": price, **parts}


def main() -> int:
    try:
        run_signal_cycle()
        return 0
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

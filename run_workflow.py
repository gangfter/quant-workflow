"""Workflow orchestrator (the script OpenClaw schedules).

Pipeline: ingestion -> signal -> regime gate -> risk -> execution gate -> analytics
All paths are ROOT-relative, so this is safe from any CWD (Termux cron).
Execution defaults to DRY_RUN; set WORKFLOW_DRY_RUN=0 to enable real orders.
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

INGEST_STEPS = [
    ("ingestion/binance_ingest.py", True),    # (script, required)
    ("ingestion/coinbase_premium.py", True),
    ("ingestion/funding_ingest.py", False),   # research-only data, non-fatal
]

DRY_RUN = os.getenv("WORKFLOW_DRY_RUN", "1") != "0"
EQUITY = float(os.getenv("WORKFLOW_EQUITY", "10000"))

RISK_PARAMS = {
    "daily_loss_limit": 0.03,
    "risk_per_trade": 0.01,
    "atr_multiplier": 1.5,
    "max_exposure": 0.3,
}


def run_ingestion() -> bool:
    for script, required in INGEST_STEPS:
        result = subprocess.run([sys.executable, str(ROOT / script)], cwd=str(ROOT))
        if result.returncode != 0:
            level = "ERROR" if required else "WARN"
            print(f"[{level}] {script} failed (returncode={result.returncode})")
            if required:
                return False
    return True


def _current_atr(window: int = 14) -> float:
    conn = sqlite3.connect(str(ROOT / "database" / "messages.db"))
    cur = conn.cursor()
    cur.execute(
        "SELECT close_price FROM market_data WHERE symbol='BTCUSDT' "
        "ORDER BY timestamp DESC LIMIT ?",
        (window + 1,),
    )
    closes = [r[0] for r in cur.fetchall()]
    conn.close()
    if len(closes) < 2:
        return 0.0
    diffs = [abs(closes[i] - closes[i + 1]) for i in range(len(closes) - 1)]
    return sum(diffs) / len(diffs)


def main() -> int:
    if not run_ingestion():
        return 1

    from engine.market_regime import get_market_regime
    from engine.signal_engine import generate_signal, run_signal_cycle

    try:
        cycle = run_signal_cycle()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return 1

    regime_data = get_market_regime(symbol="BTCUSDT", window=48)
    regime = regime_data.get("regime")
    print("[REGIME]", regime_data)

    features = {"symbol": "BTCUSDT", "score": cycle["score"], "regime": regime}
    signal = generate_signal(features)

    # Risk First: stand aside on volume/volatility shocks.
    if regime == "SHOCK":
        signal = {"action": "FLAT"}

    if signal.get("action") == "FLAT":
        print("[FLAT] no action")
        return 0

    from engine.risk_engine import evaluate_risk

    atr = _current_atr()
    if atr <= 0:
        print("[ERROR] ATR unavailable - refusing to size a position")
        return 1

    portfolio = {"equity": EQUITY, "exposure": 0.0, "daily_pnl": 0.0, "atr": atr}
    risk = evaluate_risk(signal, portfolio, RISK_PARAMS)
    print("[RISK]", risk)

    if not risk.get("approved") or not risk.get("position_size"):
        return 0

    if DRY_RUN:
        print("[DRY_RUN]", signal, risk["position_size"])
    else:
        from engine import trade_executor

        side = "LONG" if signal["action"] == "BUY_LONG" else "SHORT"
        trade_executor.open_position("BTCUSDT", side, cycle["price"], risk["position_size"])

    try:
        from engine.analytics.performance import update_performance_metrics

        print("[PERF_METRICS]", update_performance_metrics())
    except Exception as e:
        print("[ANALYTICS ERROR]", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())

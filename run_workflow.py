import subprocess
import sys

# ingestion + signal engine runners
steps = [
    "ingestion/binance_ingest.py",
    "ingestion/coinbase_premium.py",
    "engine/signal_engine.py",
]

for step in steps:
    result = subprocess.run(["python", step])
    if result.returncode != 0:
        print(f"[ERROR] {step} failed (returncode={result.returncode}). Aborting.")
        sys.exit(result.returncode)

# =========================
# FINAL WIRING FIX (Signal -> Risk -> Execution)
# =========================

from engine.signal_engine import generate_signal
from engine.risk_engine import evaluate_risk

# REAL EXECUTION BINDING
from engine import trade_executor


def execute_order(signal: dict, position_size: float):
    """Execution bridge (REAL implementation).

    Note: ordering is allowed only if Risk Engine approves and returns a
    non-empty position_size.
    """
    if position_size is None or position_size <= 0:
        return

    return trade_executor.execute_order(
        symbol=signal.get("symbol"),
        action=signal.get("action"),
        size=position_size,
        confidence=signal.get("confidence"),
        regime=signal.get("regime"),
    )


# Minimal feature/portfolio/params wiring placeholders.
# Execution depends on existing data/model integration elsewhere in the project.
DRY_RUN = True

# market regime (dual z-score)
from engine.market_regime import get_market_regime

regime_data = get_market_regime(symbol="BTCUSDT", window=48)
regime = regime_data.get("regime")
print("[REGIME]", regime_data)

features = {"symbol": "BTCUSDT", "score": 0, "regime": regime}

signal = generate_signal(features)

# SHOCK handling: skip/flatten sizing by forcing FLAT
if regime == "SHOCK":
    signal = {"action": "FLAT"}

if signal.get("action") == "FLAT":
    # Terminate immediately on FLAT (no risk engine call)
    sys.exit(0)

portfolio = {
    "equity": 0.0,
    "exposure": 0.0,
    "daily_pnl": 0.0,
    "atr": 0.0,
}
params = {
    "daily_loss_limit": 0.03,
    "risk_per_trade": 0.01,
    "atr_multiplier": 1.5,
    "max_exposure": 0.3,
}

risk = evaluate_risk(signal, portfolio, params)

if not risk.get("approved"):
    sys.exit(0)

position_size = risk.get("position_size")
if position_size is None:
    sys.exit(0)

# EXECUTION GATE
if DRY_RUN:
    print("[DRY_RUN]", signal, position_size)
    # Skip real execution but continue to analytics.
    position_size = None

if position_size is not None:
    try:
        execute_order(signal, position_size)
    except Exception as e:
        print("[EXECUTION ERROR]", e)

# Performance analytics layer (must not stop trading)
try:
    from engine.analytics.performance import update_performance_metrics

    metrics = update_performance_metrics()
    print("[PERF_METRICS]", metrics)
except Exception as e:
    print("[ANALYTICS ERROR]", e)


                

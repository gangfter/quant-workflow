"""Backtest Profit Factor runner.

Research-only CLI wrapper around backtest_runner.simulate/compute_metrics.
It does not persist trades, so live/backtest DB tables are left untouched.

Usage:
    python research/backtest_pf.py [--db-path database/messages.db] [--threshold 2] [--fee-bps 4]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_runner import compute_metrics, regime_breakdown, simulate
from research.data import build_panel


def run(db_path=None, threshold=2, fee_bps=4.0, panel=None):
    if panel is None:
        panel = build_panel(db_path=db_path) if db_path is not None else build_panel()
    df, trades = simulate(panel, threshold=threshold, fee_bps=fee_bps)
    return {
        "metrics": compute_metrics(df, trades),
        "regime": regime_breakdown(trades),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path")
    ap.add_argument("--threshold", type=int, default=2)
    ap.add_argument("--fee-bps", type=float, default=4.0)
    args = ap.parse_args()

    result = run(
        db_path=args.db_path,
        threshold=args.threshold,
        fee_bps=args.fee_bps,
    )
    print("[METRICS]", result["metrics"])
    print("[PF]", result["metrics"].get("profit_factor"))
    print("[REGIME]", result["regime"])


if __name__ == "__main__":
    main()

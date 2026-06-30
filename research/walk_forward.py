"""Anchored walk-forward validation of the score-threshold strategy.

Chronological folds: optimize the threshold in-sample (expanding window),
evaluate strictly out-of-sample. If OOS expectancy collapses versus IS,
the edge is overfit -- do NOT advance to sizing/execution.

Usage: python research/walk_forward.py [--folds 5] [--fee-bps 4]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_runner import compute_metrics, simulate
from research.data import build_panel

THRESHOLDS = [1, 2, 3]


def run(n_folds=5, fee_bps=4.0, panel=None, db_path=None):
    if panel is None:
        panel = build_panel(db_path=db_path) if db_path is not None else build_panel()
    panel = panel.reset_index(drop=True)
    folds = np.array_split(np.asarray(panel.index), n_folds + 1)
    results = []
    for k in range(1, n_folds + 1):
        train = panel.loc[np.concatenate(folds[:k])]
        test = panel.loc[folds[k]]
        best, best_exp = 2, -np.inf
        for th in THRESHOLDS:
            df, trades = simulate(train, th, fee_bps)
            m = compute_metrics(df, trades)
            exp = m.get("expectancy")
            exp = -np.inf if exp is None else exp
            if exp > best_exp:
                best, best_exp = th, exp
        df, trades = simulate(test, best, fee_bps)
        oos = compute_metrics(df, trades)
        results.append(
            {
                "fold": k,
                "best_threshold": best,
                "is_expectancy": None if best_exp == -np.inf else round(best_exp, 6),
                "oos": oos,
            }
        )
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--fee-bps", type=float, default=4.0)
    ap.add_argument("--db-path")
    args = ap.parse_args()
    for r in run(args.folds, args.fee_bps, db_path=args.db_path):
        print(r)


if __name__ == "__main__":
    main()

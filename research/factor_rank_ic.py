"""Spearman Rank IC: robust to outliers / non-linear monotonic alpha.

Usage: python research/factor_rank_ic.py [--horizons 1 5 15 60 240]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.factor_ic import run as run_ic


def run(horizons, panel=None, db_path=None):
    return run_ic(horizons, rank=True, panel=panel, db_path=db_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=[1, 5, 15, 60, 240])
    ap.add_argument("--db-path")
    args = ap.parse_args()
    for f, by_h in run(args.horizons, db_path=args.db_path).items():
        print(f"[{f}]")
        for h, r in by_h.items():
            print(f"  h={h:>4}  RankIC={r['ic']}  t={r['t_stat']}  n={r['n']}")


if __name__ == "__main__":
    main()

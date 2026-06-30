"""Information Coefficient: corr(factor_t, forward_return_{t+h}).

On 1m crypto bars, |IC| > 0.02-0.03 with |t| > 2 is already meaningful.
Usage: python research/factor_ic.py [--horizons 1 5 15 60 240]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.data import build_panel

FACTORS = ["r_raw", "v_raw", "m_raw", "f_raw", "oi_raw"]


def ic(panel, factor, horizon, rank=False):
    df = panel[[factor, f"fwd_{horizon}"]].dropna()
    n = len(df)
    if n < 30:
        return {"ic": None, "t_stat": None, "n": n}
    a, b = df[factor], df[f"fwd_{horizon}"]
    if rank:
        a, b = a.rank(), b.rank()
    if a.nunique() < 2 or b.nunique() < 2:
        return {"ic": None, "t_stat": None, "n": n}
    c = float(a.corr(b))
    if np.isnan(c):
        return {"ic": None, "t_stat": None, "n": n}
    t = c * np.sqrt(n - 2) / np.sqrt(max(1e-12, 1 - c * c))
    return {"ic": round(c, 4), "t_stat": round(float(t), 2), "n": n}


def run(horizons, rank=False, panel=None, db_path=None):
    if panel is None:
        kwargs = {"horizons": horizons}
        if db_path is not None:
            kwargs["db_path"] = db_path
        panel = build_panel(**kwargs)
    results = {}
    for f in FACTORS:
        if f not in panel or panel[f].notna().sum() == 0:
            continue
        results[f] = {h: ic(panel, f, h, rank=rank) for h in horizons}
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=[1, 5, 15, 60, 240])
    ap.add_argument("--db-path")
    args = ap.parse_args()
    for f, by_h in run(args.horizons, db_path=args.db_path).items():
        print(f"[{f}]")
        for h, r in by_h.items():
            print(f"  h={h:>4}  IC={r['ic']}  t={r['t_stat']}  n={r['n']}")


if __name__ == "__main__":
    main()

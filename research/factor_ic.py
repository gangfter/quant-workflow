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

from research.data import build_panel, forward_returns

FACTORS = ["r_raw", "v_raw", "m_raw", "f_raw", "oi_raw"]


def ic(panel, factor, horizon, rank=False):
    df = panel[[factor, f"fwd_{horizon}"]].dropna()
    n = len(df)
    if n < 30:
        return {"ic": None, "t_stat": None, "n": n}
    a, b = df[factor], df[f"fwd_{horizon}"]
    if rank:
        a, b = a.rank(), b.rank()
    c = float(a.corr(b))
    if np.isnan(c):
        return {"ic": None, "t_stat": None, "n": n}
    t = c * np.sqrt(n - 2) / np.sqrt(max(1e-12, 1 - c * c))
    return {"ic": round(c, 4), "t_stat": round(float(t), 2), "n": n}


def run(horizons, rank=False, panel=None):
    if panel is None:
        panel = forward_returns(build_panel(), horizons)
    results = {}
    for f in FACTORS:
        if f not in panel or panel[f].notna().sum() == 0:
            continue
        results[f] = {h: ic(panel, f, h, rank=rank) for h in horizons}
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=[1, 5, 15, 60, 240])
    args = ap.parse_args()
    for f, by_h in run(args.horizons).items():
        print(f"[{f}]")
        for h, r in by_h.items():
            print(f"  h={h:>4}  IC={r['ic']}  t={r['t_stat']}  n={r['n']}")


if __name__ == "__main__":
    main()

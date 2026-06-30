"""Factor decay: IC(h) curve + alpha half-life.

half_life = first horizon where |IC| drops below 50% of its peak
(linear interpolation between tested horizons). None = no decay observed
within the tested range (slow alpha) or no signal at all.

Usage: python research/factor_decay.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.factor_ic import run as run_ic

HORIZONS = [1, 3, 5, 10, 15, 30, 60, 120, 240, 480]


def half_life(ic_by_h):
    pts = sorted((h, abs(v)) for h, v in ic_by_h.items() if v is not None)
    if not pts:
        return None
    peak = max(v for _, v in pts)
    if peak == 0:
        return None
    target = peak / 2
    prev = None
    for h, v in pts:
        if v <= target and prev is not None:
            h0, v0 = prev
            if v0 == v:
                return float(h)
            return round(h0 + (v0 - target) * (h - h0) / (v0 - v), 1)
        prev = (h, v)
    return None


def run(horizons=HORIZONS, panel=None, db_path=None):
    ic_all = run_ic(horizons, panel=panel, db_path=db_path)
    out = {}
    for f, by_h in ic_all.items():
        curve = {h: r["ic"] for h, r in by_h.items()}
        out[f] = {"ic_curve": curve, "half_life_bars": half_life(curve)}
    return out


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=HORIZONS)
    ap.add_argument("--db-path")
    args = ap.parse_args()
    for f, d in run(args.horizons, db_path=args.db_path).items():
        print(f"[{f}] half_life={d['half_life_bars']} bars")
        print(f"  curve={d['ic_curve']}")


if __name__ == "__main__":
    main()

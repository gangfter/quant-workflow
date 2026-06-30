"""IC decay and optimal timeout validation (Phase 3 Cycle 4).

Key question: does the signal's alpha decay faster than the current 240-bar
timeout eats it? If IC peaks at h=5 but we hold h=240, we sit in noise for
235 bars with fee drag accumulating.

Measure:
  1. Rank-IC by horizon (1,2,3,5,10,15,30,60)
  2. Half-life from decay curve
  3. Backtest at timeout={3,5,8,10,15} bars
  4. Find optimal hold = peak PF
  5. If PF still <1.0 at optimal hold, entry is the issue (not exit)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.data import build_panel

ATR_WINDOW = 14


def prepare(panel: pd.DataFrame) -> pd.DataFrame:
    """Add contrarian score and ATR."""
    df = panel.reset_index(drop=True).copy()
    df["score"] = df["r_t"] + df["v_t"] - df["m_t"]  # contrarian
    atr = df["close"].diff().abs().rolling(ATR_WINDOW, min_periods=5).mean()
    df["atr"] = atr
    df["atr_pct"] = atr / df["close"]
    return df


def ic_decay(df: pd.DataFrame) -> dict:
    """Rank-IC by horizon. Returns {horizon: ic}."""
    result = {}
    score = df["score"]
    close = df["close"]
    for h in [1, 2, 3, 5, 10, 15, 30, 60]:
        ret_h = close.shift(-h) / close - 1.0
        valid = pd.concat([score, ret_h], axis=1).dropna()
        if len(valid) < 30:
            result[h] = None
            continue
        a, b = valid.iloc[:, 0].rank(), valid.iloc[:, 1].rank()
        ic = float(a.corr(b))
        result[h] = round(ic, 4) if np.isfinite(ic) else None
    return result


def timeout_backtest(
    df: pd.DataFrame, threshold: int = 2, hold_bars: int = 5,
    rr: float = 1.0, fee_bps: float = 4.0
) -> dict:
    """Single run: signal-flip at hold_bars (or timeout). Returns metrics."""
    n = len(df)
    close = df["close"].to_numpy()
    score = df["score"].to_numpy()
    regime = df["regime"].to_numpy()

    fee = 2 * fee_bps / 1e4
    trades = []
    i = 0
    while i < n - 1:
        s = score[i]
        direction = 1 if s >= threshold else (-1 if s <= -threshold else 0)
        if direction == 0:
            i += 1
            continue
        if regime[i] == "SHOCK":
            i += 1
            continue
        entry_i = i + 1
        if entry_i >= n:
            break
        entry_px = close[entry_i]
        exit_i = min(entry_i + hold_bars, n - 1)
        exit_px = close[exit_i]
        gross = direction * (exit_px - entry_px) / entry_px
        net = gross - fee
        trades.append({"pnl_pct": net, "bars": exit_i - entry_i})
        i = exit_i + 1

    if not trades:
        return {"hold_bars": hold_bars, "trades": 0, "pf": None, "return": 0.0}
    trades_df = pd.DataFrame(trades)
    r = trades_df["pnl_pct"]
    wins = r[r > 0]
    losses = r[r <= 0]
    gw = float(wins.sum()) if len(wins) else 0.0
    gl = float(abs(losses.sum())) if len(losses) else 0.0
    pf = round(gw / gl, 3) if gl > 0 else None
    total_ret = round(float(r.sum()), 4)
    return {
        "hold_bars": hold_bars,
        "trades": len(r),
        "pf": pf,
        "return": total_ret,
        "wr": round(len(wins) / len(r), 4) if len(r) else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fee-bps", type=float, default=4.0)
    ap.add_argument("--db-path")
    args = ap.parse_args()

    panel = build_panel(db_path=args.db_path) if args.db_path else build_panel()
    df = prepare(panel)

    print("[IC DECAY] (contrarian score)")
    ic = ic_decay(df)
    print(f"{'Horizon':>8} {'IC':>8} {'Half-life?':>20}")
    for h in sorted(ic.keys()):
        hl = "-- peak at h=" + str(h) if ic[h] and all(ic.get(hh) is None or ic.get(hh, 0) < ic[h] for hh in [hh for hh in ic if hh < h]) else ""
        print(f"{h:>8} {_fmt(ic[h]):>8} {hl:>20}")

    # Infer half-life: first h where |IC| < 50% of max
    max_ic = max([v for v in ic.values() if v is not None], default=0)
    hl = next((h for h in sorted(ic.keys()) if ic.get(h) and abs(ic[h]) < 0.5 * abs(max_ic)), None)
    print(f"Estimated half-life: ~{hl} bars (|IC| < 50% of peak)\n")

    print("[TIMEOUT SWEEP] (threshold=2, signal-flip exit)")
    print(f"{'Hold (bars)':>12} {'Trades':>8} {'PF':>7} {'Return':>9} {'WR':>7}")
    results = []
    for hb in [3, 5, 8, 10, 15, 30, 60]:
        res = timeout_backtest(df, hold_bars=hb, fee_bps=args.fee_bps)
        results.append(res)
        print(f"{hb:>12} {res['trades']:>8} {_fmt(res['pf']):>7} "
              f"{res['return']:>9.4f} {_fmt(res['wr']):>7}")

    best = max(results, key=lambda x: x['pf'] if x['pf'] else 0)
    print(f"\nBest PF: {best['pf']} at hold={best['hold_bars']} bars (n={best['trades']})")
    if best['pf'] is None or best['pf'] < 1.0:
        print("CONCLUSION: PF <1.0 even at optimal hold. Entry signal, not exit, is the blocker.")
    else:
        print(f"CONCLUSION: PF>1.0 at hold={best['hold_bars']}. Current 240-bar hold is suboptimal.")


def _fmt(x):
    return "--" if x is None else f"{x:.3f}"


if __name__ == "__main__":
    main()

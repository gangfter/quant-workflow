"""R-multiple bracket backtest (research layer only).

Objective shift (Phase 3 Cycle 3):
    Optimize for RR >= 3.0, Win Rate 35-45%, PF > 1.3 -- NOT max win rate.

This is a DIFFERENT engine from backtest_runner.simulate(), which uses
signal-flip exits and has no defined R-multiple. Here every trade has a
fixed risk unit (R = atr_mult * ATR) with a bracket exit:
    SL at -1R, TP at +RR*R, or timeout at max_hold bars.

Trade frequency is cut aggressively via entry filters:
    - higher score threshold
    - TREND-regime-only entries
    - CVD (V / Coinbase-premium) confirmation in the trade direction
    - ATR-expansion filter (atr_z gate)

Data limitation: market_data has close only (no intrabar high/low), so
TP/SL are evaluated close-to-close. This cannot see intrabar stop-outs and
is therefore mildly optimistic; treat absolute numbers as upper bounds and
compare configs relative to each other. Zero lookahead: entries fill at the
NEXT bar's close; the exit scan starts strictly after the fill bar.

Usage:
    python research/bracket_backtest.py [--rr 3.0] [--fee-bps 4]
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
    """Add both score variants, ATR, and the per-bar risk unit to the panel."""
    df = panel.reset_index(drop=True).copy()
    df["score_contra"] = df["r_t"] + df["v_t"] - df["m_t"]   # mean-reversion M
    df["score_mom"] = df["r_t"] + df["v_t"] + df["m_t"]       # momentum M
    atr = df["close"].diff().abs().rolling(ATR_WINDOW, min_periods=5).mean()
    df["atr"] = atr
    df["atr_pct"] = atr / df["close"]
    return df


def backtest(
    df: pd.DataFrame,
    threshold: int = 2,
    rr: float = 3.0,
    atr_mult: float = 1.0,
    fee_bps: float = 4.0,
    trend_only: bool = False,
    require_cvd: bool = False,
    atr_z_min: float = None,
    max_hold: int = 240,
    contrarian: bool = True,
    min_risk: float = 0.0015,
):
    """Single-pass non-overlapping bracket backtest. Returns trades DataFrame.

    Each trade's pnl is expressed in R units: R = atr_mult * atr_pct of risk.
    Fee (round-trip) is subtracted in price terms before the R conversion.
    min_risk floors the risk unit so the fixed fee can't dominate a tiny stop.
    """
    n = len(df)
    close = df["close"].to_numpy()
    score = df["score_contra"].to_numpy() if contrarian else df["score_mom"].to_numpy()
    regime = df["regime"].to_numpy()
    v_t = df["v_t"].to_numpy()
    atr_pct = df["atr_pct"].to_numpy()
    atr_z = df["atr_z"].to_numpy()
    ts = df["ts"].to_numpy()

    fee_rt = 2.0 * fee_bps / 1e4  # round-trip fee in return terms
    trades = []
    i = 0
    while i < n - 1:
        s = score[i]
        direction = 1 if s >= threshold else (-1 if s <= -threshold else 0)
        if direction == 0:
            i += 1
            continue
        # --- entry filters (all evaluated on bar i, pre-fill) ---
        if trend_only and regime[i] != "TREND":
            i += 1
            continue
        if regime[i] == "SHOCK":  # Risk First, same as production
            i += 1
            continue
        if require_cvd and v_t[i] != direction:  # CVD must agree with side
            i += 1
            continue
        if atr_z_min is not None and not (atr_z[i] >= atr_z_min):
            i += 1
            continue
        risk = atr_mult * atr_pct[i]
        if not np.isfinite(risk) or risk < min_risk:  # stop must clear the fee band
            i += 1
            continue

        # --- fill at NEXT bar close (no lookahead) ---
        entry_i = i + 1
        if entry_i >= n:
            break
        entry_px = close[entry_i]
        sl = entry_px * (1 - direction * risk)
        tp = entry_px * (1 + direction * rr * risk)

        exit_i, exit_px, reason = None, None, None
        for j in range(entry_i + 1, min(entry_i + 1 + max_hold, n)):
            c = close[j]
            if direction == 1:
                hit_sl, hit_tp = c <= sl, c >= tp
            else:
                hit_sl, hit_tp = c >= sl, c <= tp
            if hit_sl:  # check stop first (conservative)
                exit_i, exit_px, reason = j, sl, "SL"
                break
            if hit_tp:
                exit_i, exit_px, reason = j, tp, "TP"
                break
        if exit_i is None:  # timeout exit at last available close
            exit_i = min(entry_i + max_hold, n - 1)
            exit_px, reason = close[exit_i], "TIMEOUT"

        gross = direction * (exit_px - entry_px) / entry_px
        net = gross - fee_rt
        r_mult = net / risk
        trades.append(
            {
                "entry_ts": ts[entry_i],
                "exit_ts": ts[exit_i],
                "direction": "LONG" if direction == 1 else "SHORT",
                "regime": regime[i],
                "reason": reason,
                "risk_pct": float(risk),
                "net_pct": float(net),
                "r_mult": float(r_mult),
                "bars": int(exit_i - entry_i),
            }
        )
        i = exit_i + 1  # non-overlapping: resume after exit

    return pd.DataFrame(trades)


def metrics(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {"trades": 0, "win_rate": None, "pf": None, "avg_r": None,
                "avg_win_r": None, "avg_loss_r": None, "total_r": 0.0, "expectancy_r": None}
    r = trades["r_mult"]
    wins = r[r > 0]
    losses = r[r <= 0]
    gw, gl = float(wins.sum()), float(abs(losses.sum()))
    return {
        "trades": int(len(r)),
        "win_rate": round(len(wins) / len(r), 4),
        "pf": round(gw / gl, 3) if gl > 0 else None,
        "avg_r": round(float(r.mean()), 4),
        "avg_win_r": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loss_r": round(float(losses.mean()), 4) if len(losses) else None,
        "total_r": round(float(r.sum()), 3),
        "expectancy_r": round(float(r.mean()), 4),
    }


def build_configs(rr):
    """Direction x stop-width x filter sweep. Wider stops (higher atr_mult)
    move the SL outside 1m noise so RR>=3 brackets can breathe."""
    cfgs = []
    for contra in (True, False):
        tag = "contra" if contra else "mom"
        for am in (2.0, 4.0, 8.0):
            base = dict(contrarian=contra, atr_mult=am, rr=rr)
            cfgs.append((f"{tag} th2 x{am:g}ATR", dict(base, threshold=2)))
            cfgs.append((f"{tag} TREND th2 x{am:g}ATR",
                         dict(base, threshold=2, trend_only=True)))
            cfgs.append((f"{tag} TREND th2 +CVD x{am:g}ATR",
                         dict(base, threshold=2, trend_only=True, require_cvd=True)))
    return cfgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rr", type=float, default=3.0)
    ap.add_argument("--fee-bps", type=float, default=4.0)
    ap.add_argument("--max-hold", type=int, default=240)
    ap.add_argument("--db-path")
    args = ap.parse_args()

    panel = build_panel(db_path=args.db_path) if args.db_path else build_panel()
    df = prepare(panel)
    print(f"[BRACKET] bars={len(df)} rr={args.rr} "
          f"fee={args.fee_bps}bps max_hold={args.max_hold}")
    print(f"{'config':<30} {'N':>5} {'WR':>7} {'PF':>7} "
          f"{'avgR':>7} {'avgW':>7} {'avgL':>7} {'totR':>8}")
    for name, kw in build_configs(args.rr):
        trades = backtest(df, fee_bps=args.fee_bps, max_hold=args.max_hold, **kw)
        m = metrics(trades)
        print(f"{name:<30} {m['trades']:>5} "
              f"{_fmt(m['win_rate']):>7} {_fmt(m['pf']):>7} "
              f"{_fmt(m['avg_r']):>7} {_fmt(m['avg_win_r']):>7} "
              f"{_fmt(m['avg_loss_r']):>7} {_fmt(m['total_r']):>8}")

    # RR frontier: is the edge mean-reverting (PF peaks at LOW rr)?
    print("\n[RR FRONTIER]  (does any RR cross PF>1.3?)")
    print(f"{'config / rr':<26} {'N':>5} {'WR':>7} {'PF':>7} {'avgR':>7}")
    frontier = [
        ("contra th2 x4ATR", dict(contrarian=True, atr_mult=4.0, threshold=2)),
        ("contra th2 x8ATR", dict(contrarian=True, atr_mult=8.0, threshold=2)),
        ("mom TREND+CVD x4ATR",
         dict(contrarian=False, atr_mult=4.0, threshold=2,
              trend_only=True, require_cvd=True)),
    ]
    for name, kw in frontier:
        for rr in (1.0, 1.5, 2.0, 3.0):
            trades = backtest(df, rr=rr, fee_bps=args.fee_bps,
                              max_hold=args.max_hold, **kw)
            m = metrics(trades)
            print(f"{name+' rr'+str(rr):<26} {m['trades']:>5} "
                  f"{_fmt(m['win_rate']):>7} {_fmt(m['pf']):>7} {_fmt(m['avg_r']):>7}")


def _fmt(x):
    return "--" if x is None else f"{x:.3f}"


if __name__ == "__main__":
    main()

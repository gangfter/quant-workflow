"""Research-grade backtest engine.

- Point-in-time factor panel (research/data.py): zero lookahead by construction
- Next-bar fills: a signal decided on bar t is executed at the close of t+1
- Regime gate: SHOCK -> flat (Risk First)
- Metrics: Profit Factor, MDD, Win Rate, Expectancy, Sharpe, regime breakdown
- Trades persisted to trades_log with source='backtest' (live rows untouched)

Usage:
    python backtest_runner.py [--threshold 2] [--fee-bps 4]
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.schema import ensure_schema
from research.data import DB, build_panel

BARS_PER_YEAR = 365 * 24 * 60  # 1m candles


def simulate(panel: pd.DataFrame, threshold: int = 2, fee_bps: float = 4.0):
    df = panel.dropna(subset=["ret_1"]).reset_index(drop=True).copy()
    raw_pos = np.where(df["score"] >= threshold, 1, np.where(df["score"] <= -threshold, -1, 0))
    raw_pos = np.where(df["regime"] == "SHOCK", 0, raw_pos)  # Risk First
    pos = pd.Series(raw_pos, index=df.index).shift(1).fillna(0)  # next-bar execution
    fee = pos.diff().abs().fillna(pos.abs().iloc[0] if len(pos) else 0) * fee_bps / 1e4
    df["pos"] = pos
    df["strat_ret"] = pos * df["ret_1"] - fee
    df["equity"] = (1 + df["strat_ret"]).cumprod()

    trades, entry_i, cur_pos = [], None, 0
    for i in range(len(df)):
        p = int(df["pos"].iloc[i])
        if p != cur_pos:
            if cur_pos != 0 and entry_i is not None:
                trades.append(_trade(df, entry_i, i, cur_pos))
            entry_i = i if p != 0 else None
            cur_pos = p
    if cur_pos != 0 and entry_i is not None:
        trades.append(_trade(df, entry_i, len(df) - 1, cur_pos))
    return df, pd.DataFrame(trades)


def _trade(df, i0, i1, direction):
    e, x = df["close"].iloc[i0], df["close"].iloc[i1]
    return {
        "entry_ts": df["ts"].iloc[i0],
        "exit_ts": df["ts"].iloc[i1],
        "direction": "LONG" if direction > 0 else "SHORT",
        "regime": df["regime"].iloc[i0],
        "entry": float(e),
        "exit": float(x),
        "pnl_pct": float(direction * (x - e) / e),
        "bars": int(i1 - i0),
    }


def compute_metrics(df, trades):
    rets = df["strat_ret"]
    eq = df["equity"]
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak).min()) if len(eq) else 0.0
    sharpe = (
        float(rets.mean() / rets.std() * np.sqrt(BARS_PER_YEAR))
        if len(rets) and rets.std() > 0
        else 0.0
    )
    out = {
        "bars": int(len(df)),
        "total_return": round(float(eq.iloc[-1] - 1), 6) if len(eq) else 0.0,
        "sharpe": round(sharpe, 3),
        "mdd": round(mdd, 5),
        "trades": int(len(trades)),
    }
    if len(trades):
        wins = trades[trades["pnl_pct"] > 0]["pnl_pct"]
        losses = trades[trades["pnl_pct"] <= 0]["pnl_pct"]
        gross_win, gross_loss = float(wins.sum()), float(abs(losses.sum()))
        out.update(
            {
                "win_rate": round(len(wins) / len(trades), 4),
                "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
                "expectancy": round(float(trades["pnl_pct"].mean()), 6),
                "avg_hold_bars": round(float(trades["bars"].mean()), 1),
            }
        )
    return out


def regime_breakdown(trades):
    if trades is None or trades.empty:
        return {}
    out = {}
    for regime, grp in trades.groupby("regime"):
        wins = grp[grp["pnl_pct"] > 0]
        out[regime] = {
            "trades": int(len(grp)),
            "win_rate": round(len(wins) / len(grp), 4),
            "expectancy": round(float(grp["pnl_pct"].mean()), 6),
            "total_pnl_pct": round(float(grp["pnl_pct"].sum()), 6),
        }
    return out


def persist_trades(trades):
    conn = sqlite3.connect(DB)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM trades_log WHERE source='backtest'")
    for t in (trades.to_dict("records") if len(trades) else []):
        cur.execute(
            """
            INSERT INTO trades_log (symbol, regime, action, entry_price, exit_price,
                                    position_size, realized_pnl, confidence, exit_reason,
                                    hold_minutes, timestamp, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'backtest')
            """,
            (
                "BTCUSDT", t["regime"], t["direction"], t["entry"], t["exit"],
                None, t["pnl_pct"], None, "SIGNAL_FLIP", t["bars"], str(t["exit_ts"]),
            ),
        )
    conn.commit()
    conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=2)
    ap.add_argument("--fee-bps", type=float, default=4.0)
    args = ap.parse_args()

    panel = build_panel()
    print(f"[BACKTEST] bars={len(panel)} threshold={args.threshold} fee={args.fee_bps}bps")
    df, trades = simulate(panel, args.threshold, args.fee_bps)
    metrics = compute_metrics(df, trades)
    print("[METRICS]", metrics)
    print("[REGIME]", regime_breakdown(trades))
    persist_trades(trades)
    return metrics


if __name__ == "__main__":
    main()

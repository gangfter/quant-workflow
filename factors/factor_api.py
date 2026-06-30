"""Unified point-in-time factor API (single source of truth).

Contract -- every factor follows the same signature:

    get_x_factor(as_of=None) -> int in {-1, 0, +1}

`as_of` (ISO-8601 string or datetime): only data observable at `as_of`
is used. None = "now" (live mode). Lookahead bias is eliminated by
construction:

- R (ETF flows): flows for day D publish after US close, so the
  point-in-time query uses days strictly BEFORE DATE(as_of).
- V / M / F / OI: rows with timestamp <= as_of only.

Thresholds live in THRESHOLDS and are shared with research/ so live
signals and research panels can never diverge.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = str(ROOT / "database" / "messages.db")

THRESHOLDS = {"r": 1.5, "v": 1.0, "m": 0.0005, "f": 1.0, "oi": 1.0}
VWAP_WINDOW = 100      # bars for M
PREMIUM_WINDOW = 500   # premium observations for V
FUNDING_WINDOW = 90    # funding/OI observations for F/OI


def _connect():
    return sqlite3.connect(DB)


def _iso(as_of):
    if as_of is None:
        return None
    if isinstance(as_of, datetime):
        return as_of.isoformat()
    return str(as_of)


def _zscore_last(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = var ** 0.5
    if std == 0:
        return 0.0
    return (values[-1] - mean) / std


def _disc(value, threshold):
    if value > threshold:
        return 1
    if value < -threshold:
        return -1
    return 0


def _trailing(table, column, as_of, limit, extra=""):
    """Last `limit` non-null observations at or before `as_of` (oldest first)."""
    conn = _connect()
    cur = conn.cursor()
    ts = _iso(as_of)
    try:
        if ts is None:
            cur.execute(
                f"SELECT {column} FROM {table} "
                f"WHERE {column} IS NOT NULL {extra} "
                f"ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        else:
            cur.execute(
                f"SELECT {column} FROM {table} "
                f"WHERE {column} IS NOT NULL {extra} AND timestamp <= ? "
                f"ORDER BY timestamp DESC LIMIT ?",
                (ts, limit),
            )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [r[0] for r in rows][::-1]


def get_r_factor(as_of=None) -> int:
    """ETF net-inflow z-score (expanding). T+1 publication lag enforced."""
    conn = _connect()
    cur = conn.cursor()
    ts = _iso(as_of)
    if ts is None:
        cur.execute("SELECT net_inflow FROM etf_flows ORDER BY date")
    else:
        cur.execute(
            "SELECT net_inflow FROM etf_flows WHERE date < DATE(?) ORDER BY date",
            (ts,),
        )
    vals = [r[0] for r in cur.fetchall()]
    conn.close()
    return _disc(_zscore_last(vals), THRESHOLDS["r"])


def get_v_factor(as_of=None) -> int:
    """Coinbase premium z-score over a trailing window."""
    vals = _trailing("premium_data", "premium", as_of, PREMIUM_WINDOW)
    return _disc(_zscore_last(vals), THRESHOLDS["v"])


def get_m_factor(as_of=None) -> int:
    """VWAP momentum: deviation of last close from trailing VWAP."""
    conn = _connect()
    cur = conn.cursor()
    ts = _iso(as_of)
    if ts is None:
        cur.execute(
            "SELECT close_price, volume FROM market_data "
            "ORDER BY timestamp DESC LIMIT ?",
            (VWAP_WINDOW,),
        )
    else:
        cur.execute(
            "SELECT close_price, volume FROM market_data WHERE timestamp <= ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (ts, VWAP_WINDOW),
        )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return 0
    prices = [r[0] for r in rows]
    volumes = [r[1] for r in rows]
    denom = sum(volumes)
    if denom == 0:
        return 0
    vwap = sum(p * v for p, v in zip(prices, volumes)) / denom
    if vwap == 0:
        return 0
    deviation = (prices[0] - vwap) / vwap
    return _disc(deviation, THRESHOLDS["m"])


def get_f_factor(as_of=None) -> int:
    """Funding-rate z-score, CONTRARIAN: crowded longs (+z) -> -1.

    Candidate alpha. Not wired into S_final until validated in research/.
    """
    vals = _trailing(
        "funding_data", "funding_rate", as_of, FUNDING_WINDOW,
        extra="AND kind='funding'",
    )
    return -_disc(_zscore_last(vals), THRESHOLDS["f"])


def get_oi_factor(as_of=None) -> int:
    """Open-interest expansion z-score. Candidate alpha (direction TBD by IC)."""
    vals = _trailing(
        "funding_data", "open_interest", as_of, FUNDING_WINDOW,
        extra="AND kind='oi'",
    )
    return _disc(_zscore_last(vals), THRESHOLDS["oi"])

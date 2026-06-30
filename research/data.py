"""Point-in-time factor panel builder for research.

`build_panel()` is the research data access API. Every factor row at bar t
uses only source data observable at or before t:
- M: trailing-window VWAP deviation over market bars <= t
- V: premium z-score, backward as-of joined onto market bars
- R: ETF-flow expanding z-score with T+1 publication lag
- Funding/OI: event z-scores, backward as-of joined onto market bars

Forward returns are labels only; they are never used to compute factors.
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factors.factor_api import FUNDING_WINDOW, PREMIUM_WINDOW, THRESHOLDS, VWAP_WINDOW

DB = str(ROOT / "database" / "messages.db")


def _to_naive_utc(series):
    """Normalize mixed tz-aware/naive ISO timestamps to naive UTC datetime64."""
    return pd.to_datetime(series, utc=True, format="mixed").dt.tz_localize(None)


def _asof_sql(as_of):
    if as_of is None:
        return None
    if isinstance(as_of, datetime):
        return as_of.isoformat()
    return str(as_of)


def _normalize_horizons(horizon=None, horizons=None):
    if horizon is not None and horizons is not None:
        raise ValueError("Use either horizon or horizons, not both")
    if horizon is not None:
        return [int(horizon)]
    if horizons is None:
        return []
    return [int(h) for h in horizons]


def _read(conn, sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


def _connect_readonly(db_path):
    path = Path(db_path)
    if not path.exists():
        raise RuntimeError(f"database not found: {path}")
    uri = "file:" + path.resolve().as_posix() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _event_z(df, col, window, as_of=None):
    """Rolling z-score of an irregular event series (PIT-safe: trailing only)."""
    if df.empty:
        return pd.DataFrame(columns=["ts", "z"])
    d = df.copy()
    d["ts"] = _to_naive_utc(d["timestamp"])
    if as_of is not None:
        cutoff = _to_naive_utc(pd.Series([as_of])).iloc[0]
        d = d[d["ts"] <= cutoff]
    d = d.drop_duplicates("ts").sort_values("ts")
    mu = d[col].rolling(window, min_periods=5).mean()
    sd = d[col].rolling(window, min_periods=5).std()
    d["z"] = (d[col] - mu) / sd.replace(0, np.nan)
    return d[["ts", "z"]].dropna()


def _disc(s, th):
    return np.sign(s).where(s.abs() > th, 0).fillna(0).astype(int)


def build_panel(
    db_path=DB,
    symbol="BTCUSDT",
    horizon=None,
    horizons=None,
    as_of=None,
    regime_window=48,
):
    """Build a point-in-time research panel.

    Args:
        db_path: SQLite database path.
        symbol: Market/funding symbol to load.
        horizon: Optional single forward-return horizon in bars.
        horizons: Optional iterable of forward-return horizons in bars.
        as_of: Optional timestamp cutoff. Source rows after this timestamp are
            excluded before factor construction.
        regime_window: Rolling bars for the regime helper columns.
    """
    requested_horizons = _normalize_horizons(horizon, horizons)
    cutoff = _asof_sql(as_of)
    conn = _connect_readonly(db_path)
    market_sql = (
        "SELECT timestamp, symbol, close_price AS close, volume FROM market_data "
        "WHERE symbol=?"
    )
    market_params = [symbol]
    if cutoff is not None:
        market_sql += " AND timestamp <= ?"
        market_params.append(cutoff)
    market_sql += " ORDER BY timestamp"
    try:
        px = _read(
            conn,
            market_sql,
            tuple(market_params),
        )
    except Exception as exc:
        conn.close()
        raise RuntimeError("market_data table is missing or unreadable") from exc

    event_cutoff = " WHERE timestamp <= ?" if cutoff is not None else ""
    event_params = (cutoff,) if cutoff is not None else ()
    prem = _read(
        conn,
        f"SELECT timestamp, premium FROM premium_data{event_cutoff} ORDER BY timestamp",
        event_params,
    )

    etf_cutoff = " WHERE date < DATE(?)" if cutoff is not None else ""
    etf_params = (cutoff,) if cutoff is not None else ()
    etf = _read(
        conn,
        f"SELECT date, net_inflow FROM etf_flows{etf_cutoff} ORDER BY date",
        etf_params,
    )

    try:
        funding_sql = (
            "SELECT timestamp, funding_rate FROM funding_data "
            "WHERE kind='funding' AND symbol=?"
        )
        oi_sql = (
            "SELECT timestamp, open_interest FROM funding_data "
            "WHERE kind='oi' AND symbol=?"
        )
        funding_params = [symbol]
        oi_params = [symbol]
        if cutoff is not None:
            funding_sql += " AND timestamp <= ?"
            oi_sql += " AND timestamp <= ?"
            funding_params.append(cutoff)
            oi_params.append(cutoff)
        funding_sql += " ORDER BY timestamp"
        oi_sql += " ORDER BY timestamp"
        fund = _read(
            conn,
            funding_sql,
            tuple(funding_params),
        )
        oi = _read(
            conn,
            oi_sql,
            tuple(oi_params),
        )
    except Exception:
        fund = pd.DataFrame(columns=["timestamp", "funding_rate"])
        oi = pd.DataFrame(columns=["timestamp", "open_interest"])
    conn.close()

    if px.empty:
        raise RuntimeError("market_data is empty - run ingestion first")

    px["ts"] = _to_naive_utc(px["timestamp"])
    px = px.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    px["symbol"] = symbol

    # M: trailing VWAP deviation
    pv = (px["close"] * px["volume"]).rolling(VWAP_WINDOW, min_periods=10).sum()
    vv = px["volume"].rolling(VWAP_WINDOW, min_periods=10).sum()
    vwap = pv / vv.replace(0, np.nan)
    px["m_raw"] = (px["close"] - vwap) / vwap

    # V / F / OI: event z-scores, as-of joined backward
    for name, (df, col, win) in {
        "v_raw": (prem, "premium", PREMIUM_WINDOW),
        "funding_raw": (fund, "funding_rate", FUNDING_WINDOW),
        "oi_raw": (oi, "open_interest", FUNDING_WINDOW),
    }.items():
        ev = _event_z(df, col, win, as_of=cutoff)
        if ev.empty:
            px[name] = np.nan
        else:
            px = pd.merge_asof(
                px, ev.rename(columns={"z": name}), on="ts", direction="backward"
            )

    # R: daily ETF flow expanding z, observable from the next UTC date.
    if not etf.empty:
        e = etf.copy()
        e["flow_date"] = _to_naive_utc(e["date"])
        e = e.drop_duplicates("flow_date").sort_values("flow_date")
        mu = e["net_inflow"].expanding(min_periods=2).mean()
        sd = e["net_inflow"].expanding(min_periods=2).std()
        e["r_raw"] = (e["net_inflow"] - mu) / sd.replace(0, np.nan)
        e["ts"] = e["flow_date"] + pd.Timedelta(days=1)
        e = e.drop_duplicates("ts").sort_values("ts")
        if cutoff is not None:
            cutoff_ts = _to_naive_utc(pd.Series([cutoff])).iloc[0]
            e = e[e["ts"] <= cutoff_ts]
        px = pd.merge_asof(px, e[["ts", "r_raw"]].dropna(), on="ts", direction="backward")
    else:
        px["r_raw"] = np.nan

    # Discrete factors (same thresholds as live)
    px["r_t"] = _disc(px["r_raw"], THRESHOLDS["r"])
    px["v_t"] = _disc(px["v_raw"], THRESHOLDS["v"])
    px["m_t"] = _disc(px["m_raw"], THRESHOLDS["m"])
    px["funding_t"] = -_disc(px["funding_raw"], THRESHOLDS["f"])   # contrarian
    px["oi_t"] = _disc(px["oi_raw"], THRESHOLDS["oi"])

    # Compatibility aliases for existing research modules.
    px["f_raw"] = px["funding_raw"]
    px["r"] = px["r_t"]
    px["v"] = px["v_t"]
    px["m"] = px["m_t"]
    px["f"] = px["funding_t"]
    px["oi"] = px["oi_t"]
    px["score"] = px["r"] + px["v"] + px["m"]

    # Regime (same rule as engine/market_regime.py, computed point-in-time)
    vol_mu = px["volume"].rolling(regime_window, min_periods=2).mean()
    vol_sd = px["volume"].rolling(regime_window, min_periods=2).std()
    px["vol_z"] = ((px["volume"] - vol_mu) / vol_sd.replace(0, np.nan)).fillna(0)
    atr = px["close"].diff().abs()
    atr_mu = atr.rolling(regime_window, min_periods=2).mean()
    atr_sd = atr.rolling(regime_window, min_periods=2).std()
    px["atr_z"] = ((atr - atr_mu) / atr_sd.replace(0, np.nan)).fillna(0)
    px["regime"] = np.where(
        (px["vol_z"] > 3.0) & (px["atr_z"] > 2.5),
        "SHOCK",
        np.where((px["vol_z"] > 1.5) & (px["atr_z"] > 1.0), "TREND", "RANGE"),
    )

    px["ret_1"] = px["close"].pct_change().shift(-1)  # forward 1-bar return
    if requested_horizons:
        px = forward_returns(px, requested_horizons)
    return px


def forward_returns(panel, horizons):
    out = panel.copy()
    for h in horizons:
        out[f"fwd_{h}"] = out["close"].shift(-h) / out["close"] - 1.0
    return out

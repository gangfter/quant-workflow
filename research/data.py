"""Point-in-time factor panel builder (the research workhorse).

Every row t uses ONLY data observable at bar t:
- M:   trailing-window VWAP deviation (bars <= t)
- V:   premium z over trailing window, as-of joined backward
- R:   daily ETF-flow expanding z, shifted 1 day (T+1 publication lag)
- F:   funding-rate z (events <= t), OI: open-interest z
- regime: rolling volume-z / ATR-z, same rule as engine/market_regime.py

Discrete thresholds are imported from factors/factor_api.py so research
and live signals can never diverge.
"""
import sqlite3
import sys
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


def _read(conn, sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


def _event_z(df, col, window):
    """Rolling z-score of an irregular event series (PIT-safe: trailing only)."""
    if df.empty:
        return pd.DataFrame(columns=["ts", "z"])
    d = df.copy()
    d["ts"] = _to_naive_utc(d["timestamp"])
    d = d.drop_duplicates("ts").sort_values("ts")
    mu = d[col].rolling(window, min_periods=5).mean()
    sd = d[col].rolling(window, min_periods=5).std()
    d["z"] = (d[col] - mu) / sd.replace(0, np.nan)
    return d[["ts", "z"]].dropna()


def _disc(s, th):
    return np.sign(s).where(s.abs() > th, 0).fillna(0).astype(int)


def build_panel(db_path=DB, symbol="BTCUSDT", regime_window=48):
    conn = sqlite3.connect(db_path)
    px = _read(
        conn,
        "SELECT timestamp, close_price AS close, volume FROM market_data "
        "WHERE symbol=? ORDER BY timestamp",
        (symbol,),
    )
    prem = _read(conn, "SELECT timestamp, premium FROM premium_data ORDER BY timestamp")
    etf = _read(conn, "SELECT date, net_inflow FROM etf_flows ORDER BY date")
    try:
        fund = _read(
            conn,
            "SELECT timestamp, funding_rate FROM funding_data "
            "WHERE kind='funding' AND symbol=? ORDER BY timestamp",
            (symbol,),
        )
        oi = _read(
            conn,
            "SELECT timestamp, open_interest FROM funding_data "
            "WHERE kind='oi' AND symbol=? ORDER BY timestamp",
            (symbol,),
        )
    except Exception:
        fund = pd.DataFrame(columns=["timestamp", "funding_rate"])
        oi = pd.DataFrame(columns=["timestamp", "open_interest"])
    conn.close()

    if px.empty:
        raise RuntimeError("market_data is empty - run ingestion first")

    px["ts"] = _to_naive_utc(px["timestamp"])
    px = px.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)

    # M: trailing VWAP deviation
    pv = (px["close"] * px["volume"]).rolling(VWAP_WINDOW, min_periods=10).sum()
    vv = px["volume"].rolling(VWAP_WINDOW, min_periods=10).sum()
    vwap = pv / vv.replace(0, np.nan)
    px["m_raw"] = (px["close"] - vwap) / vwap

    # V / F / OI: event z-scores, as-of joined backward
    for name, (df, col, win) in {
        "v_raw": (prem, "premium", PREMIUM_WINDOW),
        "f_raw": (fund, "funding_rate", FUNDING_WINDOW),
        "oi_raw": (oi, "open_interest", FUNDING_WINDOW),
    }.items():
        ev = _event_z(df, col, win)
        if ev.empty:
            px[name] = np.nan
        else:
            px = pd.merge_asof(
                px, ev.rename(columns={"z": name}), on="ts", direction="backward"
            )

    # R: daily ETF flow expanding z, T+1 lag
    if not etf.empty:
        e = etf.copy()
        e["ts"] = _to_naive_utc(e["date"])
        e = e.drop_duplicates("ts").sort_values("ts")
        mu = e["net_inflow"].expanding(min_periods=2).mean()
        sd = e["net_inflow"].expanding(min_periods=2).std()
        e["r_raw"] = ((e["net_inflow"] - mu) / sd.replace(0, np.nan)).shift(1)
        px = pd.merge_asof(px, e[["ts", "r_raw"]].dropna(), on="ts", direction="backward")
    else:
        px["r_raw"] = np.nan

    # Discrete factors (same thresholds as live)
    px["r"] = _disc(px["r_raw"], THRESHOLDS["r"])
    px["v"] = _disc(px["v_raw"], THRESHOLDS["v"])
    px["m"] = _disc(px["m_raw"], THRESHOLDS["m"])
    px["f"] = -_disc(px["f_raw"], THRESHOLDS["f"])   # contrarian
    px["oi"] = _disc(px["oi_raw"], THRESHOLDS["oi"])
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
    return px


def forward_returns(panel, horizons):
    out = panel.copy()
    for h in horizons:
        out[f"fwd_{h}"] = out["close"].shift(-h) / out["close"] - 1.0
    return out

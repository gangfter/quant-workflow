"""Funding rate + open interest ingestion (Binance USDT-M futures, free API).

Research-only data feeding the F / OI candidate factors. run_workflow treats
this step as OPTIONAL: failure here never blocks the main pipeline.
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB = str(ROOT / "database" / "messages.db")
SYMBOL = "BTCUSDT"
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"


def _ms_to_iso(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


def ingest_funding(cur):
    rows = requests.get(
        FUNDING_URL, params={"symbol": SYMBOL, "limit": 200}, timeout=10
    ).json()
    for r in rows:
        cur.execute(
            "INSERT OR IGNORE INTO funding_data (timestamp, symbol, kind, funding_rate) "
            "VALUES (?, ?, 'funding', ?)",
            (_ms_to_iso(r["fundingTime"]), SYMBOL, float(r["fundingRate"])),
        )


def ingest_open_interest(cur):
    rows = requests.get(
        OI_HIST_URL, params={"symbol": SYMBOL, "period": "5m", "limit": 200}, timeout=10
    ).json()
    for r in rows:
        cur.execute(
            "INSERT OR IGNORE INTO funding_data (timestamp, symbol, kind, open_interest) "
            "VALUES (?, ?, 'oi', ?)",
            (_ms_to_iso(r["timestamp"]), SYMBOL, float(r["sumOpenInterest"])),
        )


def main():
    from database.schema import ensure_schema

    conn = sqlite3.connect(DB)
    ensure_schema(conn)
    cur = conn.cursor()
    ingest_funding(cur)
    ingest_open_interest(cur)
    conn.commit()
    cur.execute("SELECT kind, COUNT(*) FROM funding_data GROUP BY kind")
    print("[FUNDING_INGEST]", dict(cur.fetchall()))
    conn.close()


if __name__ == "__main__":
    main()

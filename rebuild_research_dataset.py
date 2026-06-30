#!/usr/bin/env python3
"""
Rebuild research dataset from scratch.

Tasks:
1. Create and initialize database schema
2. Ingest 30 days of BTCUSDT 1m market data from Binance
3. Ingest funding rates and open interest
4. Ingest premium data
5. Generate ETF flow data
6. Validate minimum data requirements
7. Report table statistics
"""
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
import numpy as np

ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT))

from database.schema import ensure_schema

DB_PATH = ROOT / "database" / "messages.db"
SYMBOL = "BTCUSDT"
BINANCE_URL = "https://api.binance.com/api/v3/klines"
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
OI_URL = "https://fapi.binance.com/futures/data/openInterestHist"


def _ms_to_iso(ms):
    """Convert milliseconds to ISO 8601 UTC string."""
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


def _ensure_db():
    """Create database and schema if absent."""
    conn = sqlite3.connect(str(DB_PATH))
    ensure_schema(conn)
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")


def _ingest_market_data_30d(conn):
    """Fetch 30 days of 1m BTCUSDT data from Binance."""
    cur = conn.cursor()

    # Calculate time windows: fetch ~500 bars per request, going back 30 days
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    thirty_days_ago_ms = now_ms - (30 * 24 * 60 * 60 * 1000)

    # Binance API allows max 1000 bars per request, we'll use 500 for safety
    window_ms = 500 * 60 * 1000  # 500 bars * 60 seconds * 1000 ms

    inserted = 0
    current_end_ms = now_ms

    print(f"[MARKET] Fetching {SYMBOL} 1m data (30 days window)...")

    while current_end_ms > thirty_days_ago_ms:
        try:
            params = {
                "symbol": SYMBOL,
                "interval": "1m",
                "endTime": current_end_ms,
                "limit": 500,
            }
            response = requests.get(BINANCE_URL, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()

            if not klines:
                break

            rows = []
            for kline in klines:
                ts_ms = int(kline[0])
                close = float(kline[4])
                volume = float(kline[7])  # Quote asset volume
                rows.append((_ms_to_iso(ts_ms), SYMBOL, close, volume))

            before = conn.total_changes
            cur.executemany(
                "INSERT OR IGNORE INTO market_data (timestamp, symbol, close_price, volume) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            inserted += conn.total_changes - before

            # Move to the start of the last batch
            current_end_ms = int(klines[0][0]) - 1
            print(f"  Fetched {len(klines)} bars, inserted {inserted} unique")

        except Exception as e:
            print(f"  Warning: {e}")
            break

    print(f"[MARKET] Total inserted: {inserted} bars")
    return inserted


def _ingest_funding_data(conn):
    """Fetch funding rates and open interest."""
    cur = conn.cursor()

    print(f"[FUNDING] Fetching {SYMBOL} funding rates...")
    try:
        rows = requests.get(
            FUNDING_URL,
            params={"symbol": SYMBOL, "limit": 1000},
            timeout=10,
        ).json()

        inserted = 0
        for r in rows:
            ts = _ms_to_iso(r["fundingTime"])
            funding_rate = float(r["fundingRate"])
            cur.execute(
                "INSERT OR IGNORE INTO funding_data (timestamp, symbol, kind, funding_rate) "
                "VALUES (?, ?, 'funding', ?)",
                (ts, SYMBOL, funding_rate),
            )
            inserted += 1

        conn.commit()
        print(f"[FUNDING] Inserted {inserted} funding rate records")
    except Exception as e:
        print(f"[FUNDING] Warning: {e}")

    print(f"[OI] Fetching {SYMBOL} open interest...")
    try:
        rows = requests.get(
            OI_URL,
            params={"symbol": SYMBOL, "period": "5m", "limit": 1000},
            timeout=10,
        ).json()

        inserted = 0
        for r in rows:
            ts = _ms_to_iso(r["timestamp"])
            oi = float(r["sumOpenInterest"])
            cur.execute(
                "INSERT OR IGNORE INTO funding_data (timestamp, symbol, kind, open_interest) "
                "VALUES (?, ?, 'oi', ?)",
                (ts, SYMBOL, oi),
            )
            inserted += 1

        conn.commit()
        print(f"[OI] Inserted {inserted} OI records")
    except Exception as e:
        print(f"[OI] Warning: {e}")


def _ingest_premium_data(conn):
    """Generate synthetic premium data (CBP - BPUSDT typically -$50 to +$200)."""
    cur = conn.cursor()

    print(f"[PREMIUM] Generating synthetic premium data...")

    # Get market data timestamps
    cur.execute("SELECT DISTINCT timestamp FROM market_data ORDER BY timestamp")
    timestamps = [row[0] for row in cur.fetchall()]

    if not timestamps:
        print("[PREMIUM] No market data found, skipping")
        return

    # Generate synthetic but realistic premium values
    np.random.seed(42)
    premiums = np.cumsum(np.random.normal(0, 5, len(timestamps))) + 50

    inserted = 0
    for ts, premium in zip(timestamps, premiums):
        try:
            cur.execute(
                "INSERT OR IGNORE INTO premium_data (timestamp, premium) VALUES (?, ?)",
                (ts, float(premium)),
            )
            inserted += 1
        except Exception:
            pass

    conn.commit()
    print(f"[PREMIUM] Inserted {inserted} premium records")


def _ingest_etf_flows(conn):
    """Generate synthetic ETF flow data."""
    cur = conn.cursor()

    print(f"[ETF] Generating synthetic ETF flow data...")

    # Get unique dates from market data
    cur.execute(
        "SELECT DATE(timestamp) as date FROM market_data GROUP BY DATE(timestamp) ORDER BY date"
    )
    dates = [row[0] for row in cur.fetchall()]

    if not dates:
        print("[ETF] No market data found, skipping")
        return

    # Generate synthetic but realistic flows (-500M to +500M)
    np.random.seed(42)
    flows = np.cumsum(np.random.normal(0, 50, len(dates))) * 1_000_000

    inserted = 0
    for date, flow in zip(dates, flows):
        try:
            cur.execute(
                "INSERT OR IGNORE INTO etf_flows (date, net_inflow, created_at) "
                "VALUES (?, ?, ?)",
                (date, float(flow), datetime.now().isoformat()),
            )
            inserted += 1
        except Exception:
            pass

    conn.commit()
    print(f"[ETF] Inserted {inserted} ETF flow records")


def _validate_data(conn):
    """Validate minimum data requirements."""
    cur = conn.cursor()

    print("\n[VALIDATION] Checking data completeness...")

    stats = {}
    for table in ["market_data", "premium_data", "funding_data", "etf_flows", "signals", "signal_performance"]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]

            if count > 0:
                if table == "etf_flows":
                    cur.execute(
                        f"SELECT MIN(date) as earliest, MAX(date) as latest FROM {table} "
                        f"WHERE date IS NOT NULL LIMIT 1"
                    )
                else:
                    cur.execute(
                        f"SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest FROM {table} "
                        f"WHERE timestamp IS NOT NULL LIMIT 1"
                    )
                result = cur.fetchone()
                earliest = result[0] if result and result[0] else "N/A"
                latest = result[1] if result and result[1] else "N/A"
            else:
                earliest, latest = "N/A", "N/A"

            stats[table] = {
                "count": count,
                "earliest": earliest,
                "latest": latest,
            }
        except Exception as e:
            stats[table] = {"error": str(e)}

    # Check market_data specifically for 2880 bars requirement
    cur.execute("SELECT COUNT(*) FROM market_data WHERE symbol = ?", (SYMBOL,))
    market_count = cur.fetchone()[0]

    if market_count < 2880:
        print(f"WARNING: Only {market_count} bars (need 2880 for 48h horizon)")
    else:
        print(f"OK: {market_count} bars available (sufficient for 48h+ research)")

    return stats


def _print_stats(stats):
    """Pretty print table statistics."""
    print("\n" + "="*70)
    print("DATASET STATISTICS")
    print("="*70)

    for table, data in stats.items():
        if "error" in data:
            print(f"\n{table:.<20} ERROR: {data['error']}")
        else:
            count = data["count"]
            earliest = data["earliest"]
            latest = data["latest"]
            print(f"\n{table:.<20}")
            print(f"  Rows:      {count:>10,}")
            print(f"  Earliest:  {str(earliest):>20}")
            print(f"  Latest:    {str(latest):>20}")


def main():
    print("="*70)
    print("REBUILD RESEARCH DATASET")
    print("="*70)

    # Step 1: Initialize DB
    _ensure_db()

    # Step 2: Ingest data
    conn = sqlite3.connect(str(DB_PATH))
    _ingest_market_data_30d(conn)
    _ingest_funding_data(conn)
    _ingest_premium_data(conn)
    _ingest_etf_flows(conn)

    # Step 3: Validate
    stats = _validate_data(conn)
    conn.close()

    # Step 4: Report
    _print_stats(stats)

    print("\n" + "="*70)
    print("REBUILD COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  python research/factor_ic.py --db-path database/messages.db")
    print("  python research/factor_decay.py --db-path database/messages.db")
    print("  python research/walk_forward.py --db-path database/messages.db --folds 5")
    print("  python research/report_generator.py --db-path database/messages.db")
    print("  python research/backtest_pf.py --db-path database/messages.db --threshold 2 --fee-bps 4")


if __name__ == "__main__":
    main()

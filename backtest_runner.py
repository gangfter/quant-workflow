import sqlite3
from datetime import datetime

from engine.market_regime import get_market_regime
from engine.signal_engine import generate_signal
from engine.risk_engine import evaluate_risk
from engine.analytics.performance import update_performance_metrics

DB = "database/messages.db"
SYMBOL = "BTCUSDT"


def _fetch_market_data(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT timestamp, close_price, volume
        FROM market_data
        WHERE symbol = ?
        ORDER BY timestamp ASC
        """,
        (SYMBOL,),
    )
    return cur.fetchall()


def run_backtest():
    conn = sqlite3.connect(DB)
    rows = _fetch_market_data(conn)
    cur = conn.cursor()

    # Disable runtime freshness gates inside factor scripts / signal engine.
    import os
    os.environ["BACKTEST_MODE"] = "1"

    print(f"[BACKTEST] start | candles={len(rows)} | symbol={SYMBOL}")

    # iterate candles (sample mode)
    SAMPLE_N = 10
    for i, (ts, close_price, volume) in enumerate(rows, start=1):
        if i > SAMPLE_N:
            break
        # features: run factors/regime.py, m_factor.py, v_factor.py to compute R_t/M_t/V_t
        # Run in-process so we can parse outputs.
        if i == 1 or i == len(rows) or i % 100 == 0:
            print(f"[BACKTEST] progress {i}/{len(rows)}")

        # fast factor evaluation via importable APIs (no subprocess)
        from factors.regime_api import get_r_factor
        from factors.m_factor_api import get_m_factor
        from factors.v_factor_api import get_v_factor

        r_t = get_r_factor()
        m_t = get_m_factor()
        v_t = get_v_factor(ts)
        score = r_t + m_t + v_t

        # sample log
        print("[SAMPLE]", ts, close_price, "R_t=", r_t, "M_t=", m_t, "V_t=", v_t, "score=", score)

        regime_data = get_market_regime(symbol=SYMBOL, window=48)
        regime = regime_data.get("regime")

        features = {"symbol": SYMBOL, "score": score, "regime": regime}

        signal = generate_signal(features)

        portfolio = {
            "equity": 10000.0,
            "exposure": 0.0,
            "daily_pnl": 0.0,
            "atr": max(1e-9, abs(close_price - close_price)),
        }
        params = {
            "daily_loss_limit": 0.03,
            "risk_per_trade": 0.01,
            "atr_multiplier": 1.5,
            "max_exposure": 0.3,
        }

        risk = evaluate_risk(signal, portfolio, params)
        approved = bool(risk.get("approved"))
        position_size = risk.get("position_size")

        # mock execution: insert placeholder realized_pnl=0 when approved
        if approved:
            cur.execute(
                """
                INSERT INTO trades_log (
                    symbol, regime, action, entry_price, exit_price,
                    position_size, realized_pnl, confidence, exit_reason,
                    hold_minutes, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    SYMBOL,
                    features.get("regime"),
                    signal.get("action"),
                    float(close_price),
                    float(close_price),
                    float(position_size) if position_size is not None else None,
                    0.0,
                    float(signal.get("confidence", 0.0)),
                    "MOCK",
                    0,
                    ts,
                ),
            )

    conn.commit()
    conn.close()

    metrics = update_performance_metrics()
    print("[BACKTEST_PERF]", metrics)
    print("[BACKTEST] end")


if __name__ == "__main__":
    run_backtest()

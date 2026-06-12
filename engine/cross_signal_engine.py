import sqlite3
from datetime import datetime

DB = "database/messages.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()


# =========================
# 1. 최신 가격 로드
# =========================
cur.execute("""
SELECT symbol, close
FROM market_data_multi
ORDER BY timestamp DESC
""")

rows = cur.fetchall()

prices = {}
for symbol, price in rows:
    if symbol not in prices:
        prices[symbol] = price


btc = prices.get("BTCUSDT", 0)
eth = prices.get("ETHUSDT", 0)
sol = prices.get("SOLUSDT", 0)


# =========================
# 2. RETURN 기반 계산 (핵심 수정)
# =========================
btc_ret = 0
eth_ret = (eth - btc) / btc if btc != 0 else 0
sol_ret = (sol - btc) / btc if btc != 0 else 0


# =========================
# 3. SIGNAL SCORE
# =========================
score = 0

# ETH momentum
if eth_ret > 0:
    score += 1
else:
    score -= 1

# SOL momentum
if sol_ret > 0:
    score += 1
else:
    score -= 1

# rotation signal
if sol_ret > eth_ret:
    score += 1
else:
    score -= 1


# =========================
# 4. FINAL SIGNAL
# =========================
if score >= 2:
    signal = "LONG"
elif score <= -2:
    signal = "SHORT"
else:
    signal = "FLAT"


print("BTC:", btc)
print("ETH:", eth)
print("SOL:", sol)
print("Score:", score)
print("Signal:", signal)


# =========================
# 5. SAVE
# =========================
cur.execute("""
INSERT INTO signals (
    timestamp,
    r_t,
    m_t,
    v_t,
    score,
    signal
)
VALUES (?, ?, ?, ?, ?, ?)
""", (
    datetime.now().isoformat(),
    0,
    0,
    0,
    score,
    signal
))

conn.commit()
conn.close()

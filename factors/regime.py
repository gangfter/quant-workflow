import sqlite3
import pandas as pd

conn = sqlite3.connect("database/messages.db")

df = pd.read_sql_query("""
SELECT date, net_inflow
FROM etf_flows
ORDER BY date
""", conn)

conn.close()

if len(df) < 2:
    print("R_t = 0")
    exit()

mean = df["net_inflow"].mean()
std = df["net_inflow"].std()

if std == 0:
    print("ETF std = 0")
    print("R_t = 0")
    exit()

latest = df["net_inflow"].iloc[-1]

z_score = (latest - mean) / std

if z_score > 1.5:
    r_t = 1
elif z_score < -1.5:
    r_t = -1
else:
    r_t = 0

print(f"ETF Z-Score = {z_score:.2f}")
print(f"R_t = {r_t}")

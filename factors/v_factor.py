import sqlite3
import pandas as pd

conn = sqlite3.connect("database/messages.db")

df = pd.read_sql_query("""
SELECT premium
FROM premium_data
ORDER BY id
""", conn)

conn.close()

if len(df) < 2:
    print("V_t = 0")
    exit()

mean = df["premium"].mean()
std = df["premium"].std()

if std == 0:
    print("V_t = 0")
    exit()

latest = df["premium"].iloc[-1]

z_score = (latest - mean) / std

if z_score > 0.5:
    v_t = 1
elif z_score < -0.5:
    v_t = -1
else:
    v_t = 0

print(f"Premium Z-Score = {z_score:.2f}")
print(f"V_t = {v_t}")
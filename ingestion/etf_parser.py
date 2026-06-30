import re

sample = """
BlackRock Bitcoin ETF Net Inflow +$120M
"""

pattern = r'([+-]?\$?[\d\.]+)\s*([MB]?)'

match = re.search(pattern, sample)

if match:
    value = float(match.group(1).replace('$', ''))

    suffix = match.group(2)

    if suffix == 'M':
        value *= 1_000_000
    elif suffix == 'B':
        value *= 1_000_000_000

    print(value)

import sqlite3
from datetime import datetime

conn = sqlite3.connect("database/messages.db")
cur = conn.cursor()

cur.execute("""
INSERT INTO etf_flows (
    date,
    net_inflow,
    created_at
)
VALUES (?, ?, ?)
""", (
    datetime.now().strftime("%Y-%m-%d"),
    value,
    datetime.now().isoformat()
))

conn.commit()
conn.close()

print("saved to etf_flows")
import sqlite3
import hashlib
from datetime import datetime, UTC

IMPORTANT_KEYWORDS = [
    "BTC",
    "ETF",
    "CPI",
    "FOMC"
]

DB = "workflow.db"

# 테스트용 가짜 뉴스
text = "BTC ETF inflow increased today"

important = any(
    kw.lower() in text.lower()
    for kw in IMPORTANT_KEYWORDS
)

h = hashlib.sha256(
    text[:500].encode()
).hexdigest()

conn = sqlite3.connect("messages.db")

cur = conn.cursor()

cur.execute(
    "SELECT hash FROM news_cache WHERE hash=?",
    (h,)
)

exists = cur.fetchone()

duplicate = exists is not None

print("important:", important)
print("duplicate:", duplicate)

if important and not duplicate:

    cur.execute("""
    INSERT INTO news_cache (
        hash,
        raw_text,
        created_at
    )
    VALUES (?, ?, ?)
    """, (
        h,
        text,
        datetime.now(UTC).isoformat()
    ))

    conn.commit()

    print("saved to db")

else:
    print("skipped")

conn.close()

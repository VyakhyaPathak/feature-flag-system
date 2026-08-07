"""
Day 16 - Daily flush job.

Aggregates the hourly evaluation counters sitting in Redis into the
`evaluation_analytics` table in Postgres, then clears those Redis keys.
Run this once a day (e.g. via cron on Linux/Mac, or Windows Task
Scheduler) - the design intentionally keeps every evaluation off
Postgres's write path and only touches the database once per flag per
hour, in this batch job:

    python flush_analytics.py

Example cron entry (runs at 01:00 daily):
    0 1 * * *  cd /path/to/backend && venv/bin/python flush_analytics.py
"""
from app.database import SessionLocal
from app.analytics import flush_counters_to_db

db = SessionLocal()
try:
    flushed = flush_counters_to_db(db)
    print(f"Flushed {flushed} flag-hour bucket(s) into evaluation_analytics.")
finally:
    db.close()
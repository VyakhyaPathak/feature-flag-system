"""
Test helper - seeds synthetic evaluation history into evaluation_analytics
so you can see the Day 16 chart, Avg/Day, Max/Hour, and the vs-previous-
period percentage badge working with realistic multi-day data, without
waiting for actual usage to accumulate over real days.

This inserts backdated rows directly into the table - it does NOT touch
Redis and does NOT go through record_evaluation()/flush_counters_to_db(),
since those are keyed off datetime.now() and can't produce historical
data. Safe to run multiple times: it clears any previous seed data for
the same flag_key first, so re-running just regenerates fresh numbers.

Usage:
    python seed_analytics_test_data.py <flag_key> [days]

Example:
    python seed_analytics_test_data.py dark_mode 30
"""
import sys
import random
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app import models

if len(sys.argv) < 2:
    print("Usage: python seed_analytics_test_data.py <flag_key> [days]")
    sys.exit(1)

flag_key = sys.argv[1]
days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

db = SessionLocal()

# Wipe any previously seeded data for this flag so re-running gives a
# clean, predictable result instead of stacking on top of old test runs.
deleted = (
    db.query(models.EvaluationAnalytics)
    .filter(models.EvaluationAnalytics.flag_key == flag_key)
    .delete(synchronize_session=False)
)
db.commit()
if deleted:
    print(f"Cleared {deleted} existing row(s) for '{flag_key}' before reseeding.")

now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
rows_created = 0

# Generate `days` of history, with a handful of active hours per day and
# a gentle upward trend so the most recent days look busier than the
# oldest ones (realistic "adoption is growing" shape, and a meaningful
# non-zero vs-previous-period percentage).
for day_offset in range(days, 0, -1):
    day_start = now - timedelta(days=day_offset)
    trend_factor = 1 + (days - day_offset) / days  # ~1.0 -> ~2.0 across the range
    active_hours = random.sample(range(24), k=random.randint(3, 8))
    for hour in active_hours:
        hour_bucket = day_start.replace(hour=hour)
        count = max(1, int(random.randint(20, 200) * trend_factor))
        db.add(models.EvaluationAnalytics(
            flag_key=flag_key,
            hour_bucket=hour_bucket,
            count=count,
        ))
        rows_created += 1

db.commit()
db.close()

print(f"Seeded {rows_created} hourly row(s) of synthetic evaluation history for '{flag_key}' across {days} days.")
print("Refresh the flag's Evaluation Count chart to see it.")
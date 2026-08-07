"""
Day 17 - Nightly cleanup detection job.

Scans every flag, finds the ones that are fully rolled out (100% +
enabled) or fully disabled in every environment they're configured in,
and stores/updates them in `cleanup_candidates` for the dashboard's
Cleanup Suggestions panel. Safe to run as often as you like - it's the
same scan the dashboard triggers live on GET /cleanup/candidates, this
script just lets it run unattended on a schedule:

    python run_cleanup_scan.py

Example cron entry (runs at 01:00 daily, matching the "Runs Daily" flow):
    0 1 * * *  cd /path/to/backend && venv/bin/python run_cleanup_scan.py
"""
from app.database import SessionLocal
from app.cleanup import scan_and_store

db = SessionLocal()
try:
    count = scan_and_store(db)
    print(f"Cleanup scan complete: {count} candidate(s) currently fully rolled out or fully disabled.")
finally:
    db.close()

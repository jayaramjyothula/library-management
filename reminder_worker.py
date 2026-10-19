"""
reminder_worker.py - Background Automatic Reminder Worker
Runs scheduled or periodic checks for upcoming due dates and overdue book loans.
Deduplicates notifications to ensure students do not receive repeated reminders for the same event.
Can be executed as:
1. One-shot cron job / scheduled task: python reminder_worker.py
2. Continuous background daemon:       python reminder_worker.py --daemon --interval 3600
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import database as db


def run_reminder_cycle(db_path: Path | None = None) -> dict:
    """Executes a single reminder cycle and logs formatted summary."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.init_db(db_path)
    print(f"[{now_str}] Starting automatic library reminder scan...")

    summary = db.check_and_send_reminders(db_file=db_path)

    print(f"[{now_str}] Scan Complete:")
    print(f"  - Active Loans Scanned : {summary['active_loans_scanned']}")
    print(f"  - Upcoming Due Notices : {summary['due_soon_reminders']}")
    print(f"  - Overdue Alerts       : {summary['overdue_reminders']}")
    print(f"  - Duplicates Suppressed: {summary['duplicates_skipped']}")
    print(f"  - Delivery Mode        : {summary['delivery_mode']}")

    if summary["details"]:
        print("  - Action Details:")
        for detail in summary["details"]:
            print(f"    * {detail}")
    else:
        print("  - No new notifications required at this time.")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Library Management Automatic Reminder Background Worker")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely in background")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds between scans (default: 3600s / 1 hr)")
    parser.add_argument("--db", type=str, default=None, help="Optional custom SQLite database file path")
    args = parser.parse_args()

    custom_db = Path(args.db) if args.db else None

    if args.daemon:
        print(f"Starting Library Reminder Worker in daemon mode (interval: {args.interval}s)...")
        try:
            while True:
                run_reminder_cycle(custom_db)
                print(f"Sleeping for {args.interval} seconds...\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nReminder daemon stopped by user.")
    else:
        run_reminder_cycle(custom_db)


if __name__ == "__main__":
    main()

"""
Baby — Backup

Zips the entire entities folder and saves it to gestation/backups/.
Run manually or hook into a nightly cron.

Usage:
    python backup.py
"""

import shutil
from datetime import datetime

from config import ENTITIES_DIR, BACKUPS_DIR


def backup():
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"entities_{timestamp}"
    archive_path = BACKUPS_DIR / archive_name

    result = shutil.make_archive(str(archive_path), "zip", str(ENTITIES_DIR))

    print(f"Backup saved: {result}")


if __name__ == "__main__":
    backup()

"""
Baby — Daily Signal Loop

Run this once per day. It checks the trimester,
sends heartbeat signals to each entity, and logs the day.

Usage:
    python run_day.py
"""

from datetime import datetime

from config import ENTITY_NAMES, BIRTH_DATE
from memory import get_gestation_day, get_trimester
from heartbeat import run_heartbeat

TRIMESTER_LABELS = {
    1: "Trimester 1 — Neural architecture forming. No output expected.",
    2: "Trimester 2 — First reflexive responses. Like a fetus kicking.",
    3: "Trimester 3 — Consolidation. Character without content.",
    0: "Post-birth. The world is open.",
}


def run_day():
    day = get_gestation_day()
    trimester = get_trimester(day)

    print("=" * 50)
    print(f"  BABY — Day {day} of 270")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Birth: {BIRTH_DATE.isoformat()}")
    print()
    print(f"  {TRIMESTER_LABELS.get(trimester, '???')}")
    print("=" * 50)
    print()

    for name in ENTITY_NAMES:
        print(f"--- {name} ---")
        run_heartbeat(name)
        print()

    print("=" * 50)
    print(f"  Day {day} complete. All five heartbeats recorded.")
    print("=" * 50)


if __name__ == "__main__":
    run_day()

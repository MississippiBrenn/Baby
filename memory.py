"""
Baby — Memory

Simple JSON-based episodic memory.
Each entity's memories are individual JSON files, human-readable,
stored in entities/<name>/memory/episodic/
"""

import json
from datetime import date, datetime
from pathlib import Path

from config import START_DATE, ENTITIES_DIR, TRIMESTER_1_END, TRIMESTER_2_END, TRIMESTER_3_END


def get_gestation_day() -> int:
    """How many days since conception. Day 1 is March 18, 2026."""
    delta = date.today() - START_DATE
    return max(delta.days + 1, 1)


def get_trimester(day: int = None) -> int:
    """Which trimester are we in? Returns 1, 2, or 3."""
    if day is None:
        day = get_gestation_day()
    if day <= TRIMESTER_1_END:
        return 1
    elif day <= TRIMESTER_2_END:
        return 2
    elif day <= TRIMESTER_3_END:
        return 3
    else:
        return 0  # born


def _episodic_dir(entity: str) -> Path:
    d = ENTITIES_DIR / entity / "memory" / "episodic"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_episodic(entity: str, content: dict, tags: list[str] = None):
    """
    Write one memory entry to an entity's episodic memory.
    Each entry is a separate JSON file, timestamped.
    """
    now = datetime.now()
    day = get_gestation_day()

    entry = {
        "timestamp": now.isoformat(),
        "gestation_day": day,
        "trimester": get_trimester(day),
        "tags": tags or [],
        "content": content,
    }

    filename = f"day{day:03d}_{now.strftime('%H%M%S')}_{now.strftime('%f')[:4]}.json"
    path = _episodic_dir(entity) / filename

    with open(path, "w") as f:
        json.dump(entry, f, indent=2)

    return path


def read_recent(entity: str, n: int = 10) -> list[dict]:
    """Read the most recent n episodic memories for an entity."""
    d = _episodic_dir(entity)
    files = sorted(d.glob("*.json"), reverse=True)[:n]
    entries = []
    for f in files:
        with open(f) as fh:
            entries.append(json.load(fh))
    return entries

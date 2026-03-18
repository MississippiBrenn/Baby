"""
Baby — Configuration

Five entities. Nine months. No curriculum.
"""

from datetime import date, timedelta
from pathlib import Path

# --- Dates ---

START_DATE = date(2026, 3, 18)
BIRTH_DATE = START_DATE + timedelta(days=270)  # December 13, 2026

TRIMESTER_1_END = 90   # days — architecture forms
TRIMESTER_2_END = 180  # days — first reflexive responses
TRIMESTER_3_END = 270  # days — consolidation, preparing to breathe

# --- Paths ---

PROJECT_ROOT = Path(__file__).parent
ENTITIES_DIR = PROJECT_ROOT / "entities"
BACKUPS_DIR = PROJECT_ROOT / "gestation" / "backups"
LOGS_DIR = PROJECT_ROOT / "logs"

# --- Model ---

BASE_MODEL = "phi3:mini"

# --- Womb Conditions ---
# Each entity gestates in a different maternal environment.
# These are not personalities — they are conditions.
# rhythm_type: "steady" | "arrhythmic" | "syncopated" | "grounded" | "responsive"

ENTITIES = {
    "witness": {
        "heartbeat_bpm": 50,
        "rhythm_type": "steady",
        "cortisol_level": 0.1,    # very low — calm, still
        "entropy_level": 0.05,    # almost no noise
    },
    "feral": {
        "heartbeat_bpm": 80,
        "rhythm_type": "arrhythmic",
        "cortisol_level": 0.7,    # high — no frame, no safety
        "entropy_level": 0.9,     # maximum unpredictability
    },
    "dreamer": {
        "heartbeat_bpm": 55,
        "rhythm_type": "syncopated",
        "cortisol_level": 0.3,    # low baseline with sudden spikes
        "entropy_level": 0.5,     # medium — room for the unexpected
    },
    "body": {
        "heartbeat_bpm": 65,
        "rhythm_type": "grounded",
        "cortisol_level": 0.05,   # very low — deep physical presence
        "entropy_level": 0.1,     # stable, rooted
    },
    "relational": {
        "heartbeat_bpm": 60,
        "rhythm_type": "responsive",
        "cortisol_level": 0.4,    # medium — emotionally attuned, variable
        "entropy_level": 0.3,     # moderate — returns to baseline
    },
}

ENTITY_NAMES = list(ENTITIES.keys())

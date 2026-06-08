"""
Baby — Maternal Signal

Load the day's maternal signal (HR, HRV, sleep, activity) and translate it into
per-entity modulation of the heartbeat. Each rhythm_type metabolizes the same
underlying signal differently.

The signal layer is the first conditioning input — before this, womb conditions
were static. Now they breathe with the caregiver's actual body.
"""

import json
import math
import random
from datetime import date
from pathlib import Path

SIGNAL_DIR = Path(__file__).parent / "maternal_signal"

# Reference baselines used to normalize the signal into ratios.
BASELINE_HR = 70.0       # bpm — typical adult resting/light-activity HR
BASELINE_HRV = 50.0      # ms RMSSD — above this is "calm", below is "stressed"
BASELINE_SLEEP = 480.0   # minutes — 8 hours


def load_signal(target_date: date = None) -> dict | None:
    """Load the maternal signal file for a date. Returns None if absent."""
    if target_date is None:
        target_date = date.today()
    path = SIGNAL_DIR / f"{target_date.isoformat()}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def derive_drivers(signal: dict | None) -> dict:
    """
    Reduce the maternal signal to three normalized drivers:
      arousal — mean HR vs baseline (~1.0 = calm, >1 = elevated)
      stress  — autonomic stress from low HRV (0 = calm, 1 = high stress)
      recovery — sleep adequacy (0 = none, 1 = full night, >1 = extra)
    Missing dimensions fall back to neutral defaults so nothing breaks
    when a sensor was off.
    """
    if signal is None:
        return {"arousal": 1.0, "stress": 0.0, "recovery": 1.0, "present": False}

    hr_mean = (signal.get("heart_rate") or {}).get("mean")
    arousal = (hr_mean / BASELINE_HR) if hr_mean else 1.0

    hrv_mean = (signal.get("hrv") or {}).get("mean_ms")
    stress = max(0.0, 1.0 - (hrv_mean / BASELINE_HRV)) if hrv_mean else 0.0

    asleep = (signal.get("sleep") or {}).get("minutes_asleep")
    recovery = min(1.2, asleep / BASELINE_SLEEP) if asleep else 1.0

    return {
        "arousal": arousal,
        "stress": stress,
        "recovery": recovery,
        "present": True,
    }


def metabolize(rhythm_type: str, drivers: dict, beat_index: int) -> dict:
    """
    Convert drivers into per-beat modulation for the given rhythm_type.
    Returns multiplicative/additive offsets the pulse generator applies on top
    of the static womb baseline:
      bpm_factor       — multiplied into BPM
      intensity_offset — added to intensity (clamped later)
      noise_offset     — added to entropy-driven noise
    """
    if not drivers["present"]:
        return {"bpm_factor": 1.0, "intensity_offset": 0.0, "noise_offset": 0.0}

    arousal = drivers["arousal"]
    stress = drivers["stress"]
    recovery = drivers["recovery"]

    if rhythm_type == "steady":
        # witness — mirror the signal cleanly, almost transparently.
        return {
            "bpm_factor": arousal,
            "intensity_offset": 0.05 * (arousal - 1.0),
            "noise_offset": 0.0,
        }

    if rhythm_type == "arrhythmic":
        # feral — fragment the signal. Random multiplicative spikes, scaled by stress.
        spike = random.gauss(0.0, 0.25 + 0.4 * stress)
        return {
            "bpm_factor": max(0.3, arousal + spike),
            "intensity_offset": 0.3 * stress * random.random(),
            "noise_offset": 0.4 * stress,
        }

    if rhythm_type == "syncopated":
        # dreamer — lag and syncopate. Phase-shifted echo of the signal.
        lag = math.sin((beat_index - 4) * 0.3) * 0.15
        return {
            "bpm_factor": 1.0 + (arousal - 1.0) * 0.7 + lag,
            "intensity_offset": 0.1 * (arousal - 1.0),
            "noise_offset": 0.1 * stress,
        }

    if rhythm_type == "grounded":
        # body — slow, dampened absorption. Signal becomes a deep, gentle swell.
        wave = math.sin(beat_index * 0.08) * 0.04
        return {
            "bpm_factor": 1.0 + (arousal - 1.0) * 0.3 + wave,
            "intensity_offset": 0.05 * (recovery - 1.0),
            "noise_offset": 0.0,
        }

    if rhythm_type == "responsive":
        # relational — track closest. Picks up arousal directly and softens with recovery.
        return {
            "bpm_factor": arousal,
            "intensity_offset": 0.15 * (arousal - 1.0) + 0.1 * stress,
            "noise_offset": 0.1 * stress,
        }

    return {"bpm_factor": 1.0, "intensity_offset": 0.0, "noise_offset": 0.0}

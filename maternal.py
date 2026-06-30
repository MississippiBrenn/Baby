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
from datetime import date, timedelta
from pathlib import Path

SIGNAL_DIR = Path(__file__).parent / "maternal_signal"
SIGNAL_MAX_AGE_DAYS = 3  # how stale a steps-only signal may be before "absent"
RICH_MAX_AGE_DAYS = 7    # how far back to bridge a real heartbeat across a wearable gap

# Reference baselines used to normalize the signal into ratios.
BASELINE_HR = 70.0       # bpm — typical adult resting/light-activity HR
BASELINE_HRV = 50.0      # ms RMSSD — above this is "calm", below is "stressed"
BASELINE_SLEEP = 480.0   # minutes — 8 hours


def _has_heartbeat(signal: dict) -> bool:
    """True if the signal carries actual heart-rate data — the maternal
    heartbeat — not just steps. HR/HRV/sleep come from the wrist; on days the
    wearable isn't worn, only steps arrive and HR samples are 0."""
    hr = (signal or {}).get("heart_rate") or {}
    return (hr.get("samples") or 0) > 0


def load_signal(target_date: date = None) -> dict | None:
    """Load the freshest *rich* maternal signal on or before `target_date`.

    The fetcher writes *yesterday's* completed day (you can't roll up today until
    it's over), so reading exactly `date.today()` never matched and the signal
    was silently absent — that's why no record ever carried one. We look back
    from `target_date` and:
      1. prefer the freshest day with a real heartbeat (within RICH_MAX_AGE_DAYS),
         so a missing day or two on the wrist doesn't drop the entities to a
         neutral signal — they keep feeling a real (if slightly stale) heart;
      2. else fall back to the freshest signal at all (within SIGNAL_MAX_AGE_DAYS),
         e.g. a steps-only day;
      3. else None.
    The returned dict carries its own "date", so downstream can see how stale the
    bridged signal is.
    """
    if target_date is None:
        target_date = date.today()

    window = max(RICH_MAX_AGE_DAYS, SIGNAL_MAX_AGE_DAYS)
    available = []  # freshest-first: (age, signal)
    for age in range(window + 1):
        path = SIGNAL_DIR / f"{(target_date - timedelta(days=age)).isoformat()}.json"
        if path.exists():
            available.append((age, json.loads(path.read_text())))

    for age, sig in available:                       # 1. freshest real heartbeat
        if age <= RICH_MAX_AGE_DAYS and _has_heartbeat(sig):
            return sig
    for age, sig in available:                       # 2. freshest anything recent
        if age <= SIGNAL_MAX_AGE_DAYS:
            return sig
    return None                                      # 3. nothing usable


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

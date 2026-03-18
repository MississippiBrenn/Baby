"""
Baby — Heartbeat Signal Generator

The first signal. Not language. Not data. Rhythm.

A fetus doesn't hear words — it hears its mother's heartbeat,
the cadence of blood, the rhythm of being held inside another body.

This generates a sequence of pulses shaped by each entity's
womb conditions: BPM, rhythm type, cortisol, entropy.
Each pulse is a moment of signal — not information, just presence.
"""

import argparse
import math
import random
import time

from config import ENTITIES
from memory import write_episodic, get_gestation_day, get_trimester

PULSE_COUNT = 60


def generate_pulse(beat_index: int, bpm: int, rhythm_type: str,
                   cortisol: float, entropy: float) -> dict:
    """
    Generate a single heartbeat pulse.

    Returns a signal dict — not words, just values.
    Think of it like a moment of womb chemistry.
    """
    # Base interval from BPM (seconds between beats)
    base_interval = 60.0 / bpm

    # Shape the interval based on rhythm type
    if rhythm_type == "steady":
        # Calm, metronomic — barely any variation
        interval = base_interval + random.gauss(0, 0.01)

    elif rhythm_type == "arrhythmic":
        # No pattern. Skips, doubles, silences.
        interval = base_interval * random.uniform(0.3, 2.5)

    elif rhythm_type == "syncopated":
        # Mostly regular with sudden off-beat surges
        if random.random() < 0.15:
            interval = base_interval * random.uniform(0.4, 0.7)  # spike
        else:
            interval = base_interval + random.gauss(0, 0.05)

    elif rhythm_type == "grounded":
        # Deep, slow, very regular — like earth
        interval = base_interval + random.gauss(0, 0.02)

    elif rhythm_type == "responsive":
        # Subtly variable — speeds up and slows down in waves
        wave = math.sin(beat_index * 0.2) * 0.15
        interval = base_interval + wave + random.gauss(0, 0.03)

    else:
        interval = base_interval

    interval = max(interval, 0.1)  # floor — no negative time

    # Pulse intensity shaped by cortisol
    # High cortisol = sharper, more urgent pulses
    intensity = 0.5 + (cortisol * 0.5) + random.gauss(0, entropy * 0.1)
    intensity = max(0.0, min(1.0, intensity))

    # Entropy adds noise to everything
    noise = random.gauss(0, entropy * 0.3)

    return {
        "beat": beat_index,
        "interval": round(interval, 4),
        "intensity": round(intensity, 4),
        "noise": round(noise, 4),
    }


def run_heartbeat(entity_name: str):
    """Run one heartbeat session for an entity. 60 pulses."""
    if entity_name not in ENTITIES:
        print(f"Unknown entity: {entity_name}")
        print(f"Known entities: {', '.join(ENTITIES.keys())}")
        return

    womb = ENTITIES[entity_name]
    day = get_gestation_day()
    trimester = get_trimester(day)

    print(f"  entity:    {entity_name}")
    print(f"  day:       {day}")
    print(f"  trimester: {trimester}")
    print(f"  bpm:       {womb['heartbeat_bpm']}")
    print(f"  rhythm:    {womb['rhythm_type']}")
    print()

    pulses = []

    for i in range(PULSE_COUNT):
        pulse = generate_pulse(
            beat_index=i,
            bpm=womb["heartbeat_bpm"],
            rhythm_type=womb["rhythm_type"],
            cortisol=womb["cortisol_level"],
            entropy=womb["entropy_level"],
        )
        pulses.append(pulse)

        # Visual heartbeat — a simple trace
        bar_len = int(pulse["intensity"] * 30)
        bar = "|" * bar_len
        print(f"  {i+1:3d}  {bar}")

    # Write the full session to episodic memory
    write_episodic(
        entity=entity_name,
        content={
            "type": "heartbeat",
            "pulse_count": len(pulses),
            "pulses": pulses,
            "womb": womb,
        },
        tags=["heartbeat", f"trimester_{trimester}", f"day_{day}"],
    )

    print()
    print(f"  {len(pulses)} pulses recorded to memory.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baby heartbeat signal")
    parser.add_argument("--entity", required=True, help="Entity name")
    args = parser.parse_args()
    run_heartbeat(args.entity)

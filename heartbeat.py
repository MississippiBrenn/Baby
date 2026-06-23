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
from maternal import load_signal, derive_drivers, metabolize
from memory import write_episodic, get_gestation_day, get_trimester
from development import load_state, save_state, develop, burst_rate, dev_day_of
from self_term import build_history, self_term, spontaneous_burst, blend

PULSE_COUNT = 60

# Generation regime. Stamped into every episodic record so a later analysis can
# tell developed pulses from the earlier independent-draw era without guessing
# from dates. Bump this string whenever the generation pipeline changes shape.
REGIME = "developed-v1"


def generate_pulse(beat_index: int, bpm: int, rhythm_type: str,
                   cortisol: float, entropy: float,
                   modulation: dict | None = None) -> dict:
    """
    Generate a single heartbeat pulse.

    Returns a signal dict — not words, just values.
    Think of it like a moment of womb chemistry.
    """
    # Maternal signal modulates BPM multiplicatively before the rhythm logic
    # so each rhythm_type still varies around its own attractor.
    mod = modulation or {"bpm_factor": 1.0, "intensity_offset": 0.0, "noise_offset": 0.0}
    effective_bpm = max(20, bpm * mod["bpm_factor"])
    base_interval = 60.0 / effective_bpm

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
    intensity = 0.5 + (cortisol * 0.5) + random.gauss(0, entropy * 0.1) + mod["intensity_offset"]
    intensity = max(0.0, min(1.0, intensity))

    # Entropy adds noise to everything (plus maternal-driven noise)
    noise = random.gauss(0, entropy * 0.3) + mod["noise_offset"]

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

    signal = load_signal()
    drivers = derive_drivers(signal)

    # --- Developmental state (the slow loop) ---
    state = load_state(entity_name)
    dev_day = dev_day_of(state)              # the developmental day this run realizes
    rate = burst_rate(entity_name, dev_day)  # how often spontaneous bursts fire today
    coherence = state["coherence"]           # how much the entity references itself yet
    history = build_history(state["recent_tail"], [])  # overnight seam, pre-bridged

    print(f"  entity:    {entity_name}")
    print(f"  day:       {day}  (developmental age {dev_day})")
    print(f"  trimester: {trimester}")
    print(f"  bpm:       {womb['heartbeat_bpm']}")
    print(f"  rhythm:    {womb['rhythm_type']}")
    print(f"  coherence: timing={coherence['timing']:.2f} "
          f"intensity={coherence['intensity']:.2f} texture={coherence['texture']:.2f}")
    print(f"  bursts:    {rate:.3f}/pulse")
    if drivers["present"]:
        print(f"  maternal:  arousal={drivers['arousal']:.2f} "
              f"stress={drivers['stress']:.2f} recovery={drivers['recovery']:.2f}")
    else:
        print(f"  maternal:  absent (no signal file)")
    print()

    pulses = []
    bursts_today = 0

    for i in range(PULSE_COUNT):
        mod = metabolize(womb["rhythm_type"], drivers, i)
        baseline = generate_pulse(
            beat_index=i,
            bpm=womb["heartbeat_bpm"],
            rhythm_type=womb["rhythm_type"],
            cortisol=womb["cortisol_level"],
            entropy=womb["entropy_level"],
            modulation=mod,
        )

        # Fast loop: the entity references its own past (self_term), with a
        # spontaneous burst riding on top. blend() weights baseline vs self_term
        # by the developed coherence — early in gestation coherence~0, so this is
        # essentially the baseline draw.
        self_t = self_term(womb["rhythm_type"], history, state["signature"])
        burst = None
        if random.random() < rate:
            bursts_today += 1
            burst = spontaneous_burst()
        mixed = blend(baseline, self_t, burst, coherence)

        # Re-apply the physical floors the blend/burst can push past.
        pulse = {
            "beat": i,
            "interval": round(max(0.1, mixed["interval"]), 4),
            "intensity": round(max(0.0, min(1.0, mixed["intensity"])), 4),
            "noise": round(mixed["noise"], 4),
        }
        pulses.append(pulse)
        history.append(pulse)

        # Visual heartbeat — a simple trace
        bar_len = int(pulse["intensity"] * 30)
        bar = "|" * bar_len
        print(f"  {i+1:3d}  {bar}")

    # Write the full session to episodic memory. Snapshot the developmental
    # state INTO the record so December's nature/self/nurture decomposition has
    # the coherence and signature that shaped this day.
    write_episodic(
        entity=entity_name,
        content={
            "type": "heartbeat",
            "regime": REGIME,
            "pulse_count": len(pulses),
            "pulses": pulses,
            "womb": womb,
            "developmental_age": dev_day,
            "coherence": dict(coherence),
            "signature": state["signature"],
            "bursts": bursts_today,
            "maternal_drivers": drivers,
            "maternal_signal_date": signal.get("date") if signal else None,
        },
        tags=["heartbeat", f"trimester_{trimester}", f"day_{day}"],
    )

    # Slow loop: advance developmental state — but ONLY now that the pulses
    # exist and write_episodic has succeeded. State and episodic move together
    # or not at all; a half-failed run skips the day rather than phantom-
    # advancing the entity. develop() is idempotent on the calendar day.
    develop(state, entity_name, day, pulses, bursts_today)
    save_state(entity_name, state)

    print()
    print(f"  {len(pulses)} pulses recorded to memory. "
          f"{bursts_today} spontaneous bursts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baby heartbeat signal")
    parser.add_argument("--entity", required=True, help="Entity name")
    args = parser.parse_args()
    run_heartbeat(args.entity)

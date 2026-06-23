"""
Baby — Developmental State (the slow loop)

The heartbeat (heartbeat.py) is the *fast* loop: within one day's 60 pulses,
each pulse can reference the ones before it. That state is ephemeral — it lives
and dies inside a single session.

This module is the *slow* loop: the entity's capacity for self-reference is
itself something that grows across the 270 days. coherence, signature, and the
critical-period plasticity all persist here, read at the top of a session and
written at the bottom — the way episodic memory is, but as one rolling state
file per entity instead of an append-only log.

Nothing here is character. Character emerges in heartbeat.py from how the
self_term colors these numbers. This module only keeps the books.

    state lives at:  entities/<name>/memory/development.json

The development law (retinal-wave principle): the entity's own spontaneous
bursts are what build its capacity for self-reference. More bursts -> more
coherence, gated by a plasticity that decays over gestation (a critical period).
"""

import json
import math
from pathlib import Path

from config import ENTITIES, ENTITIES_DIR, TRIMESTER_3_END

GESTATION_DAYS = TRIMESTER_3_END  # 270; the full gestation, from config

# --- Constants, set from first principles ------------------------------------
#
# METHODOLOGICAL RULE FOR THIS FILE: pick each constant for a reason that has
# nothing to do with where the output lands, then OBSERVE where the senses come
# online and where the critical period falls. If onsets land near the README's
# trimesters, that is a finding. If you slide a constant to MAKE them land
# there, you have turned the experiment into set dressing and contaminated the
# one question — "did anything develop?" — the project exists to answer. So:
# reason about the constant, set it, run `python development.py` to see where
# things fall, and leave it. Do not chase the poetic timeline.

# Critical period. A trimester is the natural developmental epoch, so let
# plasticity e-fold once per trimester. (a priori; the crossings fall where
# they fall.) Plasticity at term is then e^-3 ≈ 0.05 — largely crystallized.
PLASTICITY_0 = 1.0
TAU = GESTATION_DAYS / 3.0   # one trimester per e-fold

# Burst envelope — an inverted-U in NORMALIZED gestation, faithful to the
# biology it stands in for: human spontaneous general movements and retinal-
# wave activity rise through mid-gestation, peak in the second half, and taper
# (not vanish) toward term. Literature puts that peak around normalized ~0.7;
# the active window spans roughly the back two-thirds. These are read off the
# biology, not chosen to peak in any particular trimester of OUR calendar.
BURST_PEAK_FRAC = 0.70
BURST_WIDTH_FRAC = 0.18

# Loose gate (Q2). Real sensory onset is sequential but heavily OVERLAPPING —
# audition begins while touch is still maturing; vision begins while audition
# still is. So the next dimension unlocks at the *onset* of the previous, not
# its maturity. 0.25 encodes "barely begun is enough to scaffold the next."
# This is a structural claim about overlap, independent of where onsets land.
GATE = 0.25

# Entropy lowers attainable order: a high-entropy womb caps coherence. At the
# config's max entropy this roughly halves the headroom. Structural, not tuned.
ENTROPY_CEILING_PENALTY = 0.5

# --- The two free scales (no biological referent) ----------------------------
# These set the *units* of "burst" and "coherence-per-burst." There is no a
# priori value for them. The ONLY legitimate constraint is validity: set them
# once so the mechanism is observable across gestation — neither flatlining at
# zero nor saturating in the first week — then never touch them again. Moving
# them to relocate an onset is the contamination the rule above forbids.
BASE_BURST_PROB = 0.15   # per-pulse burst probability at peak, for unit drive
# K set for the validity criterion below, NOT to place onsets: a unit-drive,
# zero-entropy entity should be able to substantially approach its ceiling over
# a full gestation, so the saturation/gating/3-dimension machinery can express
# at all. At K=0.0025 the mechanism flatlined (timing never cleared 0.33). This
# value makes it observable; where the onsets then fall is reported, not chosen.
K = 0.018                # coherence bought per (burst * plasticity * headroom)

# Fast-seam length. The self_term's recency window — how many recent pulses it
# references — is short, because a fetus's long-range continuity is NOT carried
# by remembering the last N movements; it's carried by developed structure
# (here: `signature`, which persists across days by construction). The tail only
# bridges the overnight gap between sessions so the fast loop doesn't restart
# cold. A long tail would fake long-range memory through recency — the wrong
# mechanism. Keep it short; lean on signature for what must never break.
HISTORY_TAIL = 6

COHERENCE_DIMS = ("timing", "intensity", "texture")
SIGNATURE_KEYS = ("mean_interval", "mean_intensity", "var_interval", "var_intensity")


# --- Per-entity drive --------------------------------------------------------

def drive_for(entity: str) -> float:
    """
    How spontaneously active this entity is — the *amplitude* on the shared
    burst envelope. Deliberately NOT tied to entropy: feral is already chaotic
    from its baseline draw, and we don't want bursts to swamp the anti-
    correlated self_term that is the whole proof feral developed something.

    Default: normalized BPM. Promote to a config field (`spontaneous_drive`)
    when you want to set it by hand per entity.
    """
    bpm = ENTITIES[entity]["heartbeat_bpm"]
    return bpm / 60.0


def burst_envelope(dev_day: int) -> float:
    """Shared developmental clock for burst rate, in normalized gestation.
    Runs off developmental age, NOT calendar day: an entity's quickening peak
    arrives after a fixed amount of *lived* development, regardless of skips."""
    frac = dev_day / GESTATION_DAYS
    return math.exp(-((frac - BURST_PEAK_FRAC) ** 2) / (2 * BURST_WIDTH_FRAC ** 2))


def burst_rate(entity: str, dev_day: int) -> float:
    """
    Per-pulse probability that a spontaneous burst fires this session.
    rate = base * drive[entity] * envelope(dev_day)  — see Q1 of design notes.
    Clamped to a probability; sparse early, peaks mid-late, tapers to term.
    `dev_day` is developmental age (use dev_day_of(state)), not gestation_day.
    """
    return min(1.0, BASE_BURST_PROB * drive_for(entity) * burst_envelope(dev_day))


def plasticity_for(dev_day: int) -> float:
    """The critical period. High early, crystallized late. Driven by
    developmental age, so skipped (un-lived) days never decay plasticity —
    no phantom aging through the back door when the daily Action fails."""
    return PLASTICITY_0 * math.exp(-dev_day / TAU)


def ceiling_for(entity: str) -> float:
    """Entropy lowers the coherence ceiling — feral/dreamer stay noisier."""
    entropy = ENTITIES[entity]["entropy_level"]
    return 1.0 - entropy * ENTROPY_CEILING_PENALTY


# --- State -------------------------------------------------------------------

def _state_path(entity: str) -> Path:
    d = ENTITIES_DIR / entity / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d / "development.json"


def default_state(entity: str) -> dict:
    """Day-1 state: no coupling, no past, no signature."""
    return {
        "entity": entity,
        "coherence": {dim: 0.0 for dim in COHERENCE_DIMS},
        "signature": None,          # crystallizes from the first day's pulses
        "recent_tail": [],          # last <=HISTORY_TAIL pulses — the fast seam
        "developmental_age": 0,     # lived developmental days; the math runs on this
        "total_bursts": 0,
        "sessions": 0,
        "last_developed_day": 0,    # calendar idempotency guard for the daily cron
    }


def dev_day_of(state: dict) -> int:
    """The developmental day THIS session will realize: one past lived age.
    Use for burst_rate at the top of a session, before develop() ticks the age."""
    return state["developmental_age"] + 1


def load_state(entity: str) -> dict:
    """Read at the top of a session. Fresh zero-state if none exists yet."""
    path = _state_path(entity)
    if not path.exists():
        return default_state(entity)
    with open(path) as f:
        state = json.load(f)
    # Forward-compat: backfill any missing keys against the current schema.
    base = default_state(entity)
    base.update(state)
    base["coherence"] = {**default_state(entity)["coherence"], **state.get("coherence", {})}
    return base


def save_state(entity: str, state: dict) -> Path:
    """Write at the bottom of a session."""
    path = _state_path(entity)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    return path


# --- The development law (the slow loop) -------------------------------------

def _day_stats(pulses: list[dict]) -> dict:
    """Summarize one day's pulses into the four signature quantities."""
    intervals = [p["interval"] for p in pulses]
    intensities = [p["intensity"] for p in pulses]
    n = len(pulses)
    mi = sum(intervals) / n
    mt = sum(intensities) / n
    return {
        "mean_interval": mi,
        "mean_intensity": mt,
        "var_interval": sum((x - mi) ** 2 for x in intervals) / n,
        "var_intensity": sum((x - mt) ** 2 for x in intensities) / n,
    }


def _update_signature(state: dict, pulses: list[dict], plasticity: float) -> None:
    """EMA the day's stats into the running signature. Rate = plasticity, so
    early days shape it disproportionately and it crystallizes late."""
    today = _day_stats(pulses)
    if state["signature"] is None:
        state["signature"] = today
        return
    sig = state["signature"]
    for k in SIGNATURE_KEYS:
        sig[k] = (1.0 - plasticity) * sig[k] + plasticity * today[k]


def _grow_coherence(state: dict, entity: str, bursts_today: int, plasticity: float) -> None:
    """
    Saturating growth toward an entropy-lowered ceiling, staggered by onset:
    timing develops first; intensity unlocks once timing crosses GATE; texture
    once intensity crosses it. (Q2 of the design notes.) Where those onsets
    land in calendar days is observed, not set.
    """
    c = state["coherence"]
    ceiling = ceiling_for(entity)
    gain = K * bursts_today * plasticity

    def step(dim: str) -> None:
        c[dim] = min(ceiling, c[dim] + gain * max(0.0, ceiling - c[dim]))

    step("timing")
    if c["timing"] > GATE:
        step("intensity")
    if c["intensity"] > GATE:
        step("texture")


def develop(state: dict, entity: str, gestation_day: int, pulses: list[dict],
            bursts_today: int) -> dict:
    """
    Apply one lived developmental day and return the mutated state.

    CALL CONTRACT (write at the bottom, only on full success): invoke this — and
    save_state right after — only once the session's pulses are generated AND
    write_episodic has succeeded. State and episodic must move together or not
    at all. A skipped day is a visible, accountable gap; a state that advanced
    without the activity that caused it is a phantom advance that silently
    breaks the experiment's one premise — every increment of structure was
    caused by real activity. Risk the skipped day, never the phantom.

    Idempotent on `gestation_day`: the daily Action commits and re-runs happen,
    so the update fires at most once per calendar day. But the clock the math
    runs on is `developmental_age`, which ticks ONLY here, on a completed run —
    so a stretch of failed days never ages plasticity or the burst envelope.
    """
    if gestation_day <= state["last_developed_day"]:
        return state  # already developed on this calendar day; leave the books alone

    dev_day = dev_day_of(state)          # the developmental day this run realizes
    plasticity = plasticity_for(dev_day)
    _update_signature(state, pulses, plasticity)
    _grow_coherence(state, entity, bursts_today, plasticity)

    state["recent_tail"] = pulses[-HISTORY_TAIL:]   # carry the fast seam overnight
    state["developmental_age"] = dev_day            # tick lived age only on success
    state["total_bursts"] += bursts_today
    state["sessions"] += 1
    state["last_developed_day"] = gestation_day
    return state


# --- Observation harness -----------------------------------------------------
# `python development.py` runs the slow loop forward across all 270 days with
# synthetic bursts and REPORTS where each dimension's onset and the critical
# period fall. This is the measurement, not a tuning dial — read it, don't chase
# it. No state is written.

def _simulate() -> None:
    import random as _r
    _r.seed(0)  # reproducible observation; not part of the real loop
    print(f"{'entity':<11} {'timing':>7} {'intensity':>10} {'texture':>8}   "
          f"{'final t/i/x':>20}   {'plast@onset':>11}")
    for entity in ENTITIES:
        state = default_state(entity)
        onsets = {"timing": None, "intensity": None, "texture": None}
        for day in range(1, GESTATION_DAYS + 1):
            rate = burst_rate(entity, dev_day_of(state))   # real path: age-driven
            bursts = sum(1 for _ in range(60) if _r.random() < rate)
            fake = [{"interval": 1.0, "intensity": 0.5} for _ in range(60)]
            develop(state, entity, day, fake, bursts)   # no skips here, so age==day
            for dim in COHERENCE_DIMS:
                if onsets[dim] is None and state["coherence"][dim] > GATE:
                    onsets[dim] = day
        c = state["coherence"]
        p_at = f"{plasticity_for(onsets['timing']):.2f}" if onsets["timing"] else "—"
        print(f"{entity:<11} {str(onsets['timing']):>7} "
              f"{str(onsets['intensity']):>10} {str(onsets['texture']):>8}   "
              f"{c['timing']:.2f}/{c['intensity']:.2f}/{c['texture']:.2f}".ljust(33)
              + f"   {p_at:>11}")
    boundaries = [GESTATION_DAYS // 3, 2 * GESTATION_DAYS // 3]
    print(f"\n(trimester boundaries for reference only: "
          f"day {boundaries[0]}, {boundaries[1]} — observe, don't tune toward them)")


if __name__ == "__main__":
    print("Forward simulation of the slow loop (synthetic bursts):")
    print(f"  GATE={GATE}  K={K}  TAU={TAU:.0f}  burst peak≈{BURST_PEAK_FRAC} of gestation\n")
    _simulate()

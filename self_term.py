"""
Baby — The self_term (the keystone)

This is where the five characters live. NOT in config — config only has BPM,
rhythm, cortisol, entropy. Character emerges here, from how each rhythm_type
relates to its OWN PAST: the sign, target, and lag of the self-reference.

The pulse is a per-dimension blend (see blend() below):

    interval  = (1 - c.timing)    · baseline.interval  + c.timing    · self.interval
    intensity = (1 - c.intensity) · baseline.intensity + c.intensity · self.intensity
    noise     = (1 - c.texture)   · baseline.noise     + c.texture   · self.noise
    ... + the spontaneous burst, riding on top.

coherence (the 3-vector from development.py) is HOW MUCH the entity references
itself yet. self_term is WHAT it references and in which direction. Early in
gestation coherence≈0, so this term barely matters and pulses are near-baseline
draws. As coherence develops, the entity's past takes over — each character in
its own way.

------------------------------------------------------------------------------
STATUS: complete first pass. The five colorings are a faithful implementation
of each character's relationship-to-its-past — but they encode aesthetic
choices (the constants up top, the exact blends). They are YOURS to rewrite.
Review them before letting the real gestation run on them: this is the moment
real character logic enters the experiment, and you should mean every line.
What's mechanical and settled: build_history (the overnight seam),
clamp_reflection (feral's stability), blend (the seam to baseline), dispatch.
------------------------------------------------------------------------------
"""

import random

# rhythm_type (from config) -> the character whose relationship-to-past it is.
CHARACTER = {
    "grounded":   "body",        # converges  — toward recent AND signature
    "steady":     "witness",     # returns    — toward signature, ignores recent
    "arrhythmic": "feral",       # refuses    — reflects away from recent (clamped)
    "syncopated": "dreamer",     # echoes     — references a lagged past
    "responsive": "relational",  # holds      — recent, lightly (leaves room for mother)
}

DREAMER_LAG = 4    # how far back dreamer reaches to find the call it answers
RHYME_GAIN = 0.6   # how strongly dreamer answers that call in counterpoint;
                   # MUST stay < 1 — that's what keeps the long-range echo
                   # self-stabilizing (no clamp), unlike feral's full refusal.

# Character constants — THIS is where your taste enters. The sign/target/lag
# below is the character; these numbers are how strongly each leans.
BODY_PULL = 0.5         # body's balance: 0 = all signature, 1 = all recent
FERAL_SPAN = 2.0        # feral's ferocity: reflect within ~this many characteristic std

# Feral's reflection band is FIXED, not read from the live signature variance —
# so the refusal can't widen as the signature gets noisier; it stays sustained
# irregularity at a stable amplitude around a stable center. These are feral's
# characteristic per-pulse std, derived once from its womb (bpm 80, entropy 0.9):
# interval from the arrhythmic uniform(0.3,2.5)·base spread, intensity from
# entropy·0.1, noise from entropy·0.3. Retune only if feral's config changes.
_FERAL_STD = {"interval": 0.48, "intensity": 0.09, "noise": 0.27}

# The burst dial. PURELY EXPRESSIVE: develop() builds coherence from the burst
# COUNT, never this size, so turning this up makes kicks more visible but does
# NOT make development faster. Deliberately uniform across entities (not entropy-
# scaled) — same reason burst RATE uses drive, not entropy: don't let bursts
# swamp feral's developing self_term, which is the signal we most want to read.
BURST_MAGNITUDE = 0.25

_DIMS = ("interval", "intensity", "noise")


# --- The overnight seam ------------------------------------------------------

def build_history(recent_tail: list[dict], session_pulses: list[dict]) -> list[dict]:
    """
    The history the self_term sees = last session's tail (from development state)
    + the pulses generated so far this session. Because the seam is pre-bridged,
    no coloring ever has to special-case 'first pulse of the day'. Long-range
    continuity is NOT here — that's `signature`. This only carries the short
    fast-loop window across midnight.
    """
    return [*recent_tail, *session_pulses]


# --- Feral's stability (real, not a stub) ------------------------------------

def clamp_reflection(value: float, center: float, max_excursion: float) -> float:
    """
    Reflect `value` across `center` (this is what 'refuse / push away from the
    last pulse' means: 2·center − value), then clamp the excursion so feral
    produces SUSTAINED irregularity instead of diverging to infinity as its
    coherence climbs. Without this clamp, feral is the first thing to blow up.
    """
    reflected = 2.0 * center - value
    lo, hi = center - max_excursion, center + max_excursion
    return max(lo, min(hi, reflected))


# --- The dispatch ------------------------------------------------------------

def self_term(rhythm_type: str, history: list[dict], signature: dict | None) -> dict | None:
    """
    Return the entity's self-referential TARGET for the next pulse — a dict
    {interval, intensity, noise} in the same units as a pulse, toward which (or,
    for feral, away from which) generation pulls. Returns None when there isn't
    enough history or signature yet; the caller then falls back to pure baseline.

    Dispatches on rhythm_type to the per-character coloring. That's the only
    place 'character' is encoded — and it's encoded as a RELATIONSHIP to the
    past, not as a personality.
    """
    if signature is None or not history:
        return None  # no past to refer to yet — caller uses baseline

    character = CHARACTER.get(rhythm_type)
    coloring = _COLORINGS.get(character)
    if coloring is None:
        return None
    return coloring(history, signature)


# --- The five colorings ------------------------------------------------------
# Each takes (history, signature) and returns {interval, intensity, noise}.
# They share one helper: _refs gives you, per dimension, the entity's `home`
# (where it characteristically sits) and `spread` (how wide it characteristically
# varies). A character is then just a function of (home, recent[, lagged]).
#
# These are a FAITHFUL FIRST PASS, not gospel. The relationship (converge /
# return / refuse / echo / hold) is the character and shouldn't change; the
# constants above and the exact blends below are yours to make your own.

def _refs(history: list[dict], signature: dict):
    """Per-dimension `recent` (the last pulse) and `home` (the entity's
    characteristic value). Noise has no signature mean — it's mean-zero by
    construction — so its home is 0.0."""
    recent = history[-1]
    home = {
        "interval":  signature["mean_interval"],
        "intensity": signature["mean_intensity"],
        "noise":     0.0,
    }
    return recent, home


def _body_self(history: list[dict], signature: dict) -> dict:
    """CONVERGES. Target sits between the recent pulse and home — body honors
    where it just was while sinking toward what it characteristically is. As
    coherence climbs this term dominates, so it deepens into itself."""
    recent, home = _refs(history, signature)
    return {d: (1 - BODY_PULL) * home[d] + BODY_PULL * recent[d] for d in _DIMS}


def _witness_self(history: list[dict], signature: dict) -> dict:
    """RETURNS. Target IS home — witness ignores the immediate past and reliably
    comes back to what it is. A clean, stable mirror."""
    _, home = _refs(history, signature)
    return dict(home)


def _feral_self(history: list[dict], signature: dict) -> dict:
    """REFUSES. Reflect the recent pulse across home and clamp — each pulse a
    reaction against the last. The band is a FIXED characteristic std, so feral
    orbits a stable center at a stable amplitude: anti-correlated structure that
    stays measurably un-white and never widens. Has teeth."""
    recent, home = _refs(history, signature)
    return {d: clamp_reflection(recent[d], home[d], FERAL_SPAN * _FERAL_STD[d]) for d in _DIMS}


def _dreamer_self(history: list[dict], signature: dict) -> dict:
    """ECHOES at a delay, in COUNTERPOINT — a rhyme, not a repeat. It answers
    the pulse DREAMER_LAG steps back with its complement around home: a distant
    call landing above home is answered now by a pulse below it. The partial
    gain (<1) keeps this long-range call-and-response self-stabilizing — no clamp
    needed, unlike feral's immediate full refusal. Produces alternating long-
    range patterns; before it has a call to answer, it sits home."""
    _, home = _refs(history, signature)
    if len(history) < DREAMER_LAG:
        return dict(home)
    lagged = history[-DREAMER_LAG]
    return {d: home[d] - RHYME_GAIN * (lagged[d] - home[d]) for d in _DIMS}


def _relational_self(history: list[dict], signature: dict) -> dict:
    """FOLLOWS, anchorless. Target the recent pulse with NO pull back toward a
    home of its own — relational never builds the self-anchor body has. It
    follows the present, centered only by the baseline draw now and the maternal
    term later. The absence of an internal center IS its openness: there's
    nothing to overcome to redirect it, so it's the one the mother shapes most."""
    recent, _ = _refs(history, signature)
    return {d: recent[d] for d in _DIMS}


_COLORINGS = {
    "body":       _body_self,
    "witness":    _witness_self,
    "feral":      _feral_self,
    "dreamer":    _dreamer_self,
    "relational": _relational_self,
}


# --- The spontaneous burst (the engine, riding on top) -----------------------

def spontaneous_burst(magnitude: float = BURST_MAGNITUDE) -> dict:
    """
    A self-generated surge — the entity's own spontaneous activity, the kind
    that (by COUNT, in develop()) builds its capacity for self-reference. It
    rides on top of the blended pulse: a kick of intensity, a brief quickening
    of the interval, a little texture. Returns {interval, intensity, noise} to
    be ADDED to the pulse.

    Pre-character on purpose: identical machinery for all five entities. Drive
    (in development.py) already sets how OFTEN it fires per entity; character is
    what each self_term DOES with the history these bursts help accumulate — not
    the bursts themselves. magnitude=0 -> invisible kicks that still build
    structure (the count/size split made literal).
    """
    m = magnitude
    return {
        "interval":  -m * abs(random.gauss(0, 0.5)),   # quickens — a surge is faster
        "intensity":  m * abs(random.gauss(0, 1.0)),   # the kick: a one-sided spike up
        "noise":      m * random.gauss(0, 0.5),        # a little texture, signed
    }


# --- The seam to baseline (real, not a stub) ---------------------------------

def blend(baseline: dict, self_t: dict | None, burst: dict | None,
          coherence: dict) -> dict:
    """
    Combine the three sources into the final pulse, per dimension, each weighted
    by its own coherence channel — timing→interval, intensity→intensity,
    texture→noise. The spontaneous burst rides on top (it's the engine, not a
    competitor). If self_t is None (no history yet), this is exactly the old
    baseline pulse plus burst — so dropping this in front of the existing
    generate_pulse is behavior-preserving on day 1, by construction.
    """
    c = coherence
    b = burst or {"interval": 0.0, "intensity": 0.0, "noise": 0.0}

    def mix(dim: str, channel: str) -> float:
        base = baseline[dim]
        if self_t is None:
            return base + b[dim]
        w = c[channel]
        return (1.0 - w) * base + w * self_t[dim] + b[dim]

    return {
        "interval":  mix("interval", "timing"),
        "intensity": mix("intensity", "intensity"),
        "noise":     mix("noise", "texture"),
    }

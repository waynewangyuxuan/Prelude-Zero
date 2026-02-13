"""
Humanize engine — make MIDI sound like a human performance.

Three layers:
  1. Velocity shaping — beat emphasis, phrase arcs, subject prominence, jitter
  2. Timing micro-offsets — Gaussian jitter, voice bias, cadence rubato
  3. Articulation — note duration scaling for non-legato feel

Works on PrettyMIDI objects. Style-agnostic defaults with Baroque preset.

Usage:
    pm = pretty_midi.PrettyMIDI("input.mid")
    pm_human = humanize(pm, config=BAROQUE, section_beats=[0, 36, 44, ...])
    stats = compare(pm, pm_human)
"""

import numpy as np
import pretty_midi
from dataclasses import dataclass, field
from copy import deepcopy


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

@dataclass
class HumanizeConfig:
    """All knobs in one place."""

    # ── Velocity ──
    beat_weights: dict = field(default_factory=lambda: {
        0.0: 8,     # beat 1: strongest
        1.0: -3,    # beat 2: weak
        2.0: 4,     # beat 3: medium
        3.0: -3,    # beat 4: weak
    })
    velocity_jitter: float = 5.0        # ± uniform random range
    phrase_arc_strength: float = 0.08   # fraction of velocity for arc peak

    # ── Timing ──
    timing_sigma: float = 0.008         # gaussian σ in seconds (~8ms)
    voice_timing_bias: dict = field(default_factory=lambda: {
        0:  0.003,   # Soprano: slightly late  (melody floats)
        1:  0.000,   # Alto: on beat
        2:  0.000,   # Tenor: on beat
        3: -0.005,   # Bass: slightly early (harmonic anchor)
    })
    cadence_rubato: float = 0.06        # max slowdown fraction at phrase ends
    cadence_window: float = 2.0         # beats before section end to start rubato

    # ── Articulation ──
    default_legato: float = 0.85        # base note-duration ratio
    stepwise_legato: float = 0.92       # for stepwise motion (≤ 2 semitones)
    phrase_end_legato: float = 0.95     # lingering on last few notes of a voice
    min_note_dur: float = 0.04          # never shorten below this (seconds)

    # ── Global ──
    bpm: float = 80.0
    beats_per_bar: int = 4


@dataclass
class ProminenceWindow:
    """Mark a time range where a voice should be louder (e.g. subject entry)."""
    voice_idx: int
    start_beat: float
    end_beat: float
    boost: int = 10     # velocity boost


# ── Presets ──

BAROQUE = HumanizeConfig(
    # Slightly detached, clear articulation, moderate dynamics
    velocity_jitter=5.0,
    phrase_arc_strength=0.08,
    timing_sigma=0.008,
    default_legato=0.85,
    cadence_rubato=0.06,
)

ROMANTIC = HumanizeConfig(
    # More legato, wider dynamics, more rubato
    velocity_jitter=8.0,
    phrase_arc_strength=0.15,
    timing_sigma=0.012,
    default_legato=0.92,
    cadence_rubato=0.12,
    cadence_window=3.0,
)


# ═══════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════

def humanize(
    pm: pretty_midi.PrettyMIDI,
    config: HumanizeConfig = None,
    section_beats: list[float] = None,
    prominence: list[ProminenceWindow] = None,
    seed: int = 42,
) -> pretty_midi.PrettyMIDI:
    """
    Apply full humanization to a PrettyMIDI object.

    Args:
        pm: input PrettyMIDI (not modified — returns a deep copy)
        config: humanization parameters (default: BAROQUE)
        section_beats: list of section boundary positions in BEATS
                       e.g. [0, 36, 44, 53, ...] for phrase arcs + rubato
        prominence: list of ProminenceWindow for subject emphasis
        seed: random seed for reproducibility

    Returns:
        new PrettyMIDI with humanized notes
    """
    if config is None:
        config = BAROQUE

    rng = np.random.RandomState(seed)
    result = deepcopy(pm)

    beat_dur = 60.0 / config.bpm

    # Convert section boundaries and prominence to seconds
    sec_secs = [b * beat_dur for b in section_beats] if section_beats else None
    prom_secs = None
    if prominence:
        prom_secs = [
            (pw.voice_idx, pw.start_beat * beat_dur, pw.end_beat * beat_dur, pw.boost)
            for pw in prominence
        ]

    for voice_idx, inst in enumerate(result.instruments):
        inst.notes.sort(key=lambda n: n.start)
        n_notes = len(inst.notes)

        for i, note in enumerate(inst.notes):
            # ── 1. Velocity ──
            vel = _shape_velocity(
                note, voice_idx, i, n_notes,
                config, beat_dur, rng, sec_secs, prom_secs,
            )
            note.velocity = max(25, min(127, int(vel)))

            # ── 2. Timing ──
            offset = _timing_offset(note, voice_idx, config, beat_dur, rng, sec_secs)
            note.start = max(0.0, note.start + offset)
            note.end = max(note.start + 0.01, note.end + offset)

            # ── 3. Articulation ──
            new_dur = _articulate(note, i, inst.notes, config)
            note.end = note.start + new_dur

    return result


# ═══════════════════════════════════════════════════════════════
# Layer 1: Velocity shaping
# ═══════════════════════════════════════════════════════════════

def _shape_velocity(note, voice_idx, note_idx, total_notes,
                    config, beat_dur, rng, sec_secs, prom_secs):
    """Compute humanized velocity for a single note."""
    vel = float(note.velocity)

    # ── Beat-position weight ──
    beat_in_bar = (note.start / beat_dur) % config.beats_per_bar
    best_weight = 0
    best_dist = 999.0
    for beat_pos, weight in config.beat_weights.items():
        dist = abs(beat_in_bar - beat_pos)
        if dist < best_dist:
            best_dist = dist
            best_weight = weight
    if best_dist < 0.25:   # only apply if note is near a metrical beat
        vel += best_weight

    # ── Phrase arc (bell-curve per section) ──
    if sec_secs and len(sec_secs) >= 2:
        s_start, s_end = _find_section(note.start, sec_secs)
        s_dur = s_end - s_start
        if s_dur > 0:
            pos = (note.start - s_start) / s_dur
            # Bell curve: peaks at 40% of section, tapers at ends
            arc = max(0.0, 1.0 - ((pos - 0.4) / 0.45) ** 2)
            vel += arc * config.phrase_arc_strength * vel

    # ── Subject prominence ──
    if prom_secs:
        for vi, p_start, p_end, boost in prom_secs:
            if vi == voice_idx and p_start <= note.start < p_end:
                vel += boost
                break

    # ── Random jitter ──
    vel += rng.uniform(-config.velocity_jitter, config.velocity_jitter)

    return vel


# ═══════════════════════════════════════════════════════════════
# Layer 2: Timing micro-offsets
# ═══════════════════════════════════════════════════════════════

def _timing_offset(note, voice_idx, config, beat_dur, rng, sec_secs):
    """Compute timing offset in seconds for a single note."""
    # Base gaussian jitter (the "human imprecision")
    offset = rng.normal(0, config.timing_sigma)

    # Voice-specific bias (bass early, soprano late)
    offset += config.voice_timing_bias.get(voice_idx, 0.0)

    # Cadence rubato: progressive delay near section ends
    if sec_secs and config.cadence_rubato > 0:
        cadence_win_sec = config.cadence_window * beat_dur
        for j in range(len(sec_secs) - 1):
            sec_end = sec_secs[j + 1]
            cad_start = sec_end - cadence_win_sec
            if cad_start <= note.start < sec_end:
                progress = (note.start - cad_start) / cadence_win_sec
                rubato_delay = progress * config.cadence_rubato * beat_dur
                offset += rubato_delay
                break

    return offset


# ═══════════════════════════════════════════════════════════════
# Layer 3: Articulation
# ═══════════════════════════════════════════════════════════════

def _articulate(note, note_idx, all_notes, config):
    """Compute articulated note duration (shorter = more detached)."""
    original_dur = note.end - note.start
    if original_dur < config.min_note_dur:
        return original_dur

    ratio = config.default_legato

    # Stepwise connection → more legato
    if note_idx > 0:
        if abs(note.pitch - all_notes[note_idx - 1].pitch) <= 2:
            ratio = max(ratio, config.stepwise_legato)
    if note_idx < len(all_notes) - 1:
        if abs(all_notes[note_idx + 1].pitch - note.pitch) <= 2:
            ratio = max(ratio, config.stepwise_legato)

    # Last 3 notes of voice → linger
    if note_idx >= len(all_notes) - 3:
        ratio = max(ratio, config.phrase_end_legato)

    return max(config.min_note_dur, original_dur * ratio)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _find_section(time_sec, sec_secs):
    """Find (start, end) of the section containing time_sec."""
    for j in range(len(sec_secs) - 1):
        if sec_secs[j] <= time_sec < sec_secs[j + 1]:
            return sec_secs[j], sec_secs[j + 1]
    return sec_secs[0], sec_secs[-1]


# ═══════════════════════════════════════════════════════════════
# A/B comparison
# ═══════════════════════════════════════════════════════════════

def compare(original: pretty_midi.PrettyMIDI,
            humanized: pretty_midi.PrettyMIDI) -> dict:
    """
    Compare original vs humanized — stats for verification.

    Returns per-voice stats: velocity shift, timing jitter, duration ratio.
    """
    stats = {}
    n_inst = min(len(original.instruments), len(humanized.instruments))

    for vi in range(n_inst):
        orig = sorted(original.instruments[vi].notes, key=lambda n: n.start)
        hum = sorted(humanized.instruments[vi].notes, key=lambda n: n.start)
        n = min(len(orig), len(hum))
        if n == 0:
            continue

        vel_d = [hum[i].velocity - orig[i].velocity for i in range(n)]
        time_d = [(hum[i].start - orig[i].start) * 1000 for i in range(n)]  # ms
        dur_r = [
            (hum[i].end - hum[i].start) / max(0.01, orig[i].end - orig[i].start)
            for i in range(n)
        ]

        name = original.instruments[vi].name or f"Voice {vi}"
        stats[name] = {
            "notes": n,
            "velocity": {
                "mean_shift": round(float(np.mean(vel_d)), 1),
                "std": round(float(np.std(vel_d)), 1),
                "range": (int(min(vel_d)), int(max(vel_d))),
            },
            "timing_ms": {
                "mean_shift": round(float(np.mean(time_d)), 1),
                "std": round(float(np.std(time_d)), 1),
                "range": (round(min(time_d), 1), round(max(time_d), 1)),
            },
            "duration_ratio": {
                "mean": round(float(np.mean(dur_r)), 3),
                "std": round(float(np.std(dur_r)), 3),
            },
        }

    return stats

"""
Metric-guided melody generator.

The core idea: instead of composing note-by-note and checking metrics after,
generate melodies DIRECTLY from metric targets. The generator does a
constrained random walk on the scale, shaped by the target profile.

Input:  StyleTarget (metric ranges) + Scale + BPM + duration
Output: list of (pitch, onset, duration) tuples

Algorithm:
  1. Duration sequence: generate rhythmic backbone from density + duration_cv
  2. Pitch walk: random walk on scale, guided by step_ratio, direction changes,
     run length, chromatic probability
  3. Phrase shaping: apply arc contours per phrase
  4. Repetition: optionally repeat/vary phrases for riff-based styles

This is the interface that the LLM operator layer uses:
  "Give me a Phrygian melody, density 1.0, high duration contrast, wide range"
"""

import numpy as np
from dataclasses import dataclass, field
from core.scales import Scale, from_name


# ═══════════════════════════════════════════════════════════════
# Style targets
# ═══════════════════════════════════════════════════════════════

@dataclass
class StyleTarget:
    """
    Metric targets for melody generation.
    Each is a (center, tolerance) pair. Generator aims for center ± tolerance.
    """
    # Rhythm
    density: float = 2.0           # notes per beat
    duration_cv: float = 0.3       # coefficient of variation of durations
    rhythm_variety: int = 3        # how many distinct duration values to use

    # Pitch motion
    step_ratio: float = 0.7        # fraction of intervals ≤ 2 semitones
    leap_probability: float = 0.05 # fraction of intervals > 7 semitones
    direction_change_prob: float = 0.4  # probability of reversing at each note
    target_run_length: float = 2.0 # mean notes in same direction before change

    # Range
    pitch_center: int = 69         # A4 — center of the melody
    pitch_range: int = 12          # total range in semitones
    contour_bias: float = 0.0      # +1 = always ascend, -1 = always descend, 0 = balanced

    # Color
    chromaticism: float = 0.0      # probability of chromatic neighbor/passing tone
    repetition: float = 0.2        # target pitch bigram repetition rate

    # Phrase structure
    phrase_length_beats: float = 8.0  # average phrase length
    phrase_arc: bool = True           # apply velocity arc per phrase


# ── Presets from Experiment 005 data ──

BACH_TARGET = StyleTarget(
    density=3.0, duration_cv=0.15, rhythm_variety=2,
    step_ratio=0.75, leap_probability=0.02,
    direction_change_prob=0.45, target_run_length=2.0,
    pitch_center=69, pitch_range=12, contour_bias=0.0,
    chromaticism=0.0, repetition=0.33,
    phrase_length_beats=4.0, phrase_arc=True,
)

CHOPIN_TARGET = StyleTarget(
    density=1.5, duration_cv=0.30, rhythm_variety=4,
    step_ratio=0.85, leap_probability=0.0,
    direction_change_prob=0.25, target_run_length=3.0,
    pitch_center=74, pitch_range=12, contour_bias=0.0,
    chromaticism=0.15, repetition=0.18,
    phrase_length_beats=8.0, phrase_arc=True,
)

FLOYD_TARGET = StyleTarget(
    density=0.8, duration_cv=0.95, rhythm_variety=6,
    step_ratio=0.45, leap_probability=0.12,
    direction_change_prob=0.55, target_run_length=1.6,
    pitch_center=67, pitch_range=25, contour_bias=0.0,
    chromaticism=0.25, repetition=0.50,
    phrase_length_beats=8.0, phrase_arc=False,
)


# ═══════════════════════════════════════════════════════════════
# Generator
# ═══════════════════════════════════════════════════════════════

@dataclass
class MelodyNote:
    pitch: int
    onset: float       # seconds
    duration: float    # seconds
    velocity: int = 75
    is_chromatic: bool = False


def generate_melody(
    scale: Scale,
    target: StyleTarget,
    bpm: float,
    total_beats: float,
    seed: int = 42,
) -> list[MelodyNote]:
    """
    Generate a melody matching the given style target.

    Args:
        scale: the Scale to use (defines legal pitches)
        target: StyleTarget with metric targets
        bpm: tempo in beats per minute
        total_beats: total length in beats
        seed: random seed for reproducibility

    Returns:
        list of MelodyNote
    """
    rng = np.random.RandomState(seed)
    beat_dur = 60.0 / bpm

    # ── Step 1: Generate duration sequence ──
    durations_beats = _generate_rhythm(target, total_beats, rng)

    # ── Step 2: Generate pitch sequence ──
    pitches, chromatic_flags = _generate_pitches(
        scale, target, len(durations_beats), rng
    )

    # ── Step 3: Apply phrase shaping ──
    velocities = _shape_phrases(target, durations_beats, rng)

    # ── Step 4: Apply repetition (riff/motif reuse) ──
    if target.repetition > 0.35:
        lo = target.pitch_center - target.pitch_range // 2
        hi = target.pitch_center + target.pitch_range // 2
        pitches = _apply_repetition(pitches, target, rng, scale, lo, hi)

    # ── Assemble ──
    notes = []
    t = 0.0
    for i in range(len(pitches)):
        dur_s = durations_beats[i] * beat_dur
        notes.append(MelodyNote(
            pitch=pitches[i],
            onset=t,
            duration=dur_s,
            velocity=velocities[i],
            is_chromatic=chromatic_flags[i] if i < len(chromatic_flags) else False,
        ))
        t += dur_s

    return notes


# ═══════════════════════════════════════════════════════════════
# Step 1: Rhythm generation
# ═══════════════════════════════════════════════════════════════

def _generate_rhythm(target: StyleTarget, total_beats: float,
                     rng: np.random.RandomState) -> list[float]:
    """
    Generate a sequence of note durations (in beats) that matches
    the target density and duration_cv.

    Strategy: build a palette where the ratio between shortest and longest
    is controlled by duration_cv. Then sample from it with weights.
    """
    base_dur = 1.0 / target.density  # beats per note
    n_types = max(2, target.rhythm_variety)

    if target.duration_cv < 0.15:
        # Nearly uniform rhythm (Bach motor rhythm)
        # Just base_dur with tiny jitter
        durations = []
        remaining = total_beats
        while remaining > base_dur * 0.3:
            d = base_dur * rng.uniform(0.92, 1.08)
            d = min(remaining, d)
            durations.append(d)
            remaining -= d
        return durations

    # ── Build palette with controlled spread ──
    # CV 0.3 → ratio 1:2, CV 0.6 → ratio 1:4, CV 1.0 → ratio 1:8
    max_ratio = 2.0 ** (target.duration_cv * 3)
    max_ratio = min(max_ratio, 16.0)  # cap

    # Shortest and longest durations centered around base_dur
    # geometric mean of (shortest, longest) = base_dur
    shortest = base_dur / (max_ratio ** 0.5)
    longest = base_dur * (max_ratio ** 0.5)
    shortest = max(0.125, shortest)  # at least 32nd note
    longest = min(total_beats * 0.3, longest)  # no single note > 30% of piece

    # Evenly spaced in log-space
    palette = list(np.geomspace(shortest, longest, n_types))

    # Weights: for most music, shorter durations are more common
    # But Floyd-like styles want some very long notes too
    if target.duration_cv > 0.7:
        # Bimodal: prefer extremes (short bursts + long sustains)
        weights = np.array([1.0] * n_types, dtype=float)
        weights[0] *= 2.0   # boost shortest
        weights[-1] *= 2.0  # boost longest
    else:
        # Gentle falloff toward longer notes
        weights = np.array([n_types - i for i in range(n_types)], dtype=float)
    weights /= weights.sum()

    # ── Generate sequence ──
    # Fix note count from density, then scale durations to fill total_beats.
    # This decouples "how many notes" (density) from "what rhythm" (CV/palette).
    n_notes = max(4, int(target.density * total_beats))

    raw = []
    for _ in range(n_notes):
        idx = rng.choice(n_types, p=weights)
        d = palette[idx] * rng.uniform(0.88, 1.12)  # jitter
        raw.append(d)

    # Scale so they sum to total_beats (preserves relative durations = CV)
    total_raw = sum(raw)
    if total_raw > 0:
        scale_factor = total_beats / total_raw
        durations = [d * scale_factor for d in raw]
    else:
        durations = [base_dur] * n_notes

    return durations


# ═══════════════════════════════════════════════════════════════
# Step 2: Pitch generation
# ═══════════════════════════════════════════════════════════════

def _generate_pitches(scale: Scale, target: StyleTarget, n_notes: int,
                      rng: np.random.RandomState) -> tuple[list[int], list[bool]]:
    """
    Generate a pitch sequence via constrained random walk on the scale.
    """
    # Define pitch bounds
    lo = target.pitch_center - target.pitch_range // 2
    hi = target.pitch_center + target.pitch_range // 2

    # Start near center
    pitch = scale.snap(target.pitch_center, lo, hi)
    direction = 1  # 1=ascending, -1=descending
    run_count = 0  # how many notes in current direction

    pitches = [pitch]
    chromatic = [False]

    for i in range(1, n_notes):
        # ── Decide direction ──
        run_count += 1

        # Probability of changing direction increases with run length
        base_change_prob = target.direction_change_prob
        # Boost probability as run exceeds target
        if run_count > target.target_run_length:
            overshoot = (run_count - target.target_run_length) / target.target_run_length
            change_prob = min(0.95, base_change_prob + overshoot * 0.3)
        else:
            change_prob = base_change_prob

        # Force direction change if hitting bounds
        if pitch >= hi - 2:
            change_prob = 0.9 if direction == 1 else 0.1
        elif pitch <= lo + 2:
            change_prob = 0.9 if direction == -1 else 0.1

        # Apply contour bias
        if target.contour_bias != 0:
            if direction == 1 and target.contour_bias < 0:
                change_prob += abs(target.contour_bias) * 0.2
            elif direction == -1 and target.contour_bias > 0:
                change_prob += abs(target.contour_bias) * 0.2

        if rng.random() < change_prob:
            direction = -direction
            run_count = 0

        # ── Decide interval size ──
        r = rng.random()
        if r < target.step_ratio:
            # Stepwise: 1 scale degree
            step_size = 1
        elif r < target.step_ratio + (1 - target.step_ratio - target.leap_probability):
            # Skip: 2-3 scale degrees
            step_size = rng.choice([2, 3])
        else:
            # Leap: 4+ scale degrees
            step_size = rng.choice([4, 5, 6, 7])

        # ── Move ──
        new_pitch = scale.step(pitch, direction, step_size, lo, hi)

        # ── Chromaticism ──
        # The metric counts unique chromatic pitch classes / unique PCs,
        # so even a few chromatic notes inflate the score significantly.
        # Use a low multiplier (0.15) to keep measured chromaticism near target.
        is_chrom = False
        chrom_prob = target.chromaticism * 0.15
        if chrom_prob > 0 and rng.random() < chrom_prob:
            neighbors = scale.chromatic_neighbors(new_pitch)
            if neighbors:
                new_pitch = rng.choice(neighbors)
                is_chrom = True

        # ── Repetition: occasionally repeat the same pitch ──
        if rng.random() < 0.05:
            new_pitch = pitch  # stay on same note

        pitch = max(lo, min(hi, new_pitch))
        pitches.append(pitch)
        chromatic.append(is_chrom)

    return pitches, chromatic


# ═══════════════════════════════════════════════════════════════
# Step 3: Phrase shaping
# ═══════════════════════════════════════════════════════════════

def _shape_phrases(target: StyleTarget, durations: list[float],
                   rng: np.random.RandomState) -> list[int]:
    """
    Apply velocity shaping per phrase (bell-curve arc).
    """
    n = len(durations)
    velocities = [75] * n

    if not target.phrase_arc:
        # Flat dynamics with light random variation
        for i in range(n):
            velocities[i] = int(70 + rng.uniform(-8, 8))
        return velocities

    # Divide into phrases
    cumulative = 0.0
    phrase_start = 0
    for i in range(n):
        cumulative += durations[i]
        if cumulative >= target.phrase_length_beats or i == n - 1:
            # Shape this phrase
            phrase_len = i - phrase_start + 1
            for j in range(phrase_len):
                # Bell curve peaking at 40% through the phrase
                pos = j / max(1, phrase_len - 1)
                arc = max(0.0, 1.0 - ((pos - 0.4) / 0.45) ** 2)
                base_vel = 60 + arc * 30
                velocities[phrase_start + j] = int(base_vel + rng.uniform(-4, 4))
            phrase_start = i + 1
            cumulative = 0.0

    return velocities


# ═══════════════════════════════════════════════════════════════
# Step 4: Repetition (riff/motif reuse)
# ═══════════════════════════════════════════════════════════════

def _apply_repetition(pitches: list[int], target: StyleTarget,
                      rng: np.random.RandomState,
                      scale: Scale = None,
                      lo: int = 21, hi: int = 108) -> list[int]:
    """
    For high-repetition styles (Floyd riffs, Bach motifs):
    Take short motifs and repeat/vary them.
    Transposed pitches are snapped back to scale to avoid accidental chromaticism.
    """
    if len(pitches) < 8:
        return pitches

    # Extract motif: first 4-8 notes
    motif_len = min(8, max(4, int(len(pitches) * 0.15)))
    motif = pitches[:motif_len]

    result = list(pitches)

    # Replace some later sections with motif variations
    rep_rate = target.repetition
    i = motif_len
    while i < len(result) - motif_len:
        if rng.random() < rep_rate * 0.6:
            # Insert a motif repetition (possibly transposed)
            transposition = rng.choice([0, 0, 0, 2, -2, 5, 7])
            for j in range(motif_len):
                if i + j < len(result):
                    p = motif[j] + transposition
                    # Snap transposed pitch back to scale to avoid chromaticism
                    if scale is not None and not scale.contains(p):
                        p = scale.snap(p, lo, hi)
                    result[i + j] = p
            i += motif_len
        else:
            i += 1

    return result


# ═══════════════════════════════════════════════════════════════
# Convenience: generate and export to PrettyMIDI
# ═══════════════════════════════════════════════════════════════

def melody_to_pretty_midi(
    notes: list[MelodyNote],
    bpm: float,
    program: int = 0,
    instrument_name: str = 'Melody',
) -> 'pretty_midi.PrettyMIDI':
    """Convert melody notes to a PrettyMIDI instrument."""
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=program, name=instrument_name)
    for n in notes:
        inst.notes.append(pretty_midi.Note(
            velocity=n.velocity,
            pitch=max(21, min(108, n.pitch)),
            start=max(0.0, n.onset),
            end=max(n.onset + 0.01, n.onset + n.duration),
        ))
    pm.instruments.append(inst)
    return pm

"""
Melody metrics engine — 10 computable dimensions for single-voice melody quality.

Architecture layer: Metric Space
These metrics measure WHAT the melody is, not whether it's good or bad.
"Good" = falling within the target range for the intended style.

Easy tier (6 dimensions):
  1. Pitch range & tessitura  — how wide, how centered
  2. Interval distribution    — step vs leap, direction changes
  3. Pitch entropy           — predictability of pitch choices
  4. Rhythmic entropy        — predictability of rhythm patterns
  5. Rhythmic density        — notes per beat
  6. Tonal clarity           — how clear is the implied key

Medium tier (4 dimensions, added 2026-02-14):
  7. Contour shape           — ascending/descending runs, direction bias
  8. Mode/scale detection    — Dorian? Mixolydian? Pentatonic? Blues?
  9. Duration variance       — uniform motor rhythm vs rubato
  10. Repetition index       — motivic economy vs through-composed

Each metric returns both a raw value and genre-relative assessment.

Usage:
    profile = compute_melody_profile(pitches, onsets, durations, bpm=120)
    print(summarize(profile))

    # Or from MIDI:
    profile = from_midi(pm, voice=0, bpm=120)
"""

import numpy as np
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional
import pretty_midi


# ═══════════════════════════════════════════════════════════════
# Genre reference ranges (from literature + to be refined by benchmark)
# ═══════════════════════════════════════════════════════════════

GENRE_RANGES = {
    # Ranges calibrated from benchmark v1 (15 reference melodies, 2026-02-13)
    # These are for SHORT themes/phrases (8-32 notes). Full pieces will differ.
    # transition_entropy removed: unreliable for short melodies (too few bigram repeats)
    "baroque": {
        "pitch_range":      (8, 14),       # semitones (themes are compact)
        "tessitura_std":    (2.4, 4.0),    # std of pitches
        "step_ratio":       (0.12, 0.80),  # wide: arpeggiated (cello) vs scalar (inventions)
        "leap_ratio":       (0.00, 0.10),  # rarely large leaps in subjects
        "direction_change": (0.35, 1.00),  # high — baroque melodies change direction often
        "mean_abs_interval": (2.0, 4.5),   # semitones
        "pitch_entropy":    (2.3, 3.0),    # bits (pitch class H)
        "rhythm_entropy":   (0.0, 1.0),    # low — motor rhythm, uniform note values
        "rhythm_density":   (2.5, 4.5),    # notes per beat (fast, dense)
        "tonal_clarity":    (0.68, 0.95),  # strong tonal center
    },
    "romantic": {
        "pitch_range":      (5, 15),       # short themes can be narrow (Chopin Prelude 4!)
        "tessitura_std":    (1.5, 4.5),    # varies widely
        "step_ratio":       (0.50, 0.95),  # mostly stepwise, lyrical
        "leap_ratio":       (0.00, 0.10),  # leaps more common in full-piece development
        "direction_change": (0.20, 0.40),  # LOW — romantic melodies sustain direction
        "mean_abs_interval": (0.8, 3.0),   # chromatic = small intervals
        "pitch_entropy":    (2.4, 2.9),    # bits
        "rhythm_entropy":   (0.0, 1.2),    # moderate variety
        "rhythm_density":   (1.0, 2.2),    # slower, more sustained
        "tonal_clarity":    (0.40, 0.95),  # wide — chromatic vs diatonic
    },
    "pop": {
        "pitch_range":      (9, 13),       # vocal range constraint
        "tessitura_std":    (2.5, 3.6),    # moderate spread
        "step_ratio":       (0.65, 0.95),  # mostly stepwise, singable
        "leap_ratio":       (0.00, 0.05),  # very few leaps
        "direction_change": (0.15, 0.50),  # lower — phrases sustain direction
        "mean_abs_interval": (1.3, 2.5),   # small intervals
        "pitch_entropy":    (2.2, 2.6),    # bits — limited pitch vocabulary
        "rhythm_entropy":   (0.3, 1.2),    # repetitive patterns
        "rhythm_density":   (0.8, 1.6),    # slower than baroque
        "tonal_clarity":    (0.64, 0.95),  # strong tonal center
    },
}


# ═══════════════════════════════════════════════════════════════
# Data structure
# ═══════════════════════════════════════════════════════════════

@dataclass
class MelodyProfile:
    """Complete metric profile for a single-voice melody."""

    # Dimension 1: Pitch range & tessitura
    pitch_range: int          # max - min in semitones
    pitch_min: int            # lowest MIDI note
    pitch_max: int            # highest MIDI note
    pitch_mean: float         # mean MIDI pitch
    pitch_std: float          # std of MIDI pitches
    note_count: int           # total notes

    # Dimension 2: Interval distribution
    step_ratio: float         # fraction of intervals ≤ 2 semitones
    leap_ratio: float         # fraction of intervals > 7 semitones (P5)
    mean_abs_interval: float  # mean absolute interval size
    direction_change_ratio: float  # fraction of direction changes

    # Dimension 3: Pitch entropy
    pitch_class_entropy: float      # H(pitch class) — 0th order
    pitch_transition_entropy: float # H(pc_n | pc_{n-1}) — 1st order

    # Dimension 4: Rhythmic entropy
    rhythm_entropy: float     # H(IOI) quantized to 16th-note grid

    # Dimension 5: Rhythmic density
    rhythm_density: float     # notes per beat
    duration_seconds: float   # total duration

    # Dimension 6: Tonal clarity
    tonal_clarity: float      # max correlation with K-S key profile
    estimated_key: str        # best-fit key name
    chromaticism: float       # fraction of non-diatonic pitch classes

    # ── Medium tier (added 2026-02-14) ──

    # Dimension 7: Contour shape
    mean_run_length: float = 0.0        # avg consecutive same-direction intervals
    longest_run: int = 0                # longest same-direction run
    contour_direction_bias: float = 0.0 # (ascending - descending) / total: -1 to +1

    # Dimension 8: Mode/scale detection
    best_mode: str = ""                 # best-fit mode key (e.g., "dorian")
    best_mode_display: str = ""         # human-readable (e.g., "D Dorian")
    mode_coverage: float = 0.0          # fraction of notes in best-fit scale
    mode_clarity: float = 0.0           # coverage gap to 2nd-best mode

    # Dimension 9: Duration variance
    duration_cv: float = 0.0            # coefficient of variation (std/mean)
    duration_range_ratio: float = 0.0   # (max_dur - min_dur) / mean_dur

    # Dimension 10: Repetition index
    pitch_bigram_rep: float = 0.0       # fraction of pitch bigrams that repeat
    rhythm_bigram_rep: float = 0.0      # fraction of IOI bigrams that repeat
    combined_rep: float = 0.0           # fraction of (pitch, IOI) bigrams that repeat

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def genre_fit(self, genre: str) -> dict[str, str]:
        """Compare each metric against genre reference range."""
        if genre not in GENRE_RANGES:
            return {"error": f"Unknown genre: {genre}"}

        ref = GENRE_RANGES[genre]
        result = {}
        checks = [
            ("pitch_range",         self.pitch_range),
            ("tessitura_std",       self.pitch_std),
            ("step_ratio",          self.step_ratio),
            ("leap_ratio",          self.leap_ratio),
            ("direction_change",    self.direction_change_ratio),
            ("mean_abs_interval",   self.mean_abs_interval),
            ("pitch_entropy",       self.pitch_class_entropy),
            ("transition_entropy",  self.pitch_transition_entropy),
            ("rhythm_entropy",      self.rhythm_entropy),
            ("rhythm_density",      self.rhythm_density),
            ("tonal_clarity",       self.tonal_clarity),
        ]
        for name, value in checks:
            if name not in ref:
                continue
            lo, hi = ref[name]
            if value < lo:
                result[name] = f"LOW ({value:.3f} < {lo})"
            elif value > hi:
                result[name] = f"HIGH ({value:.3f} > {hi})"
            else:
                result[name] = f"OK ({value:.3f} in [{lo}, {hi}])"
        return result


# ═══════════════════════════════════════════════════════════════
# Core computation
# ═══════════════════════════════════════════════════════════════

def _shannon_entropy(sequence) -> float:
    """Shannon entropy of a discrete sequence."""
    if len(sequence) == 0:
        return 0.0
    counts = Counter(sequence)
    total = len(sequence)
    probs = [c / total for c in counts.values()]
    return -sum(p * np.log2(p) for p in probs if p > 0)


# Krumhansl-Schmuckler key profiles
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                            2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                            2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
_KEY_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

# Diatonic pitch classes for each major key (for chromaticism calculation)
_MAJOR_DIATONIC = {
    i: set((np.array([0, 2, 4, 5, 7, 9, 11]) + i) % 12)
    for i in range(12)
}
_MINOR_DIATONIC = {
    i: set((np.array([0, 2, 3, 5, 7, 8, 10]) + i) % 12)
    for i in range(12)
}


# Scale/mode templates (pitch class intervals from root)
_SCALE_TEMPLATES = {
    "ionian":      [0, 2, 4, 5, 7, 9, 11],   # major
    "dorian":      [0, 2, 3, 5, 7, 9, 10],    # minor with raised 6th
    "phrygian":    [0, 1, 3, 5, 7, 8, 10],    # minor with lowered 2nd
    "lydian":      [0, 2, 4, 6, 7, 9, 11],    # major with raised 4th
    "mixolydian":  [0, 2, 4, 5, 7, 9, 10],    # major with lowered 7th
    "aeolian":     [0, 2, 3, 5, 7, 8, 10],    # natural minor
    "pent_major":  [0, 2, 4, 7, 9],           # 5-note major pentatonic
    "pent_minor":  [0, 3, 5, 7, 10],          # 5-note minor pentatonic
    "blues":       [0, 3, 5, 6, 7, 10],       # minor pent + b5
}

_MODE_DISPLAY = {
    "ionian": "Ionian (Major)", "dorian": "Dorian", "phrygian": "Phrygian",
    "lydian": "Lydian", "mixolydian": "Mixolydian", "aeolian": "Aeolian (Minor)",
    "pent_major": "Pentatonic Major", "pent_minor": "Pentatonic Minor",
    "blues": "Blues",
}


def _mode_detection(pitch_classes: list[int]) -> tuple[str, str, float, float]:
    """
    Detect best-fit mode/scale by pitch class coverage.

    Returns: (best_mode_key, display_name, coverage, clarity)
      coverage: fraction of notes in best-fit scale [0,1]
      clarity: coverage_best - coverage_2nd_best
    """
    if not pitch_classes:
        return "ionian", "C Ionian (Major)", 0.0, 0.0

    scores = []  # (coverage, root, mode_key)

    for root in range(12):
        for mode_key, intervals in _SCALE_TEMPLATES.items():
            scale_pcs = set((root + i) % 12 for i in intervals)
            matching = sum(1 for pc in pitch_classes if pc in scale_pcs)
            coverage = matching / len(pitch_classes)
            scores.append((coverage, root, mode_key))

    scores.sort(reverse=True)
    best_cov, best_root, best_mode = scores[0]
    second_cov = scores[1][0]
    clarity = best_cov - second_cov

    root_name = _KEY_NAMES[best_root]
    display = f"{root_name} {_MODE_DISPLAY[best_mode]}"

    return best_mode, display, best_cov, clarity


def _key_finding(pitch_classes: list[int]) -> tuple[float, str, set]:
    """
    Krumhansl-Schmuckler key-finding algorithm.
    Returns (max_correlation, key_name, diatonic_set).
    """
    if len(pitch_classes) == 0:
        return 0.0, "C major", _MAJOR_DIATONIC[0]

    # Build pitch class histogram
    histogram = np.zeros(12)
    for pc in pitch_classes:
        histogram[pc % 12] += 1

    best_corr = -1.0
    best_key = "C major"
    best_diatonic = _MAJOR_DIATONIC[0]

    for shift in range(12):
        rotated = np.roll(histogram, -shift)

        # Major
        corr_maj = np.corrcoef(rotated, _MAJOR_PROFILE)[0, 1]
        if corr_maj > best_corr:
            best_corr = corr_maj
            best_key = f"{_KEY_NAMES[shift]} major"
            best_diatonic = _MAJOR_DIATONIC[shift]

        # Minor
        corr_min = np.corrcoef(rotated, _MINOR_PROFILE)[0, 1]
        if corr_min > best_corr:
            best_corr = corr_min
            best_key = f"{_KEY_NAMES[shift]} minor"
            best_diatonic = _MINOR_DIATONIC[shift]

    return best_corr, best_key, best_diatonic


def compute_melody_profile(
    pitches: list[int],
    onsets: list[float],
    durations: list[float],
    bpm: float = 120.0,
) -> MelodyProfile:
    """
    Compute all 6 melody metric dimensions from raw note data.

    Args:
        pitches: MIDI note numbers (e.g., 60 = C4)
        onsets: onset times in seconds
        durations: note durations in seconds
        bpm: tempo in beats per minute (for density calculation)
    """
    pitches = np.array(pitches, dtype=int)
    onsets = np.array(onsets, dtype=float)
    durations = np.array(durations, dtype=float)
    n = len(pitches)

    assert n == len(onsets) == len(durations), "Arrays must be same length"
    assert n >= 2, "Need at least 2 notes"

    # Sort by onset time
    order = np.argsort(onsets)
    pitches = pitches[order]
    onsets = onsets[order]
    durations = durations[order]

    beat_dur = 60.0 / bpm

    # ── Dimension 1: Pitch range & tessitura ──
    pitch_range = int(pitches.max() - pitches.min())
    pitch_min = int(pitches.min())
    pitch_max = int(pitches.max())
    pitch_mean = float(np.mean(pitches))
    pitch_std = float(np.std(pitches))

    # ── Dimension 2: Interval distribution ──
    intervals = np.diff(pitches)  # signed intervals
    abs_intervals = np.abs(intervals)
    n_intervals = len(intervals)

    if n_intervals > 0:
        step_ratio = float(np.sum(abs_intervals <= 2) / n_intervals)
        leap_ratio = float(np.sum(abs_intervals > 7) / n_intervals)
        mean_abs_interval = float(np.mean(abs_intervals))

        # Direction changes: count sign changes in interval sequence
        signs = np.sign(intervals)
        # Remove zeros (repeated notes) for direction analysis
        nonzero_signs = signs[signs != 0]
        if len(nonzero_signs) > 1:
            direction_changes = np.sum(np.diff(nonzero_signs) != 0)
            direction_change_ratio = float(direction_changes / (len(nonzero_signs) - 1))
        else:
            direction_change_ratio = 0.0
    else:
        step_ratio = 0.0
        leap_ratio = 0.0
        mean_abs_interval = 0.0
        direction_change_ratio = 0.0

    # ── Dimension 3: Pitch entropy ──
    pitch_classes = [int(p % 12) for p in pitches]
    pitch_class_entropy = _shannon_entropy(pitch_classes)

    # Transition entropy: H of (pc_from, pc_to) bigrams
    if n >= 2:
        bigrams = [(pitch_classes[i], pitch_classes[i + 1]) for i in range(n - 1)]
        pitch_transition_entropy = _shannon_entropy(bigrams)
    else:
        pitch_transition_entropy = 0.0

    # ── Dimension 4: Rhythmic entropy ──
    # Quantize IOIs to 16th-note grid
    iois = np.diff(onsets)
    sixteenth = beat_dur / 4.0
    if len(iois) > 0 and sixteenth > 0:
        quantized_iois = np.round(iois / sixteenth).astype(int)
        quantized_iois = np.clip(quantized_iois, 1, 64)  # cap at 4 bars of 16ths
        rhythm_entropy = _shannon_entropy(quantized_iois.tolist())
    else:
        rhythm_entropy = 0.0

    # ── Dimension 5: Rhythmic density ──
    total_duration = float(onsets[-1] + durations[-1] - onsets[0])
    total_beats = total_duration / beat_dur if beat_dur > 0 else 1.0
    rhythm_density = float(n / total_beats) if total_beats > 0 else 0.0

    # ── Dimension 6: Tonal clarity ──
    tonal_clarity, estimated_key, diatonic_set = _key_finding(pitch_classes)

    # Chromaticism: fraction of pitch classes NOT in the diatonic set
    unique_pcs = set(pitch_classes)
    chromatic_pcs = unique_pcs - diatonic_set
    chromaticism = float(len(chromatic_pcs) / len(unique_pcs)) if unique_pcs else 0.0

    # ── Dimension 7: Contour shape ──
    if n_intervals > 0:
        signs = np.sign(intervals)
        nonzero_signs = signs[signs != 0]

        # Direction bias: (ascending - descending) / total
        n_ascending = int(np.sum(nonzero_signs > 0))
        n_descending = int(np.sum(nonzero_signs < 0))
        n_total_dir = n_ascending + n_descending
        contour_direction_bias = float((n_ascending - n_descending) / n_total_dir) if n_total_dir > 0 else 0.0

        # Run lengths: consecutive same-direction intervals
        if len(nonzero_signs) > 0:
            runs = []
            current_run = 1
            for i in range(1, len(nonzero_signs)):
                if nonzero_signs[i] == nonzero_signs[i - 1]:
                    current_run += 1
                else:
                    runs.append(current_run)
                    current_run = 1
            runs.append(current_run)
            mean_run_length = float(np.mean(runs))
            longest_run = int(max(runs))
        else:
            mean_run_length = 0.0
            longest_run = 0
    else:
        contour_direction_bias = 0.0
        mean_run_length = 0.0
        longest_run = 0

    # ── Dimension 8: Mode/scale detection ──
    best_mode, best_mode_display, mode_coverage, mode_clarity = _mode_detection(pitch_classes)

    # ── Dimension 9: Duration variance ──
    dur_mean = float(np.mean(durations))
    dur_std = float(np.std(durations))
    duration_cv = float(dur_std / dur_mean) if dur_mean > 0 else 0.0
    dur_range = float(np.max(durations) - np.min(durations))
    duration_range_ratio = float(dur_range / dur_mean) if dur_mean > 0 else 0.0

    # ── Dimension 10: Repetition index ──
    def _repetition_ratio(seq_list):
        """Fraction of bigrams that appear more than once."""
        if len(seq_list) < 2:
            return 0.0
        bigrams = [tuple(seq_list[i:i+2]) for i in range(len(seq_list) - 1)]
        counts = Counter(bigrams)
        repeated = sum(1 for c in counts.values() if c > 1)
        return float(repeated / len(counts)) if counts else 0.0

    pitch_list = pitches.tolist()
    pitch_bigram_rep = _repetition_ratio(pitch_list)

    # IOI bigrams (quantized to 16th grid for fair comparison)
    if len(iois) > 0 and sixteenth > 0:
        q_iois = np.round(iois / sixteenth).astype(int).tolist()
        rhythm_bigram_rep = _repetition_ratio(q_iois)
        # Combined: (pitch, IOI) pairs
        combined_seq = list(zip(pitch_list[:-1], q_iois))
        combined_bigrams = [tuple(combined_seq[i:i+2]) for i in range(len(combined_seq) - 1)]
        combined_counts = Counter(combined_bigrams)
        combined_repeated = sum(1 for c in combined_counts.values() if c > 1)
        combined_rep = float(combined_repeated / len(combined_counts)) if combined_counts else 0.0
    else:
        rhythm_bigram_rep = 0.0
        combined_rep = 0.0

    return MelodyProfile(
        pitch_range=pitch_range,
        pitch_min=pitch_min,
        pitch_max=pitch_max,
        pitch_mean=pitch_mean,
        pitch_std=pitch_std,
        note_count=n,
        step_ratio=step_ratio,
        leap_ratio=leap_ratio,
        mean_abs_interval=mean_abs_interval,
        direction_change_ratio=direction_change_ratio,
        pitch_class_entropy=pitch_class_entropy,
        pitch_transition_entropy=pitch_transition_entropy,
        rhythm_entropy=rhythm_entropy,
        rhythm_density=rhythm_density,
        duration_seconds=total_duration,
        tonal_clarity=tonal_clarity,
        estimated_key=estimated_key,
        chromaticism=chromaticism,
        # Medium tier
        mean_run_length=mean_run_length,
        longest_run=longest_run,
        contour_direction_bias=contour_direction_bias,
        best_mode=best_mode,
        best_mode_display=best_mode_display,
        mode_coverage=mode_coverage,
        mode_clarity=mode_clarity,
        duration_cv=duration_cv,
        duration_range_ratio=duration_range_ratio,
        pitch_bigram_rep=pitch_bigram_rep,
        rhythm_bigram_rep=rhythm_bigram_rep,
        combined_rep=combined_rep,
    )


# ═══════════════════════════════════════════════════════════════
# MIDI convenience
# ═══════════════════════════════════════════════════════════════

def from_midi(
    pm: pretty_midi.PrettyMIDI,
    voice: int = 0,
    bpm: float = 120.0,
) -> MelodyProfile:
    """
    Compute melody profile from a PrettyMIDI instrument track.

    Args:
        pm: PrettyMIDI object
        voice: instrument index (0 = first track)
        bpm: tempo
    """
    if voice >= len(pm.instruments):
        raise ValueError(f"Voice {voice} not found (only {len(pm.instruments)} instruments)")

    inst = pm.instruments[voice]
    notes = sorted(inst.notes, key=lambda n: n.start)

    if len(notes) < 2:
        raise ValueError(f"Voice {voice} has only {len(notes)} notes (need ≥ 2)")

    pitches = [n.pitch for n in notes]
    onsets = [n.start for n in notes]
    durations = [n.end - n.start for n in notes]

    return compute_melody_profile(pitches, onsets, durations, bpm=bpm)


def from_midi_all_voices(
    pm: pretty_midi.PrettyMIDI,
    bpm: float = 120.0,
) -> dict[str, MelodyProfile]:
    """Compute melody profiles for all voices in a PrettyMIDI."""
    profiles = {}
    for i, inst in enumerate(pm.instruments):
        name = inst.name or f"voice_{i}"
        notes = sorted(inst.notes, key=lambda n: n.start)
        if len(notes) >= 2:
            pitches = [n.pitch for n in notes]
            onsets = [n.start for n in notes]
            durations = [n.end - n.start for n in notes]
            profiles[name] = compute_melody_profile(pitches, onsets, durations, bpm=bpm)
    return profiles


# ═══════════════════════════════════════════════════════════════
# Human-readable summary
# ═══════════════════════════════════════════════════════════════

def summarize(profile: MelodyProfile, genre: Optional[str] = None) -> str:
    """Human-readable summary of a melody profile."""
    lines = [
        "═══ Melody Profile ═══",
        "",
        f"  Notes: {profile.note_count}  Duration: {profile.duration_seconds:.1f}s",
        "",
        "── Dimension 1: Pitch Range & Tessitura ──",
        f"  Range: {profile.pitch_range} semitones ({profile.pitch_min} → {profile.pitch_max})",
        f"  Mean: {profile.pitch_mean:.1f}  Std: {profile.pitch_std:.1f}",
        "",
        "── Dimension 2: Interval Distribution ──",
        f"  Step ratio (≤2st): {profile.step_ratio:.3f}",
        f"  Leap ratio (>7st): {profile.leap_ratio:.3f}",
        f"  Mean |interval|: {profile.mean_abs_interval:.2f} semitones",
        f"  Direction changes: {profile.direction_change_ratio:.3f}",
        "",
        "── Dimension 3: Pitch Entropy ──",
        f"  Pitch class H: {profile.pitch_class_entropy:.3f} bits",
        f"  Transition H:  {profile.pitch_transition_entropy:.3f} bits",
        "",
        "── Dimension 4: Rhythmic Entropy ──",
        f"  IOI entropy: {profile.rhythm_entropy:.3f} bits",
        "",
        "── Dimension 5: Rhythmic Density ──",
        f"  Density: {profile.rhythm_density:.2f} notes/beat",
        "",
        "── Dimension 6: Tonal Clarity ──",
        f"  Key: {profile.estimated_key} (clarity: {profile.tonal_clarity:.3f})",
        f"  Chromaticism: {profile.chromaticism:.3f}",
        "",
        "── Dimension 7: Contour Shape ──",
        f"  Mean run length: {profile.mean_run_length:.2f} (higher = more sustained direction)",
        f"  Longest run: {profile.longest_run}",
        f"  Direction bias: {profile.contour_direction_bias:+.3f} (+asc / -desc)",
        "",
        "── Dimension 8: Mode/Scale ──",
        f"  Best fit: {profile.best_mode_display}",
        f"  Coverage: {profile.mode_coverage:.3f}  Clarity: {profile.mode_clarity:.3f}",
        "",
        "── Dimension 9: Duration Variance ──",
        f"  CV: {profile.duration_cv:.3f} (0=uniform, higher=varied)",
        f"  Range ratio: {profile.duration_range_ratio:.3f}",
        "",
        "── Dimension 10: Repetition ──",
        f"  Pitch bigram rep: {profile.pitch_bigram_rep:.3f}",
        f"  Rhythm bigram rep: {profile.rhythm_bigram_rep:.3f}",
        f"  Combined rep: {profile.combined_rep:.3f}",
    ]

    if genre:
        lines.append("")
        lines.append(f"── Genre Fit: {genre} ──")
        fit = profile.genre_fit(genre)
        for metric, assessment in fit.items():
            lines.append(f"  {metric}: {assessment}")

    return "\n".join(lines)

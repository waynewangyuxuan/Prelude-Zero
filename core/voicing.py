"""
Vector-based voicing engine.

Core idea from Tymoczko's Geometry of Music:
  - Chord = point in Z^n
  - Voice leading = displacement vector d = v2 - v1
  - Good voice leading = min ||d|| subject to constraints
  - Parallel fifths/octaves = forbidden directions in displacement space

Replaces ad-hoc voicing with exhaustive search over all valid voicings.
"""
import numpy as np
from itertools import product as cartesian_product
from music21 import roman, key, pitch


# ── Interval constants (mod 12) ──
PERFECT_FIFTH = 7
PERFECT_OCTAVE = 0  # mod 12

# ── Default ranges (MIDI note numbers) ──
UPPER_LOW = 55   # G3 — keep upper voices in a musical range
UPPER_HIGH = 79  # G5


# ═══════════════════════════════════════════════════════════════
# Section 1: Enumeration — generate all possible voicings
# ═══════════════════════════════════════════════════════════════

def _pc_to_midi_options(pc: int, low: int, high: int) -> list[int]:
    """All MIDI note numbers for a pitch class within [low, high]."""
    options = []
    # Start from the lowest occurrence
    midi = low + ((pc - low) % 12)
    while midi <= high:
        options.append(midi)
        midi += 12
    return options


def enumerate_voicings(pitch_classes: list[int],
                       low: int = UPPER_LOW,
                       high: int = UPPER_HIGH) -> list[tuple[int, ...]]:
    """
    Generate all possible voicings of a set of pitch classes.

    Each pitch class → exactly one MIDI note in [low, high].
    Returns sorted tuples (ascending = no voice crossing by construction).
    Deduplicates.
    """
    options = [_pc_to_midi_options(pc, low, high) for pc in pitch_classes]

    # Filter out pitch classes with no options in range
    valid_options = [o for o in options if len(o) > 0]
    if len(valid_options) < len(pitch_classes):
        # Some pitch classes can't be placed — widen range and retry
        return enumerate_voicings(pitch_classes, low - 12, high + 12)

    voicings = set()
    for combo in cartesian_product(*options):
        v = tuple(sorted(combo))
        # No duplicate MIDI notes
        if len(set(v)) == len(v):
            voicings.add(v)

    return list(voicings)


# ═══════════════════════════════════════════════════════════════
# Section 2: Constraints — pure vector math, no music21
# ═══════════════════════════════════════════════════════════════

def has_parallels(v1: np.ndarray, v2: np.ndarray) -> bool:
    """
    Check for parallel fifths or octaves between two voicings.

    Parallel motion = two voices move by the same displacement.
    Forbidden when the interval between them is a perfect 5th or octave.

    Math:
      d = v2 - v1
      For voices i, j: if d[i] == d[j] and d[i] != 0,
        and |v1[j] - v1[i]| mod 12 ∈ {0, 7} → parallel
    """
    if len(v1) != len(v2):
        return False  # can't check with different voice counts

    d = v2 - v1
    n = len(v1)

    for i in range(n):
        for j in range(i + 1, n):
            if d[i] == d[j] and d[i] != 0:
                interval = abs(int(v1[j]) - int(v1[i])) % 12
                if interval in (PERFECT_OCTAVE, PERFECT_FIFTH):
                    return True
    return False


def parallels_detail(v1: np.ndarray, v2: np.ndarray) -> list[str]:
    """Like has_parallels but returns detailed descriptions."""
    if len(v1) != len(v2):
        return []

    d = v2 - v1
    n = len(v1)
    issues = []

    for i in range(n):
        for j in range(i + 1, n):
            if d[i] == d[j] and d[i] != 0:
                interval = abs(int(v1[j]) - int(v1[i])) % 12
                if interval == PERFECT_FIFTH:
                    issues.append(
                        f"∥5th voices {i},{j}: "
                        f"{v1[i]}→{v2[i]}, {v1[j]}→{v2[j]}, d={d[i]}"
                    )
                elif interval == PERFECT_OCTAVE:
                    issues.append(
                        f"∥8ve voices {i},{j}: "
                        f"{v1[i]}→{v2[i]}, {v1[j]}→{v2[j]}, d={d[i]}"
                    )
    return issues


def spacing_ok(voicing: tuple | np.ndarray, max_gap: int = 12) -> bool:
    """Adjacent upper voices within max_gap semitones."""
    v = np.asarray(voicing)
    if len(v) < 2:
        return True
    gaps = np.diff(v)
    return bool(np.all(gaps <= max_gap))


def voices_above_bass(voicing: tuple | np.ndarray, bass: int) -> bool:
    """All upper voices must be above the bass."""
    return all(n > bass for n in voicing)


# ═══════════════════════════════════════════════════════════════
# Section 3: Optimization — find the best voicing
# ═══════════════════════════════════════════════════════════════

def find_best_voicing(
    pitch_classes: list[int],
    bass_midi: int,
    prev_upper: np.ndarray | None = None,
    prev_bass: int | None = None,
    low: int = UPPER_LOW,
    high: int = UPPER_HIGH,
    max_spacing: int = 12,
) -> np.ndarray:
    """
    Find the optimal voicing for upper voices via exhaustive search.

    Algorithm:
      1. Enumerate all voicings of pitch_classes in [low, high]
      2. Filter: above bass, spacing OK
      3. If prev exists: filter out parallel 5ths/8ves (check FULL chord
         including bass, not just upper voices)
      4. Score remaining by L1 distance to prev_upper (or compactness if no prev)
      5. Return the best

    Args:
        pitch_classes: list of pitch classes (0-11) for upper voices
        bass_midi: MIDI note number of the bass
        prev_upper: previous voicing as numpy array (or None for first chord)
        prev_bass: previous bass MIDI note (needed for full-chord parallel check)
        low, high: MIDI range for upper voices
        max_spacing: max semitones between adjacent voices

    Returns:
        numpy array of MIDI notes, sorted ascending
    """
    effective_low = max(low, bass_midi + 1)

    # Step 1: enumerate
    candidates = enumerate_voicings(pitch_classes, effective_low, high)

    if not candidates:
        # Emergency fallback
        mid = (effective_low + high) // 2
        fallback = sorted(mid + ((pc - mid % 12) % 12) for pc in pitch_classes)
        return np.array(fallback)

    # Step 2: hard filters
    valid = [
        c for c in candidates
        if spacing_ok(c, max_spacing) and voices_above_bass(c, bass_midi)
    ]

    # If too restrictive, relax spacing
    if not valid:
        valid = [c for c in candidates if voices_above_bass(c, bass_midi)]
    if not valid:
        valid = candidates

    # Step 3: filter parallels — check FULL chord (bass + upper)
    # This catches parallels between bass and upper voices, not just upper-upper
    if prev_upper is not None and len(prev_upper) > 0:
        prev_full = np.array(sorted(
            [prev_bass] + prev_upper.tolist()
        )) if prev_bass is not None else prev_upper

        def _full_chord(c):
            return np.array(sorted([bass_midi] + list(c)))

        no_parallels = [
            c for c in valid
            if len(_full_chord(c)) != len(prev_full)  # can't check → allow
            or not has_parallels(prev_full, _full_chord(c))
        ]
        if no_parallels:
            valid = no_parallels
        # else: all options have parallels — keep all, pick closest

    # Step 4: score and pick
    if prev_upper is not None and len(prev_upper) > 0:
        def score(c):
            v = np.array(c)
            if len(v) == len(prev_upper):
                # Primary: L1 distance (total voice movement)
                l1 = np.sum(np.abs(v - prev_upper))
                # Secondary: prefer compact voicing
                span = v[-1] - v[0]
                return l1 * 10 + span
            else:
                # Different voice count — score by compactness
                return (v[-1] - v[0]) * 10
    else:
        # First chord — pick compact voicing in the center of range
        mid = (effective_low + high) / 2.0

        def score(c):
            v = np.array(c, dtype=float)
            center_dist = abs(np.mean(v) - mid)
            span = v[-1] - v[0]
            return center_dist + span * 0.5

    best = min(valid, key=score)
    return np.array(best)


# ═══════════════════════════════════════════════════════════════
# Section 4: Full progression voice leading
# ═══════════════════════════════════════════════════════════════

def _ensure_n_pcs(pcs: list[int], n: int, bass_pc: int,
                   all_pcs: list[int]) -> list[int]:
    """
    Ensure exactly n pitch classes for upper voices.

    Strategy:
      - If too many: drop doublings, prefer keeping chord tones that
        differ from bass
      - If too few: double the root (most common), then fifth, then third
    """
    if len(pcs) == n:
        return pcs

    if len(pcs) > n:
        # Prefer pitch classes that are not the bass
        non_bass = [pc for pc in pcs if pc != bass_pc]
        if len(non_bass) >= n:
            return non_bass[:n]
        return pcs[:n]

    # Too few — need to add doublings
    result = list(pcs)
    # Doubling priority: root (most common in SATB), then 5th, then 3rd
    # all_pcs[0] is typically the root
    doubling_order = all_pcs  # root first, then other chord tones
    idx = 0
    while len(result) < n:
        result.append(doubling_order[idx % len(doubling_order)])
        idx += 1
    return result


def voice_lead_progression(
    progression: list[tuple[str, str]],
    key_str: str = "C",
    bass_octave: int = 3,
    n_upper: int = 3,
    upper_range: tuple[int, int] = (UPPER_LOW, UPPER_HIGH),
    max_spacing: int = 12,
) -> list[dict]:
    """
    Apply optimal voice leading to an entire chord progression.

    Always produces exactly n_upper upper voices (default 3 → SATB texture).
    When a chord has fewer pitch classes, doubles appropriately.
    When it has more, selects the most important ones.

    Args:
        progression: list of (roman_numeral, bass_note_name) tuples
            e.g. [("I", "C"), ("V7", "G"), ("I", "C")]
        key_str: key signature
        bass_octave: octave for bass notes
        n_upper: number of upper voices (default 3 for SATB)
        upper_range: (low, high) MIDI range for upper voices
        max_spacing: max gap between adjacent upper voices

    Returns:
        list of {"roman": str, "bass": int, "upper": list[int],
                 "full_chord": list[int]} dicts
    """
    k = key.Key(key_str)
    result = []
    prev_upper = None
    prev_bass = None

    for roman_str, bass_note in progression:
        # Roman numeral → pitch classes
        rn = roman.RomanNumeral(roman_str, k)
        all_pcs = [p.midi % 12 for p in rn.pitches]  # ordered by chord structure
        unique_pcs = sorted(set(all_pcs))

        # Bass
        bass_p = pitch.Pitch(bass_note)
        bass_p.octave = bass_octave
        bass_midi = bass_p.midi
        bass_pc = bass_midi % 12

        # Build upper voice pitch classes:
        # 1. Remove bass PC if we have enough other PCs
        upper_pcs = [pc for pc in unique_pcs if pc != bass_pc]
        if len(upper_pcs) < 2:
            upper_pcs = unique_pcs  # keep all including bass PC

        # 2. Ensure exactly n_upper pitch classes
        upper_pcs = _ensure_n_pcs(upper_pcs, n_upper, bass_pc, all_pcs)

        # Find optimal voicing (now checks full chord including bass)
        upper = find_best_voicing(
            upper_pcs, bass_midi, prev_upper,
            prev_bass=prev_bass,
            low=upper_range[0], high=upper_range[1],
            max_spacing=max_spacing,
        )

        full = sorted([bass_midi] + upper.tolist())

        result.append({
            "roman": roman_str,
            "bass": bass_midi,
            "upper": upper.tolist(),
            "full_chord": full,
        })
        prev_upper = upper
        prev_bass = bass_midi

    return result


def validate_voice_led_progression(measures: list[dict],
                                    verbose: bool = False) -> dict:
    """
    Validate a voice-led progression for parallel 5ths/8ves.
    Works on output of voice_lead_progression().

    Returns:
        {"ok": bool, "errors": list[str], "stats": dict}
    """
    errors = []
    total_transitions = 0
    total_movement = 0

    for i in range(len(measures) - 1):
        m1 = measures[i]
        m2 = measures[i + 1]

        # Check full chord (bass + upper) for parallels
        v1 = np.array(m1["full_chord"])
        v2 = np.array(m2["full_chord"])

        if len(v1) == len(v2):
            total_transitions += 1
            total_movement += int(np.sum(np.abs(v2 - v1)))

            issues = parallels_detail(v1, v2)
            for issue in issues:
                errors.append(f"m.{i+1}→{i+2}: {issue}")

    avg_movement = total_movement / max(total_transitions, 1)

    result = {
        "ok": len(errors) == 0,
        "errors": errors,
        "stats": {
            "transitions": total_transitions,
            "total_movement": total_movement,
            "avg_movement_per_transition": round(avg_movement, 1),
        }
    }

    if verbose:
        if errors:
            print(f"ERRORS ({len(errors)}):")
            for e in errors:
                print(f"  ✗ {e}")
        else:
            print("  ✓ No parallel 5ths or 8ves")
        print(f"  Movement stats: avg {avg_movement:.1f} semitones/transition, "
              f"total {total_movement} over {total_transitions} transitions")

    return result

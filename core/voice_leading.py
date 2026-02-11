"""
Voice leading validation using music21.
Checks for parallel fifths/octaves, voice crossing, and other rules.
"""
from music21 import voiceLeading, pitch, note, chord


def check_parallel_fifths_octaves(chord1_pitches: list[int],
                                   chord2_pitches: list[int]) -> list[str]:
    """
    Check for parallel fifths and octaves between two chords.

    Args:
        chord1_pitches: MIDI note numbers of first chord (sorted low to high)
        chord2_pitches: MIDI note numbers of second chord (sorted low to high)

    Returns:
        List of warning strings. Empty = no issues.
    """
    warnings = []

    # Need same number of voices
    n = min(len(chord1_pitches), len(chord2_pitches))
    if n < 2:
        return warnings

    p1 = [pitch.Pitch(midi=m) for m in chord1_pitches[:n]]
    p2 = [pitch.Pitch(midi=m) for m in chord2_pitches[:n]]

    # Check every pair of voices
    for i in range(n):
        for j in range(i + 1, n):
            try:
                vlq = voiceLeading.VoiceLeadingQuartet(
                    p1[i], p2[i], p1[j], p2[j]
                )
                if vlq.parallelFifth():
                    warnings.append(
                        f"Parallel 5th: voices {i},{j} "
                        f"({p1[i].nameWithOctave}-{p1[j].nameWithOctave} → "
                        f"{p2[i].nameWithOctave}-{p2[j].nameWithOctave})"
                    )
                if vlq.parallelOctave():
                    warnings.append(
                        f"Parallel 8ve: voices {i},{j} "
                        f"({p1[i].nameWithOctave}-{p1[j].nameWithOctave} → "
                        f"{p2[i].nameWithOctave}-{p2[j].nameWithOctave})"
                    )
            except Exception:
                pass  # skip if voice leading check fails

    return warnings


def check_voice_crossing(chord_pitches: list[int]) -> list[str]:
    """Check that voices don't cross (each voice is higher than the one below)."""
    warnings = []
    for i in range(len(chord_pitches) - 1):
        if chord_pitches[i] >= chord_pitches[i + 1]:
            warnings.append(
                f"Voice crossing: voice {i} ({chord_pitches[i]}) "
                f">= voice {i+1} ({chord_pitches[i+1]})"
            )
    return warnings


def check_spacing(chord_pitches: list[int], max_gap: int = 12) -> list[str]:
    """Check that adjacent upper voices are within an octave of each other."""
    warnings = []
    # Skip bass-to-next check (bass can be far from upper voices)
    for i in range(1, len(chord_pitches) - 1):
        gap = chord_pitches[i + 1] - chord_pitches[i]
        if gap > max_gap:
            warnings.append(
                f"Wide spacing: voices {i},{i+1} are {gap} semitones apart "
                f"(max {max_gap})"
            )
    return warnings


def validate_progression(chords: list[list[int]],
                         verbose: bool = False) -> dict:
    """
    Validate an entire chord progression.

    Args:
        chords: list of chords, each chord is a list of MIDI note numbers
        verbose: print details

    Returns:
        {"ok": bool, "errors": list[str], "warnings": list[str]}
    """
    errors = []
    warnings = []

    for i, ch in enumerate(chords):
        # Check voice crossing
        vc = check_voice_crossing(ch)
        if vc:
            warnings.extend([f"m.{i+1}: {w}" for w in vc])

        # Check spacing
        sp = check_spacing(ch)
        if sp:
            warnings.extend([f"m.{i+1}: {w}" for w in sp])

        # Check parallels with next chord
        if i < len(chords) - 1:
            par = check_parallel_fifths_octaves(ch, chords[i + 1])
            if par:
                errors.extend([f"m.{i+1}→{i+2}: {w}" for w in par])

    result = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

    if verbose:
        if errors:
            print(f"ERRORS ({len(errors)}):")
            for e in errors:
                print(f"  ✗ {e}")
        if warnings:
            print(f"WARNINGS ({len(warnings)}):")
            for w in warnings:
                print(f"  ⚠ {w}")
        if not errors and not warnings:
            print("  ✓ All checks passed")

    return result

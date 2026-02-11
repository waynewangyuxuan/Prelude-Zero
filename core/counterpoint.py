"""
Counterpoint rule engine for fugue generation.

Checks two-voice counterpoint (note-against-note, first species extended)
against standard Baroque rules. Does NOT generate — only validates.

The principle: every rule is a pure function
    (voice1_notes, voice2_notes) → list[Issue]

This makes rules composable, testable, and independent.
"""
import numpy as np
from dataclasses import dataclass
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════

class Severity(Enum):
    ERROR = "error"       # Hard violation (parallel 5ths, etc.)
    WARNING = "warning"   # Stylistic concern
    INFO = "info"         # Observation

@dataclass
class Issue:
    severity: Severity
    beat: int          # position (0-indexed)
    rule: str          # which rule flagged this
    detail: str        # human-readable description

@dataclass
class Note:
    """A note with pitch and duration."""
    midi: int          # MIDI note number
    onset: float       # beat position (0-based)
    duration: float    # in beats

    @property
    def pc(self) -> int:
        return self.midi % 12

    @property
    def name(self) -> str:
        names = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]
        return names[self.midi % 12] + str(self.midi // 12 - 1)


# ═══════════════════════════════════════════════════════════════
# Interval classification
# ═══════════════════════════════════════════════════════════════

# Perfect consonances
PERFECT_UNISON = 0
PERFECT_FIFTH = 7
PERFECT_OCTAVE = 0  # mod 12

# Imperfect consonances
CONSONANT_INTERVALS = {0, 3, 4, 7, 8, 9}  # P1, m3, M3, P5, m6, M6
PERFECT_INTERVALS = {0, 7}                  # P1/P8, P5

# Dissonances
DISSONANT_INTERVALS = {1, 2, 5, 6, 10, 11}  # m2, M2, P4, tritone, m7, M7


def interval_class(midi1: int, midi2: int) -> int:
    """Interval in semitones mod 12 (undirected)."""
    return abs(midi1 - midi2) % 12


def is_consonant(midi1: int, midi2: int) -> bool:
    return interval_class(midi1, midi2) in CONSONANT_INTERVALS


def is_perfect(midi1: int, midi2: int) -> bool:
    return interval_class(midi1, midi2) in PERFECT_INTERVALS


# ═══════════════════════════════════════════════════════════════
# Rule: No parallel perfect intervals
# ═══════════════════════════════════════════════════════════════

def check_parallels(v1: list[Note], v2: list[Note]) -> list[Issue]:
    """
    Detect parallel fifths and octaves between two voices.

    Two voices moving in parallel with a perfect interval (P5, P8)
    between them is forbidden in strict counterpoint.
    """
    issues = []
    pairs = _align_simultaneous(v1, v2)

    for i in range(len(pairs) - 1):
        (a1, a2), (b1, b2) = pairs[i], pairs[i + 1]
        if a1 is None or a2 is None or b1 is None or b2 is None:
            continue

        int1 = interval_class(a1.midi, a2.midi)
        int2 = interval_class(b1.midi, b2.midi)

        # Both are perfect AND both voices move in same direction
        if int1 in PERFECT_INTERVALS and int2 in PERFECT_INTERVALS and int1 == int2:
            d1 = b1.midi - a1.midi
            d2 = b2.midi - a2.midi
            if d1 != 0 and d2 != 0 and np.sign(d1) == np.sign(d2):
                name = "8ve" if int1 == 0 else "5th"
                issues.append(Issue(
                    Severity.ERROR, i,
                    "parallel_perfect",
                    f"Parallel {name}: {a1.name},{a2.name} → {b1.name},{b2.name}"
                ))

    return issues


# ═══════════════════════════════════════════════════════════════
# Rule: No direct (hidden) fifths/octaves
# ═══════════════════════════════════════════════════════════════

def check_direct_intervals(v1: list[Note], v2: list[Note]) -> list[Issue]:
    """
    Detect direct (hidden) fifths and octaves.

    Two voices arriving at a perfect interval by similar motion
    (both moving in the same direction) is suspicious.
    In strict style: only allowed if the upper voice moves by step.
    """
    issues = []
    pairs = _align_simultaneous(v1, v2)

    for i in range(len(pairs) - 1):
        (a1, a2), (b1, b2) = pairs[i], pairs[i + 1]
        if a1 is None or a2 is None or b1 is None or b2 is None:
            continue

        int2 = interval_class(b1.midi, b2.midi)
        d1 = b1.midi - a1.midi
        d2 = b2.midi - a2.midi

        if int2 in PERFECT_INTERVALS and d1 != 0 and d2 != 0:
            if np.sign(d1) == np.sign(d2):  # similar motion
                upper_step = min(abs(d1), abs(d2)) <= 2
                if not upper_step:
                    name = "8ve" if int2 == 0 else "5th"
                    issues.append(Issue(
                        Severity.WARNING, i,
                        "direct_perfect",
                        f"Direct {name}: → {b1.name},{b2.name} (both leap)"
                    ))

    return issues


# ═══════════════════════════════════════════════════════════════
# Rule: Consonance on strong beats
# ═══════════════════════════════════════════════════════════════

def check_consonance(v1: list[Note], v2: list[Note],
                     strong_beats: set = None) -> list[Issue]:
    """
    Dissonance on strong beats must be prepared and resolved
    (suspension, passing tone, etc.).

    Simplified check: flag any dissonance on a strong beat.
    """
    if strong_beats is None:
        strong_beats = {0, 2}  # beats 1 and 3 in 4/4

    issues = []
    pairs = _align_simultaneous(v1, v2)

    for i, (n1, n2) in enumerate(pairs):
        if n1 is None or n2 is None:
            continue
        beat_in_bar = n1.onset % 4
        if beat_in_bar in strong_beats:
            if not is_consonant(n1.midi, n2.midi):
                ic = interval_class(n1.midi, n2.midi)
                issues.append(Issue(
                    Severity.WARNING, i,
                    "dissonance_on_strong_beat",
                    f"Dissonance (ic={ic}) on strong beat: "
                    f"{n1.name} vs {n2.name} at beat {n1.onset:.1f}"
                ))

    return issues


# ═══════════════════════════════════════════════════════════════
# Rule: Voice crossing
# ═══════════════════════════════════════════════════════════════

def check_crossing(upper: list[Note], lower: list[Note]) -> list[Issue]:
    """
    Flag when the 'upper' voice goes below the 'lower' voice.
    Not forbidden in Bach but worth tracking.
    """
    issues = []
    pairs = _align_simultaneous(upper, lower)

    for i, (u, l) in enumerate(pairs):
        if u is None or l is None:
            continue
        if u.midi < l.midi:
            issues.append(Issue(
                Severity.INFO, i,
                "voice_crossing",
                f"Upper ({u.name}) below lower ({l.name}) at beat {u.onset:.1f}"
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# Rule: Melodic intervals (per voice)
# ═══════════════════════════════════════════════════════════════

def check_melody(voice: list[Note]) -> list[Issue]:
    """
    Check melodic intervals within a single voice.

    Rules:
    - Augmented intervals forbidden (aug 2nd, aug 4th)
    - Leaps > octave rare and flagged
    - Tritone outline over several notes flagged
    - After a leap, prefer stepwise return (gap-fill)
    """
    issues = []

    for i in range(len(voice) - 1):
        interval = abs(voice[i+1].midi - voice[i].midi)

        # Augmented/diminished leaps
        if interval == 6:  # tritone
            issues.append(Issue(
                Severity.WARNING, i,
                "melodic_tritone",
                f"Tritone leap: {voice[i].name} → {voice[i+1].name}"
            ))
        elif interval > 12:  # > octave
            issues.append(Issue(
                Severity.WARNING, i,
                "melodic_large_leap",
                f"Leap > octave ({interval} st): "
                f"{voice[i].name} → {voice[i+1].name}"
            ))
        elif interval in (10, 11):  # m7, M7
            issues.append(Issue(
                Severity.WARNING, i,
                "melodic_seventh",
                f"Seventh leap ({interval} st): "
                f"{voice[i].name} → {voice[i+1].name}"
            ))

    # Gap-fill check: after a leap (>4 semitones), next note should
    # move in opposite direction by step
    for i in range(1, len(voice) - 1):
        prev_interval = voice[i].midi - voice[i-1].midi
        next_interval = voice[i+1].midi - voice[i].midi
        if abs(prev_interval) > 4:  # leap
            if next_interval != 0 and np.sign(next_interval) == np.sign(prev_interval):
                issues.append(Issue(
                    Severity.INFO, i,
                    "no_gap_fill",
                    f"Leap ({prev_interval:+d}) not filled: "
                    f"{voice[i-1].name}→{voice[i].name}→{voice[i+1].name}"
                ))

    return issues


# ═══════════════════════════════════════════════════════════════
# Composite validation
# ═══════════════════════════════════════════════════════════════

def validate_two_voices(v1: list[Note], v2: list[Note],
                        verbose: bool = False) -> dict:
    """
    Run all counterpoint rules on two voices.

    Returns dict with categorized issues and a summary.
    """
    all_issues = []
    all_issues.extend(check_parallels(v1, v2))
    all_issues.extend(check_direct_intervals(v1, v2))
    all_issues.extend(check_consonance(v1, v2))
    all_issues.extend(check_crossing(v1, v2))
    all_issues.extend(check_melody(v1))
    all_issues.extend(check_melody(v2))

    errors = [i for i in all_issues if i.severity == Severity.ERROR]
    warnings = [i for i in all_issues if i.severity == Severity.WARNING]
    infos = [i for i in all_issues if i.severity == Severity.INFO]

    result = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "total_issues": len(all_issues),
    }

    if verbose:
        print(f"\n── Counterpoint Validation ──")
        print(f"  Errors:   {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        print(f"  Infos:    {len(infos)}")
        if errors:
            for e in errors:
                print(f"    ✗ [{e.rule}] beat {e.beat}: {e.detail}")
        if warnings:
            for w in warnings:
                print(f"    ⚠ [{w.rule}] beat {w.beat}: {w.detail}")

    return result


# ═══════════════════════════════════════════════════════════════
# Helper: align simultaneous notes
# ═══════════════════════════════════════════════════════════════

def _align_simultaneous(v1: list[Note], v2: list[Note]) -> list[tuple]:
    """
    Align two voices by onset time.
    Returns list of (note_from_v1, note_from_v2) pairs.
    None if one voice has no note at that onset.
    """
    # Collect all unique onset times
    onsets = sorted(set(n.onset for n in v1) | set(n.onset for n in v2))

    # Build lookup: onset → note (last note at that onset)
    v1_map = {n.onset: n for n in v1}
    v2_map = {n.onset: n for n in v2}

    pairs = []
    last_v1, last_v2 = None, None
    for t in onsets:
        n1 = v1_map.get(t, last_v1)
        n2 = v2_map.get(t, last_v2)
        pairs.append((n1, n2))
        if n1 is not None:
            last_v1 = n1
        if n2 is not None:
            last_v2 = n2

    return pairs

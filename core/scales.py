"""
Scale/Mode engine — the pitch vocabulary layer.

Every melody and harmony operation needs to know "what notes are legal."
This module provides that vocabulary as a reusable, transposable system.

Core concepts:
  - A Scale is a set of pitch classes (0-11) + a root
  - snap() finds the nearest scale tone for any MIDI pitch
  - step() moves up/down by scale degrees (not semitones)
  - chromatic_neighbors() finds leading-tone-like tensions

All modes from Ionian to Locrian, plus pentatonics and blues.
"""

from dataclasses import dataclass
from functools import lru_cache


# ═══════════════════════════════════════════════════════════════
# Scale Templates — intervals from root (in semitones)
# ═══════════════════════════════════════════════════════════════

TEMPLATES: dict[str, tuple[int, ...]] = {
    # Church modes
    'ionian':     (0, 2, 4, 5, 7, 9, 11),
    'dorian':     (0, 2, 3, 5, 7, 9, 10),
    'phrygian':   (0, 1, 3, 5, 7, 8, 10),
    'lydian':     (0, 2, 4, 6, 7, 9, 11),
    'mixolydian': (0, 2, 4, 5, 7, 9, 10),
    'aeolian':    (0, 2, 3, 5, 7, 8, 10),
    'locrian':    (0, 1, 3, 5, 6, 8, 10),

    # Common aliases
    'major':         (0, 2, 4, 5, 7, 9, 11),
    'natural_minor': (0, 2, 3, 5, 7, 8, 10),
    'harmonic_minor': (0, 2, 3, 5, 7, 8, 11),
    'melodic_minor':  (0, 2, 3, 5, 7, 9, 11),

    # Pentatonics
    'pentatonic_major': (0, 2, 4, 7, 9),
    'pentatonic_minor': (0, 3, 5, 7, 10),

    # Blues
    'blues': (0, 3, 5, 6, 7, 10),

    # Symmetric
    'whole_tone':  (0, 2, 4, 6, 8, 10),
    'diminished':  (0, 2, 3, 5, 6, 8, 9, 11),  # half-whole
    'chromatic':   tuple(range(12)),
}

# Note names for display
NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


# ═══════════════════════════════════════════════════════════════
# Scale class
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Scale:
    """
    A musical scale: root pitch class + interval template.

    The root is a pitch class (0=C, 1=C#, ..., 11=B).
    The template defines which intervals above the root are "in the scale."
    """
    root: int           # 0-11
    template_name: str  # key into TEMPLATES
    _pcs: tuple = None  # cached pitch classes (set at creation)

    def __post_init__(self):
        template = TEMPLATES[self.template_name]
        pcs = tuple(sorted((self.root + iv) % 12 for iv in template))
        object.__setattr__(self, '_pcs', pcs)

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        """The pitch classes in this scale, sorted ascending."""
        return self._pcs

    @property
    def name(self) -> str:
        """Human-readable name like 'E Phrygian' or 'Bb Major'."""
        return f"{NOTE_NAMES[self.root]} {self.template_name.replace('_', ' ').title()}"

    @property
    def degree_count(self) -> int:
        """Number of distinct pitch classes (7 for diatonic, 5 for pentatonic, etc.)."""
        return len(self._pcs)

    # ── Pitch generation ──

    @lru_cache(maxsize=256)
    def pitches(self, lo: int = 21, hi: int = 108) -> tuple[int, ...]:
        """
        All MIDI pitches in this scale within [lo, hi].
        Cached for performance — called frequently during generation.
        """
        result = []
        for midi in range(lo, hi + 1):
            if midi % 12 in self._pcs:
                result.append(midi)
        return tuple(result)

    def contains(self, midi_pitch: int) -> bool:
        """Is this MIDI pitch in the scale?"""
        return midi_pitch % 12 in self._pcs

    # ── Core operations ──

    def snap(self, midi_pitch: int, lo: int = 21, hi: int = 108) -> int:
        """
        Snap a MIDI pitch to the nearest scale tone.
        Ties broken toward the lower pitch.
        """
        pts = self.pitches(lo, hi)
        if not pts:
            return midi_pitch
        # Binary-search-like: find closest
        best = pts[0]
        best_dist = abs(midi_pitch - best)
        for p in pts:
            d = abs(midi_pitch - p)
            if d < best_dist:
                best = p
                best_dist = d
            elif d > best_dist + 12:
                break  # optimization: pitches are sorted
        return best

    def step(self, midi_pitch: int, direction: int, steps: int = 1,
             lo: int = 21, hi: int = 108) -> int:
        """
        Move up or down by `steps` scale degrees from the nearest scale tone.

        Args:
            midi_pitch: starting MIDI pitch (snapped to scale first)
            direction: +1 for ascending, -1 for descending
            steps: how many scale degrees to move
            lo, hi: MIDI range bounds

        Returns:
            The target MIDI pitch after moving.
        """
        pts = self.pitches(lo, hi)
        if not pts:
            return midi_pitch

        # Find current position in the pitch list
        snapped = self.snap(midi_pitch, lo, hi)
        try:
            idx = pts.index(snapped)
        except ValueError:
            idx = min(range(len(pts)), key=lambda i: abs(pts[i] - midi_pitch))

        target_idx = idx + direction * steps
        target_idx = max(0, min(len(pts) - 1, target_idx))
        return pts[target_idx]

    def degree_of(self, midi_pitch: int) -> int | None:
        """
        Which scale degree is this pitch? (0-indexed from root)
        Returns None if not in scale.
        """
        pc = midi_pitch % 12
        if pc not in self._pcs:
            return None
        template = TEMPLATES[self.template_name]
        interval = (pc - self.root) % 12
        if interval in template:
            return template.index(interval)
        return None

    def interval_between(self, p1: int, p2: int) -> int:
        """
        Scale-degree distance between two pitches.
        Positive if p2 > p1 (ascending).
        """
        pts = self.pitches()
        try:
            i1 = pts.index(self.snap(p1))
            i2 = pts.index(self.snap(p2))
            return i2 - i1
        except (ValueError, IndexError):
            return 0

    # ── Chromatic operations ──

    def chromatic_neighbors(self, midi_pitch: int) -> list[int]:
        """
        Find chromatic neighbor tones (non-scale tones ±1 semitone).
        These are the source of "color" and tension.
        """
        neighbors = []
        for delta in [-1, 1]:
            n = midi_pitch + delta
            if not self.contains(n):
                neighbors.append(n)
        return neighbors

    def chromatic_passing(self, p1: int, p2: int) -> int | None:
        """
        If p1 and p2 are a whole step apart (2 semitones),
        return the chromatic passing tone between them.
        """
        if abs(p2 - p1) == 2:
            return (p1 + p2) // 2
        return None

    # ── Transposition ──

    def transpose(self, semitones: int) -> 'Scale':
        """Return a new Scale transposed by the given semitones."""
        new_root = (self.root + semitones) % 12
        return Scale(new_root, self.template_name)

    def relative_mode(self, mode_name: str) -> 'Scale':
        """
        Get the relative mode starting from this scale's root.
        E.g., C Ionian → A Aeolian (relative minor).
        """
        return Scale(self.root, mode_name)

    def parallel_mode(self, mode_name: str) -> 'Scale':
        """Same root, different mode. E.g., C Major → C Phrygian."""
        return Scale(self.root, mode_name)

    # ── Chord generation ──

    def triad(self, degree: int, midi_octave: int = 4) -> list[int]:
        """
        Build a triad on the given scale degree (0-indexed).
        Returns 3 MIDI pitches in the given octave.
        """
        pts = self.pitches()
        base = self.root + 12 * (midi_octave + 1)  # MIDI octave convention
        snapped = self.snap(base)
        try:
            idx = pts.index(snapped)
        except ValueError:
            return [base, base + 4, base + 7]  # fallback major triad

        # Move to the target degree
        idx += degree
        if idx < 0 or idx >= len(pts) - 4:
            idx = max(0, min(len(pts) - 5, idx))

        # Stack thirds: root, +2 degrees, +4 degrees
        return [pts[idx], pts[idx + 2], pts[idx + 4]]

    def seventh(self, degree: int, midi_octave: int = 4) -> list[int]:
        """Build a seventh chord on the given scale degree."""
        pts = self.pitches()
        base = self.root + 12 * (midi_octave + 1)
        snapped = self.snap(base)
        try:
            idx = pts.index(snapped)
        except ValueError:
            return [base, base + 4, base + 7, base + 11]

        idx += degree
        idx = max(0, min(len(pts) - 7, idx))
        return [pts[idx], pts[idx + 2], pts[idx + 4], pts[idx + 6]]


# ═══════════════════════════════════════════════════════════════
# Convenience constructors
# ═══════════════════════════════════════════════════════════════

def from_name(note: str, mode: str = 'major') -> Scale:
    """
    Create a Scale from note name + mode.

    Examples:
        from_name('C', 'major')
        from_name('E', 'phrygian')
        from_name('Bb', 'dorian')
        from_name('A', 'natural_minor')
    """
    # Parse note name to pitch class
    note = note.strip()
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    if len(note) == 1:
        pc = base[note.upper()]
    elif note[1] == '#':
        pc = (base[note[0].upper()] + 1) % 12
    elif note[1] == 'b':
        pc = (base[note[0].upper()] - 1) % 12
    else:
        pc = base[note[0].upper()]

    mode_key = mode.lower().replace(' ', '_')
    if mode_key not in TEMPLATES:
        raise ValueError(f"Unknown mode: {mode}. Available: {list(TEMPLATES.keys())}")

    return Scale(pc, mode_key)


# Common scales as constants
C_MAJOR = Scale(0, 'major')
A_MINOR = Scale(9, 'natural_minor')
E_PHRYGIAN = Scale(4, 'phrygian')
D_DORIAN = Scale(2, 'dorian')
G_MIXOLYDIAN = Scale(7, 'mixolydian')
Bb_MAJOR = Scale(10, 'major')
Eb_MAJOR = Scale(3, 'major')

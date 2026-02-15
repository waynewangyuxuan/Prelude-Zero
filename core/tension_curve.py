"""
Prescriptive tension curve — defines WHERE tension should be, beat by beat.

Unlike tension.py (which measures tension FROM music), this module generates
a target tension curve BEFORE composition. It's the "intent" layer.

Usage:
    form = PieceForm(bpm=76, sections=[
        Section("Intro",    beats=32, tension=0.15),
        Section("Build",    beats=32, tension=0.35),
        Section("Climax",   beats=24, tension=0.80),
        Section("Fade",     beats=24, tension=0.10),
    ])
    curve = form.render()   # → TensionCurve (per-beat array)
    t = curve.at(beat=50)   # → 0.62 (interpolated)

The curve is generic — no style binding. Style comes from how the
orchestrator maps tension values to StyleTarget parameters.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Section:
    """One section of a piece."""
    name: str
    beats: int              # duration in beats
    tension: float          # target tension at peak of section [0, 1]
    transition: str = "smooth"  # "smooth" (cosine), "linear", "sudden"


@dataclass
class TensionCurve:
    """Per-beat tension values with query interface."""
    values: np.ndarray      # tension[i] = tension at beat i
    bpm: float
    section_boundaries: list[tuple[int, str]]  # (beat, name) pairs

    @property
    def total_beats(self) -> int:
        return len(self.values)

    @property
    def duration_seconds(self) -> float:
        return self.total_beats * 60.0 / self.bpm

    def at(self, beat: float) -> float:
        """Get interpolated tension at any beat position."""
        if beat <= 0:
            return float(self.values[0])
        if beat >= self.total_beats - 1:
            return float(self.values[-1])
        lo = int(beat)
        hi = lo + 1
        frac = beat - lo
        return float(self.values[lo] * (1 - frac) + self.values[hi] * frac)

    def section_at(self, beat: float) -> str:
        """Get section name at a given beat."""
        name = self.section_boundaries[0][1] if self.section_boundaries else "Unknown"
        for b, n in self.section_boundaries:
            if beat >= b:
                name = n
            else:
                break
        return name

    def section_range(self, section_name: str) -> tuple[int, int]:
        """Get (start_beat, end_beat) for a named section."""
        start = None
        for i, (b, n) in enumerate(self.section_boundaries):
            if n == section_name:
                start = b
                # End is next section's start or total beats
                if i + 1 < len(self.section_boundaries):
                    return (start, self.section_boundaries[i + 1][0])
                else:
                    return (start, self.total_beats)
        raise KeyError(f"Section '{section_name}' not found")

    def mean_tension(self, start_beat: int, end_beat: int) -> float:
        """Average tension over a beat range."""
        s = max(0, start_beat)
        e = min(self.total_beats, end_beat)
        if s >= e:
            return 0.0
        return float(np.mean(self.values[s:e]))

    def summary(self) -> str:
        lines = [f"Tension Curve: {self.total_beats} beats, "
                 f"{self.duration_seconds:.1f}s @ {self.bpm} BPM"]
        lines.append(f"  Range: [{self.values.min():.2f}, {self.values.max():.2f}]")
        lines.append(f"  Mean:  {self.values.mean():.3f}")
        lines.append("")
        for i, (b, name) in enumerate(self.section_boundaries):
            if i + 1 < len(self.section_boundaries):
                end = self.section_boundaries[i + 1][0]
            else:
                end = self.total_beats
            sec_vals = self.values[b:end]
            lines.append(f"  {name:20s} beats {b:3d}-{end:3d}  "
                         f"tension [{sec_vals.min():.2f}, {sec_vals.max():.2f}]  "
                         f"mean {sec_vals.mean():.3f}")
        return "\n".join(lines)


class PieceForm:
    """
    Defines the large-scale form of a piece as a sequence of sections.
    Renders to a smooth TensionCurve.
    """

    def __init__(self, bpm: float, sections: list[Section]):
        self.bpm = bpm
        self.sections = sections

    @property
    def total_beats(self) -> int:
        return sum(s.beats for s in self.sections)

    @property
    def duration_seconds(self) -> float:
        return self.total_beats * 60.0 / self.bpm

    def render(self) -> TensionCurve:
        """
        Generate a smooth per-beat tension curve.

        Each section holds its target tension at its center, with smooth
        transitions between sections using cosine interpolation (or linear/sudden).
        """
        total = self.total_beats
        values = np.zeros(total)
        boundaries = []

        # First pass: assign each section's center tension
        # We use a "hold in middle, transition at edges" approach
        beat = 0
        section_centers = []  # (center_beat, tension)

        for sec in self.sections:
            boundaries.append((beat, sec.name))
            center = beat + sec.beats // 2
            section_centers.append((center, sec.tension, sec.transition))
            beat += sec.beats

        # Build curve by interpolating between section centers
        # Add boundary points at start and end
        control_points = []
        # Start: hold first section's tension
        control_points.append((0, self.sections[0].tension))
        for center, tension, _ in section_centers:
            control_points.append((center, tension))
        # End: hold last section's tension
        control_points.append((total - 1, self.sections[-1].tension))

        # Interpolate between control points
        for i in range(len(control_points) - 1):
            b0, t0 = control_points[i]
            b1, t1 = control_points[i + 1]

            if b0 == b1:
                continue

            # Determine transition type from the section that ENDS at this transition
            trans_type = "smooth"
            for ci, (_, _, tr) in enumerate(section_centers):
                center_beat = section_centers[ci][0]
                if center_beat == b0 or center_beat == b1:
                    trans_type = tr
                    break

            for b in range(b0, min(b1 + 1, total)):
                frac = (b - b0) / (b1 - b0) if b1 > b0 else 0

                if trans_type == "smooth":
                    # Cosine interpolation (ease in/out)
                    frac = 0.5 * (1 - np.cos(np.pi * frac))
                elif trans_type == "sudden":
                    # Step function at midpoint
                    frac = 0.0 if frac < 0.5 else 1.0
                # else linear: frac stays as-is

                values[b] = t0 + (t1 - t0) * frac

        return TensionCurve(
            values=values,
            bpm=self.bpm,
            section_boundaries=boundaries,
        )


# ═══════════════════════════════════════════════════════════════
# Presets — reusable form templates
# ═══════════════════════════════════════════════════════════════

def long_form_build(bpm: float = 76, total_minutes: float = 3.5) -> PieceForm:
    """
    Long-form build (Pink Floyd / post-rock style):
    Intro → Build → Development → Climax → Fade

    Characteristic: slow build, single peak, gradual decay.
    """
    total_beats = int(total_minutes * bpm)

    # Distribute beats: 20% intro, 25% build, 20% development, 20% climax, 15% fade
    intro = int(total_beats * 0.20)
    build = int(total_beats * 0.25)
    develop = int(total_beats * 0.20)
    climax = int(total_beats * 0.20)
    fade = total_beats - intro - build - develop - climax

    return PieceForm(bpm=bpm, sections=[
        Section("Intro",       beats=intro,   tension=0.12),
        Section("Build",       beats=build,   tension=0.35),
        Section("Development", beats=develop, tension=0.55),
        Section("Climax",      beats=climax,  tension=0.82),
        Section("Fade",        beats=fade,    tension=0.08),
    ])


def arch_form(bpm: float = 72, total_minutes: float = 3.0) -> PieceForm:
    """
    ABA arch form (Chopin Nocturne style):
    A → B (contrasting) → A' (return)

    Characteristic: symmetry, B section is the peak.
    """
    total_beats = int(total_minutes * bpm)
    a = int(total_beats * 0.35)
    b = int(total_beats * 0.35)
    a_prime = total_beats - a - b

    return PieceForm(bpm=bpm, sections=[
        Section("A",  beats=a,       tension=0.25),
        Section("B",  beats=b,       tension=0.65),
        Section("A'", beats=a_prime, tension=0.20),
    ])


def ramp_form(bpm: float = 92, total_minutes: float = 2.0) -> PieceForm:
    """
    Continuous ramp (Bach fugue style):
    Exposition → Development → Stretto/Climax → Cadence

    Characteristic: nearly monotonic increase to a late peak.
    """
    total_beats = int(total_minutes * bpm)
    expo = int(total_beats * 0.30)
    dev = int(total_beats * 0.35)
    stretto = int(total_beats * 0.25)
    cadence = total_beats - expo - dev - stretto

    return PieceForm(bpm=bpm, sections=[
        Section("Exposition", beats=expo,    tension=0.20),
        Section("Development", beats=dev,    tension=0.40),
        Section("Stretto",    beats=stretto, tension=0.75),
        Section("Cadence",    beats=cadence, tension=0.10, transition="sudden"),
    ])


# ═══════════════════════════════════════════════════════════════
# Smoke test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    form = long_form_build(bpm=76, total_minutes=3.5)
    curve = form.render()
    print(curve.summary())
    print()

    # Quick ASCII visualization
    width = 60
    height = 12
    for row in range(height, -1, -1):
        threshold = row / height
        line = ""
        step = max(1, curve.total_beats // width)
        for col in range(width):
            beat = col * step
            if beat < curve.total_beats:
                v = curve.values[beat]
                line += "█" if v >= threshold else "·"
            else:
                line += " "
        label = f"{threshold:.1f}" if row % 3 == 0 else "   "
        print(f"  {label:>3s} │{line}│")
    print(f"      └{'─' * width}┘")
    print(f"       0{'':>{width//2-1}}beats{'':>{width//2-4}}{curve.total_beats}")

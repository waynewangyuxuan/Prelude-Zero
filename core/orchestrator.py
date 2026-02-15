"""
Orchestrator — tension-driven multi-voice arrangement engine.

This is the bridge between:
  - TensionCurve (WHERE tension should be)
  - StyleTarget (WHAT the melody should sound like)
  - melody_gen (HOW to generate notes)

Core capabilities:
  1. tension_to_target(): map [0,1] tension → StyleTarget, per voice role
  2. VoicePlan: decide which voices are active in each section
  3. arrange(): generate all voices → assemble into PrettyMIDI

The orchestrator is style-agnostic — it takes a base_style (FLOYD_TARGET,
BACH_TARGET, etc.) and modulates it by tension. The tension→parameter
mapping is the same for all styles; the base_style provides the character.

Usage:
    from core.tension_curve import long_form_build
    from core.melody_gen import FLOYD_TARGET
    from core.scales import from_name

    form = long_form_build(bpm=76, total_minutes=3.5)
    curve = form.render()

    orch = Orchestrator(
        curve=curve,
        scale=from_name('E', 'phrygian'),
        base_style=FLOYD_TARGET,
        bpm=76,
    )
    pm = orch.arrange()
    pm.write('floyd_longform.mid')
"""

import copy
import numpy as np
import pretty_midi
from dataclasses import dataclass, field
from typing import Optional

from core.tension_curve import TensionCurve, Section
from core.melody_gen import StyleTarget, MelodyNote, generate_melody
from core.scales import Scale
from core.humanize import humanize, HumanizeConfig


# ═══════════════════════════════════════════════════════════════
# Voice roles and their behavior
# ═══════════════════════════════════════════════════════════════

@dataclass
class VoiceConfig:
    """Configuration for a single voice role."""
    name: str
    program: int              # GM MIDI program number
    entry_tension: float      # tension level at which this voice enters [0, 1]
    exit_tension: float       # tension below which this voice exits (on the way down)
    octave_offset: int = 0    # shift pitch center by this many octaves
    velocity_base: int = 70   # base velocity for this voice
    is_melodic: bool = True   # if False, generate sustained chords instead


# Default voice palette — can be overridden per style
VOICE_PALETTE = {
    'lead': VoiceConfig(
        name='Lead', program=25,  # Acoustic Guitar (steel)
        entry_tension=0.0, exit_tension=-1.0,  # always present
        octave_offset=0, velocity_base=75, is_melodic=True,
    ),
    'bass': VoiceConfig(
        name='Bass', program=33,  # Electric Bass (finger)
        entry_tension=0.18, exit_tension=0.10,
        octave_offset=-2, velocity_base=70, is_melodic=True,
    ),
    'pad': VoiceConfig(
        name='Pad', program=89,   # Pad 2 (warm)
        entry_tension=0.28, exit_tension=0.15,
        octave_offset=-1, velocity_base=55, is_melodic=False,
    ),
    'counter': VoiceConfig(
        name='Counter', program=26,  # Acoustic Guitar (jazz)
        entry_tension=0.50, exit_tension=0.35,
        octave_offset=0, velocity_base=60, is_melodic=True,
    ),
}


# ═══════════════════════════════════════════════════════════════
# Tension → StyleTarget mapping
# ═══════════════════════════════════════════════════════════════

def tension_to_target(tension: float, base: StyleTarget, role: str) -> StyleTarget:
    """
    Map a [0, 1] tension value to a StyleTarget.

    The base style provides the character (Floyd sparse, Bach dense, etc.).
    Tension modulates parameters around the base:
      - Low tension: sparser, narrower, more stepwise, less chromatic
      - High tension: denser, wider, more leaps, more chromatic

    Each role has a different modulation curve.
    """
    t = max(0.0, min(1.0, tension))
    out = copy.copy(base)

    if role == 'lead':
        # Lead: the primary voice, most affected by tension
        out.density = base.density * _lerp(0.5, 1.4, t)
        out.duration_cv = base.duration_cv * _lerp(0.6, 1.3, t)
        out.step_ratio = base.step_ratio + 0.15 * (1 - t)  # more stepwise at low T
        out.step_ratio = min(out.step_ratio, 0.95)
        out.direction_change_prob = base.direction_change_prob * _lerp(0.7, 1.2, t)
        out.chromaticism = base.chromaticism * _lerp(0.0, 1.5, t)
        out.pitch_range = max(8, int(base.pitch_range * _lerp(0.4, 1.1, t)))
        out.leap_probability = base.leap_probability * _lerp(0.2, 1.5, t)
        out.repetition = base.repetition * _lerp(1.3, 0.6, t)  # more repetitive at low T

    elif role == 'counter':
        # Counter: complementary to lead — sparser when lead is dense
        out.density = base.density * _lerp(0.3, 0.8, t)
        out.duration_cv = base.duration_cv * _lerp(0.8, 1.2, t)
        out.step_ratio = base.step_ratio  # same motion style
        out.direction_change_prob = base.direction_change_prob * 1.1  # slightly more changes
        out.chromaticism = base.chromaticism * _lerp(0.0, 1.0, t)
        out.pitch_range = max(8, int(base.pitch_range * 0.7))  # narrower than lead
        out.pitch_center = base.pitch_center + 5  # offset to avoid collision
        out.contour_bias = -base.contour_bias  # tend opposite direction

    elif role == 'bass':
        # Bass: sparse, root-oriented, wider intervals
        out.density = _lerp(0.3, 0.8, t)  # absolute, not relative to base
        out.duration_cv = _lerp(0.1, 0.5, t)
        out.step_ratio = _lerp(0.3, 0.5, t)  # more leaps (root movement)
        out.leap_probability = _lerp(0.15, 0.25, t)
        out.direction_change_prob = 0.45
        out.chromaticism = base.chromaticism * _lerp(0.0, 0.5, t)
        out.pitch_center = base.pitch_center - 24 + base.octave_offset if hasattr(base, 'octave_offset') else base.pitch_center - 24
        out.pitch_range = 14  # one octave + a bit
        out.repetition = _lerp(0.5, 0.3, t)  # pedal-like at low tension
        out.rhythm_variety = 3

    elif role == 'pad':
        # Pad: sustained chords (not used for melody generation)
        # These targets are informational — the pad generator uses tension directly
        out.density = _lerp(0.15, 0.3, t)  # very sparse
        out.chromaticism = base.chromaticism * t
        out.pitch_range = int(_lerp(10, 20, t))

    return out


def _lerp(lo: float, hi: float, t: float) -> float:
    """Linear interpolation between lo and hi."""
    return lo + (hi - lo) * t


# ═══════════════════════════════════════════════════════════════
# Voice Plan — who plays when
# ═══════════════════════════════════════════════════════════════

@dataclass
class VoiceEntry:
    """A voice active in a specific beat range."""
    role: str
    start_beat: int
    end_beat: int
    mean_tension: float


def plan_voices(curve: TensionCurve,
                palette: dict[str, VoiceConfig] = None) -> list[VoiceEntry]:
    """
    Determine which voices are active at each beat.

    Uses hysteresis: a voice enters when tension rises above entry_tension,
    and exits when it drops below exit_tension. This prevents rapid on/off
    switching near thresholds.

    Returns a list of VoiceEntry describing active ranges.
    """
    if palette is None:
        palette = VOICE_PALETTE

    entries = []

    for role, config in palette.items():
        active = False
        start = 0
        tension_sum = 0.0
        count = 0

        for beat in range(curve.total_beats):
            t = curve.values[beat]

            if not active and t >= config.entry_tension:
                active = True
                start = beat
                tension_sum = 0.0
                count = 0

            if active and t < config.exit_tension:
                # Voice exits
                mean_t = tension_sum / count if count > 0 else 0.0
                entries.append(VoiceEntry(role, start, beat, mean_t))
                active = False

            if active:
                tension_sum += t
                count += 1

        # Close any still-active voice
        if active:
            mean_t = tension_sum / count if count > 0 else 0.0
            entries.append(VoiceEntry(role, start, curve.total_beats, mean_t))

    # Sort by start beat then by role priority
    role_order = {'lead': 0, 'bass': 1, 'pad': 2, 'counter': 3}
    entries.sort(key=lambda e: (e.start_beat, role_order.get(e.role, 99)))

    return entries


# ═══════════════════════════════════════════════════════════════
# Pad generator (sustained chords, not melody_gen)
# ═══════════════════════════════════════════════════════════════

def _generate_pad(scale: Scale, curve: TensionCurve,
                  start_beat: int, end_beat: int, bpm: float,
                  base_pitch: int = 60, seed: int = 42) -> list[MelodyNote]:
    """
    Generate sustained chord tones for a pad voice.

    Uses scale triads, changing chord every 4-8 beats depending on tension.
    Higher tension = more frequent changes + wider voicings.
    """
    rng = np.random.RandomState(seed)
    beat_dur = 60.0 / bpm
    notes = []
    beat = start_beat

    # Scale degrees for chord roots (cycle through)
    roots = [0, 3, 4, 2, 5, 0, 6, 4]  # I, IV, V, iii, vi, I, vii, V
    root_idx = 0

    while beat < end_beat:
        t = curve.at(beat)
        # Chord duration: 8 beats at low tension, 4 at high
        chord_beats = int(_lerp(8, 4, t))
        chord_beats = max(2, min(chord_beats, end_beat - beat))

        # Get chord tones from scale
        root_degree = roots[root_idx % len(roots)]
        root_pitch = scale.step(base_pitch, root_degree)
        chord_pcs = scale.triad(root_pitch)

        # Build voicing: spread based on tension
        voicing = []
        for pc in chord_pcs:
            # Place near base_pitch
            p = pc
            while p < base_pitch - 6:
                p += 12
            while p > base_pitch + 18:
                p -= 12
            voicing.append(p)

        # Add seventh at higher tension
        if t > 0.5:
            seventh_pcs = scale.seventh(root_pitch)
            if len(seventh_pcs) > 3:
                p = seventh_pcs[3]
                while p < base_pitch:
                    p += 12
                while p > base_pitch + 18:
                    p -= 12
                voicing.append(p)

        onset = beat * beat_dur
        dur = chord_beats * beat_dur * 0.95  # slight gap between chords

        for p in voicing:
            vel = int(45 + 25 * t)  # 45 at low tension, 70 at high
            notes.append(MelodyNote(
                pitch=p, onset=onset, duration=dur,
                velocity=vel, is_chromatic=False,
            ))

        beat += chord_beats
        root_idx += 1

    return notes


# ═══════════════════════════════════════════════════════════════
# Orchestrator — the main class
# ═══════════════════════════════════════════════════════════════

class Orchestrator:
    """
    Tension-driven multi-voice arrangement engine.

    Takes a tension curve + scale + base style, produces a complete
    multi-voice MIDI arrangement.
    """

    def __init__(self, curve: TensionCurve, scale: Scale,
                 base_style: StyleTarget, bpm: float,
                 palette: dict[str, VoiceConfig] = None,
                 humanize_config: Optional[HumanizeConfig] = None,
                 seed: int = 42):
        self.curve = curve
        self.scale = scale
        self.base_style = base_style
        self.bpm = bpm
        self.palette = palette or dict(VOICE_PALETTE)
        self.humanize_config = humanize_config
        self.seed = seed

    def arrange(self, verbose: bool = True) -> pretty_midi.PrettyMIDI:
        """
        Generate the full arrangement.

        Returns a PrettyMIDI with one instrument per voice.
        """
        beat_dur = 60.0 / self.bpm

        # Plan voices
        voice_plan = plan_voices(self.curve, self.palette)

        if verbose:
            print(f"\nOrchestrator: {self.curve.total_beats} beats, "
                  f"{self.curve.duration_seconds:.0f}s @ {self.bpm} BPM")
            print(f"  Voices planned: {len(voice_plan)} entries")
            for ve in voice_plan:
                sec = self.curve.section_at(ve.start_beat)
                print(f"    {ve.role:10s} beats {ve.start_beat:3d}-{ve.end_beat:3d}  "
                      f"mean_t={ve.mean_tension:.2f}  ({sec}...)")

        pm = pretty_midi.PrettyMIDI(initial_tempo=self.bpm)
        rng_base = self.seed

        for i, ve in enumerate(voice_plan):
            config = self.palette[ve.role]
            inst = pretty_midi.Instrument(
                program=config.program,
                name=f"{config.name}_{i}",
            )

            if config.is_melodic:
                notes = self._generate_melodic_voice(ve, rng_base + i * 1000)
            else:
                notes = self._generate_pad_voice(ve, rng_base + i * 1000)

            # Convert MelodyNotes to MIDI
            for mn in notes:
                if mn.duration <= 0 or mn.pitch < 0 or mn.pitch > 127:
                    continue
                midi_note = pretty_midi.Note(
                    velocity=max(20, min(127, mn.velocity)),
                    pitch=mn.pitch,
                    start=mn.onset,
                    end=mn.onset + mn.duration,
                )
                inst.notes.append(midi_note)

            if inst.notes:
                pm.instruments.append(inst)

        # Humanize if config provided
        if self.humanize_config is not None:
            # Set BPM in config and derive section boundaries
            self.humanize_config.bpm = self.bpm
            sbeats = [b for b, _ in self.curve.section_boundaries]
            pm = humanize(pm, config=self.humanize_config,
                          section_beats=sbeats)

        if verbose:
            total_notes = sum(len(inst.notes) for inst in pm.instruments)
            print(f"\n  Result: {len(pm.instruments)} instruments, {total_notes} notes, "
                  f"{pm.get_end_time():.1f}s")

        return pm

    def _generate_melodic_voice(self, ve: VoiceEntry, seed: int) -> list[MelodyNote]:
        """Generate melody notes for a voice entry, section by section."""
        beat_dur = 60.0 / self.bpm
        all_notes = []
        config = self.palette[ve.role]

        # Split into sub-sections aligned to piece form sections
        sections = self._voice_sections(ve)

        for sec_start, sec_end, sec_name in sections:
            sec_beats = sec_end - sec_start
            if sec_beats < 2:
                continue

            # Average tension for this section
            mean_t = self.curve.mean_tension(sec_start, sec_end)

            # Compute StyleTarget for this role at this tension
            target = tension_to_target(mean_t, self.base_style, ve.role)

            # Apply octave offset
            target.pitch_center = self.base_style.pitch_center + config.octave_offset * 12

            # Generate melody for this section
            section_notes = generate_melody(
                scale=self.scale,
                target=target,
                bpm=self.bpm,
                total_beats=sec_beats,
                seed=seed + sec_start,
            )

            # Offset to correct position in time
            time_offset = sec_start * beat_dur
            for note in section_notes:
                note.onset += time_offset
                note.velocity = int(note.velocity * config.velocity_base / 75)
                note.velocity = max(20, min(127, note.velocity))

            all_notes.extend(section_notes)

        return all_notes

    def _generate_pad_voice(self, ve: VoiceEntry, seed: int) -> list[MelodyNote]:
        """Generate pad (sustained chords) for a voice entry."""
        config = self.palette[ve.role]
        base_pitch = self.base_style.pitch_center + config.octave_offset * 12

        return _generate_pad(
            scale=self.scale,
            curve=self.curve,
            start_beat=ve.start_beat,
            end_beat=ve.end_beat,
            bpm=self.bpm,
            base_pitch=base_pitch,
            seed=seed,
        )

    def _voice_sections(self, ve: VoiceEntry) -> list[tuple[int, int, str]]:
        """
        Split a voice entry into sub-sections aligned to piece form boundaries.
        This ensures each section gets a StyleTarget based on its local tension.
        """
        boundaries = self.curve.section_boundaries
        result = []

        for i, (b, name) in enumerate(boundaries):
            # Section end
            if i + 1 < len(boundaries):
                sec_end = boundaries[i + 1][0]
            else:
                sec_end = self.curve.total_beats

            # Overlap with voice entry
            overlap_start = max(b, ve.start_beat)
            overlap_end = min(sec_end, ve.end_beat)

            if overlap_start < overlap_end:
                result.append((overlap_start, overlap_end, name))

        return result

    def summary(self) -> str:
        """Human-readable arrangement plan."""
        voice_plan = plan_voices(self.curve, self.palette)
        lines = [f"Arrangement: {self.curve.total_beats} beats, "
                 f"{self.curve.duration_seconds:.0f}s"]
        lines.append("")

        # Section-by-section view
        for b, name in self.curve.section_boundaries:
            try:
                start, end = self.curve.section_range(name)
            except KeyError:
                continue
            mean_t = self.curve.mean_tension(start, end)
            active = [ve.role for ve in voice_plan
                      if ve.start_beat < end and ve.end_beat > start]
            lines.append(f"  {name:20s} beats {start:3d}-{end:3d}  "
                         f"T={mean_t:.2f}  voices: {', '.join(active)}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Smoke test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from core.tension_curve import long_form_build
    from core.melody_gen import FLOYD_TARGET
    from core.scales import from_name

    form = long_form_build(bpm=76, total_minutes=3.5)
    curve = form.render()

    orch = Orchestrator(
        curve=curve,
        scale=from_name('E', 'phrygian'),
        base_style=FLOYD_TARGET,
        bpm=76,
    )

    print(orch.summary())
    print()

    # Quick generation test (without humanize for speed)
    pm = orch.arrange(verbose=True)
    pm.write('/tmp/orchestrator_test.mid')
    print(f"\n  Saved: /tmp/orchestrator_test.mid")

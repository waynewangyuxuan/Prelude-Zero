"""
Tension engine — model musical tension as a continuous function T(t).

The core insight: music is tension and release.
Bach doesn't just avoid errors — he sculpts a tension arc.

Five dimensions of tension:
  1. Harmonic:   distance from tonal center (via DFT f₅)
  2. Dissonance: sensory roughness of simultaneous intervals
  3. Melodic:    interval sizes + contour volatility in each voice
  4. Registral:  vertical spread between voices
  5. Density:    notes per unit time

Combined: T(t) = Σ wᵢ · Tᵢ(t),  each component normalized to [0, 1].

Usage:
    curve = compute_tension(pm, bpm=80)
    curve.plot()                     # matplotlib
    target = target_curve("fugue", n_beats=104)
    diff = curve.distance(target)    # how far are we from the ideal?
"""

import numpy as np
import pretty_midi
from dataclasses import dataclass, field
from typing import Optional

TAU = 2 * np.pi


# ═══════════════════════════════════════════════════════════════
# Core data structure
# ═══════════════════════════════════════════════════════════════

@dataclass
class TensionCurve:
    """Multi-dimensional tension over time."""
    beats: np.ndarray           # time axis (in beats)
    harmonic: np.ndarray        # [0,1] — harmonic distance from tonal center
    dissonance: np.ndarray      # [0,1] — sensory roughness
    melodic: np.ndarray         # [0,1] — intervallic tension in voices
    registral: np.ndarray       # [0,1] — vertical spread
    density: np.ndarray         # [0,1] — note activity
    weights: dict = field(default_factory=lambda: {
        "harmonic": 0.30,
        "dissonance": 0.25,
        "melodic": 0.20,
        "registral": 0.10,
        "density": 0.15,
    })

    @property
    def combined(self) -> np.ndarray:
        """Weighted combination of all tension dimensions."""
        w = self.weights
        return (w["harmonic"]   * self.harmonic +
                w["dissonance"] * self.dissonance +
                w["melodic"]    * self.melodic +
                w["registral"]  * self.registral +
                w["density"]    * self.density)

    @property
    def n_beats(self) -> int:
        return len(self.beats)

    def distance(self, target: 'TensionCurve') -> float:
        """L2 distance between this curve and a target."""
        n = min(len(self.combined), len(target.combined))
        return float(np.sqrt(np.mean((self.combined[:n] - target.combined[:n]) ** 2)))

    def to_dict(self) -> dict:
        """Export for visualization."""
        return {
            "beats": self.beats.tolist(),
            "harmonic": self.harmonic.tolist(),
            "dissonance": self.dissonance.tolist(),
            "melodic": self.melodic.tolist(),
            "registral": self.registral.tolist(),
            "density": self.density.tolist(),
            "combined": self.combined.tolist(),
        }


# ═══════════════════════════════════════════════════════════════
# Main computation
# ═══════════════════════════════════════════════════════════════

def compute_tension(
    pm: pretty_midi.PrettyMIDI,
    bpm: float = 80.0,
    resolution: float = 0.5,     # sample every half-beat
    key_pc: int = 0,             # tonic pitch class (0=C)
    smooth_window: int = 3,      # smoothing window (in samples)
) -> TensionCurve:
    """
    Compute multi-dimensional tension curve from a PrettyMIDI.

    Args:
        pm: input MIDI
        bpm: tempo (beats per minute)
        resolution: sampling interval in beats
        key_pc: tonic pitch class for harmonic tension reference
        smooth_window: moving-average window for smoothing
    """
    beat_dur = 60.0 / bpm
    end_time = pm.get_end_time()
    end_beat = end_time / beat_dur
    beats = np.arange(0, end_beat, resolution)
    n = len(beats)

    harmonic = np.zeros(n)
    dissonance = np.zeros(n)
    melodic = np.zeros(n)
    registral = np.zeros(n)
    density = np.zeros(n)

    # Collect all notes across instruments with voice labels
    all_notes = []
    for vi, inst in enumerate(pm.instruments):
        for note in inst.notes:
            all_notes.append({
                "voice": vi,
                "pitch": note.pitch,
                "start": note.start,
                "end": note.end,
                "start_beat": note.start / beat_dur,
                "end_beat": note.end / beat_dur,
            })

    # For each time sample
    for i, t in enumerate(beats):
        t_sec = t * beat_dur

        # ── Notes sounding at this moment ──
        sounding = [n for n in all_notes
                     if n["start"] <= t_sec < n["end"]]
        pitches = [n["pitch"] for n in sounding]

        if not pitches:
            continue

        # ── 1. Harmonic tension: DFT f₅ ──
        harmonic[i] = _harmonic_tension(pitches, key_pc)

        # ── 2. Dissonance ──
        dissonance[i] = _dissonance(pitches)

        # ── 3. Melodic tension ──
        # Look at interval from previous beat in each voice
        if i > 0:
            prev_t_sec = beats[i - 1] * beat_dur
            melodic[i] = _melodic_tension(all_notes, prev_t_sec, t_sec)

        # ── 4. Registral spread ──
        registral[i] = _registral_spread(pitches)

        # ── 5. Note density ──
        density[i] = _density(all_notes, t_sec, beat_dur * resolution)

    # Normalize each dimension to [0, 1]
    harmonic = _normalize(harmonic)
    dissonance = _normalize(dissonance)
    melodic = _normalize(melodic)
    registral = _normalize(registral)
    density = _normalize(density)

    # Smooth
    if smooth_window > 1:
        harmonic = _smooth(harmonic, smooth_window)
        dissonance = _smooth(dissonance, smooth_window)
        melodic = _smooth(melodic, smooth_window)
        registral = _smooth(registral, smooth_window)
        density = _smooth(density, smooth_window)

    return TensionCurve(
        beats=beats,
        harmonic=harmonic,
        dissonance=dissonance,
        melodic=melodic,
        registral=registral,
        density=density,
    )


# ═══════════════════════════════════════════════════════════════
# Dimension 1: Harmonic tension via DFT
# ═══════════════════════════════════════════════════════════════

def _harmonic_tension(pitches: list[int], key_pc: int) -> float:
    """
    Harmonic tension = 1 - normalized diatonic quality.

    Uses DFT coefficient f₅ on the pitch-class distribution.
    High |f₅| = strong diatonic alignment = low tension.
    Low  |f₅| = chromatic / atonal = high tension.

    Also factors in the phase distance from the expected key.
    """
    # Build pitch-class vector (weighted by count)
    pc_vec = np.zeros(12)
    for p in pitches:
        pc_vec[p % 12] += 1

    if pc_vec.sum() == 0:
        return 0.0

    # DFT coefficient f₅
    k = 5
    re = np.sum(pc_vec * np.cos(-TAU * k * np.arange(12) / 12))
    im = np.sum(pc_vec * np.sin(-TAU * k * np.arange(12) / 12))
    mag = np.sqrt(re**2 + im**2)
    phase = np.arctan2(im, re)

    # Max possible |f₅| for this many notes
    n_notes = pc_vec.sum()
    max_mag = n_notes  # all notes on same PC

    # Diatonic quality: how close to maximum
    diatonic_quality = mag / max_mag if max_mag > 0 else 0

    # Phase distance from expected key
    # The phase of f₅ for key of C should be near 0
    expected_phase = -TAU * k * key_pc / 12
    phase_dist = abs(((phase - expected_phase + np.pi) % TAU) - np.pi) / np.pi

    # Combined: low diatonic quality OR far from key = tension
    tension = (1 - diatonic_quality) * 0.6 + phase_dist * 0.4

    return tension


# ═══════════════════════════════════════════════════════════════
# Dimension 2: Dissonance (interval-class model)
# ═══════════════════════════════════════════════════════════════

# Dissonance weights for each interval class (0-6)
# Based on Hindemith/Huron rankings
INTERVAL_DISSONANCE = {
    0: 0.0,   # unison
    1: 1.0,   # m2 — maximum dissonance
    2: 0.3,   # M2
    3: 0.2,   # m3
    4: 0.15,  # M3
    5: 0.05,  # P4
    6: 0.8,   # tritone
}

def _dissonance(pitches: list[int]) -> float:
    """
    Dissonance = sum of pairwise interval-class roughness.

    Uses the interval-class vector (ICV) weighted by perceptual dissonance.
    """
    if len(pitches) < 2:
        return 0.0

    total = 0.0
    count = 0
    for i in range(len(pitches)):
        for j in range(i + 1, len(pitches)):
            ic = abs(pitches[i] - pitches[j]) % 12
            if ic > 6:
                ic = 12 - ic  # interval class (0-6)
            total += INTERVAL_DISSONANCE.get(ic, 0.3)
            count += 1

    return total / count if count > 0 else 0.0


# ═══════════════════════════════════════════════════════════════
# Dimension 3: Melodic tension (interval sizes in voices)
# ═══════════════════════════════════════════════════════════════

def _melodic_tension(all_notes: list[dict], prev_t: float, curr_t: float) -> float:
    """
    Melodic tension = average absolute interval across voices between two time points.

    Large intervals = more tension. Direction changes also add tension.
    """
    intervals = []

    # Group by voice
    voices = {}
    for n in all_notes:
        vi = n["voice"]
        if vi not in voices:
            voices[vi] = []
        voices[vi].append(n)

    for vi, notes in voices.items():
        # Find note sounding at prev_t and curr_t
        prev_pitch = None
        curr_pitch = None
        for n in notes:
            if n["start"] <= prev_t < n["end"]:
                prev_pitch = n["pitch"]
            if n["start"] <= curr_t < n["end"]:
                curr_pitch = n["pitch"]
        if prev_pitch is not None and curr_pitch is not None:
            interval = abs(curr_pitch - prev_pitch)
            intervals.append(interval)

    if not intervals:
        return 0.0

    # Average interval, scaled: 0 semitones = 0 tension, 12+ = high tension
    avg = np.mean(intervals)
    return min(avg / 12.0, 1.0)


# ═══════════════════════════════════════════════════════════════
# Dimension 4: Registral spread
# ═══════════════════════════════════════════════════════════════

def _registral_spread(pitches: list[int]) -> float:
    """
    Registral tension = spread between highest and lowest sounding notes.

    Wider spread = generally more tension/grandeur.
    Normalized: 0 semitones = 0, 48+ semitones (4 octaves) = 1.
    """
    if len(pitches) < 2:
        return 0.0
    spread = max(pitches) - min(pitches)
    return min(spread / 48.0, 1.0)


# ═══════════════════════════════════════════════════════════════
# Dimension 5: Note density
# ═══════════════════════════════════════════════════════════════

def _density(all_notes: list[dict], t_sec: float, window_sec: float) -> float:
    """
    Note density = number of note onsets in a time window.

    More onsets = more activity = more tension.
    """
    count = sum(1 for n in all_notes
                if t_sec <= n["start"] < t_sec + window_sec)
    # Normalize: 0 onsets = 0, 8+ = 1 (very dense)
    return min(count / 8.0, 1.0)


# ═══════════════════════════════════════════════════════════════
# Target tension curves (archetypes)
# ═══════════════════════════════════════════════════════════════

def target_curve(
    form: str,
    n_beats: float,
    resolution: float = 0.5,
    sections: list[tuple] = None,
) -> TensionCurve:
    """
    Generate an idealized target tension curve for a musical form.

    Forms:
    - "prelude": gradual build → climax at 75% → resolution
    - "fugue": stepped entries → development → stretto peak → cadence
    - "arch": simple rise → fall
    - "custom": provide section-wise tension targets
    """
    beats = np.arange(0, n_beats, resolution)
    n = len(beats)
    t_norm = beats / n_beats  # normalized time [0, 1]

    if form == "prelude":
        # Gradual build with climax at ~75%
        base = 0.3 + 0.5 * np.sin(np.pi * t_norm ** 0.8)
        # Extra peak at 70-80%
        peak = 0.2 * np.exp(-((t_norm - 0.75) / 0.08) ** 2)
        # Resolution dip at end
        resolution_dip = -0.3 * np.maximum(0, (t_norm - 0.9) / 0.1)
        curve = np.clip(base + peak + resolution_dip, 0, 1)

    elif form == "fugue":
        # Stepped entries (each adds tension)
        curve = np.zeros(n)
        # Exposition: stepped increases
        expo_end = 0.35
        expo_mask = t_norm < expo_end
        curve[expo_mask] = 0.2 + 0.3 * (t_norm[expo_mask] / expo_end)
        # Episodes + middle entries: fluctuating middle tension
        mid_mask = (t_norm >= expo_end) & (t_norm < 0.75)
        curve[mid_mask] = 0.5 + 0.15 * np.sin(6 * np.pi * (t_norm[mid_mask] - expo_end))
        # Stretto: peak tension
        stretto_mask = (t_norm >= 0.75) & (t_norm < 0.92)
        curve[stretto_mask] = 0.7 + 0.2 * ((t_norm[stretto_mask] - 0.75) / 0.17)
        # Final cadence: release
        cad_mask = t_norm >= 0.92
        curve[cad_mask] = 0.9 - 0.7 * ((t_norm[cad_mask] - 0.92) / 0.08)

    elif form == "arch":
        # Simple arch
        curve = np.sin(np.pi * t_norm)

    elif form == "custom" and sections:
        # Sections: list of (start_beat, end_beat, start_tension, end_tension)
        curve = np.zeros(n)
        for start_b, end_b, t_start, t_end in sections:
            mask = (beats >= start_b) & (beats < end_b)
            if mask.any():
                local_t = (beats[mask] - start_b) / max(end_b - start_b, 0.01)
                curve[mask] = t_start + (t_end - t_start) * local_t
    else:
        curve = 0.5 * np.ones(n)

    # Distribute equally across dimensions for target
    uniform = curve
    return TensionCurve(
        beats=beats,
        harmonic=uniform.copy(),
        dissonance=uniform.copy() * 0.8,
        melodic=uniform.copy() * 0.6,
        registral=uniform.copy() * 0.5,
        density=uniform.copy() * 0.7,
    )


# ═══════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════

def _normalize(arr: np.ndarray) -> np.ndarray:
    """Normalize array to [0, 1]."""
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-10:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


def _smooth(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average smoothing."""
    if window <= 1 or len(arr) < window:
        return arr
    kernel = np.ones(window) / window
    smoothed = np.convolve(arr, kernel, mode='same')
    return smoothed


def summarize(curve: TensionCurve, sections: list[tuple] = None) -> str:
    """Print a human-readable summary of the tension curve."""
    lines = []
    c = curve.combined
    lines.append(f"Tension summary: {curve.n_beats} samples")
    lines.append(f"  Overall: mean={c.mean():.3f}, max={c.max():.3f} at beat {curve.beats[c.argmax()]:.1f}, "
                 f"min={c.min():.3f} at beat {curve.beats[c.argmin()]:.1f}")
    lines.append(f"  Harmonic:   mean={curve.harmonic.mean():.3f}")
    lines.append(f"  Dissonance: mean={curve.dissonance.mean():.3f}")
    lines.append(f"  Melodic:    mean={curve.melodic.mean():.3f}")
    lines.append(f"  Registral:  mean={curve.registral.mean():.3f}")
    lines.append(f"  Density:    mean={curve.density.mean():.3f}")

    if sections:
        lines.append("\n  Per-section tension:")
        for name, start, end in sections:
            mask = (curve.beats >= start) & (curve.beats < end)
            if mask.any():
                sec_c = c[mask]
                lines.append(f"    {name:20s} [{start:.0f}-{end:.0f}] "
                             f"mean={sec_c.mean():.3f} peak={sec_c.max():.3f}")

    return "\n".join(lines)

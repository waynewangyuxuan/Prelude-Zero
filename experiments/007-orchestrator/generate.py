"""
Experiment 007 — Orchestrator Validation

Generate a 3.5-minute Floyd long-form piece using the new engine stack:
  tension_curve → orchestrator → melody_gen → MIDI

This validates:
  1. Tension curve drives generation (narrative arc)
  2. Multi-voice arrangement (progressive layering)
  3. Per-section StyleTarget modulation
  4. Lead melody metrics still match Floyd profile
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pretty_midi

from core.tension_curve import PieceForm, Section, long_form_build
from core.orchestrator import Orchestrator, VOICE_PALETTE, VoiceConfig
from core.melody_gen import FLOYD_TARGET, StyleTarget
from core.scales import from_name
from core.humanize import HumanizeConfig
from core.audio import prettymidi_to_wav
from core.melody import compute_melody_profile, summarize

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
# Piece definition
# ═══════════════════════════════════════════════════════════════

BPM = 76

# Custom form — more control than the preset
form = PieceForm(bpm=BPM, sections=[
    Section("Intro",       beats=40,  tension=0.10),
    Section("Build",       beats=48,  tension=0.32),
    Section("Development", beats=48,  tension=0.55),
    Section("Climax",      beats=48,  tension=0.80),
    Section("Descent",     beats=32,  tension=0.40),
    Section("Fade",        beats=32,  tension=0.08),
])

curve = form.render()
print(curve.summary())

# ═══════════════════════════════════════════════════════════════
# Floyd voice palette (customize GM programs)
# ═══════════════════════════════════════════════════════════════

floyd_palette = {
    'lead': VoiceConfig(
        name='Lead Guitar', program=29,  # Overdriven Guitar
        entry_tension=0.0, exit_tension=-1.0,
        octave_offset=0, velocity_base=78, is_melodic=True,
    ),
    'bass': VoiceConfig(
        name='Bass', program=33,  # Electric Bass (finger)
        entry_tension=0.15, exit_tension=0.06,
        octave_offset=-2, velocity_base=72, is_melodic=True,
    ),
    'pad': VoiceConfig(
        name='Synth Pad', program=89,  # Pad 2 (warm)
        entry_tension=0.25, exit_tension=0.12,
        octave_offset=-1, velocity_base=55, is_melodic=False,
    ),
    'counter': VoiceConfig(
        name='Counter Guitar', program=26,  # Jazz Guitar (clean)
        entry_tension=0.48, exit_tension=0.30,
        octave_offset=0, velocity_base=62, is_melodic=True,
    ),
}

# ═══════════════════════════════════════════════════════════════
# Humanize config (Floyd: loose timing, moderate dynamics)
# ═══════════════════════════════════════════════════════════════

floyd_humanize = HumanizeConfig(
    velocity_jitter=6,
    timing_sigma=0.012,       # 12ms gaussian σ
    default_legato=0.90,
    stepwise_legato=0.95,
    phrase_arc_strength=0.15,
    cadence_rubato=0.08,
)

# ═══════════════════════════════════════════════════════════════
# Generate
# ═══════════════════════════════════════════════════════════════

orch = Orchestrator(
    curve=curve,
    scale=from_name('E', 'phrygian'),
    base_style=FLOYD_TARGET,
    bpm=BPM,
    palette=floyd_palette,
    humanize_config=floyd_humanize,
    seed=42,
)

print("\n" + orch.summary())
print()

pm = orch.arrange(verbose=True)

# Save MIDI
midi_path = os.path.join(OUT_DIR, 'floyd_longform.mid')
pm.write(midi_path)
print(f"\n  MIDI: {midi_path}")

# Save WAV (preview only — render MIDI in GarageBand for real quality)
wav_path = os.path.join(OUT_DIR, 'floyd_longform.wav')
prettymidi_to_wav(pm, wav_path, sample_rate=44100)
print(f"  WAV:  {wav_path}")

# ═══════════════════════════════════════════════════════════════
# Evaluate lead melody
# ═══════════════════════════════════════════════════════════════

print("\n" + "="*60)
print("  LEAD MELODY EVALUATION")
print("="*60)

# Extract lead instrument (track 0)
lead_inst = pm.instruments[0]
lead_notes = sorted(lead_inst.notes, key=lambda n: n.start)
print(f"\n  Lead: {lead_inst.name}, {len(lead_notes)} notes")

# Compute melody profile from raw note data
pitches = [n.pitch for n in lead_notes]
onsets = [n.start for n in lead_notes]
durations = [n.end - n.start for n in lead_notes]
profile = compute_melody_profile(pitches, onsets, durations, BPM)
report = summarize(profile)
print(report)

# Per-section analysis
print("\n" + "="*60)
print("  PER-SECTION ANALYSIS")
print("="*60)

beat_dur = 60.0 / BPM
for b, name in curve.section_boundaries:
    try:
        start, end = curve.section_range(name)
    except KeyError:
        continue

    start_s = start * beat_dur
    end_s = end * beat_dur
    mean_t = curve.mean_tension(start, end)

    # Count notes in this section
    sec_notes = [n for n in lead_inst.notes
                 if n.start >= start_s and n.start < end_s]
    n_notes = len(sec_notes)
    sec_density = n_notes / (end - start) if end > start else 0

    # Count active voices in this section
    active_voices = sum(1 for inst in pm.instruments
                        if any(n.start >= start_s and n.start < end_s
                               for n in inst.notes))

    print(f"\n  {name:20s} beats {start:3d}-{end:3d}  T={mean_t:.2f}")
    print(f"    Lead: {n_notes:3d} notes, density={sec_density:.2f}/beat")
    print(f"    Active voices: {active_voices}")

# Compare with Experiment 005 Floyd reference
print("\n" + "="*60)
print("  FLOYD REFERENCE COMPARISON")
print("="*60)

FLOYD_REF = {
    'pitch_range': (27.42, 10.36),
    'step_ratio': (0.421, 0.211),
    'direction_change_ratio': (0.617, 0.100),
    'rhythm_density': (1.100, 0.832),
    'chromaticism': (0.245, 0.104),
    'duration_cv': (0.967, 0.390),
    'mean_run_length': (1.649, 0.249),
    'tonal_clarity': (0.779, 0.084),
}

print(f"\n  {'Metric':28s} {'Generated':>10s} {'Reference':>12s} {'σ dist':>8s}")
print(f"  {'-'*60}")

within_2sigma = 0
total = 0
for key, (ref_mean, ref_std) in FLOYD_REF.items():
    val = getattr(profile, key, None)
    if val is None:
        continue
    if ref_std > 0:
        sigma = (val - ref_mean) / ref_std
    else:
        sigma = abs(val - ref_mean) * 10.0
    within = abs(sigma) <= 2.0
    marker = "✓" if within else "✗"
    total += 1
    if within:
        within_2sigma += 1
    print(f"  {key:28s} {val:10.3f} {ref_mean:7.3f}±{ref_std:.3f} {sigma:+6.1f}σ  {marker}")

print(f"\n  Score: {within_2sigma}/{total} metrics within 2σ of Floyd reference")

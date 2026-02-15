"""
Experiment 006 v2: Generate three styles using the new engine.
Uses core/scales.py + core/melody_gen.py instead of hand-composed notes.

Bach  — A minor, 92 BPM (slower than v1), motor rhythm, two-voice texture
Chopin — Eb major, 72 BPM, singing melody + arpeggio accompaniment
Floyd  — E Phrygian, 76 BPM, spacious lead + pad + bass
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pretty_midi
from core.scales import Scale, from_name
from core.melody_gen import (
    generate_melody, melody_to_pretty_midi,
    StyleTarget, MelodyNote,
    BACH_TARGET, CHOPIN_TARGET, FLOYD_TARGET,
)
from core.audio import prettymidi_to_wav
from core.humanize import humanize, HumanizeConfig
from core.melody import compute_melody_profile

OUT = os.path.dirname(__file__)


def add_note(inst, pitch, start, end, vel=75):
    pitch = max(21, min(108, int(pitch)))
    vel = max(30, min(120, int(vel)))
    if end > start + 0.01:
        inst.notes.append(pretty_midi.Note(velocity=vel, pitch=pitch,
                                           start=float(start), end=float(end)))


# ═══════════════════════════════════════════════════════════════
# BACH — Two voices, generated melody + algorithmic counterpoint
# ═══════════════════════════════════════════════════════════════

def generate_bach():
    BPM = 92  # slower than v1 (108), per Wayne's feedback
    beat = 60.0 / BPM
    scale = from_name('A', 'natural_minor')

    # Generate RH melody (primary voice)
    target_rh = StyleTarget(
        density=3.0, duration_cv=0.08, rhythm_variety=2,
        step_ratio=0.80, leap_probability=0.02,
        direction_change_prob=0.42, target_run_length=2.2,
        pitch_center=72, pitch_range=14, contour_bias=0.0,
        chromaticism=0.0, repetition=0.30,
        phrase_length_beats=4.0, phrase_arc=True,
    )
    rh_notes = generate_melody(scale, target_rh, BPM,
                               total_beats=72, seed=101)

    # Generate LH melody (secondary voice, lower register)
    target_lh = StyleTarget(
        density=2.5, duration_cv=0.10, rhythm_variety=2,
        step_ratio=0.75, leap_probability=0.03,
        direction_change_prob=0.50, target_run_length=1.8,
        pitch_center=57, pitch_range=14, contour_bias=0.0,
        chromaticism=0.0, repetition=0.25,
        phrase_length_beats=4.0, phrase_arc=True,
    )
    lh_notes = generate_melody(scale, target_lh, BPM,
                               total_beats=72, seed=202)

    # LH enters 4 beats late (answer, like a real invention)
    for n in lh_notes:
        n.onset += 4 * beat

    # Build PrettyMIDI
    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    rh_inst = pretty_midi.Instrument(program=0, name='Right Hand')
    lh_inst = pretty_midi.Instrument(program=0, name='Left Hand')

    for n in rh_notes:
        add_note(rh_inst, n.pitch, n.onset, n.onset + n.duration, n.velocity)
    for n in lh_notes:
        add_note(lh_inst, n.pitch, n.onset, n.onset + n.duration, n.velocity)

    pm.instruments.extend([rh_inst, lh_inst])

    # Section boundaries for humanizer (every 8 beats)
    end_time = max(n.onset + n.duration for n in rh_notes + lh_notes)
    sbeats = list(np.arange(0, end_time / beat + 1, 8))

    config = HumanizeConfig(
        bpm=BPM, velocity_jitter=4, phrase_arc_strength=0.06,
        timing_sigma=0.006, default_legato=0.85,
        cadence_rubato=0.04, cadence_window=2.0,
    )
    pm = humanize(pm, config=config, section_beats=sbeats)

    pm.write(os.path.join(OUT, 'bach_v2.mid'))
    prettymidi_to_wav(pm, os.path.join(OUT, 'bach_v2.wav'))
    dur = pm.get_end_time()
    nn = sum(len(i.notes) for i in pm.instruments)
    print(f"  Bach v2: {dur:.1f}s, {nn} notes, BPM={BPM}")
    return pm, rh_notes


# ═══════════════════════════════════════════════════════════════
# CHOPIN — Generated melody + algorithmic arpeggio accompaniment
# ═══════════════════════════════════════════════════════════════

def generate_chopin():
    BPM = 72
    beat = 60.0 / BPM
    eighth = beat / 2
    bar = beat * 4
    scale = from_name('Eb', 'major')

    # Generate melody: long arcs, mostly stepwise, some chromaticism
    target_mel = StyleTarget(
        density=1.2, duration_cv=0.35, rhythm_variety=4,
        step_ratio=0.88, leap_probability=0.0,
        direction_change_prob=0.22, target_run_length=3.2,
        pitch_center=74, pitch_range=14, contour_bias=0.0,
        chromaticism=0.12, repetition=0.15,
        phrase_length_beats=8.0, phrase_arc=True,
    )
    mel_notes = generate_melody(scale, target_mel, BPM,
                                total_beats=64, seed=303)

    # Chord progression: I-vi-IV-V-I-ii-V-I per 8 bars, repeat
    # Eb=51, Cm=48, Ab=56, Bb=58, Fm=53
    chord_prog = [
        (51, 'maj'), (48, 'min'), (56, 'maj'), (53, 'min'),
        (58, 'dom7'), (56, 'maj'), (58, 'dom7'), (51, 'maj'),
    ] * 2  # repeat for 16 bars

    # Build accompaniment: arpeggio per bar
    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    mel_inst = pretty_midi.Instrument(program=0, name='Melody')
    acc_inst = pretty_midi.Instrument(program=0, name='Accompaniment')

    for n in mel_notes:
        add_note(mel_inst, n.pitch, n.onset, n.onset + n.duration, n.velocity)

    ivs = {
        'maj': [0, 4, 7, 12, 16, 12, 7, 4],
        'min': [0, 3, 7, 12, 15, 12, 7, 3],
        'dom7': [0, 4, 7, 10, 16, 12, 7, 4],
    }

    t = 0.0
    for root, quality in chord_prog:
        for iv in ivs.get(quality, ivs['maj']):
            add_note(acc_inst, root + iv, t, t + eighth * 0.88, 42)
            t += eighth

    # Final sustained chord (all in accompaniment to keep melody track clean)
    for p in [51, 58, 63, 67, 75]:
        add_note(acc_inst, p, t, t + bar * 1.5, 45)
    t += bar * 1.5

    pm.instruments.extend([mel_inst, acc_inst])

    end_time = pm.get_end_time()
    sbeats = list(np.arange(0, end_time / beat + 1, 8))

    config = HumanizeConfig(
        bpm=BPM, velocity_jitter=6, phrase_arc_strength=0.12,
        timing_sigma=0.010, default_legato=0.93,
        cadence_rubato=0.10, cadence_window=3.0,
    )
    pm = humanize(pm, config=config, section_beats=sbeats)

    pm.write(os.path.join(OUT, 'chopin_v2.mid'))
    prettymidi_to_wav(pm, os.path.join(OUT, 'chopin_v2.wav'))
    dur = pm.get_end_time()
    nn = sum(len(i.notes) for i in pm.instruments)
    print(f"  Chopin v2: {dur:.1f}s, {nn} notes, BPM={BPM}")
    return pm, mel_notes


# ═══════════════════════════════════════════════════════════════
# FLOYD — Generated lead + pad chords + bass drone
# ═══════════════════════════════════════════════════════════════

def generate_floyd():
    BPM = 76
    beat = 60.0 / BPM
    whole = beat * 4
    scale = from_name('E', 'phrygian')

    # Generate lead: spacious, wide range, high duration contrast
    target_lead = StyleTarget(
        density=0.7, duration_cv=0.90, rhythm_variety=6,
        step_ratio=0.45, leap_probability=0.15,
        direction_change_prob=0.55, target_run_length=1.6,
        pitch_center=67, pitch_range=26, contour_bias=0.0,
        chromaticism=0.20, repetition=0.45,
        phrase_length_beats=8.0, phrase_arc=False,
    )
    lead_notes = generate_melody(scale, target_lead, BPM,
                                 total_beats=72, seed=404)

    # Chords: Em → F → D → Am (classic Phrygian)
    CHORDS = {
        'Em': [40, 47, 52, 55, 59, 64],
        'F':  [41, 48, 53, 57, 60, 65],
        'D':  [38, 45, 50, 54, 57, 62],
        'Am': [45, 52, 57, 60, 64, 69],
    }
    chord_seq = ['Em', 'Em', 'F', 'F', 'Am', 'Am', 'Em', 'Em',
                 'Em', 'F', 'D', 'D', 'Em', 'F', 'Am', 'Em',
                 'Em', 'Em']

    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    lead_inst = pretty_midi.Instrument(program=25, name='Lead Guitar')
    pad_inst  = pretty_midi.Instrument(program=89, name='Pad')
    bass_inst = pretty_midi.Instrument(program=33, name='Bass')

    for n in lead_notes:
        add_note(lead_inst, n.pitch, n.onset, n.onset + n.duration, n.velocity)

    t = 0.0
    for ch_name in chord_seq:
        chord = CHORDS[ch_name]
        for p in chord:
            add_note(pad_inst, p, t, t + whole, 36)
        add_note(bass_inst, chord[0], t, t + whole, 50)
        t += whole

    pm.instruments.extend([lead_inst, pad_inst, bass_inst])

    end_time = pm.get_end_time()
    sbeats = list(np.arange(0, end_time / beat + 1, 8))

    config = HumanizeConfig(
        bpm=BPM, velocity_jitter=8, phrase_arc_strength=0.10,
        timing_sigma=0.014, default_legato=0.92,
        cadence_rubato=0.08, cadence_window=2.5,
        voice_timing_bias={0: 0.005, 1: 0.000, 2: -0.003},
    )
    pm = humanize(pm, config=config, section_beats=sbeats)

    pm.write(os.path.join(OUT, 'floyd_v2.mid'))
    prettymidi_to_wav(pm, os.path.join(OUT, 'floyd_v2.wav'))
    dur = pm.get_end_time()
    nn = sum(len(i.notes) for i in pm.instruments)
    print(f"  Floyd v2: {dur:.1f}s, {nn} notes, BPM={BPM}")
    return pm, lead_notes


# ═══════════════════════════════════════════════════════════════
# EVALUATE
# ═══════════════════════════════════════════════════════════════

def evaluate_melody(name, notes, bpm):
    pitches = [n.pitch for n in notes]
    onsets = [n.onset for n in notes]
    durs = [n.duration for n in notes]
    p = compute_melody_profile(pitches, onsets, durs, bpm)
    print(f"\n  {name}: {len(notes)} notes | "
          f"range={p.pitch_range} step={p.step_ratio:.2f} "
          f"density={p.rhythm_density:.2f} dur_cv={p.duration_cv:.2f} "
          f"dir_ch={p.direction_change_ratio:.2f} "
          f"chrom={p.chromaticism:.2f} run={p.mean_run_length:.2f} "
          f"mode={p.best_mode_display} key={p.estimated_key}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print("=== Experiment 006 v2: Engine-Generated Styles ===\n")

    _, bach_notes = generate_bach()
    _, chopin_notes = generate_chopin()
    _, floyd_notes = generate_floyd()

    print("\n--- Melody Metrics ---")
    evaluate_melody('Bach RH', bach_notes, 92)
    evaluate_melody('Chopin Melody', chopin_notes, 72)
    evaluate_melody('Floyd Lead', floyd_notes, 76)
    print()

"""
Experiment 002: Complete C Major Fugue.

STRUCTURE (following BWV 846 Fugue's general plan):
┌──────────────────────────────────────────────────────┐
│ Section        │ Bars    │ Key       │ Content       │
│────────────────│─────────│───────────│───────────────│
│ Exposition     │ 1-8     │ C → G     │ SATB entries  │
│ Episode 1      │ 9-10    │ G → Am    │ sequence ↓    │
│ Middle Entry 1 │ 11-12   │ Am        │ S in Am       │
│ Episode 2      │ 13-14   │ Am → F    │ sequence ↑    │
│ Middle Entry 2 │ 15-16   │ F         │ T in F        │
│ Episode 3      │ 17-18   │ F → C     │ sequence ↓    │
│ Stretto        │ 19-22   │ C         │ compressed    │
│ Final cadence  │ 23-24   │ C         │ V pedal → I   │
└──────────────────────────────────────────────────────┘

SUBJECT:  C4  E4  D4  G4 | F4  E4  D4  C4  B3  C4
          q.  e   q   q  | e   e   e   e   q   h

COUNTERSUBJECT (designed for invertible counterpoint):
          E4  D4  C4  B3 | C4  D4  E4  F4  G4  E4
          e   e   q   q  | q.  e   q   q   e   h.

Design principle: when subject rises, CS descends (and vice versa).
Rhythmic complement: when subject has long notes, CS has short (and vice versa).
"""

import sys
sys.path.insert(0, '../..')

from core.fugue import (
    Subject, transpose, invert, augment, diminish,
    tonal_answer, real_answer, score_to_midi_events,
    FugueVoice, FugueScore, _fit_to_range, _nearest_diatonic_pc, _nearest,
    evaluate_subject, evaluate_exposition,
)
from core.counterpoint import Note, validate_two_voices
import pretty_midi
import numpy as np
from scipy.io import wavfile


# ═══════════════════════════════════════════════════════════════
# Musical material — Claude's designs
# ═══════════════════════════════════════════════════════════════

KEY_PCS = {0, 2, 4, 5, 7, 9, 11}   # C major

def build_subject():
    """Subject (Dux): arch-shaped C major melody."""
    return Subject.from_pitches(
        pitches=  [60, 64, 62, 67,   65, 64, 62, 60, 59, 60],
        durations=[1.5, 0.5, 1.0, 1.0,  0.5, 0.5, 0.5, 0.5, 1.0, 2.0],
    )

def build_countersubject():
    """
    Countersubject: descends when subject ascends, vice versa.
    Rhythmically complementary.
    """
    return Subject.from_pitches(
        pitches=  [64, 62, 60, 59,   60, 62, 64, 65, 67, 64],
        durations=[0.5, 0.5, 1.0, 1.0,  1.5, 0.5, 1.0, 1.0, 0.5, 1.5],
        # Total: 0.5+0.5+1+1+1.5+0.5+1+1+0.5+1.5 = 9.0 beats ✓ (matches subject)
    )


def build_episode_motif_descending():
    """Episode motif: first 4 notes of subject, used in descending sequence."""
    return Subject.from_pitches(
        pitches=  [67, 65, 64, 62],
        durations=[0.5, 0.5, 0.5, 0.5],  # 2 beats
    )

def build_episode_motif_ascending():
    """Episode motif: inversion — ascending version."""
    return Subject.from_pitches(
        pitches=  [60, 62, 64, 65],
        durations=[0.5, 0.5, 0.5, 0.5],
    )


# ═══════════════════════════════════════════════════════════════
# Episode generation — sequences from motifs
# ═══════════════════════════════════════════════════════════════

def generate_episode(motif: Subject, start_onset: float,
                     steps: list[int], voice: FugueVoice) -> list[Note]:
    """
    Generate an episode as a descending/ascending sequence of a motif.

    Args:
        motif: the fragment to sequence
        start_onset: beat position
        steps: list of transposition intervals for each repetition
        voice: target voice (for range clamping)
    """
    notes = []
    onset = start_onset
    cumulative = 0

    for step in steps:
        cumulative += step
        m = transpose(motif, cumulative, new_onset=onset)
        m = _fit_to_range(m, voice)
        notes.extend(m.notes)
        onset += motif.duration_beats

    return notes


def generate_episode_pair(onset: float, duration: float,
                          upper_voice: FugueVoice, lower_voice: FugueVoice,
                          direction: str = "down",
                          key_pcs: set = KEY_PCS) -> tuple[list[Note], list[Note]]:
    """
    Generate a 2-voice episode with interlocking sequential motifs.

    One voice sequences the motif down, the other sequences a
    complementary pattern up (or vice versa).
    """
    n_reps = int(duration / 2)  # each motif = 2 beats

    if direction == "down":
        upper_steps = [0, -2, -2, -2][:n_reps]   # descending by steps
        lower_steps = [0, -2, -2, -2][:n_reps]
        upper_motif = build_episode_motif_descending()
        lower_motif = build_episode_motif_ascending()
    else:
        upper_steps = [0, 2, 2, 2][:n_reps]
        lower_steps = [0, 2, 2, 2][:n_reps]
        upper_motif = build_episode_motif_ascending()
        lower_motif = build_episode_motif_descending()

    upper_notes = generate_episode(upper_motif, onset, upper_steps, upper_voice)
    lower_notes = generate_episode(lower_motif, onset, lower_steps, lower_voice)

    return upper_notes, lower_notes


# ═══════════════════════════════════════════════════════════════
# Stretto — compressed subject entries
# ═══════════════════════════════════════════════════════════════

def build_stretto(subject: Subject, onset: float,
                  voices: list[FugueVoice],
                  entry_delay: float = 4.0,
                  voice_indices: list[int] = None) -> dict[int, list[Note]]:
    """
    Build a stretto section: subject entries overlapping.

    The magic of stretto: voice 2 enters before voice 1 finishes.
    entry_delay < subject.duration_beats → overlap.
    """
    if voice_indices is None:
        voice_indices = [1, 0, 2, 3]  # Alto, Soprano, Tenor, Bass

    result = {}
    t = onset
    for i, vi in enumerate(voice_indices):
        # Alternate between subject and answer (transposed for variety)
        if i % 2 == 0:
            entry = transpose(subject, 0, new_onset=t)
        else:
            entry = transpose(subject, 7, new_onset=t)  # P5 up

        entry = _fit_to_range(entry, voices[vi])
        result[vi] = entry.notes
        t += entry_delay

    return result


# ═══════════════════════════════════════════════════════════════
# Final cadence — dominant pedal → resolution
# ═══════════════════════════════════════════════════════════════

def build_final_cadence(onset: float, voices: list[FugueVoice],
                        key_pcs: set = KEY_PCS) -> dict[int, list[Note]]:
    """
    Build a final cadence section.

    Bass: dominant pedal (G) for 4 beats, then tonic (C) whole note
    Upper voices: converge toward tonic triad via contrary motion
    """
    result = {}

    # Bass: G pedal → C resolution
    result[3] = [
        Note(midi=43, onset=onset, duration=4.0),        # G2 pedal
        Note(midi=36, onset=onset + 4.0, duration=4.0),   # C2 final
    ]

    # Tenor: G3 pedal (dominant) then resolve — avoids parallel 5ths with soprano
    # Fixed: was stepwise G3→F3→E3 creating parallel 5ths with soprano D5→C5→B4
    result[2] = [
        Note(midi=55, onset=onset, duration=3.0),         # G3 held (oblique vs soprano)
        Note(midi=50, onset=onset + 3.0, duration=1.0),   # D3
        Note(midi=48, onset=onset + 4.0, duration=4.0),   # C3 final
    ]

    # Alto: chromatic approach to E4
    result[1] = [
        Note(midi=62, onset=onset, duration=2.0),         # D4
        Note(midi=61, onset=onset + 2.0, duration=1.0),   # C#4 (chromatic!)
        Note(midi=62, onset=onset + 3.0, duration=1.0),   # D4
        Note(midi=64, onset=onset + 4.0, duration=4.0),   # E4 final
    ]

    # Soprano: leading tone → tonic resolution
    result[0] = [
        Note(midi=74, onset=onset, duration=1.0),         # D5
        Note(midi=72, onset=onset + 1.0, duration=1.0),   # C5
        Note(midi=71, onset=onset + 2.0, duration=2.0),   # B4 (leading tone!)
        Note(midi=72, onset=onset + 4.0, duration=4.0),   # C5 final (resolution)
    ]

    return result


# ═══════════════════════════════════════════════════════════════
# Full fugue assembly
# ═══════════════════════════════════════════════════════════════

def build_full_fugue():
    """
    Assemble a complete C major fugue.

    Structure:
    - Exposition (bars 1-8): 4 entries, subject + countersubject
    - Episode 1 (bars 9-10): descending sequence
    - Middle Entry 1 (bars 11-12): subject in A minor
    - Episode 2 (bars 13-14): ascending sequence
    - Middle Entry 2 (bars 15-16): subject in F major
    - Episode 3 (bars 17-18): descending sequence back to C
    - Stretto (bars 19-22): compressed entries
    - Final cadence (bars 23-24): dominant pedal → tonic
    """
    subject = build_subject()
    cs = build_countersubject()
    answer = tonal_answer(subject, KEY_PCS)

    # Create 4 voices
    voice_names = ["Soprano", "Alto", "Tenor", "Bass"]
    voices = []
    for name in voice_names:
        from core.fugue import VOICE_RANGES
        low, high = VOICE_RANGES[name]
        voices.append(FugueVoice(name=name, range_low=low, range_high=high))

    S_DUR = subject.duration_beats  # 9.0 beats
    t = 0.0  # current beat position

    # ── EXPOSITION (bars 1-8) ──
    # Entry 1: Alto plays subject
    alto_entry = transpose(subject, 0, new_onset=t)
    voices[1].add_notes(alto_entry.notes)

    t += S_DUR  # t = 9.0

    # Entry 2: Soprano plays answer, Alto plays countersubject
    sop_entry = transpose(answer, 0, new_onset=t)
    sop_entry = _fit_to_range(sop_entry, voices[0])
    voices[0].add_notes(sop_entry.notes)

    alto_cs = transpose(cs, 0, new_onset=t)
    voices[1].add_notes(alto_cs.notes)

    t += S_DUR  # t = 18.0

    # Entry 3: Tenor plays subject (octave lower), Alto+Soprano play counterpoint
    tenor_entry = transpose(subject, -12, new_onset=t)
    tenor_entry = _fit_to_range(tenor_entry, voices[2])
    voices[2].add_notes(tenor_entry.notes)

    # Soprano plays countersubject (transposed to fit soprano range)
    sop_cs = transpose(cs, 12, new_onset=t)
    sop_cs = _fit_to_range(sop_cs, voices[0])
    voices[0].add_notes(sop_cs.notes)

    # Alto plays free counterpoint (inverted countersubject fragment)
    alto_free = transpose(invert(cs), 0, new_onset=t)
    alto_free = _fit_to_range(alto_free, voices[1])
    voices[1].add_notes(alto_free.notes)

    t += S_DUR  # t = 27.0

    # Entry 4: Bass plays answer, upper voices play counterpoint
    bass_entry = transpose(answer, -12, new_onset=t)
    bass_entry = _fit_to_range(bass_entry, voices[3])
    voices[3].add_notes(bass_entry.notes)

    # Tenor plays countersubject
    tenor_cs = transpose(cs, -12, new_onset=t)
    tenor_cs = _fit_to_range(tenor_cs, voices[2])
    voices[2].add_notes(tenor_cs.notes)

    # Alto plays free counterpoint (subject fragment, augmented)
    alto_aug = augment(Subject.from_pitches(
        [64, 62, 60, 59, 60],
        [1.0, 1.0, 1.0, 1.0, 1.0],
    ), factor=1.8, new_onset=t)
    alto_aug = _fit_to_range(alto_aug, voices[1])
    voices[1].add_notes(alto_aug.notes)

    # Soprano: descending line (contrary to bass answer's ascent)
    voices[0].add_notes([
        Note(midi=76, onset=t, duration=2.0),       # E5 (high, then descend)
        Note(midi=74, onset=t+2, duration=2.0),     # D5
        Note(midi=72, onset=t+4, duration=2.0),     # C5
        Note(midi=71, onset=t+6, duration=1.0),     # B4
        Note(midi=72, onset=t+7, duration=2.0),     # C5 resolution
    ])

    t += S_DUR  # t = 36.0

    # ── EPISODE 1 (bars 9-10) — descending sequence ──
    ep1_dur = 8.0  # 2 bars of 4/4

    # Soprano + Alto: interlocking descending sequence
    desc_motif = build_episode_motif_descending()
    asc_motif = build_episode_motif_ascending()

    # Soprano: descending sequence
    sop_ep1 = []
    for i in range(4):
        m = transpose(desc_motif, -2 * i, new_onset=t + i * 2.0)
        m = _fit_to_range(m, voices[0])
        sop_ep1.extend(m.notes)
    voices[0].add_notes(sop_ep1)

    # Alto: complementary ascending then plateau
    alto_ep1 = []
    for i in range(4):
        m = transpose(asc_motif, -2 * i, new_onset=t + i * 2.0)
        m = _fit_to_range(m, voices[1])
        alto_ep1.extend(m.notes)
    voices[1].add_notes(alto_ep1)

    # Tenor: descending long notes (harmonic foundation)
    voices[2].add_notes([
        Note(midi=60, onset=t, duration=2.0),        # C4
        Note(midi=59, onset=t+2, duration=2.0),       # B3
        Note(midi=57, onset=t+4, duration=2.0),       # A3
        Note(midi=55, onset=t+6, duration=2.0),       # G3
    ])

    # Bass: contrary motion (ascending) to avoid parallel octaves with tenor
    voices[3].add_notes([
        Note(midi=43, onset=t, duration=2.0),         # G2
        Note(midi=45, onset=t+2, duration=2.0),       # A2
        Note(midi=47, onset=t+4, duration=2.0),       # B2
        Note(midi=48, onset=t+6, duration=2.0),       # C3
    ])

    t += ep1_dur  # t = 44.0

    # ── MIDDLE ENTRY 1 (bars 11-12) — subject in A minor ──
    # Soprano plays subject transposed to A minor (-3 semitones)
    sop_mid1 = transpose(subject, -3, new_onset=t)
    sop_mid1 = _fit_to_range(sop_mid1, voices[0])
    voices[0].add_notes(sop_mid1.notes)

    # Alto: countersubject in A minor
    alto_mid1 = transpose(cs, -3, new_onset=t)
    alto_mid1 = _fit_to_range(alto_mid1, voices[1])
    voices[1].add_notes(alto_mid1.notes)

    # Tenor: sustained notes
    voices[2].add_notes([
        Note(midi=57, onset=t, duration=3.0),      # A3
        Note(midi=55, onset=t+3, duration=3.0),     # G3
        Note(midi=53, onset=t+6, duration=3.0),     # F3
    ])

    # Bass: A minor bass line
    voices[3].add_notes([
        Note(midi=45, onset=t, duration=4.5),       # A2
        Note(midi=43, onset=t+4.5, duration=4.5),   # G2
    ])

    t += S_DUR  # t = 53.0

    # ── EPISODE 2 (bars 13-14) — ascending sequence ──
    ep2_dur = 8.0

    # Alto + Tenor: ascending sequential motifs
    for i in range(4):
        m_a = transpose(asc_motif, 2 * i, new_onset=t + i * 2.0)
        m_a = _fit_to_range(m_a, voices[1])
        voices[1].add_notes(m_a.notes)

        m_t = transpose(desc_motif, 2 * i - 12, new_onset=t + i * 2.0)
        m_t = _fit_to_range(m_t, voices[2])
        voices[2].add_notes(m_t.notes)

    # Soprano: held notes
    voices[0].add_notes([
        Note(midi=69, onset=t, duration=4.0),       # A4
        Note(midi=67, onset=t+4, duration=4.0),     # G4
    ])

    # Bass: pedal then step (avoids parallels with tenor sequence)
    voices[3].add_notes([
        Note(midi=41, onset=t, duration=4.0),       # F2 pedal
        Note(midi=43, onset=t+4, duration=2.0),     # G2
        Note(midi=45, onset=t+6, duration=2.0),     # A2
    ])

    t += ep2_dur  # t = 61.0

    # ── MIDDLE ENTRY 2 (bars 15-16) — subject in F major ──
    # Tenor plays subject in F major (-7 semitones = P4 down)
    tenor_mid2 = transpose(subject, 5, new_onset=t)  # +5 = F
    tenor_mid2 = _fit_to_range(tenor_mid2, voices[2])
    voices[2].add_notes(tenor_mid2.notes)

    # Bass: countersubject in F
    bass_mid2 = transpose(cs, 5 - 12, new_onset=t)
    bass_mid2 = _fit_to_range(bass_mid2, voices[3])
    voices[3].add_notes(bass_mid2.notes)

    # Soprano: free counterpoint — descend then return, contrary to tenor in F major
    # Avoid parallel 5th (orig G4→F4 vs tenor C4→Bb3) and parallel 8ve (A4→G4 vs A3→G3)
    # Solution: hold A4, then ascend B4 (contrary to tenor's descent)
    voices[0].add_notes([
        Note(midi=72, onset=t, duration=1.5),          # C5
        Note(midi=71, onset=t+1.5, duration=0.5),      # B4
        Note(midi=69, onset=t+2, duration=1.0),         # A4
        Note(midi=69, onset=t+3, duration=1.0),         # A4 (oblique vs tenor C4)
        Note(midi=71, onset=t+4, duration=1.0),         # B4 (↑ contrary to tenor Bb3↓)
        Note(midi=69, onset=t+5, duration=1.0),         # A4
        Note(midi=71, onset=t+6, duration=1.5),         # B4
        Note(midi=72, onset=t+7.5, duration=1.5),       # C5 (return)
    ])

    # Alto: held thirds
    voices[1].add_notes([
        Note(midi=65, onset=t, duration=3.0),       # F4
        Note(midi=64, onset=t+3, duration=3.0),     # E4
        Note(midi=62, onset=t+6, duration=3.0),     # D4
    ])

    t += S_DUR  # t = 70.0

    # ── EPISODE 3 (bars 17-18) — return to C major ──
    ep3_dur = 8.0

    # All voices: descending sequence leading back to C
    for i in range(4):
        m = transpose(desc_motif, -1 * i, new_onset=t + i * 2.0)
        m = _fit_to_range(m, voices[0])
        voices[0].add_notes(m.notes)

    voices[1].add_notes([
        Note(midi=64, onset=t, duration=2.0),
        Note(midi=62, onset=t+2, duration=2.0),
        Note(midi=60, onset=t+4, duration=2.0),
        Note(midi=59, onset=t+6, duration=2.0),
    ])

    voices[2].add_notes([
        Note(midi=55, onset=t, duration=2.0),
        Note(midi=53, onset=t+2, duration=2.0),
        Note(midi=52, onset=t+4, duration=2.0),
        Note(midi=50, onset=t+6, duration=2.0),
    ])

    # Bass: contrary motion at end to avoid parallel 5th with tenor E3→D3
    # Fixed: last note ascends B2 instead of descending G2
    voices[3].add_notes([
        Note(midi=48, onset=t, duration=2.0),          # C3
        Note(midi=47, onset=t+2, duration=2.0),         # B2
        Note(midi=45, onset=t+4, duration=2.0),         # A2
        Note(midi=47, onset=t+6, duration=2.0),         # B2 (was G2 → parallel 5th w/ tenor)
    ])

    t += ep3_dur  # t = 78.0

    # ── STRETTO (bars 19-22) — compressed entries ──
    stretto_delay = 4.5  # overlap: entry every 4.5 beats (subject = 9 beats)

    # Alto enters first with subject
    stretto_alto = transpose(subject, 0, new_onset=t)
    stretto_alto = _fit_to_range(stretto_alto, voices[1])
    voices[1].add_notes(stretto_alto.notes)

    # Soprano enters 4.5 beats later with subject (up a 4th)
    stretto_sop = transpose(subject, 5, new_onset=t + stretto_delay)
    stretto_sop = _fit_to_range(stretto_sop, voices[0])
    voices[0].add_notes(stretto_sop.notes)

    # Tenor enters 4.5 beats after soprano with subject (down an octave)
    stretto_tenor = transpose(subject, -12, new_onset=t + stretto_delay * 2)
    stretto_tenor = _fit_to_range(stretto_tenor, voices[2])
    voices[2].add_notes(stretto_tenor.notes)

    # Bass: dominant pedal under the stretto
    stretto_total = stretto_delay * 2 + S_DUR
    voices[3].add_notes([
        Note(midi=43, onset=t, duration=stretto_total),   # G2 pedal
    ])

    t += stretto_total  # t = 78 + 4.5*2 + 9 = 96.0

    # ── FINAL CADENCE (bars 23-24) ──
    cadence_notes = build_final_cadence(t, voices)
    for vi, notes in cadence_notes.items():
        voices[vi].add_notes(notes)

    t += 8.0  # cadence = 8 beats

    return FugueScore(voices=voices, key_str="C", tempo=80)


# ═══════════════════════════════════════════════════════════════
# MIDI export
# ═══════════════════════════════════════════════════════════════

def score_to_prettymidi(score: FugueScore) -> pretty_midi.PrettyMIDI:
    """Convert FugueScore to PrettyMIDI with one instrument per voice."""
    bpm = score.tempo
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    for voice in score.voices:
        inst = pretty_midi.Instrument(program=0, name=voice.name)
        for n in voice.notes:
            onset_sec = n.onset * 60.0 / bpm
            offset_sec = (n.onset + n.duration) * 60.0 / bpm
            midi_note = pretty_midi.Note(
                velocity=75 + (5 if "Soprano" in voice.name else 0),
                pitch=max(21, min(108, n.midi)),  # clamp to piano range
                start=onset_sec,
                end=offset_sec,
            )
            inst.notes.append(midi_note)
        pm.instruments.append(inst)

    return pm


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("Experiment 002: Complete C Major Fugue")
    print("  >> Subject + countersubject by Claude")
    print("  >> Assembled by fugue engine")
    print("=" * 60)

    # 1. Subject quality
    subject = build_subject()
    cs = build_countersubject()
    print("\n1. Subject & Countersubject...")
    quality = evaluate_subject(subject)
    print(f"   Subject: {' '.join(n.name for n in subject.notes)}")
    print(f"   Quality: {quality['total_score']}/{quality['max_score']} ({quality['percentage']}%)")
    print(f"   CS:      {' '.join(n.name for n in cs.notes)}")

    # Verify CS is same duration as subject
    assert abs(cs.duration_beats - subject.duration_beats) < 0.01, \
        f"CS duration {cs.duration_beats} != Subject duration {subject.duration_beats}"
    print(f"   Duration match: ✓ ({subject.duration_beats} beats each)")

    # 2. Build full fugue
    print("\n2. Assembling full fugue...")
    score = build_full_fugue()

    total_notes = sum(len(v.notes) for v in score.voices)
    total_dur = max(n.onset + n.duration for v in score.voices for n in v.notes)
    for v in score.voices:
        if v.notes:
            print(f"   {v.name:10s}: {len(v.notes):3d} notes, "
                  f"range {min(n.midi for n in v.notes)}-{max(n.midi for n in v.notes)}, "
                  f"onset {v.notes[0].onset:.0f}-{v.notes[-1].onset + v.notes[-1].duration:.0f}")

    print(f"   Total: {total_notes} notes, {total_dur:.0f} beats "
          f"({total_dur / 4:.0f} bars)")

    # 3. Counterpoint validation
    print("\n3. Counterpoint validation...")
    report = evaluate_exposition(score, verbose=True)

    # 4. Export
    print("\n4. Generating MIDI & WAV...")
    pm = score_to_prettymidi(score)
    pm.write("output.mid")
    duration_sec = pm.get_end_time()
    print(f"   MIDI: output.mid ({duration_sec:.1f}s)")

    audio = pm.synthesize(fs=44100)
    audio = audio / (np.max(np.abs(audio)) + 1e-8)
    wavfile.write("output.wav", 44100, (audio * 32767).astype(np.int16))
    print(f"   WAV:  output.wav ({duration_sec:.1f}s)")

    # 5. Structure summary
    print("\n5. Structure:")
    sections = [
        ("Exposition",    0, 36),
        ("Episode 1",     36, 44),
        ("Middle Entry 1", 44, 53),
        ("Episode 2",     53, 61),
        ("Middle Entry 2", 61, 70),
        ("Episode 3",     70, 78),
        ("Stretto",       78, 96),
        ("Final Cadence", 96, 104),
    ]
    for name, start, end in sections:
        dur_bars = (end - start) / 4
        print(f"   {name:20s} bars {start/4+1:.0f}-{end/4:.0f} ({dur_bars:.0f} bars)")

    print("\n" + "=" * 60)
    print("Done! Import output.mid into GarageBand for better sound.")
    print("=" * 60)


if __name__ == "__main__":
    main()

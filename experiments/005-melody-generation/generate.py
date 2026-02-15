"""
Experiment 005: Metric-Guided Melody Generation

The acid test: Can Claude compose a single-voice melody that
(a) targets specific metric ranges for a genre, and
(b) actually sounds like that genre?

Attempt 1: C-pop ballad verse (8 bars, G major, 72 BPM)

Design rationale:
- Pentatonic leaning (G A B D E) with passing tones (C, F#)
- Verse starts low/mid, builds gently toward chorus register
- Phrase structure: 2+2+2+2 bars (question-answer-climb-settle)
- Rhythmic feel: mix of 8ths and quarters, held notes at phrase ends
- Emotional arc: 寂静 → 叙述 → 情绪推进 → 收束

Target metrics (pop genre):
  pitch_range:      9-13 semitones
  step_ratio:       0.65-0.95
  direction_change: 0.15-0.50
  pitch_entropy:    2.2-2.6 bits
  rhythm_density:   0.8-1.6 notes/beat
  tonal_clarity:    0.64-0.95
"""
import sys
sys.path.insert(0, "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero")

import pretty_midi
import numpy as np
from core.melody import compute_melody_profile, summarize
from core.audio import prettymidi_to_wav
from core.midi_export import save_midi

# ═══════════════════════════════════════════════════════════════
# Melody composition — C-pop ballad verse
# Key: G major   BPM: 72   Time: 4/4   Bars: 8
# ═══════════════════════════════════════════════════════════════

BPM = 72
KEY = "G major"

# Pitch reference: E4=64 F#4=66 G4=67 A4=69 B4=71 C5=72 D5=74 E5=76

# Format: (MIDI pitch, onset in beats, duration in beats)
# Designed to sound like a 华语 ballad verse
#
# Phrase 1 (bars 1-2): 开场叙述 — gentle, low register
# "在某个安静的夜里" — conversational, small steps
PHRASE_1 = [
    (67, 0.0,  0.5),   # G4 — 起音
    (69, 0.5,  0.5),   # A4 — step up
    (71, 1.0,  1.0),   # B4 — linger
    (69, 2.0,  0.5),   # A4 — step back
    (67, 2.5,  1.5),   # G4 — settle (held into bar 2)
    (64, 4.0,  1.0),   # E4 — drop to low register, breath
    (67, 5.0,  0.5),   # G4 — bounce back
    (69, 5.5,  0.5),   # A4
    (71, 6.0,  1.0),   # B4 — phrase end, pentatonic 5th
    (69, 7.0,  1.0),   # A4 — gentle resolution
]

# Phrase 2 (bars 3-4): 情感铺垫 — reach higher, pull back
# "想起了那些过去的事" — starts to feel something
PHRASE_2 = [
    (71, 8.0,  0.5),   # B4 — pick up from A4
    (74, 8.5,  1.5),   # D5 — jump to 5th (pentatonic), hold
    (71, 10.0, 0.5),   # B4 — step back
    (69, 10.5, 0.5),   # A4
    (67, 11.0, 1.0),   # G4 — descend to root
    (69, 12.0, 0.5),   # A4 — echo: reach again
    (71, 12.5, 0.5),   # B4
    (72, 13.0, 0.5),   # C5 — passing tone! first non-pentatonic note
    (71, 13.5, 0.5),   # B4 — resolve chromatic neighbor
    (69, 14.0, 2.0),   # A4 — settle, half-cadence feel
]

# Phrase 3 (bars 5-6): 情绪推高 — reach the peak
# "心里那些说不出的话" — emotional push
PHRASE_3 = [
    (67, 16.0, 0.5),   # G4 — restart from root
    (69, 16.5, 0.5),   # A4
    (71, 17.0, 0.5),   # B4
    (74, 17.5, 0.5),   # D5 — ascending run
    (76, 18.0, 2.0),   # E5 — PEAK! held — emotional climax of verse
    (74, 20.0, 0.5),   # D5 — begin descent
    (71, 20.5, 0.5),   # B4
    (69, 21.0, 1.0),   # A4
    (67, 22.0, 2.0),   # G4 — long landing
]

# Phrase 4 (bars 7-8): 收束等待 — resolve, hint at chorus
# "也许明天会不一样" — acceptance, open ending
PHRASE_4 = [
    (69, 24.0, 1.0),   # A4 — gentle restart
    (71, 25.0, 0.5),   # B4
    (74, 25.5, 1.0),   # D5 — one last reach
    (72, 26.5, 0.5),   # C5 — chromatic passing tone
    (71, 27.0, 1.0),   # B4 — resolve
    (69, 28.0, 0.5),   # A4
    (67, 28.5, 0.5),   # G4
    (64, 29.0, 1.0),   # E4 — dip to low 6th
    (67, 30.0, 2.0),   # G4 — final rest on tonic
]

ALL_NOTES = PHRASE_1 + PHRASE_2 + PHRASE_3 + PHRASE_4


def create_midi(notes, bpm):
    """Convert (pitch, onset_beats, dur_beats) to PrettyMIDI."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0, name="Melody")

    beat_dur = 60.0 / bpm

    for pitch, onset_beat, dur_beat in notes:
        start = onset_beat * beat_dur
        end = start + dur_beat * beat_dur
        # Gentle velocity — ballad dynamic, slight phrase shaping
        # Phrase 3 is louder (emotional peak), phrase 4 softer
        if 16 <= onset_beat < 24:
            vel = 80  # climax
        elif 24 <= onset_beat:
            vel = 65  # resolution
        elif 8 <= onset_beat < 16:
            vel = 72  # building
        else:
            vel = 68  # gentle opening

        note = pretty_midi.Note(velocity=vel, pitch=pitch, start=start, end=end)
        inst.notes.append(note)

    pm.instruments.append(inst)
    return pm


def beats_to_seconds(beats, bpm):
    return [b * 60.0 / bpm for b in beats]


def run():
    print("=" * 60)
    print("EXPERIMENT 005: Metric-Guided Melody Generation")
    print("Attempt 1: C-pop Ballad Verse (G major, 72 BPM)")
    print("=" * 60)

    # ── Extract arrays for metrics ──
    pitches = [n[0] for n in ALL_NOTES]
    onsets_beats = [n[1] for n in ALL_NOTES]
    durs_beats = [n[2] for n in ALL_NOTES]

    onsets_sec = beats_to_seconds(onsets_beats, BPM)
    durs_sec = beats_to_seconds(durs_beats, BPM)

    print(f"\nMelody stats:")
    print(f"  Notes: {len(pitches)}")
    print(f"  Duration: {max(onsets_beats) + max(durs_beats):.1f} beats = "
          f"{(max(onsets_beats) + max(durs_beats)) * 60.0 / BPM:.1f}s")
    print(f"  Pitch range: {min(pitches)} ({pretty_midi.note_number_to_name(min(pitches))}) — "
          f"{max(pitches)} ({pretty_midi.note_number_to_name(max(pitches))})")
    print(f"  Unique pitches: {sorted(set(pitches))}")
    print(f"  Unique pitch classes: {sorted(set(p % 12 for p in pitches))}")

    # ── Compute metrics ──
    print("\n" + "-" * 60)
    print("METRIC VALIDATION")
    print("-" * 60)

    profile = compute_melody_profile(pitches, onsets_sec, durs_sec, bpm=BPM)
    print(summarize(profile, genre="pop"))

    # ── Genre fit detail ──
    fit = profile.genre_fit("pop")
    n_pass = sum(1 for v in fit.values() if v.startswith("OK"))
    n_total = len(fit)
    print(f"\n{'='*60}")
    print(f"GENRE FIT: {n_pass}/{n_total} metrics in pop range")
    print(f"{'='*60}")
    for k, v in fit.items():
        status = "✓" if v.startswith("OK") else "✗"
        print(f"  {status} {k}: {v}")

    # ── Cross-genre check ──
    print(f"\n{'='*60}")
    print("CROSS-GENRE CHECK (does it fit OTHER genres?)")
    print(f"{'='*60}")
    for genre in ["baroque", "romantic"]:
        gfit = profile.genre_fit(genre)
        gpass = sum(1 for v in gfit.values() if v == "OK")
        gtot = len(gfit)
        misses = {k: v for k, v in gfit.items() if v != "OK"}
        print(f"  {genre}: {gpass}/{gtot} {'(!!!)' if gpass >= n_pass else ''}")
        if misses:
            for k, v in misses.items():
                print(f"    ✗ {k}: {v}")

    # ── Generate MIDI + WAV ──
    print(f"\n{'='*60}")
    print("RENDERING")
    print(f"{'='*60}")

    pm = create_midi(ALL_NOTES, BPM)

    midi_path = "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero/experiments/005-melody-generation/cpop_verse_v1.mid"
    wav_path = "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero/experiments/005-melody-generation/cpop_verse_v1.wav"

    save_midi(pm, midi_path)
    prettymidi_to_wav(pm, wav_path)

    print(f"\nDone! Listen to: {wav_path}")

    return profile


if __name__ == "__main__":
    run()

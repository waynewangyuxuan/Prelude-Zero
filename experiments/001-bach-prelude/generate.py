"""
Experiment 001: Generate a new C Major Prelude in the style of BWV 846.

INPUT (Claude's "proposal"):
- Key: C major
- Structure: ~34 bars, one chord per bar, BWV 846 arpeggiation pattern
- Harmonic language: Baroque — diatonic core, secondary dominants,
  diminished approaches, pedal points
- Dramatic arc inspired by BWV 846:
  Statement → Expansion → Return → Tension → Pedal → Resolution

DESIGN NOTES:
Claude designed this progression drawing on Baroque harmonic conventions:
1. Opens with clear I–IV–V–I to establish key (like BWV 846 but different chords)
2. Sequences through related keys (vi, then briefly tonicize ii)
3. Chromatic approach chords (diminished 7ths) for color
4. Dominant pedal section for climactic tension
5. Tonic pedal for final resolution
6. Avoids direct copying of BWV 846's specific progression
7. Uses seventh chords liberally (Baroque style)
8. Smooth bass line — stepwise and by third where possible
"""

import sys
sys.path.insert(0, '../..')

from core.chords import chord_pitches_with_bass
from core.patterns import arpeggiate_bwv846
from core.midi_export import progression_to_midi, save_midi
from core.voice_leading import validate_progression
from core.humanize import apply_velocity_curve, apply_timing_jitter, apply_agogic
from core.audio import prettymidi_to_wav

# ══════════════════════════════════════════════════════════════
# Claude's harmonic proposal: a new C Major Prelude
# ══════════════════════════════════════════════════════════════

PROGRESSION = [
    # (bar, roman, bass_note, function_note)

    # ── Section A: Statement (mm. 1–4) ──
    # Establish C major clearly, but start with a warmer I–vi–IV–V–I arc
    ("I",       "C"),    # 1  Tonic
    ("vi7",     "A"),    # 2  Tonic substitute — deeper start than BWV 846
    ("IV",      "F"),    # 3  Subdominant
    ("V7",      "G"),    # 4  Dominant → back to I

    # ── Section B: Expansion with sequence (mm. 5–10) ──
    # Circle-of-fifths sequence: I → IV → viio → iii → vi → ii → V
    ("I",       "C"),    # 5  Tonic return
    ("IVmaj7",  "F"),    # 6  Subdominant with color
    ("viio",    "B"),    # 7  Leading-tone triad (tension)
    ("iii",     "E"),    # 8  Mediant — unusual, gives modal color
    ("vi7",     "A"),    # 9  Submediant
    ("ii7",     "D"),    # 10 Supertonic

    # ── Section C: Tonicize V (mm. 11–14) ──
    ("V",       "G"),    # 11 Dominant (as new "tonic")
    ("V7/V",    "D"),    # 12 Secondary dominant
    ("V",       "G"),    # 13 Confirm V
    ("viio7/V", "F#"),   # 14 Diminished approach to V

    # ── Section D: Return journey (mm. 15–20) ──
    ("V7",      "G"),    # 15 Dominant
    ("I6",      "E"),    # 16 Tonic first inversion — smooth bass
    ("IVmaj7",  "F"),    # 17 Subdominant
    ("ii7",     "D"),    # 18 Supertonic
    ("V7",      "G"),    # 19 Dominant
    ("I",       "C"),    # 20 Tonic — big return

    # ── Section E: Tonicize IV, build tension (mm. 21–25) ──
    ("V7/IV",   "C"),    # 21 Secondary dominant (= C7)
    ("IV",      "F"),    # 22 Subdominant
    ("viio7",   "B"),    # 23 Diminished 7th — dark turn
    ("viio7/V", "F#"),   # 24 Another dim7 — chromatic descent in bass
    ("V7",      "G"),    # 25 Dominant arrival

    # ── Section F: Dominant pedal (mm. 26–30) ──
    ("I6/4",    "G"),    # 26 Cadential 6/4 over G pedal
    ("V7",      "G"),    # 27 Dominant 7th
    ("vi",      "G"),    # 28 Deceptive hint over pedal (vi/G)
    ("V7",      "G"),    # 29 Back to dominant
    ("V9",      "G"),    # 30 Dominant 9th — maximum tension

    # ── Section G: Tonic pedal & resolution (mm. 31–34) ──
    ("I",       "C"),    # 31 Tonic pedal begins
    ("IV",      "C"),    # 32 Subdominant over tonic pedal (plagal color)
    ("V7",      "C"),    # 33 Dominant over tonic pedal
    ("I",       "C"),    # 34 Final tonic
]


def build_measures():
    """Convert the progression into measure dicts for the MIDI exporter.
    Uses smooth voice leading: each chord's upper voices stay close to
    the previous chord's upper voices."""
    measures = []
    prev_upper = None
    for roman_str, bass_note in PROGRESSION:
        ch = chord_pitches_with_bass(
            roman_str, "C",
            bass_note=bass_note,
            octave_bass=3,
            octave_upper=4,
            prev_upper=prev_upper,
        )
        measures.append(ch)
        prev_upper = ch["upper"]
    return measures


def main():
    print("=" * 60)
    print("Experiment 001: New C Major Prelude (Bach-style)")
    print("=" * 60)

    # 1. Build chord progression
    print("\n1. Building chord progression...")
    measures = build_measures()
    print(f"   {len(measures)} measures")

    # 2. Voice leading validation
    print("\n2. Validating voice leading...")
    chords_for_validation = []
    for m in measures:
        full_chord = sorted([m["bass"]] + m["upper"])
        chords_for_validation.append(full_chord)
    result = validate_progression(chords_for_validation, verbose=True)

    # 3. Generate MIDI
    print("\n3. Generating MIDI...")
    pm = progression_to_midi(
        measures,
        pattern_fn=arpeggiate_bwv846,
        bpm=66,
        program=0,  # Acoustic Grand Piano
    )

    # 4. Apply humanization
    print("\n4. Applying humanization...")
    for inst in pm.instruments:
        apply_velocity_curve(inst, "phrase_arc")
        apply_timing_jitter(inst, sigma=0.006)
        apply_agogic(inst, "baroque")

    # 5. Save outputs
    print("\n5. Saving outputs...")
    midi_path = "output.mid"
    wav_path = "output.wav"
    save_midi(pm, midi_path)
    prettymidi_to_wav(pm, wav_path)

    print("\n" + "=" * 60)
    print("Done! Listen to output.wav or import output.mid into GarageBand.")
    print("=" * 60)


if __name__ == "__main__":
    main()

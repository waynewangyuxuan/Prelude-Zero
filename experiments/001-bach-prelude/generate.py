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

from core.voicing import voice_lead_progression, validate_voice_led_progression
from core.patterns import arpeggiate_bwv846
from core.midi_export import progression_to_midi, save_midi
from core.humanize import humanize, compare, HumanizeConfig
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
    """Convert the progression using the vector-based voicing engine.
    Exhaustive search over all valid voicings, guaranteed no parallel 5ths/8ves."""
    voiced = voice_lead_progression(
        PROGRESSION,
        key_str="C",
        bass_octave=3,
        n_upper=3,  # SATB: bass + 3 upper voices
    )
    # Convert to the format expected by midi_export
    measures = []
    for v in voiced:
        measures.append({
            "roman": v["roman"],
            "bass": v["bass"],
            "upper": v["upper"],
        })
    return measures, voiced


def main():
    print("=" * 60)
    print("Experiment 001: New C Major Prelude (Bach-style)")
    print("  >> Using vector-based voicing engine (v2)")
    print("=" * 60)

    # 1. Build chord progression with optimal voice leading
    print("\n1. Building chord progression (vector-based voicing)...")
    measures, voiced = build_measures()
    print(f"   {len(measures)} measures, SATB (4 voices)")

    # 2. Voice leading validation
    print("\n2. Validating voice leading...")
    result = validate_voice_led_progression(voiced, verbose=True)

    # 3. Generate MIDI
    print("\n3. Generating MIDI...")
    pm = progression_to_midi(
        measures,
        pattern_fn=arpeggiate_bwv846,
        bpm=66,
        program=0,  # Acoustic Grand Piano
    )

    # 4. Save raw version
    print("\n4. Saving raw MIDI...")
    save_midi(pm, "output_raw.mid")
    prettymidi_to_wav(pm, "output_raw.wav")
    print(f"   Raw: output_raw.mid / output_raw.wav")

    # 5. Humanize
    print("\n5. Humanizing...")
    # Prelude sections (4 beats per bar):
    # A: Statement (1-4), B: Expansion (5-10), C: Tonicize V (11-14)
    # D: Return (15-20), E: Build tension (21-25), F: Dom pedal (26-30)
    # G: Resolution (31-34)
    section_beats = [0, 16, 40, 56, 80, 100, 120, 136]

    prelude_config = HumanizeConfig(
        bpm=66,
        # Prelude is arpeggiated — subtler beat weights
        beat_weights={0.0: 6, 1.0: -2, 2.0: 3, 3.0: -2},
        velocity_jitter=4.0,
        phrase_arc_strength=0.06,
        # Gentle timing — arpeggio patterns need precision
        timing_sigma=0.006,
        voice_timing_bias={0: 0.0},     # single instrument, no voice bias
        cadence_rubato=0.05,
        cadence_window=2.0,
        # Prelude: slightly more legato than fugue (flowing arpeggios)
        default_legato=0.90,
        stepwise_legato=0.95,
        phrase_end_legato=0.97,
    )

    pm_human = humanize(pm, config=prelude_config, section_beats=section_beats)

    save_midi(pm_human, "output.mid")
    prettymidi_to_wav(pm_human, "output.wav")
    print(f"   Humanized: output.mid / output.wav")

    # A/B stats
    stats = compare(pm, pm_human)
    for voice_name, s in stats.items():
        v = s["velocity"]
        t = s["timing_ms"]
        d = s["duration_ratio"]
        print(f"   {voice_name:10s}  vel {v['mean_shift']:+.1f}±{v['std']:.1f}  "
              f"timing {t['mean_shift']:+.1f}±{t['std']:.1f}ms  "
              f"dur ×{d['mean']:.3f}")

    print("\n" + "=" * 60)
    print("Done! A/B test: output_raw.wav vs output.wav")
    print("Or import output.mid into GarageBand for better sound.")
    print("=" * 60)


if __name__ == "__main__":
    main()

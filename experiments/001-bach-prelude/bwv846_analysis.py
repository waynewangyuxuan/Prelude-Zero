"""
BWV 846 — Prelude in C Major (Well-Tempered Clavier, Book I)
Ground truth harmonic analysis.

Structure: 35 measures (34 + final measure), 4/4 time
Each measure: one chord, arpeggiated in a 16th-note pattern (5 notes × 2 per beat)
Pattern: bass note held, upper voices arpeggiate as 16ths

Source: music21 corpus analysis + manual correction based on standard analysis.
"""

BWV846_ANALYSIS = {
    "title": "Prelude in C Major, BWV 846",
    "key": "C",
    "time_sig": (4, 4),
    "total_bars": 35,
    "harmony": [
        # (bar, roman_numeral, chord_name, bass_note, pitch_classes, function)
        # ── Opening: establish C major ──
        (1,  "I",        "C",       "C",  ["C", "E", "G"],           "tonic"),
        (2,  "ii4/2",    "Dm7/C",   "C",  ["C", "D", "F", "A"],     "subdominant"),
        (3,  "V6/5",     "G7/B",    "B",  ["B", "D", "F", "G"],     "dominant"),
        (4,  "I",        "C",       "C",  ["C", "E", "G"],           "tonic"),

        # ── Sequence toward V ──
        (5,  "vi6",      "Am/C",    "C",  ["A", "C", "E"],           "tonic substitute"),
        (6,  "V4/2/V",   "D7/C",    "C",  ["C", "D", "F#", "A"],    "secondary dominant"),
        (7,  "V6",       "G/B",     "B",  ["B", "D", "G"],           "dominant"),
        (8,  "Imaj4/2",  "Cmaj7/B", "B",  ["B", "C", "E", "G"],     "tonic"),

        # ── ii-V motion (toward G) ──
        (9,  "vi7",      "Am7",     "A",  ["A", "C", "E", "G"],      "tonic substitute"),
        (10, "V7/V",     "D7",      "D",  ["A", "C", "D", "F#"],     "secondary dominant"),
        (11, "V",        "G",       "G",  ["B", "D", "G"],            "dominant"),

        # ── Chromatic descent ──
        (12, "viio7/ii",  "G#dim7", "G",  ["Bb", "C#", "E", "G"],   "diminished approach"),
        (13, "ii6",       "Dm/F",   "F",  ["A", "D", "F"],           "subdominant"),
        (14, "viio6/5",   "Bdim7/F","F",  ["Ab", "B", "D", "F"],    "diminished approach"),

        # ── Return to C, then IV ──
        (15, "I6",       "C/E",     "E",  ["C", "E", "G"],           "tonic"),
        (16, "IVmaj4/2", "Fmaj7/E", "E",  ["A", "C", "E", "F"],    "subdominant"),
        (17, "ii7",      "Dm7",     "D",  ["A", "C", "D", "F"],     "subdominant"),
        (18, "V7",       "G7",      "G",  ["B", "D", "F", "G"],     "dominant"),
        (19, "I",        "C",       "C",  ["C", "E", "G"],           "tonic"),

        # ── Tonicize IV ──
        (20, "V7/IV",    "C7",      "C",  ["Bb", "C", "E", "G"],    "secondary dominant"),
        (21, "IV",       "Fmaj7",   "F",  ["A", "C", "E", "F"],     "subdominant"),

        # ── Approach dominant pedal ──
        (22, "viio7/V",  "F#dim7",  "F#", ["A", "C", "Eb", "F#"],   "diminished approach"),
        (23, "viio6/4/2","Abdim7",  "Ab", ["Ab", "B", "D", "F"],    "diminished approach"),
        (24, "V7",       "G7",      "G",  ["B", "D", "F", "G"],     "dominant"),

        # ── Dominant pedal section (G pedal, mm. 25-30) ──
        (25, "I6/4",     "C/G",     "G",  ["C", "E", "G"],           "cadential 6/4"),
        (26, "V7",       "G7",      "G",  ["B", "D", "F", "G"],     "dominant"),
        (27, "viio7",    "F#dim7/G","G",  ["A", "C", "Eb", "F#"],   "diminished over pedal"),
        (28, "I6/4",     "C/G",     "G",  ["C", "E", "G"],           "cadential 6/4"),
        (29, "V9sus",    "G9sus",   "G",  ["C", "D", "F", "G"],     "dominant sus"),
        (30, "V7",       "G7",      "G",  ["B", "D", "F", "G"],     "dominant"),

        # ── Final cadence (tonic pedal, mm. 31-35) ──
        (31, "V7/IV",    "C7",      "C",  ["Bb", "C", "E", "G"],    "subdominant coloring"),
        (32, "ii4/2",    "Dm7/C",   "C",  ["A", "C", "D", "F"],     "subdominant"),
        (33, "V7",       "G7",      "C",  ["B", "C", "D", "F", "G"],"cadential dominant"),
        (34, "I",        "C",       "C",  ["C", "E", "G"],           "tonic — final"),
    ]
}

# ── Structural observations ──
BWV846_OBSERVATIONS = """
Key structural patterns in BWV 846:

1. TONAL PLAN: C major throughout, no true modulation.
   - Brief tonicizations: V (mm. 9-11), IV (mm. 20-21)
   - Dominant pedal (mm. 25-30) builds tension before final cadence
   - Tonic pedal (mm. 31-34) for resolution

2. BASS LINE: Mostly stepwise or by third — smooth voice leading.
   C → C → B → C → C → C → B → B → A → D → G → G → F → F → E → E → D → G → C → C → F → F# → Ab → G → G → G → G → G → G → G → C → C → C → C

3. HARMONIC RHYTHM: One chord per bar (constant), creating steady motion.

4. CHORD VOCABULARY:
   - Diatonic: I, ii, IV, V, vi (core)
   - Seventh chords: ii7, V7, Imaj7, IVmaj7 (pervasive — not just triads)
   - Secondary dominants: V7/V (m.6, m.10), V7/IV (m.20, m.31)
   - Diminished 7ths: viio7/ii (m.12), viio7/V (m.22, m.27), viio (m.14, m.23)
   - Cadential 6/4: m.25, m.28

5. NO parallel 5ths or octaves in the voice leading.

6. DRAMATIC ARC:
   - mm. 1-4: Statement (I → ii → V → I)
   - mm. 5-11: Expansion (sequence toward V)
   - mm. 12-19: Return journey (chromatic → ii-V-I)
   - mm. 20-24: Tension building (tonicize IV, diminished approaches)
   - mm. 25-30: Dominant pedal (maximum tension)
   - mm. 31-34: Resolution (tonic pedal → final I)
"""

if __name__ == "__main__":
    print("BWV 846 Harmonic Ground Truth")
    print("=" * 60)
    for bar, rn, name, bass, pcs, func in BWV846_ANALYSIS["harmony"]:
        print(f"  m.{bar:2d}  {rn:12s}  {name:12s}  bass={bass:3s}  ({func})")
    print()
    print(BWV846_OBSERVATIONS)

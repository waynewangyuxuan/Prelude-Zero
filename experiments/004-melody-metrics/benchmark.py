"""
Benchmark: run melody metrics on known reference melodies across 3 genres.
Validates that metrics produce sensible, genre-differentiating numbers.
"""
import sys
sys.path.insert(0, "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero")

from core.melody import compute_melody_profile, summarize
import json

# ═══════════════════════════════════════════════════════════════
# Reference melodies — hand-encoded single-voice MIDI pitches
# Format: (pitches, onsets_in_beats, durations_in_beats, bpm, name)
# ═══════════════════════════════════════════════════════════════

def beats_to_seconds(beats, bpm):
    return [b * 60.0 / bpm for b in beats]

# ── BAROQUE ──

# Bach WTC I Fugue No.1 C major — Subject (our own fugue subject)
bach_fugue_subject = {
    "name": "Bach WTC I Fugue C major — Subject",
    "genre": "baroque",
    "bpm": 80,
    "pitches": [60, 64, 62, 67, 65, 64, 62, 60, 59, 60],
    "onsets":  [0, 1, 2, 3, 3.5, 4, 5, 6, 7, 8],
    "durs":    [1, 1, 1, 0.5, 0.5, 1, 1, 1, 1, 1],
}

# Bach WTC I Fugue No.2 C minor — Subject
bach_fugue2_subject = {
    "name": "Bach WTC I Fugue C minor — Subject",
    "genre": "baroque",
    "bpm": 72,
    "pitches": [60, 67, 65, 63, 62, 60, 62, 63, 65, 67, 68, 67, 65, 63, 62, 60],
    "onsets":  [0, 0.5, 1.0, 1.25, 1.5, 2.0, 2.5, 2.75, 3.0, 3.5, 4.0, 4.5, 4.75, 5.0, 5.25, 5.5],
    "durs":    [0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.5],
}

# Bach Invention No.1 C major — opening theme
bach_invention1 = {
    "name": "Bach Invention No.1 C major",
    "genre": "baroque",
    "bpm": 100,
    "pitches": [60, 62, 64, 60, 62, 64, 65, 62, 64, 65, 67, 64, 72, 71, 72, 67],
    "onsets":  [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75],
    "durs":    [0.25]*16,
}

# Bach Invention No.8 F major — opening theme
bach_invention8 = {
    "name": "Bach Invention No.8 F major",
    "genre": "baroque",
    "bpm": 80,
    "pitches": [65, 69, 72, 69, 65, 67, 69, 65, 67, 69, 60, 62, 64, 65, 67, 69, 70, 72],
    "onsets":  [0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75],
    "durs":    [0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
}

# Bach Cello Suite No.1 Prelude — opening bars (arpeggiated)
bach_cello = {
    "name": "Bach Cello Suite No.1 Prelude — opening",
    "genre": "baroque",
    "bpm": 66,
    "pitches": [55, 62, 57, 62, 59, 62, 57, 62,  55, 62, 57, 62, 59, 62, 57, 62,
                53, 60, 57, 60, 59, 60, 57, 60,  55, 60, 57, 60, 59, 60, 57, 60],
    "onsets":  [i * 0.25 for i in range(32)],
    "durs":    [0.25] * 32,
}

# ── ROMANTIC ──

# Chopin Nocturne Op.9 No.2 — opening melody (simplified)
chopin_nocturne = {
    "name": "Chopin Nocturne Op.9 No.2 — opening",
    "genre": "romantic",
    "bpm": 60,
    "pitches": [71, 72, 76, 75, 74, 73, 72, 71, 72, 74, 76, 79, 78, 76, 75, 76],
    "onsets":  [0, 0.5, 1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5],
    "durs":    [0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
}

# Schumann Träumerei — opening melody (simplified)
schumann_traumerei = {
    "name": "Schumann Träumerei — opening",
    "genre": "romantic",
    "bpm": 56,
    "pitches": [65, 72, 74, 77, 76, 74, 72, 74, 70, 69, 65, 67, 69, 70, 72, 65],
    "onsets":  [0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5],
    "durs":    [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
}

# Chopin Ballade No.1 — main theme (simplified)
chopin_ballade = {
    "name": "Chopin Ballade No.1 — main theme",
    "genre": "romantic",
    "bpm": 66,
    "pitches": [67, 70, 74, 72, 70, 69, 67, 65, 67, 70, 74, 77, 79, 77, 74, 70],
    "onsets":  [0, 1, 2, 2.5, 3, 3.5, 4, 4.5, 6, 7, 8, 8.5, 9, 9.5, 10, 10.5],
    "durs":    [1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 1.5, 1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
}

# Liszt Liebestraum No.3 — opening melody (simplified)
liszt_liebestraum = {
    "name": "Liszt Liebestraum No.3 — opening",
    "genre": "romantic",
    "bpm": 56,
    "pitches": [73, 72, 69, 68, 69, 72, 73, 76, 80, 78, 76, 73, 72, 69, 68, 69],
    "onsets":  [0, 1, 2, 2.5, 3, 4, 5, 6, 7, 7.5, 8, 8.5, 9, 10, 10.5, 11],
    "durs":    [1, 1, 0.5, 0.5, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.5, 1, 0.5, 0.5, 1],
}

# Chopin Prelude Op.28 No.4 in E minor — melody line (simplified)
chopin_prelude4 = {
    "name": "Chopin Prelude Op.28 No.4 E minor",
    "genre": "romantic",
    "bpm": 52,
    "pitches": [76, 76, 75, 75, 74, 74, 73, 73, 72, 72, 71, 71, 72, 71, 72, 76],
    "onsets":  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "durs":    [1]*16,
}

# ── POP ──

# "Twinkle Twinkle Little Star" (universal reference)
twinkle = {
    "name": "Twinkle Twinkle Little Star",
    "genre": "pop",
    "bpm": 120,
    "pitches": [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60],
    "onsets":  [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14],
    "durs":    [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2],
}

# Generic C-pop ballad verse pattern (Royal Road implied)
cpop_ballad_verse = {
    "name": "C-pop Ballad Verse (generic)",
    "genre": "pop",
    "bpm": 72,
    "pitches": [64, 65, 67, 69, 67, 65, 64, 62, 64, 65, 67, 72, 71, 69, 67, 65],
    "onsets":  [0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 6.0, 6.5, 7.0, 8.0, 8.5, 9.0, 9.5, 10.0],
    "durs":    [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 2.0, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 2.0],
}

# Generic C-pop chorus — wider range, more energy
cpop_chorus = {
    "name": "C-pop Chorus (generic)",
    "genre": "pop",
    "bpm": 72,
    "pitches": [67, 69, 72, 74, 72, 69, 67, 69, 72, 74, 76, 74, 72, 69, 67, 65],
    "onsets":  [0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 6.0, 6.5, 7.0, 8.0, 8.5, 9.0, 9.5, 10.0],
    "durs":    [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 2.0, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 2.0],
}

# Western pop hook pattern — repetitive with catch
pop_hook = {
    "name": "Western Pop Hook (generic)",
    "genre": "pop",
    "bpm": 120,
    "pitches": [67, 67, 69, 67, 65, 64, 67, 67, 69, 67, 72, 71, 67, 67, 69, 67, 65, 64, 62, 60],
    "onsets":  [0, 0.5, 1, 1.5, 2, 2.5, 4, 4.5, 5, 5.5, 6, 6.5, 8, 8.5, 9, 9.5, 10, 10.5, 12, 12.5],
    "durs":    [0.5]*20,
}

# Simple pentatonic pop melody
pentatonic_pop = {
    "name": "Pentatonic Pop Melody",
    "genre": "pop",
    "bpm": 100,
    "pitches": [60, 62, 64, 67, 69, 67, 64, 62, 60, 62, 64, 67, 69, 72, 69, 67],
    "onsets":  [0, 0.5, 1, 1.5, 2, 3, 3.5, 4, 6, 6.5, 7, 7.5, 8, 9, 10, 11],
    "durs":    [0.5, 0.5, 0.5, 0.5, 1, 0.5, 0.5, 2, 0.5, 0.5, 0.5, 0.5, 1, 1, 1, 1],
}

# ═══════════════════════════════════════════════════════════════
# Run benchmark
# ═══════════════════════════════════════════════════════════════

ALL_MELODIES = [
    # Baroque
    bach_fugue_subject, bach_fugue2_subject, bach_invention1,
    bach_invention8, bach_cello,
    # Romantic
    chopin_nocturne, schumann_traumerei, chopin_ballade,
    liszt_liebestraum, chopin_prelude4,
    # Pop
    twinkle, cpop_ballad_verse, cpop_chorus, pop_hook, pentatonic_pop,
]


def run_benchmark():
    results = {"baroque": [], "romantic": [], "pop": []}

    for m in ALL_MELODIES:
        bpm = m["bpm"]
        onsets_sec = beats_to_seconds(m["onsets"], bpm)
        durs_sec = beats_to_seconds(m["durs"], bpm)

        p = compute_melody_profile(m["pitches"], onsets_sec, durs_sec, bpm=bpm)
        genre = m["genre"]

        print(f"\n{'='*60}")
        print(summarize(p, genre=genre))
        print(f"  [{m['name']}]")

        results[genre].append({
            "name": m["name"],
            **p.to_dict(),
        })

    # ── Summary table ──
    print("\n\n" + "="*80)
    print("GENRE COMPARISON SUMMARY")
    print("="*80)

    metrics = [
        ("pitch_range", "Pitch Range (st)"),
        ("pitch_std", "Pitch Std"),
        ("step_ratio", "Step Ratio"),
        ("leap_ratio", "Leap Ratio"),
        ("mean_abs_interval", "Mean |Interval|"),
        ("direction_change_ratio", "Dir Changes"),
        ("pitch_class_entropy", "Pitch H (bits)"),
        ("pitch_transition_entropy", "Trans H (bits)"),
        ("rhythm_entropy", "Rhythm H (bits)"),
        ("rhythm_density", "Density (n/beat)"),
        ("tonal_clarity", "Tonal Clarity"),
        ("chromaticism", "Chromaticism"),
    ]

    import numpy as np

    header = f"{'Metric':<20} {'Baroque':>20} {'Romantic':>20} {'Pop':>20}"
    print(header)
    print("-" * 80)

    for key, label in metrics:
        vals = {}
        for genre in ["baroque", "romantic", "pop"]:
            genre_vals = [r[key] for r in results[genre]]
            mean = np.mean(genre_vals)
            std = np.std(genre_vals)
            vals[genre] = f"{mean:.3f} ± {std:.3f}"
        print(f"{label:<20} {vals['baroque']:>20} {vals['romantic']:>20} {vals['pop']:>20}")

    # Export JSON
    with open("/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero/experiments/004-melody-metrics/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\n\nResults exported to experiments/004-melody-metrics/benchmark_results.json")


if __name__ == "__main__":
    run_benchmark()

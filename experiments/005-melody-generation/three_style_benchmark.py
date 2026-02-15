"""
Experiment 005: Three-Style Metric Profiling

Goal: Establish metric profiles for Bach, Chopin, and Pink Floyd,
      then find fusion zones in the metric space.

Pink Floyd archetypes are hand-designed to capture the STYLE ESSENCE:
- Gilmour blues lament (pentatonic minor, slow bends, sustained)
- Atmospheric vocal (Dorian mode, spacious, meditative)
- Building riff (repetitive motif with gradual ascent)
- Space ballad (wide intervals, very sparse, reverb-like)
- Progressive passage (Mixolydian, mixed meter feel)

These are NOT transcriptions — they're stylistic archetypes that capture
what makes Pink Floyd's melodic language distinctive in metric space.
"""
import sys
sys.path.insert(0, "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero")

from core.melody import compute_melody_profile, summarize, GENRE_RANGES
import json
import numpy as np

def beats_to_seconds(beats, bpm):
    return [b * 60.0 / bpm for b in beats]


# ═══════════════════════════════════════════════════════════════
# BAROQUE (Bach) — from experiment 004
# ═══════════════════════════════════════════════════════════════

bach_fugue_subject = {
    "name": "Bach WTC I Fugue C major — Subject",
    "genre": "baroque",
    "bpm": 80,
    "pitches": [60, 64, 62, 67, 65, 64, 62, 60, 59, 60],
    "onsets":  [0, 1, 2, 3, 3.5, 4, 5, 6, 7, 8],
    "durs":    [1, 1, 1, 0.5, 0.5, 1, 1, 1, 1, 1],
}

bach_invention1 = {
    "name": "Bach Invention No.1 C major",
    "genre": "baroque",
    "bpm": 100,
    "pitches": [60, 62, 64, 60, 62, 64, 65, 62, 64, 65, 67, 64, 72, 71, 72, 67],
    "onsets":  [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75],
    "durs":    [0.25]*16,
}

bach_invention8 = {
    "name": "Bach Invention No.8 F major",
    "genre": "baroque",
    "bpm": 80,
    "pitches": [65, 69, 72, 69, 65, 67, 69, 65, 67, 69, 60, 62, 64, 65, 67, 69, 70, 72],
    "onsets":  [0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75],
    "durs":    [0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
}

bach_cello = {
    "name": "Bach Cello Suite No.1 Prelude",
    "genre": "baroque",
    "bpm": 66,
    "pitches": [55, 62, 57, 62, 59, 62, 57, 62,  55, 62, 57, 62, 59, 62, 57, 62,
                53, 60, 57, 60, 59, 60, 57, 60,  55, 60, 57, 60, 59, 60, 57, 60],
    "onsets":  [i * 0.25 for i in range(32)],
    "durs":    [0.25] * 32,
}

bach_fugue2_subject = {
    "name": "Bach WTC I Fugue C minor — Subject",
    "genre": "baroque",
    "bpm": 72,
    "pitches": [60, 67, 65, 63, 62, 60, 62, 63, 65, 67, 68, 67, 65, 63, 62, 60],
    "onsets":  [0, 0.5, 1.0, 1.25, 1.5, 2.0, 2.5, 2.75, 3.0, 3.5, 4.0, 4.5, 4.75, 5.0, 5.25, 5.5],
    "durs":    [0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.5],
}


# ═══════════════════════════════════════════════════════════════
# ROMANTIC (Chopin & co.) — from experiment 004
# ═══════════════════════════════════════════════════════════════

chopin_nocturne = {
    "name": "Chopin Nocturne Op.9 No.2",
    "genre": "romantic",
    "bpm": 60,
    "pitches": [71, 72, 76, 75, 74, 73, 72, 71, 72, 74, 76, 79, 78, 76, 75, 76],
    "onsets":  [0, 0.5, 1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5],
    "durs":    [0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
}

schumann_traumerei = {
    "name": "Schumann Träumerei",
    "genre": "romantic",
    "bpm": 56,
    "pitches": [65, 72, 74, 77, 76, 74, 72, 74, 70, 69, 65, 67, 69, 70, 72, 65],
    "onsets":  [0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5],
    "durs":    [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
}

chopin_ballade = {
    "name": "Chopin Ballade No.1 — main theme",
    "genre": "romantic",
    "bpm": 66,
    "pitches": [67, 70, 74, 72, 70, 69, 67, 65, 67, 70, 74, 77, 79, 77, 74, 70],
    "onsets":  [0, 1, 2, 2.5, 3, 3.5, 4, 4.5, 6, 7, 8, 8.5, 9, 9.5, 10, 10.5],
    "durs":    [1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 1.5, 1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
}

liszt_liebestraum = {
    "name": "Liszt Liebestraum No.3",
    "genre": "romantic",
    "bpm": 56,
    "pitches": [73, 72, 69, 68, 69, 72, 73, 76, 80, 78, 76, 73, 72, 69, 68, 69],
    "onsets":  [0, 1, 2, 2.5, 3, 4, 5, 6, 7, 7.5, 8, 8.5, 9, 10, 10.5, 11],
    "durs":    [1, 1, 0.5, 0.5, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.5, 1, 0.5, 0.5, 1],
}

chopin_prelude4 = {
    "name": "Chopin Prelude Op.28 No.4 E minor",
    "genre": "romantic",
    "bpm": 52,
    "pitches": [76, 76, 75, 75, 74, 74, 73, 73, 72, 72, 71, 71, 72, 71, 72, 76],
    "onsets":  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "durs":    [1]*16,
}


# ═══════════════════════════════════════════════════════════════
# PINK FLOYD — Style Archetypes (hand-designed, not transcriptions)
# ═══════════════════════════════════════════════════════════════

# Archetype 1: "Gilmour Blues Lament"
# B minor pentatonic, 72 BPM
# Character: slow bends, sustained notes, gradual arc up then down
# Think: the FEEL of a Gilmour solo — patient, singing, emotional
gilmour_lament = {
    "name": "Gilmour Blues Lament (archetype)",
    "genre": "prog_rock",
    "bpm": 72,
    "pitches": [59, 62, 64, 62, 59, 57, 59, 62, 64, 66, 69, 71, 69, 66, 64, 62, 59],
    "onsets":  [0, 2, 3, 4.5, 5, 7, 7.5, 9, 10, 10.5, 12, 14, 17, 17.5, 18, 19, 20],
    "durs":    [2.0, 1.0, 1.5, 0.5, 2.0, 0.5, 1.5, 1.0, 0.5, 1.5, 2.0, 3.0, 0.5, 0.5, 1.0, 1.0, 2.0],
}

# Archetype 2: "Floyd Atmospheric Vocal"
# E Dorian, 60 BPM
# Character: floating, spacious, meditative. Long notes, wide gaps.
# The Dorian C# gives it that distinctive "not-quite-minor" Floyd color.
floyd_atmospheric = {
    "name": "Floyd Atmospheric Vocal (archetype)",
    "genre": "prog_rock",
    "bpm": 60,
    "pitches": [64, 67, 69, 67, 66, 64, 67, 69, 71, 73, 71, 69, 67, 64],
    "onsets":  [0, 2, 4, 5, 6, 8, 11, 12, 13, 15, 16, 17, 19, 20],
    "durs":    [2.0, 2.0, 1.0, 1.0, 2.0, 3.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 3.0],
}

# Archetype 3: "Floyd Hypnotic Riff"
# A minor, 100 BPM
# Character: repetitive, driving, gradual build via slight variations.
# The motif repeats but EVOLVES — each cycle pushes slightly higher.
floyd_riff = {
    "name": "Floyd Hypnotic Riff (archetype)",
    "genre": "prog_rock",
    "bpm": 100,
    "pitches": [57, 60, 62, 60, 57, 60, 62, 64,  # cycle 1 + variation
                57, 60, 62, 60, 57, 60, 64, 67,  # cycle 2 + higher
                69, 67],                           # arrival
    "onsets":  [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5,
                4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5,
                8, 9],
    "durs":    [0.5]*16 + [1.0, 1.0],
}

# Archetype 4: "Floyd Space Ballad"
# C minor, 56 BPM
# Character: vast, reverb-soaked, wide intervals (5ths, 4ths).
# Very sparse — each note floats in space. Hypnotic stasis.
floyd_space = {
    "name": "Floyd Space Ballad (archetype)",
    "genre": "prog_rock",
    "bpm": 56,
    "pitches": [60, 67, 65, 63, 62, 60, 68, 67, 70, 72, 70, 68, 67, 63, 60],
    "onsets":  [0, 3, 5, 6, 8, 9, 12, 14, 15, 17, 20, 21, 22, 23, 24],
    "durs":    [3.0, 2.0, 1.0, 2.0, 1.0, 3.0, 2.0, 1.0, 2.0, 3.0, 1.0, 1.0, 1.0, 1.0, 4.0],
}

# Archetype 5: "Floyd Progressive"
# D Mixolydian, 80 BPM
# Character: angular, modal. The b7 (C natural) is the signature.
# Longer phrases with internal contrast. Not predictable.
floyd_prog = {
    "name": "Floyd Progressive (archetype)",
    "genre": "prog_rock",
    "bpm": 80,
    "pitches": [62, 64, 66, 69, 67, 66, 64, 62,
                72, 71, 69, 67, 66, 69, 74, 72, 69, 67, 62],
    "onsets":  [0, 1, 1.5, 2, 3.5, 4, 5, 5.5,
                7, 9, 9.5, 10, 11, 11.5, 13, 15, 15.5, 16, 17],
    "durs":    [1.0, 0.5, 0.5, 1.5, 0.5, 1.0, 0.5, 1.5,
                2.0, 0.5, 0.5, 1.0, 0.5, 1.5, 2.0, 0.5, 0.5, 1.0, 2.0],
}


# ═══════════════════════════════════════════════════════════════
# Run 3-style benchmark
# ═══════════════════════════════════════════════════════════════

ALL_MELODIES = [
    # Baroque
    bach_fugue_subject, bach_invention1, bach_invention8, bach_cello, bach_fugue2_subject,
    # Romantic
    chopin_nocturne, schumann_traumerei, chopin_ballade, liszt_liebestraum, chopin_prelude4,
    # Pink Floyd
    gilmour_lament, floyd_atmospheric, floyd_riff, floyd_space, floyd_prog,
]


def run():
    results = {"baroque": [], "romantic": [], "prog_rock": []}

    for m in ALL_MELODIES:
        bpm = m["bpm"]
        onsets_sec = beats_to_seconds(m["onsets"], bpm)
        durs_sec = beats_to_seconds(m["durs"], bpm)

        p = compute_melody_profile(m["pitches"], onsets_sec, durs_sec, bpm=bpm)
        genre = m["genre"]

        results[genre].append({
            "name": m["name"],
            **p.to_dict(),
        })

    # ── Per-melody profiles ──
    for m in ALL_MELODIES:
        bpm = m["bpm"]
        onsets_sec = beats_to_seconds(m["onsets"], bpm)
        durs_sec = beats_to_seconds(m["durs"], bpm)
        p = compute_melody_profile(m["pitches"], onsets_sec, durs_sec, bpm=bpm)
        print(f"\n{'─'*50}")
        print(f"  {m['name']}  [{m['genre']}]")
        print(f"  range={p.pitch_range}  step={p.step_ratio:.2f}  dir_ch={p.direction_change_ratio:.2f}  "
              f"pH={p.pitch_class_entropy:.2f}  rH={p.rhythm_entropy:.2f}  "
              f"dens={p.rhythm_density:.2f}  tonal={p.tonal_clarity:.2f}")
        print(f"  mode={p.best_mode_display}  run={p.mean_run_length:.1f}  "
              f"dur_cv={p.duration_cv:.2f}  pitch_rep={p.pitch_bigram_rep:.2f}  "
              f"rhythm_rep={p.rhythm_bigram_rep:.2f}")

    # ── Genre comparison table ──
    print("\n\n" + "=" * 100)
    print("THREE-STYLE COMPARISON")
    print("=" * 100)

    metrics = [
        # Easy tier
        ("pitch_range", "Pitch Range (st)"),
        ("pitch_std", "Pitch Std"),
        ("step_ratio", "Step Ratio"),
        ("leap_ratio", "Leap Ratio"),
        ("mean_abs_interval", "Mean |Interval|"),
        ("direction_change_ratio", "Dir Changes"),
        ("pitch_class_entropy", "Pitch H (bits)"),
        ("rhythm_entropy", "Rhythm H (bits)"),
        ("rhythm_density", "Density (n/beat)"),
        ("tonal_clarity", "Tonal Clarity"),
        ("chromaticism", "Chromaticism"),
        # Medium tier
        ("mean_run_length", "Mean Run Length"),
        ("longest_run", "Longest Run"),
        ("contour_direction_bias", "Dir Bias (+up/-dn)"),
        ("mode_coverage", "Mode Coverage"),
        ("mode_clarity", "Mode Clarity"),
        ("duration_cv", "Duration CV"),
        ("duration_range_ratio", "Dur Range Ratio"),
        ("pitch_bigram_rep", "Pitch Bigram Rep"),
        ("rhythm_bigram_rep", "Rhythm Bigram Rep"),
        ("combined_rep", "Combined Rep"),
    ]

    header = f"{'Metric':<20} {'Baroque':>20} {'Romantic':>20} {'Pink Floyd':>20}"
    print(header)
    print("-" * 100)

    genre_summaries = {}

    for key, label in metrics:
        vals = {}
        for genre, display in [("baroque", "Baroque"), ("romantic", "Romantic"), ("prog_rock", "Pink Floyd")]:
            genre_vals = [r[key] for r in results[genre]]
            mean = np.mean(genre_vals)
            std = np.std(genre_vals)
            vals[genre] = f"{mean:.3f} ± {std:.3f}"
            if genre not in genre_summaries:
                genre_summaries[genre] = {}
            genre_summaries[genre][key] = {"mean": mean, "std": std,
                                           "min": min(genre_vals), "max": max(genre_vals)}
        print(f"{label:<20} {vals['baroque']:>20} {vals['romantic']:>20} {vals['prog_rock']:>20}")

    # ── Fusion zone analysis ──
    print("\n\n" + "=" * 100)
    print("FUSION ZONE ANALYSIS")
    print("Where do the three styles OVERLAP in metric space?")
    print("=" * 100)

    for key, label in metrics:
        ranges = {}
        for genre in ["baroque", "romantic", "prog_rock"]:
            s = genre_summaries[genre][key]
            # Use min-max range from actual melodies
            ranges[genre] = (s["min"], s["max"])

        # Find overlap
        overlap_lo = max(r[0] for r in ranges.values())
        overlap_hi = min(r[1] for r in ranges.values())

        if overlap_lo <= overlap_hi:
            overlap_size = overlap_hi - overlap_lo
            total_range = max(r[1] for r in ranges.values()) - min(r[0] for r in ranges.values())
            overlap_pct = (overlap_size / total_range * 100) if total_range > 0 else 0

            print(f"\n  {label}:")
            print(f"    Baroque:    [{ranges['baroque'][0]:.2f}, {ranges['baroque'][1]:.2f}]")
            print(f"    Romantic:   [{ranges['romantic'][0]:.2f}, {ranges['romantic'][1]:.2f}]")
            print(f"    Pink Floyd: [{ranges['prog_rock'][0]:.2f}, {ranges['prog_rock'][1]:.2f}]")
            print(f"    → OVERLAP:  [{overlap_lo:.2f}, {overlap_hi:.2f}]  ({overlap_pct:.0f}% of total span)")
        else:
            print(f"\n  {label}:")
            print(f"    Baroque:    [{ranges['baroque'][0]:.2f}, {ranges['baroque'][1]:.2f}]")
            print(f"    Romantic:   [{ranges['romantic'][0]:.2f}, {ranges['romantic'][1]:.2f}]")
            print(f"    Pink Floyd: [{ranges['prog_rock'][0]:.2f}, {ranges['prog_rock'][1]:.2f}]")
            print(f"    → NO OVERLAP  (gap = {overlap_lo - overlap_hi:.2f})")

    # ── What makes each style UNIQUE ──
    print("\n\n" + "=" * 100)
    print("STYLE SIGNATURES — What makes each style UNIQUE?")
    print("Metrics where one style is clearly distinct from the others")
    print("=" * 100)

    for genre, display in [("baroque", "BACH"), ("romantic", "CHOPIN"), ("prog_rock", "PINK FLOYD")]:
        print(f"\n  {display}:")
        others = [g for g in ["baroque", "romantic", "prog_rock"] if g != genre]
        for key, label in metrics:
            s = genre_summaries[genre][key]
            other_means = [genre_summaries[g][key]["mean"] for g in others]
            other_mean = np.mean(other_means)
            diff = abs(s["mean"] - other_mean)
            other_std = np.mean([genre_summaries[g][key]["std"] for g in others])

            # Significant if distance > 1.5 * combined std
            combined_std = (s["std"] + other_std) / 2
            if combined_std > 0 and diff / combined_std > 1.5:
                direction = "↑ higher" if s["mean"] > other_mean else "↓ lower"
                print(f"    {label}: {s['mean']:.3f} ({direction} than others' {other_mean:.3f})")

    # Export
    output = {
        "results": results,
        "genre_summaries": {g: {k: v for k, v in s.items()} for g, s in genre_summaries.items()},
    }
    out_path = "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero/experiments/005-melody-generation/three_style_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n\nResults exported to: {out_path}")


if __name__ == "__main__":
    run()

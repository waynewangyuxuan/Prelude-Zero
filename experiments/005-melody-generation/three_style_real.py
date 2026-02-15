"""
Experiment 005: Three-Style Metric Profiling (v2 — REAL DATA)

Replaces Pink Floyd archetypes with real MIDI analysis.
Bach/Chopin: hand-encoded short themes (10-32 notes)
Pink Floyd: real MIDI tracks — lead melodies + solos (37-375 notes)

NOTE: scale difference acknowledged. Full-track Floyd naturally has
wider ranges and more variety. This is partly real and partly artifact.
We flag metrics where the length effect is significant.
"""
import sys
sys.path.insert(0, "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero")

import pretty_midi
import numpy as np
from core.melody import compute_melody_profile, GENRE_RANGES
from collections import Counter
import json

BASE = "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero"

def beats_to_seconds(beats, bpm):
    return [b * 60.0 / bpm for b in beats]


# ═══════════════════════════════════════════════════════════════
# BAROQUE (Bach) — hand-encoded short themes
# ═══════════════════════════════════════════════════════════════

BAROQUE = [
    {"name": "Bach Fugue C major Subject", "bpm": 80,
     "pitches": [60, 64, 62, 67, 65, 64, 62, 60, 59, 60],
     "onsets": [0, 1, 2, 3, 3.5, 4, 5, 6, 7, 8],
     "durs": [1, 1, 1, 0.5, 0.5, 1, 1, 1, 1, 1]},
    {"name": "Bach Invention No.1", "bpm": 100,
     "pitches": [60, 62, 64, 60, 62, 64, 65, 62, 64, 65, 67, 64, 72, 71, 72, 67],
     "onsets": [i * 0.25 for i in range(16)],
     "durs": [0.25] * 16},
    {"name": "Bach Invention No.8", "bpm": 80,
     "pitches": [65, 69, 72, 69, 65, 67, 69, 65, 67, 69, 60, 62, 64, 65, 67, 69, 70, 72],
     "onsets": [0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75],
     "durs": [0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]},
    {"name": "Bach Cello Suite No.1", "bpm": 66,
     "pitches": [55, 62, 57, 62, 59, 62, 57, 62, 55, 62, 57, 62, 59, 62, 57, 62,
                 53, 60, 57, 60, 59, 60, 57, 60, 55, 60, 57, 60, 59, 60, 57, 60],
     "onsets": [i * 0.25 for i in range(32)],
     "durs": [0.25] * 32},
    {"name": "Bach Fugue C minor Subject", "bpm": 72,
     "pitches": [60, 67, 65, 63, 62, 60, 62, 63, 65, 67, 68, 67, 65, 63, 62, 60],
     "onsets": [0, 0.5, 1.0, 1.25, 1.5, 2.0, 2.5, 2.75, 3.0, 3.5, 4.0, 4.5, 4.75, 5.0, 5.25, 5.5],
     "durs": [0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.5]},
]

# ═══════════════════════════════════════════════════════════════
# ROMANTIC (Chopin & co.) — hand-encoded short themes
# ═══════════════════════════════════════════════════════════════

ROMANTIC = [
    {"name": "Chopin Nocturne Op.9 No.2", "bpm": 60,
     "pitches": [71, 72, 76, 75, 74, 73, 72, 71, 72, 74, 76, 79, 78, 76, 75, 76],
     "onsets": [0, 0.5, 1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5],
     "durs": [0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]},
    {"name": "Schumann Träumerei", "bpm": 56,
     "pitches": [65, 72, 74, 77, 76, 74, 72, 74, 70, 69, 65, 67, 69, 70, 72, 65],
     "onsets": [0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5],
     "durs": [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]},
    {"name": "Chopin Ballade No.1", "bpm": 66,
     "pitches": [67, 70, 74, 72, 70, 69, 67, 65, 67, 70, 74, 77, 79, 77, 74, 70],
     "onsets": [0, 1, 2, 2.5, 3, 3.5, 4, 4.5, 6, 7, 8, 8.5, 9, 9.5, 10, 10.5],
     "durs": [1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 1.5, 1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]},
    {"name": "Liszt Liebestraum No.3", "bpm": 56,
     "pitches": [73, 72, 69, 68, 69, 72, 73, 76, 80, 78, 76, 73, 72, 69, 68, 69],
     "onsets": [0, 1, 2, 2.5, 3, 4, 5, 6, 7, 7.5, 8, 8.5, 9, 10, 10.5, 11],
     "durs": [1, 1, 0.5, 0.5, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.5, 1, 0.5, 0.5, 1]},
    {"name": "Chopin Prelude Op.28 No.4", "bpm": 52,
     "pitches": [76, 76, 75, 75, 74, 74, 73, 73, 72, 72, 71, 71, 72, 71, 72, 76],
     "onsets": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
     "durs": [1] * 16},
]

# ═══════════════════════════════════════════════════════════════
# PINK FLOYD — REAL MIDI tracks
# ═══════════════════════════════════════════════════════════════

FLOYD_MIDI = [
    {"file": f"{BASE}/Pink_Floyd_-_Wish_You_Were_Here.mid",
     "tracks": [
         {"idx": 1, "label": "WYWH — Vocal Melody", "bpm": 62},
         {"idx": 4, "label": "WYWH — Guitar Solo", "bpm": 62},
     ]},
    {"file": f"{BASE}/Pink_Floyd_-_Hey_You.mid",
     "tracks": [
         {"idx": 2, "label": "Hey You — Lead Vocal", "bpm": 72},
     ]},
    {"file": f"{BASE}/Pink_Floyd_-_Money.mid",
     "tracks": [
         {"idx": 3, "label": "Money — Tenor Sax", "bpm": 120},
         {"idx": 5, "label": "Money — Alto Sax", "bpm": 120},
         {"idx": 8, "label": "Money — Guitar Solo", "bpm": 120},
     ]},
    {"file": f"{BASE}/Pink_Floyd_-_Time.mid",
     "tracks": [
         {"idx": 12, "label": "Time — Lead Guitar", "bpm": 120},
     ]},
    {"file": f"{BASE}/Pink_Floyd_-_Shine_On_You_Crazy_Diamond.mid",
     "tracks": [
         {"idx": 25, "label": "SOYCD — Vocal", "bpm": 68},
         {"idx": 31, "label": "SOYCD — Guitar Lead", "bpm": 68},
     ]},
    {"file": f"{BASE}/Pink_Floyd_-_Have_a_Cigar.mid",
     "tracks": [
         {"idx": 3, "label": "Have a Cigar — Guitar", "bpm": 120},
     ]},
    {"file": f"{BASE}/Pink_Floyd_-_Another_Brick_in_the_Wall.mid",
     "tracks": [
         {"idx": 5, "label": "ABITW — Keys Lead", "bpm": 105},
         {"idx": 12, "label": "ABITW — Guitar Solo", "bpm": 105},
     ]},
]


def compute_handcoded(entries):
    """Compute profiles for hand-encoded melodies."""
    profiles = []
    for m in entries:
        onsets_sec = beats_to_seconds(m["onsets"], m["bpm"])
        durs_sec = beats_to_seconds(m["durs"], m["bpm"])
        p = compute_melody_profile(m["pitches"], onsets_sec, durs_sec, bpm=m["bpm"])
        profiles.append({"name": m["name"], "profile": p})
    return profiles


def compute_floyd():
    """Compute profiles from real MIDI files."""
    profiles = []
    for song in FLOYD_MIDI:
        try:
            pm = pretty_midi.PrettyMIDI(song["file"])
        except Exception as e:
            print(f"  ERROR loading {song['file']}: {e}")
            continue
        for track in song["tracks"]:
            if track["idx"] >= len(pm.instruments):
                continue
            inst = pm.instruments[track["idx"]]
            notes = sorted(inst.notes, key=lambda n: n.start)
            if len(notes) < 4:
                continue
            pitches = [n.pitch for n in notes]
            onsets = [n.start for n in notes]
            durations = [n.end - n.start for n in notes]
            p = compute_melody_profile(pitches, onsets, durations, bpm=track["bpm"])
            profiles.append({"name": track["label"], "profile": p})
    return profiles


def run():
    print("Computing profiles...")
    baroque_profiles = compute_handcoded(BAROQUE)
    romantic_profiles = compute_handcoded(ROMANTIC)
    floyd_profiles = compute_floyd()

    all_groups = {
        "baroque": baroque_profiles,
        "romantic": romantic_profiles,
        "prog_rock": floyd_profiles,
    }

    # ── Per-melody summary ──
    for genre, display in [("baroque", "BACH"), ("romantic", "CHOPIN"), ("prog_rock", "PINK FLOYD (real MIDI)")]:
        print(f"\n{'═'*70}")
        print(f"  {display}  ({len(all_groups[genre])} tracks)")
        print(f"{'═'*70}")
        for entry in all_groups[genre]:
            p = entry["profile"]
            print(f"  {entry['name']}")
            print(f"    range={p.pitch_range}  step={p.step_ratio:.2f}  dir={p.direction_change_ratio:.2f}  "
                  f"pH={p.pitch_class_entropy:.2f}  rH={p.rhythm_entropy:.2f}  "
                  f"dens={p.rhythm_density:.2f}  tonal={p.tonal_clarity:.2f}")
            print(f"    mode={p.best_mode_display}  dur_cv={p.duration_cv:.2f}  "
                  f"run={p.mean_run_length:.1f}  p_rep={p.pitch_bigram_rep:.2f}")

    # ── Three-style comparison ──
    metrics = [
        ("pitch_range", "Pitch Range (st)"),
        ("pitch_std", "Tessitura Std"),
        ("step_ratio", "Step Ratio"),
        ("leap_ratio", "Leap Ratio"),
        ("mean_abs_interval", "Mean |Interval|"),
        ("direction_change_ratio", "Dir Changes"),
        ("pitch_class_entropy", "Pitch H (bits)"),
        ("rhythm_entropy", "Rhythm H (bits)"),
        ("rhythm_density", "Density (n/beat)"),
        ("tonal_clarity", "Tonal Clarity"),
        ("chromaticism", "Chromaticism"),
        ("mean_run_length", "Mean Run Length"),
        ("longest_run", "Longest Run"),
        ("contour_direction_bias", "Dir Bias (+up/-dn)"),
        ("duration_cv", "Duration CV"),
        ("duration_range_ratio", "Dur Range Ratio"),
        ("pitch_bigram_rep", "Pitch Bigram Rep"),
        ("rhythm_bigram_rep", "Rhythm Bigram Rep"),
        ("combined_rep", "Combined Rep"),
        ("best_mode", "Best Mode"),
    ]

    print(f"\n\n{'='*100}")
    print("THREE-STYLE COMPARISON (v2 — Real Floyd MIDI)")
    print(f"{'='*100}")
    print(f"  Bach: {len(baroque_profiles)} short themes | "
          f"Chopin: {len(romantic_profiles)} short themes | "
          f"Floyd: {len(floyd_profiles)} real MIDI tracks")

    numeric_metrics = [m for m in metrics if m[0] != "best_mode"]

    print(f"\n{'Metric':<20} {'Baroque':>22} {'Romantic':>22} {'Pink Floyd':>22}")
    print("-" * 90)

    summaries = {}
    for key, label in numeric_metrics:
        row = {}
        for genre, display_short in [("baroque", "Baroque"), ("romantic", "Romantic"), ("prog_rock", "Floyd")]:
            vals = [getattr(e["profile"], key) for e in all_groups[genre]]
            mean, std = np.mean(vals), np.std(vals)
            row[genre] = {"mean": mean, "std": std, "min": min(vals), "max": max(vals)}
        summaries[key] = row
        print(f"{label:<20} "
              f"{row['baroque']['mean']:7.2f} ± {row['baroque']['std']:5.2f}   "
              f"{row['romantic']['mean']:7.2f} ± {row['romantic']['std']:5.2f}   "
              f"{row['prog_rock']['mean']:7.2f} ± {row['prog_rock']['std']:5.2f}")

    # ── Mode distribution ──
    print(f"\n  Mode distribution:")
    for genre, display in [("baroque", "Bach"), ("romantic", "Chopin"), ("prog_rock", "Floyd")]:
        modes = Counter(e["profile"].best_mode for e in all_groups[genre])
        mode_str = ", ".join(f"{m}:{c}" for m, c in modes.most_common(3))
        print(f"    {display}: {mode_str}")

    # ── Fusion zone ──
    print(f"\n\n{'='*100}")
    print("FUSION ZONE ANALYSIS (v2)")
    print(f"{'='*100}")

    overlap_metrics = []
    no_overlap_metrics = []

    for key, label in numeric_metrics:
        ranges = {}
        for genre in ["baroque", "romantic", "prog_rock"]:
            s = summaries[key][genre]
            ranges[genre] = (s["min"], s["max"])

        overlap_lo = max(r[0] for r in ranges.values())
        overlap_hi = min(r[1] for r in ranges.values())
        total_lo = min(r[0] for r in ranges.values())
        total_hi = max(r[1] for r in ranges.values())
        total_span = total_hi - total_lo

        if overlap_lo <= overlap_hi and total_span > 0:
            overlap_pct = (overlap_hi - overlap_lo) / total_span * 100
            overlap_metrics.append((label, key, overlap_lo, overlap_hi, overlap_pct, ranges))
        else:
            no_overlap_metrics.append((label, key, ranges))

    # Sort by overlap %
    overlap_metrics.sort(key=lambda x: -x[4])

    print(f"\n  OVERLAPPING ({len(overlap_metrics)} metrics):")
    print(f"  {'Metric':<20} {'Overlap Range':>20} {'%':>6}   Bach / Chopin / Floyd ranges")
    print(f"  {'-'*90}")
    for label, key, lo, hi, pct, ranges in overlap_metrics:
        print(f"  {label:<20} [{lo:6.2f}, {hi:6.2f}] {pct:5.0f}%   "
              f"[{ranges['baroque'][0]:.2f},{ranges['baroque'][1]:.2f}] "
              f"[{ranges['romantic'][0]:.2f},{ranges['romantic'][1]:.2f}] "
              f"[{ranges['prog_rock'][0]:.2f},{ranges['prog_rock'][1]:.2f}]")

    if no_overlap_metrics:
        print(f"\n  NO OVERLAP ({len(no_overlap_metrics)} metrics):")
        for label, key, ranges in no_overlap_metrics:
            print(f"  {label:<20}   "
                  f"Bach [{ranges['baroque'][0]:.2f},{ranges['baroque'][1]:.2f}]  "
                  f"Chopin [{ranges['romantic'][0]:.2f},{ranges['romantic'][1]:.2f}]  "
                  f"Floyd [{ranges['prog_rock'][0]:.2f},{ranges['prog_rock'][1]:.2f}]")

    # ── Style signatures ──
    print(f"\n\n{'='*100}")
    print("STYLE SIGNATURES (what makes each UNIQUE)")
    print(f"{'='*100}")

    for genre, display in [("baroque", "BACH"), ("romantic", "CHOPIN"), ("prog_rock", "PINK FLOYD")]:
        print(f"\n  {display}:")
        others = [g for g in ["baroque", "romantic", "prog_rock"] if g != genre]
        sigs = []
        for key, label in numeric_metrics:
            s = summaries[key][genre]
            other_means = [summaries[key][g]["mean"] for g in others]
            other_mean = np.mean(other_means)
            diff = s["mean"] - other_mean
            combined_std = max((s["std"] + np.mean([summaries[key][g]["std"] for g in others])) / 2, 0.001)
            effect_size = diff / combined_std
            if abs(effect_size) > 1.5:
                direction = "↑" if diff > 0 else "↓"
                sigs.append((abs(effect_size), f"    {direction} {label}: {s['mean']:.3f} (vs others' {other_mean:.3f}, effect={effect_size:+.1f}σ)"))
        sigs.sort(reverse=True)
        for _, line in sigs:
            print(line)

    # ── Export ──
    export = {}
    for genre in ["baroque", "romantic", "prog_rock"]:
        export[genre] = []
        for entry in all_groups[genre]:
            export[genre].append({"name": entry["name"], **entry["profile"].to_dict()})

    out_path = f"{BASE}/experiments/005-melody-generation/three_style_real_results.json"
    with open(out_path, "w") as f:
        json.dump(export, f, indent=2, default=str)
    print(f"\n\nExported to: {out_path}")


if __name__ == "__main__":
    run()

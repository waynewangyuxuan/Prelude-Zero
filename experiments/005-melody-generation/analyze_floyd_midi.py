"""
Analyze real Pink Floyd MIDI files — extract melody/lead tracks,
compute 10-dimension metrics, compare with archetypes.
"""
import sys
sys.path.insert(0, "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero")

import pretty_midi
import numpy as np
from core.melody import compute_melody_profile, summarize, from_midi

BASE = "/sessions/zealous-ecstatic-mccarthy/mnt/Prelude-Zero"

# ═══════════════════════════════════════════════════════════════
# Track selection: the most likely melody/lead tracks per song
# Based on instrument names, program numbers, note counts & ranges
# ═══════════════════════════════════════════════════════════════

SONGS = [
    {
        "file": f"{BASE}/Pink_Floyd_-_Wish_You_Were_Here.mid",
        "short": "Wish You Were Here",
        "tracks": [
            {"idx": 1, "label": "Vocal Melody", "bpm": 62},
            {"idx": 4, "label": "Electric Guitar Solo", "bpm": 62},
        ],
    },
    {
        "file": f"{BASE}/Pink_Floyd_-_Hey_You.mid",
        "short": "Hey You",
        "tracks": [
            {"idx": 2, "label": "Voice 1 (Lead Vocal)", "bpm": 72},
            {"idx": 3, "label": "Voice 2 (Harmony)", "bpm": 72},
        ],
    },
    {
        "file": f"{BASE}/Pink_Floyd_-_Money.mid",
        "short": "Money",
        "tracks": [
            {"idx": 3, "label": "Tenor Sax Solo", "bpm": 120},
            {"idx": 5, "label": "Alto Sax", "bpm": 120},
            {"idx": 8, "label": "Overdrive Guitar Solo", "bpm": 120},
        ],
    },
    {
        "file": f"{BASE}/Pink_Floyd_-_Time.mid",
        "short": "Time",
        "tracks": [
            {"idx": 12, "label": "Lead Guitar", "bpm": 120},
        ],
    },
    {
        "file": f"{BASE}/Pink_Floyd_-_Shine_On_You_Crazy_Diamond.mid",
        "short": "Shine On You Crazy Diamond",
        "tracks": [
            {"idx": 25, "label": "Vocal (synth voice)", "bpm": 68},
            {"idx": 31, "label": "Guitar Lead", "bpm": 68},
        ],
    },
    {
        "file": f"{BASE}/Pink_Floyd_-_Have_a_Cigar.mid",
        "short": "Have a Cigar",
        "tracks": [
            {"idx": 3, "label": "Overdrive Guitar Lead", "bpm": 120},
            {"idx": 5, "label": "Synth Lead", "bpm": 120},
        ],
    },
    {
        "file": f"{BASE}/Pink_Floyd_-_Another_Brick_in_the_Wall.mid",
        "short": "Another Brick in the Wall",
        "tracks": [
            {"idx": 5, "label": "Organ/Keys Lead", "bpm": 105},
            {"idx": 12, "label": "Guitar Solo A", "bpm": 105},
        ],
    },
]


def analyze_track(pm, track_idx, bpm):
    """Extract and analyze a single track."""
    inst = pm.instruments[track_idx]
    notes = sorted(inst.notes, key=lambda n: n.start)

    if len(notes) < 4:
        return None, f"Too few notes ({len(notes)})"

    pitches = [n.pitch for n in notes]
    onsets = [n.start for n in notes]
    durations = [n.end - n.start for n in notes]

    profile = compute_melody_profile(pitches, onsets, durations, bpm=bpm)
    return profile, None


def run():
    all_profiles = []

    for song in SONGS:
        print(f"\n{'═'*70}")
        print(f"  {song['short']}")
        print(f"{'═'*70}")

        try:
            pm = pretty_midi.PrettyMIDI(song["file"])
        except Exception as e:
            print(f"  ERROR loading: {e}")
            continue

        for track in song["tracks"]:
            idx = track["idx"]
            label = track["label"]
            bpm = track["bpm"]

            if idx >= len(pm.instruments):
                print(f"  [{idx}] {label}: Track not found")
                continue

            profile, err = analyze_track(pm, idx, bpm)
            if err:
                print(f"  [{idx}] {label}: {err}")
                continue

            p = profile
            print(f"\n  [{idx}] {label}  ({p.note_count} notes, {p.duration_seconds:.0f}s)")
            print(f"      range={p.pitch_range}st  step={p.step_ratio:.2f}  dir_ch={p.direction_change_ratio:.2f}")
            print(f"      pH={p.pitch_class_entropy:.2f}  rH={p.rhythm_entropy:.2f}  "
                  f"dens={p.rhythm_density:.2f}  tonal={p.tonal_clarity:.2f}")
            print(f"      mode={p.best_mode_display}  key={p.estimated_key}")
            print(f"      run_len={p.mean_run_length:.1f}  dur_cv={p.duration_cv:.2f}  "
                  f"pitch_rep={p.pitch_bigram_rep:.2f}  rhythm_rep={p.rhythm_bigram_rep:.2f}")

            all_profiles.append({
                "song": song["short"],
                "track": label,
                "profile": p,
            })

    # ── Summary statistics ──
    if not all_profiles:
        print("\nNo profiles computed!")
        return

    print(f"\n\n{'═'*70}")
    print(f"  PINK FLOYD REAL DATA — AGGREGATE ({len(all_profiles)} tracks)")
    print(f"{'═'*70}")

    metrics = [
        ("pitch_range", "Pitch Range"),
        ("step_ratio", "Step Ratio"),
        ("direction_change_ratio", "Dir Changes"),
        ("pitch_class_entropy", "Pitch H"),
        ("rhythm_entropy", "Rhythm H"),
        ("rhythm_density", "Density"),
        ("tonal_clarity", "Tonal Clarity"),
        ("chromaticism", "Chromaticism"),
        ("mean_run_length", "Mean Run Len"),
        ("duration_cv", "Duration CV"),
        ("pitch_bigram_rep", "Pitch Rep"),
        ("rhythm_bigram_rep", "Rhythm Rep"),
    ]

    print(f"\n  {'Metric':<18} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
    print(f"  {'-'*58}")

    for key, label in metrics:
        vals = [getattr(entry["profile"], key) for entry in all_profiles]
        print(f"  {label:<18} {np.mean(vals):8.3f} {np.std(vals):8.3f} "
              f"{np.min(vals):8.3f} {np.max(vals):8.3f}")

    # ── Mode distribution ──
    print(f"\n  Mode distribution:")
    from collections import Counter
    modes = Counter(entry["profile"].best_mode for entry in all_profiles)
    for mode, count in modes.most_common():
        print(f"    {mode}: {count}")

    # ── Compare with archetypes ──
    print(f"\n\n{'═'*70}")
    print(f"  REAL DATA vs ARCHETYPES")
    print(f"{'═'*70}")

    archetype_means = {
        "pitch_range": 11.8, "step_ratio": 0.635, "direction_change_ratio": 0.313,
        "pitch_class_entropy": 2.440, "rhythm_entropy": 1.411, "rhythm_density": 0.943,
        "tonal_clarity": 0.840, "duration_cv": 0.468, "pitch_bigram_rep": 0.265,
        "rhythm_bigram_rep": 0.500,
    }

    print(f"\n  {'Metric':<18} {'Real Mean':>10} {'Archetype':>10} {'Diff':>10}")
    print(f"  {'-'*52}")

    for key, label in metrics:
        if key in archetype_means:
            real_vals = [getattr(entry["profile"], key) for entry in all_profiles]
            real_mean = np.mean(real_vals)
            arch_mean = archetype_means[key]
            diff = real_mean - arch_mean
            flag = " ⚠" if abs(diff) > 0.3 * max(abs(real_mean), abs(arch_mean)) else ""
            print(f"  {label:<18} {real_mean:10.3f} {arch_mean:10.3f} {diff:+10.3f}{flag}")


if __name__ == "__main__":
    run()

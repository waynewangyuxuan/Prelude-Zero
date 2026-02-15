"""
Experiment 003: Tension Profile Analysis

Apply the multi-dimensional tension engine to:
  1. Our generated C Major Prelude (Exp 001)
  2. Our generated C Major Fugue (Exp 002)
  3. Compare actual vs target tension curves

Outputs:
  - Console summary
  - JSON data for interactive visualization
  - Per-section breakdown
"""

import sys
sys.path.insert(0, '../..')

import json
import pretty_midi
import numpy as np
from core.tension import compute_tension, target_curve, summarize

# ══════════════════════════════════════════════════════════════
# 1. Analyze Prelude
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("PRELUDE TENSION ANALYSIS")
print("=" * 60)

pm_prelude = pretty_midi.PrettyMIDI("../001-bach-prelude/output.mid")

# Prelude: BPM=66, C major, 34 bars × 4 beats = 136 beats
prelude_curve = compute_tension(pm_prelude, bpm=66, key_pc=0, resolution=0.5, smooth_window=3)

prelude_sections = [
    ("A: Statement",      0,   16),
    ("B: Expansion",      16,  40),
    ("C: Tonicize V",     40,  56),
    ("D: Return",         56,  80),
    ("E: Build tension",  80,  100),
    ("F: Dom pedal",      100, 120),
    ("G: Resolution",     120, 136),
]

print(summarize(prelude_curve, prelude_sections))

# Target curve for prelude form
prelude_target = target_curve("prelude", n_beats=136, resolution=0.5)
prelude_dist = prelude_curve.distance(prelude_target)
print(f"\n  Distance from ideal prelude curve: {prelude_dist:.4f}")

# ══════════════════════════════════════════════════════════════
# 2. Analyze Fugue
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("FUGUE TENSION ANALYSIS")
print("=" * 60)

pm_fugue = pretty_midi.PrettyMIDI("../002-bach-fugue/output.mid")

# Fugue: BPM=80, C major, 104 beats total
fugue_curve = compute_tension(pm_fugue, bpm=80, key_pc=0, resolution=0.5, smooth_window=3)

fugue_sections = [
    ("Exposition",        0,   36),
    ("Episode 1",         36,  44),
    ("Middle Entry 1",    44,  53),
    ("Episode 2",         53,  61),
    ("Middle Entry 2",    61,  70),
    ("Episode 3",         70,  78),
    ("Stretto",           78,  96),
    ("Final Cadence",     96,  104),
]

print(summarize(fugue_curve, fugue_sections))

# Target curve for fugue form
fugue_target = target_curve("fugue", n_beats=104, resolution=0.5)
fugue_dist = fugue_curve.distance(fugue_target)
print(f"\n  Distance from ideal fugue curve: {fugue_dist:.4f}")

# ══════════════════════════════════════════════════════════════
# 3. Detailed per-section analysis
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("DETAILED DIMENSION BREAKDOWN")
print("=" * 60)

def dimension_breakdown(curve, sections, label):
    print(f"\n{label}:")
    print(f"  {'Section':20s} {'Harm':>6s} {'Diss':>6s} {'Melo':>6s} {'Reg':>6s} {'Dens':>6s} {'Comb':>6s}")
    print("  " + "-" * 60)
    for name, start, end in sections:
        mask = (curve.beats >= start) & (curve.beats < end)
        if mask.any():
            h = curve.harmonic[mask].mean()
            d = curve.dissonance[mask].mean()
            m = curve.melodic[mask].mean()
            r = curve.registral[mask].mean()
            dn = curve.density[mask].mean()
            c = curve.combined[mask].mean()
            print(f"  {name:20s} {h:6.3f} {d:6.3f} {m:6.3f} {r:6.3f} {dn:6.3f} {c:6.3f}")

dimension_breakdown(prelude_curve, prelude_sections, "PRELUDE")
dimension_breakdown(fugue_curve, fugue_sections, "FUGUE")

# ══════════════════════════════════════════════════════════════
# 4. Export JSON for visualization
# ══════════════════════════════════════════════════════════════

export = {
    "prelude": {
        "curve": prelude_curve.to_dict(),
        "target": prelude_target.to_dict(),
        "distance": prelude_dist,
        "sections": [{"name": n, "start": s, "end": e} for n, s, e in prelude_sections],
        "bpm": 66,
        "key": "C",
    },
    "fugue": {
        "curve": fugue_curve.to_dict(),
        "target": fugue_target.to_dict(),
        "distance": fugue_dist,
        "sections": [{"name": n, "start": s, "end": e} for n, s, e in fugue_sections],
        "bpm": 80,
        "key": "C",
    },
}

with open("tension_data.json", "w") as f:
    json.dump(export, f, indent=2)

print(f"\nExported tension data to tension_data.json")

# ══════════════════════════════════════════════════════════════
# 5. Key findings
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("KEY FINDINGS")
print("=" * 60)

# Where are the actual tension peaks?
p_combined = prelude_curve.combined
f_combined = fugue_curve.combined

print(f"\nPrelude:")
print(f"  Peak tension:   {p_combined.max():.3f} at beat {prelude_curve.beats[p_combined.argmax()]:.1f}")
print(f"  Lowest tension: {p_combined.min():.3f} at beat {prelude_curve.beats[p_combined.argmin()]:.1f}")
print(f"  Tension range:  {p_combined.max() - p_combined.min():.3f}")
print(f"  Expected peak zone: beats 90-110 (Section F: Dom pedal)")

# Check if peak is in the right zone
peak_beat = prelude_curve.beats[p_combined.argmax()]
if 80 <= peak_beat <= 120:
    print(f"  >> Peak is in the right zone!")
else:
    print(f"  >> Peak is NOT in the expected zone (at beat {peak_beat:.1f})")

print(f"\nFugue:")
print(f"  Peak tension:   {f_combined.max():.3f} at beat {fugue_curve.beats[f_combined.argmax()]:.1f}")
print(f"  Lowest tension: {f_combined.min():.3f} at beat {fugue_curve.beats[f_combined.argmin()]:.1f}")
print(f"  Tension range:  {f_combined.max() - f_combined.min():.3f}")
print(f"  Expected peak zone: beats 88-96 (Stretto)")

peak_beat_f = fugue_curve.beats[f_combined.argmax()]
if 85 <= peak_beat_f <= 100:
    print(f"  >> Peak is in the right zone!")
else:
    print(f"  >> Peak is NOT in the expected zone (at beat {peak_beat_f:.1f})")

# Tension variance (is the curve interesting or flat?)
print(f"\nTension Variance (higher = more dynamic):")
print(f"  Prelude: {p_combined.std():.4f}")
print(f"  Fugue:   {f_combined.std():.4f}")

if p_combined.std() < 0.1:
    print(f"  >> Prelude tension is FLAT — needs more contrast")
if f_combined.std() < 0.1:
    print(f"  >> Fugue tension is FLAT — needs more contrast")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)

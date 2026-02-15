"""
Entropy baseline analysis: measure our current fugue + prelude
to understand where we are on the predictability spectrum.

Key question: are we too boring (low H) or too random (high H)?
"""

import sys
sys.path.insert(0, '../..')

import json
import pretty_midi
from core.entropy import compute_entropy, summarize

# ══════════════════════════════════════════════════════════════
# 1. Prelude
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("PRELUDE ENTROPY ANALYSIS")
print("=" * 60)

pm_prelude = pretty_midi.PrettyMIDI("../001-bach-prelude/output.mid")
prelude_profile = compute_entropy(pm_prelude, bpm=66, window_beats=8.0)

prelude_sections = [
    ("A: Statement",      0,   16),
    ("B: Expansion",      16,  40),
    ("C: Tonicize V",     40,  56),
    ("D: Return",         56,  80),
    ("E: Build tension",  80,  100),
    ("F: Dom pedal",      100, 120),
    ("G: Resolution",     120, 136),
]

print(summarize(prelude_profile, prelude_sections))

# ══════════════════════════════════════════════════════════════
# 2. Fugue
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("FUGUE ENTROPY ANALYSIS")
print("=" * 60)

pm_fugue = pretty_midi.PrettyMIDI("../002-bach-fugue/output.mid")
fugue_profile = compute_entropy(pm_fugue, bpm=80, window_beats=8.0)

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

print(summarize(fugue_profile, fugue_sections))

# ══════════════════════════════════════════════════════════════
# 3. Comparison & diagnosis
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("DIAGNOSIS")
print("=" * 60)

p_h = prelude_profile.overall_pitch_h()
f_h = fugue_profile.overall_pitch_h()

print(f"\nPrelude overall pitch transition H: {p_h:.3f} bits")
print(f"Fugue overall pitch transition H:   {f_h:.3f} bits")
print(f"\nSweet spot reference (Bach): 2.3-3.2 bits")
print(f"Max possible (12 pitch classes): {3.585:.3f} bits")

# Per-section entropy for fugue (the one we're about to modify)
print(f"\nFugue per-section pitch entropy (windowed):")
for name, start, end in fugue_sections:
    mask = (fugue_profile.beats >= start) & (fugue_profile.beats < end)
    if mask.any():
        sec_h = fugue_profile.windowed_pitch_h[mask]
        mean_h = sec_h.mean()
        # Is this section interesting or boring?
        if mean_h < 2.3:
            tag = "← LOW (predictable)"
        elif mean_h > 3.2:
            tag = "← HIGH (chaotic)"
        else:
            tag = "← OK"
        print(f"  {name:20s} H={mean_h:.3f} {tag}")

# Stretto specifically
print(f"\nStretto deep dive:")
stretto_mask = (fugue_profile.beats >= 78) & (fugue_profile.beats < 96)
if stretto_mask.any():
    s_pitch = fugue_profile.windowed_pitch_h[stretto_mask]
    s_rhythm = fugue_profile.windowed_rhythm_h[stretto_mask]
    print(f"  Pitch H:  mean={s_pitch.mean():.3f}, range=[{s_pitch.min():.3f}, {s_pitch.max():.3f}]")
    print(f"  Rhythm H: mean={s_rhythm.mean():.3f}, range=[{s_rhythm.min():.3f}, {s_rhythm.max():.3f}]")

# Cross-voice analysis
print(f"\nCross-voice mutual information:")
print(f"  Prelude MI: {prelude_profile.cross_voice_mi:.3f}")
print(f"  Fugue MI:   {fugue_profile.cross_voice_mi:.3f}")
print(f"  (Higher = voices more correlated, Lower = more independent)")

# Export
export = {
    "prelude": prelude_profile.to_dict(),
    "fugue": fugue_profile.to_dict(),
}
with open("entropy_data.json", "w") as f:
    json.dump(export, f, indent=2)
print(f"\nExported to entropy_data.json")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)

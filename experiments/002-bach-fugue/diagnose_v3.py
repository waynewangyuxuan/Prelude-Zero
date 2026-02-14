"""Diagnose stretto v3 counterpoint errors."""
import sys
sys.path.insert(0, '../..')

from generate import build_full_fugue
from core.counterpoint import validate_two_voices, Severity

score = build_full_fugue()
voices = score.voices
voice_names = [v.name for v in voices]

print("=" * 60)
print("Stretto v3 error diagnosis")
print("=" * 60)

# Check all pairs, only show errors
for i in range(len(voices)):
    for j in range(i+1, len(voices)):
        result = validate_two_voices(voices[i].notes, voices[j].notes)
        errors = result["errors"]
        if errors:
            print(f"\n{voice_names[i]} ↔ {voice_names[j]}: {len(errors)} errors")
            for e in errors:
                # Find actual beat position
                # The beat index in the error might not directly map to onset
                # Let's check if the error is in stretto range (beat >= 78)
                detail = e.detail
                print(f"  [{e.rule}] idx={e.beat}: {detail}")

# Also check just the stretto range (beat >= 78) to confirm all errors are there
print("\n" + "=" * 60)
print("Errors by section (stretto = beats 78-96)")
print("=" * 60)

for i in range(len(voices)):
    for j in range(i+1, len(voices)):
        # Get notes only from stretto
        vi_stretto = [n for n in voices[i].notes if n.onset >= 78 and n.onset < 96]
        vj_stretto = [n for n in voices[j].notes if n.onset >= 78 and n.onset < 96]

        # Also get pre-stretto notes that might still be sounding at beat 78
        vi_pre = [n for n in voices[i].notes if n.onset < 78 and n.onset + n.duration > 78]
        vj_pre = [n for n in voices[j].notes if n.onset < 78 and n.onset + n.duration > 78]

        vi_all = vi_pre + vi_stretto
        vj_all = vj_pre + vj_stretto

        if vi_all and vj_all:
            result = validate_two_voices(vi_all, vj_all)
            errors = result["errors"]
            if errors:
                print(f"\n{voice_names[i]} ↔ {voice_names[j]}: {len(errors)} stretto errors")
                for e in errors:
                    print(f"  [{e.rule}] idx={e.beat}: {e.detail}")

# Print stretto note details for manual inspection
print("\n" + "=" * 60)
print("Stretto notes by voice (beats 78-96)")
print("=" * 60)
for vi, v in enumerate(voices):
    notes = [n for n in v.notes if 78 <= n.onset < 96]
    print(f"\n{v.name}: {len(notes)} notes")
    for n in sorted(notes, key=lambda x: x.onset):
        print(f"  beat {n.onset:6.2f}: {n.name:5s} (midi={n.midi}, dur={n.duration:.2f})")

"""Quick check: do the errors exist with old stretto or only new?"""
import sys
sys.path.insert(0, '../..')

from core.fugue import (
    Subject, transpose, tonal_answer,
    FugueVoice, FugueScore, _fit_to_range, VOICE_RANGES,
    evaluate_exposition,
)
from core.counterpoint import Note, validate_two_voices

KEY_PCS = {0, 2, 4, 5, 7, 9, 11}

def build_subject():
    return Subject.from_pitches(
        pitches=  [60, 64, 62, 67,   65, 64, 62, 60, 59, 60],
        durations=[1.5, 0.5, 1.0, 1.0,  0.5, 0.5, 0.5, 0.5, 1.0, 2.0],
    )

# Import the full build function but intercept just before stretto
from generate import build_full_fugue

# Build with current code (new stretto)
score_new = build_full_fugue()

# Count errors in sections BEFORE stretto (onset < 78)
voice_names = ["Soprano", "Alto", "Tenor", "Bass"]
voices = score_new.voices

print("Checking notes BEFORE beat 78 only:")
for i in range(4):
    for j in range(i + 1, 4):
        # Only notes before beat 78
        v1_pre = [n for n in voices[i].notes if n.onset < 78]
        v2_pre = [n for n in voices[j].notes if n.onset < 78]
        result = validate_two_voices(v1_pre, v2_pre, verbose=False)
        n_err = len(result["errors"])
        if n_err > 0:
            print(f"  {voice_names[i]}↔{voice_names[j]}: {n_err} errors")
            for e in result["errors"]:
                print(f"    beat={e.beat} {e.detail}")

print("\nChecking notes ONLY in stretto (beat 78-96):")
for i in range(4):
    for j in range(i + 1, 4):
        v1_str = [n for n in voices[i].notes if 78 <= n.onset < 96]
        v2_str = [n for n in voices[j].notes if 78 <= n.onset < 96]
        if v1_str and v2_str:
            result = validate_two_voices(v1_str, v2_str, verbose=False)
            n_err = len(result["errors"])
            if n_err > 0:
                print(f"  {voice_names[i]}↔{voice_names[j]}: {n_err} errors")
                for e in result["errors"]:
                    print(f"    beat={e.beat} {e.detail}")

print("\nChecking notes including stretto+cadence (beat 78+):")
for i in range(4):
    for j in range(i + 1, 4):
        v1_post = [n for n in voices[i].notes if n.onset >= 78]
        v2_post = [n for n in voices[j].notes if n.onset >= 78]
        if v1_post and v2_post:
            result = validate_two_voices(v1_post, v2_post, verbose=False)
            n_err = len(result["errors"])
            if n_err > 0:
                print(f"  {voice_names[i]}↔{voice_names[j]}: {n_err} errors")
                for e in result["errors"]:
                    print(f"    beat={e.beat} {e.detail}")

print("\nChecking FULL piece:")
for i in range(4):
    for j in range(i + 1, 4):
        result = validate_two_voices(voices[i].notes, voices[j].notes, verbose=False)
        n_err = len(result["errors"])
        if n_err > 0:
            print(f"  {voice_names[i]}↔{voice_names[j]}: {n_err} errors")
            for e in result["errors"]:
                print(f"    beat={e.beat} {e.detail}")

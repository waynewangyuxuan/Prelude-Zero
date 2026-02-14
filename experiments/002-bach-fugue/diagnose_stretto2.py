"""Diagnose the 3 stretto errors at beat pair index 5."""
import sys
sys.path.insert(0, '../..')
from generate import build_full_fugue
from core.counterpoint import _align_simultaneous

score = build_full_fugue()
voices = score.voices
voice_names = ["Soprano", "Alto", "Tenor", "Bass"]
note_names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def nn(midi):
    return note_names[midi % 12] + str(midi // 12 - 1)

# Check stretto notes (78-96)
for pair_label, i, j in [("S↔A", 0, 1), ("S↔T", 0, 2), ("T↔B", 2, 3)]:
    v1_str = [n for n in voices[i].notes if 78 <= n.onset < 96]
    v2_str = [n for n in voices[j].notes if 78 <= n.onset < 96]

    pairs = _align_simultaneous(v1_str, v2_str)

    print(f"\n{pair_label} stretto pairs (showing around pair 5):")
    for idx in range(max(0, 3), min(len(pairs), 10)):
        n1, n2 = pairs[idx]
        if n1 and n2:
            ic = abs(n1.midi - n2.midi) % 12
            interval_name = {0:"P1/P8", 1:"m2", 2:"M2", 3:"m3", 4:"M3", 5:"P4", 6:"tri", 7:"P5", 8:"m6", 9:"M6", 10:"m7", 11:"M7"}.get(ic, "?")
            marker = " <<<" if idx == 5 or idx == 4 else ""
            print(f"  [{idx:2d}] t={n1.onset:5.1f} {voice_names[i]:8s}={nn(n1.midi):4s}({n1.midi})  "
                  f"{voice_names[j]:8s}={nn(n2.midi):4s}({n2.midi})  "
                  f"interval={interval_name:5s}{marker}")
        else:
            print(f"  [{idx:2d}] incomplete pair")

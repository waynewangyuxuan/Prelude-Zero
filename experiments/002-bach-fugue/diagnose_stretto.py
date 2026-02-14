"""Diagnose counterpoint errors in the new stretto."""
import sys
sys.path.insert(0, '../..')

from generate import build_full_fugue
from core.counterpoint import validate_two_voices

score = build_full_fugue()
voices = score.voices
voice_names = ["Soprano", "Alto", "Tenor", "Bass"]

# Focus on the stretto region (beats 78-96) + final cadence (96-104)
for i in range(4):
    for j in range(i + 1, 4):
        result = validate_two_voices(voices[i].notes, voices[j].notes)
        errors = [e for e in result["errors"]]
        if errors:
            print(f"\n{voice_names[i]}↔{voice_names[j]}: {len(errors)} errors")
            for e in errors:
                print(f"  beat={e.beat} rule={e.rule} detail={e.detail}")

                # Find notes around the error beat
                # beat in counterpoint = onset value
                onset = e.beat
                # Convert: counterpoint uses 8th-note beats, so onset ~ beat/2 or just beat
                # Check nearby notes
                print(f"  Context:")
                for vi_idx in [i, j]:
                    v = voices[vi_idx]
                    nearby = [n for n in v.notes if onset/2 - 3 <= n.onset <= onset/2 + 3]
                    note_names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
                    for n in nearby:
                        nn = note_names[n.midi % 12] + str(n.midi // 12 - 1)
                        print(f"    {voice_names[vi_idx]:10s} t={n.onset:.1f} {nn} (midi {n.midi}) dur={n.duration}")

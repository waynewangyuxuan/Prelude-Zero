"""
Chord engine: Roman numeral ↔ actual pitches.
Uses music21 as the theory backend.
"""
from music21 import roman, key, pitch, chord


def roman_to_pitches(roman_str: str, key_str: str = "C",
                     octave: int = 4) -> list[int]:
    """
    Convert a Roman numeral string to MIDI pitch numbers.

    Args:
        roman_str: e.g. "I", "V7", "ii6/5", "viio7/V"
        key_str: e.g. "C", "G", "a" (lowercase = minor)
        octave: base octave for the chord

    Returns:
        List of MIDI note numbers, sorted low to high.
    """
    k = key.Key(key_str)
    rn = roman.RomanNumeral(roman_str, k)
    # Get pitches and transpose to desired octave
    midi_notes = []
    for p in rn.pitches:
        # Adjust octave relative to middle C region
        midi_num = p.midi
        # Keep pitches in a reasonable range around the given octave
        target_base = 12 * (octave + 1)  # MIDI octave convention
        while midi_num < target_base - 6:
            midi_num += 12
        while midi_num > target_base + 18:
            midi_num -= 12
        midi_notes.append(midi_num)
    return sorted(midi_notes)


def roman_to_pitch_names(roman_str: str, key_str: str = "C") -> list[str]:
    """
    Convert Roman numeral to pitch name strings (e.g. ["C4", "E4", "G4"]).
    """
    k = key.Key(key_str)
    rn = roman.RomanNumeral(roman_str, k)
    return [p.nameWithOctave for p in rn.pitches]


def voicing_close(midi_notes: list[int], bass_midi: int | None = None) -> list[int]:
    """
    Close-position voicing: pack all notes within an octave above the bass.
    Optionally specify a different bass note.
    """
    if not midi_notes:
        return []
    if bass_midi is not None:
        # Put bass at bottom, stack rest close above
        pcs = sorted(set(n % 12 for n in midi_notes))
        result = [bass_midi]
        current = bass_midi + 1
        for _ in range(len(pcs) - 1):
            for pc in pcs:
                candidate = current + ((pc - current) % 12)
                if candidate not in result and candidate > bass_midi:
                    result.append(candidate)
                    current = candidate + 1
                    break
        return sorted(result)
    return sorted(midi_notes)


def voicing_open(midi_notes: list[int]) -> list[int]:
    """
    Open-position voicing: spread notes across ~2 octaves.
    Alternating notes go up an octave.
    """
    if len(midi_notes) <= 2:
        return sorted(midi_notes)
    result = list(midi_notes)
    # Raise every other upper voice by an octave
    for i in range(1, len(result), 2):
        result[i] += 12
    return sorted(result)


def chord_pitches_with_bass(roman_str: str, key_str: str, bass_note: str,
                            octave_bass: int = 3, octave_upper: int = 4,
                            prev_upper: list[int] | None = None) -> dict:
    """
    Generate a chord with a specific bass note and upper voices.
    If prev_upper is provided, uses smooth voice leading (minimal movement).

    Returns:
        {"bass": int, "upper": list[int]} with MIDI note numbers.
    """
    k = key.Key(key_str)
    rn = roman.RomanNumeral(roman_str, k)

    # Bass
    bass_p = pitch.Pitch(bass_note)
    bass_p.octave = octave_bass
    bass_midi = bass_p.midi

    # Get pitch classes for upper voices (exclude bass pitch class)
    bass_pc = bass_midi % 12
    upper_pcs = []
    for p in rn.pitches:
        pc = pitch.Pitch(p.name).midi % 12
        upper_pcs.append(pc)
    # Remove duplicates, keep order
    seen = set()
    unique_pcs = []
    for pc in upper_pcs:
        if pc not in seen:
            seen.add(pc)
            unique_pcs.append(pc)
    upper_pcs = unique_pcs

    if prev_upper is not None and len(prev_upper) > 0:
        # Smooth voice leading: each new voice finds the closest pitch
        # that belongs to the new chord
        upper = []
        used_pcs = set()
        for prev_note in sorted(prev_upper):
            best = None
            best_dist = 999
            for pc in upper_pcs:
                if pc in used_pcs and len(upper_pcs) > len(prev_upper):
                    continue
                # Find closest octave of this pitch class
                for octave_shift in range(-1, 2):
                    candidate = (prev_note // 12 + octave_shift) * 12 + pc
                    dist = abs(candidate - prev_note)
                    # Avoid doubling bass at octave
                    if candidate % 12 == bass_pc and candidate != bass_midi:
                        dist += 3  # penalty for bass doubling
                    if dist < best_dist and candidate > bass_midi:
                        best = candidate
                        best_dist = dist
            if best is not None:
                upper.append(best)
                used_pcs.add(best % 12)
        upper = sorted(upper)
    else:
        # No previous chord — place in target octave range
        target = 12 * (octave_upper + 1)
        upper = []
        for pc in upper_pcs:
            midi_num = pc
            while midi_num < target - 2:
                midi_num += 12
            while midi_num > target + 14:
                midi_num -= 12
            # Avoid exact bass doubling
            if midi_num % 12 == bass_pc and abs(midi_num - bass_midi) % 12 == 0:
                midi_num += 12 if midi_num < target + 6 else -12
            if midi_num > bass_midi:
                upper.append(midi_num)
        upper = sorted(set(upper))

    return {"bass": bass_midi, "upper": sorted(set(upper))}


# ── Convenience: common progressions ──

def royal_road(key_str: str = "C") -> list[str]:
    """The Royal Road progression: IVmaj7 – V7 – iii7 – vi"""
    return ["IVmaj7", "V7", "iii7", "vi"]


def bach_cadence(key_str: str = "C") -> list[str]:
    """Typical Bach cadential pattern: ii – V7 – I"""
    return ["ii", "V7", "I"]

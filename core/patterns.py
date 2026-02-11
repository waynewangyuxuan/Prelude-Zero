"""
Arpeggiation / accompaniment pattern engine.
Takes chord pitches and expands them into timed note sequences.
"""


def arpeggiate_bwv846(bass: int, upper: list[int],
                      beat_duration: float = 0.5) -> list[tuple]:
    """
    BWV 846-style arpeggiation pattern.

    The original pattern per measure (4/4 time, 16th notes):
    - Beat 1: bass (held), then upper[0], upper[1], upper[2], upper[1]
    - Beat 2: bass (held), then upper[0], upper[1], upper[2], upper[1]
    - Beat 3-4: same pattern repeats

    Each 16th note = beat_duration / 4.

    Args:
        bass: MIDI note number for bass
        upper: list of 3+ MIDI note numbers for upper voices
        beat_duration: duration of one beat in seconds

    Returns:
        List of (midi_note, start_time, duration, velocity) tuples
    """
    if len(upper) < 3:
        # Pad upper voices if needed
        while len(upper) < 3:
            upper.append(upper[-1] + 12 if upper else bass + 12)

    sixteenth = beat_duration / 4.0
    notes = []

    # Bass note: held for the whole measure (4 beats)
    notes.append((bass, 0.0, beat_duration * 4, 60))

    # Upper voice pattern per beat: up[0], up[1], up[2], up[1]
    pattern = [upper[0], upper[1], upper[2], upper[1]]

    for beat in range(4):  # 4 beats per measure
        beat_start = beat * beat_duration
        for i, note in enumerate(pattern):
            t = beat_start + (i + 1) * sixteenth  # +1 because beat starts with bass
            # Actually in BWV 846, the 16th pattern is:
            # pos 0: upper[0], pos 1: upper[1], pos 2: upper[2],
            # pos 3: upper[0], pos 4: upper[1]
            # Let me re-examine...
            pass

    # Let me implement the actual BWV 846 pattern more carefully.
    # Each beat has 4 sixteenth notes in the RH:
    # The pattern for each beat is: note1, note2, note3, note2
    # (or more precisely: 3rd, 4th, 5th voice, 4th voice if 5 voices)
    #
    # But simplified to 3 upper voices:
    # Pattern per beat: up[0], up[1], up[2], up[1]
    notes = []

    # Bass: one long note per measure
    notes.append((bass, 0.0, beat_duration * 4, 55))

    for beat in range(4):
        beat_start = beat * beat_duration
        sub_pattern = [upper[0], upper[1], upper[2], upper[1]]
        for i, note in enumerate(sub_pattern):
            t = beat_start + i * sixteenth
            notes.append((note, t, sixteenth, 70))

    return notes


def arpeggiate_ascending(bass: int, upper: list[int],
                         beat_duration: float = 0.5) -> list[tuple]:
    """
    Simple ascending arpeggio: bass, then each upper voice in order.
    Repeats to fill the measure.
    """
    all_notes = [bass] + sorted(upper)
    sixteenth = beat_duration / 4.0
    notes = []
    total_slots = 16  # 4 beats × 4 sixteenths

    for i in range(total_slots):
        note = all_notes[i % len(all_notes)]
        t = i * sixteenth
        vel = 70 if i % 4 == 0 else 60  # accent on beat
        notes.append((note, t, sixteenth, vel))

    return notes


def arpeggiate_alberti(bass: int, upper: list[int],
                       beat_duration: float = 0.5) -> list[tuple]:
    """
    Alberti bass pattern: low-high-mid-high (classical style).
    """
    if len(upper) < 2:
        upper = upper + [upper[-1] + 12]

    low, mid, high = upper[0], upper[len(upper)//2], upper[-1]
    pattern = [low, high, mid, high]
    sixteenth = beat_duration / 4.0
    notes = []

    # Bass held
    notes.append((bass, 0.0, beat_duration * 4, 55))

    for beat in range(4):
        for i, note in enumerate(pattern):
            t = beat * beat_duration + i * sixteenth
            notes.append((note, t, sixteenth, 65))

    return notes

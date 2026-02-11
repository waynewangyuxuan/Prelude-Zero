"""
MIDI export: turn chord progressions + patterns into MIDI files.
Uses pretty_midi for clean output.
"""
import pretty_midi


def progression_to_midi(
    measures: list[dict],
    pattern_fn,
    bpm: float = 66.0,
    instrument_name: str = "Acoustic Grand Piano",
    program: int = 0,
) -> pretty_midi.PrettyMIDI:
    """
    Convert a chord progression into a MIDI file.

    Args:
        measures: list of {"bass": int, "upper": list[int]} dicts
        pattern_fn: function(bass, upper, beat_duration) -> list of
                    (midi_note, relative_start, duration, velocity)
        bpm: tempo
        instrument_name: GM instrument name
        program: GM program number (0=piano, 6=harpsichord)

    Returns:
        PrettyMIDI object
    """
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    instrument = pretty_midi.Instrument(program=program, name=instrument_name)

    beat_duration = 60.0 / bpm  # seconds per beat
    measure_duration = beat_duration * 4  # 4/4 time

    for i, measure in enumerate(measures):
        measure_start = i * measure_duration
        bass = measure["bass"]
        upper = measure["upper"]

        # Generate notes using the pattern function
        pattern_notes = pattern_fn(bass, upper, beat_duration)

        for midi_note, rel_start, dur, vel in pattern_notes:
            start = measure_start + rel_start
            end = start + dur
            note = pretty_midi.Note(
                velocity=vel,
                pitch=midi_note,
                start=start,
                end=end,
            )
            instrument.notes.append(note)

    pm.instruments.append(instrument)
    return pm


def save_midi(pm: pretty_midi.PrettyMIDI, path: str):
    """Save PrettyMIDI object to file."""
    pm.write(path)
    print(f"Saved MIDI: {path}")
    # Print some stats
    total_notes = sum(len(inst.notes) for inst in pm.instruments)
    duration = pm.get_end_time()
    print(f"  {total_notes} notes, {duration:.1f}s, "
          f"{len(pm.instruments)} instrument(s)")

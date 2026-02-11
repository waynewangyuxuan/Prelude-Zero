"""
Humanize: add micro-variations to make MIDI sound less mechanical.
Applies to pretty_midi Note objects in-place.
"""
import random
import pretty_midi


def apply_velocity_curve(instrument: pretty_midi.Instrument,
                         curve: str = "natural"):
    """
    Apply velocity variation to all notes in an instrument.

    Curves:
    - "natural": slight random variation around original velocity
    - "crescendo": gradually increase
    - "decrescendo": gradually decrease
    - "phrase_arc": rise then fall per ~8 notes (phrase shaping)
    """
    notes = instrument.notes
    if not notes:
        return

    if curve == "natural":
        for n in notes:
            jitter = random.randint(-8, 8)
            n.velocity = max(20, min(127, n.velocity + jitter))

    elif curve == "crescendo":
        for i, n in enumerate(notes):
            scale = 0.7 + 0.3 * (i / len(notes))
            n.velocity = max(20, min(127, int(n.velocity * scale)))

    elif curve == "decrescendo":
        for i, n in enumerate(notes):
            scale = 1.0 - 0.3 * (i / len(notes))
            n.velocity = max(20, min(127, int(n.velocity * scale)))

    elif curve == "phrase_arc":
        phrase_len = 8
        for i, n in enumerate(notes):
            pos = (i % phrase_len) / phrase_len
            # Arc: rise to middle, fall at end
            arc = 1.0 - 2.0 * abs(pos - 0.5)  # 0→1→0
            scale = 0.8 + 0.2 * arc
            n.velocity = max(20, min(127, int(n.velocity * scale)))


def apply_timing_jitter(instrument: pretty_midi.Instrument,
                        sigma: float = 0.008):
    """
    Add random timing micro-offsets to simulate human imprecision.

    Args:
        sigma: standard deviation in seconds (~8ms is subtle, ~15ms is noticeable)
    """
    for n in instrument.notes:
        offset = random.gauss(0, sigma)
        n.start = max(0, n.start + offset)
        n.end = max(n.start + 0.01, n.end + offset)  # keep minimum duration


def apply_agogic(instrument: pretty_midi.Instrument,
                 style: str = "baroque"):
    """
    Apply agogic accents — slight lengthening/shortening for musical emphasis.

    Styles:
    - "baroque": slight ritardando at phrase ends, emphasis on downbeats
    - "romantic": more rubato, larger timing shifts
    """
    notes = sorted(instrument.notes, key=lambda n: n.start)
    if not notes:
        return

    total_duration = notes[-1].end - notes[0].start
    if total_duration <= 0:
        return

    if style == "baroque":
        for n in notes:
            # Subtle downbeat emphasis: slightly early, slightly louder
            pos_in_beat = n.start % 0.5  # assuming ~120bpm quarter notes
            if pos_in_beat < 0.05:  # near a beat boundary
                n.velocity = min(127, n.velocity + 5)

            # Slight ritardando in the last 10% of the piece
            progress = (n.start - notes[0].start) / total_duration
            if progress > 0.9:
                stretch = 1.0 + 0.05 * ((progress - 0.9) / 0.1)
                offset = n.start * (stretch - 1.0) * 0.1
                n.start += offset
                n.end += offset

    elif style == "romantic":
        for n in notes:
            progress = (n.start - notes[0].start) / total_duration
            # More pronounced rubato
            if progress > 0.85:
                stretch = 1.0 + 0.1 * ((progress - 0.85) / 0.15)
                offset = n.start * (stretch - 1.0) * 0.15
                n.start += offset
                n.end += offset
            # Random micro-rubato
            n.start += random.gauss(0, 0.012)
            n.start = max(0, n.start)
            n.end = max(n.start + 0.01, n.end)

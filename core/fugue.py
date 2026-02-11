"""
Fugue assembly engine.

A fugue is an algebraic structure:
  Subject S under transformation group G = {T, I, Aug, Dim, Retrograde}
  where:
    T_n(S) = transpose by n semitones
    I(S) = inversion (mirror around axis)
    Aug(S) = augmentation (double durations)
    Dim(S) = diminution (halve durations)
    R(S) = retrograde (reverse order)

This engine handles:
  1. Subject definition and transformation
  2. Answer generation (real vs tonal)
  3. Exposition assembly (entry scheduling)
  4. Episode construction (sequences from subject fragments)
  5. Quality evaluation

The engine does NOT compose — it assembles and validates.
The LLM proposes (subject, countersubject ideas).
The engine validates (counterpoint rules, structure).
"""
import numpy as np
from dataclasses import dataclass, field
from copy import deepcopy
from core.counterpoint import Note, validate_two_voices, Issue, Severity


# ═══════════════════════════════════════════════════════════════
# Subject definition
# ═══════════════════════════════════════════════════════════════

@dataclass
class Subject:
    """
    A fugue subject = sequence of (midi, duration) pairs.

    Properties derived:
    - Key center (first/last note)
    - Interval profile (for pattern matching)
    - Tonal answer adjustments
    """
    notes: list[Note]
    key_midi: int = 60  # C4 default

    @classmethod
    def from_intervals(cls, intervals: list[int], durations: list[float],
                       start_midi: int = 60, start_onset: float = 0.0):
        """
        Build a subject from interval sequence.

        Args:
            intervals: list of semitone intervals (positive = up)
                       First entry is ignored (or 0 for first note)
            durations: duration of each note in beats
            start_midi: MIDI number of first note
            start_onset: beat position of first note
        """
        notes = []
        midi = start_midi
        onset = start_onset
        for i, dur in enumerate(durations):
            if i > 0 and i < len(intervals):
                midi += intervals[i]
            notes.append(Note(midi=midi, onset=onset, duration=dur))
            onset += dur
        return cls(notes=notes, key_midi=start_midi)

    @classmethod
    def from_pitches(cls, pitches: list[int], durations: list[float],
                     start_onset: float = 0.0):
        """Build subject from absolute MIDI pitches and durations."""
        notes = []
        onset = start_onset
        for midi, dur in zip(pitches, durations):
            notes.append(Note(midi=midi, onset=onset, duration=dur))
            onset += dur
        return cls(notes=notes, key_midi=pitches[0])

    @property
    def duration_beats(self) -> float:
        """Total duration in beats."""
        if not self.notes:
            return 0
        last = self.notes[-1]
        return last.onset + last.duration - self.notes[0].onset

    @property
    def interval_profile(self) -> list[int]:
        """Directed interval sequence (for pattern matching)."""
        return [self.notes[i+1].midi - self.notes[i].midi
                for i in range(len(self.notes) - 1)]

    @property
    def pitch_range(self) -> int:
        """Ambitus: highest - lowest MIDI."""
        pitches = [n.midi for n in self.notes]
        return max(pitches) - min(pitches)


# ═══════════════════════════════════════════════════════════════
# Subject transformations (the algebra)
# ═══════════════════════════════════════════════════════════════

def transpose(subject: Subject, semitones: int, new_onset: float = None) -> Subject:
    """T_n: transpose all notes by n semitones."""
    new_notes = []
    onset_offset = 0
    if new_onset is not None:
        onset_offset = new_onset - subject.notes[0].onset

    for n in subject.notes:
        new_notes.append(Note(
            midi=n.midi + semitones,
            onset=n.onset + onset_offset,
            duration=n.duration,
        ))
    return Subject(
        notes=new_notes,
        key_midi=subject.key_midi + semitones,
    )


def invert(subject: Subject, axis_midi: int = None,
           new_onset: float = None) -> Subject:
    """I: invert (mirror) around axis note."""
    if axis_midi is None:
        axis_midi = subject.notes[0].midi

    new_notes = []
    onset_offset = 0
    if new_onset is not None:
        onset_offset = new_onset - subject.notes[0].onset

    for n in subject.notes:
        new_midi = 2 * axis_midi - n.midi
        new_notes.append(Note(
            midi=new_midi,
            onset=n.onset + onset_offset,
            duration=n.duration,
        ))
    return Subject(notes=new_notes, key_midi=axis_midi)


def augment(subject: Subject, factor: float = 2.0,
            new_onset: float = None) -> Subject:
    """Aug: multiply all durations by factor."""
    base_onset = new_onset if new_onset is not None else subject.notes[0].onset
    new_notes = []
    for n in subject.notes:
        relative_onset = n.onset - subject.notes[0].onset
        new_notes.append(Note(
            midi=n.midi,
            onset=base_onset + relative_onset * factor,
            duration=n.duration * factor,
        ))
    return Subject(notes=new_notes, key_midi=subject.key_midi)


def diminish(subject: Subject, factor: float = 2.0,
             new_onset: float = None) -> Subject:
    """Dim: divide all durations by factor."""
    return augment(subject, 1.0 / factor, new_onset)


def retrograde(subject: Subject, new_onset: float = None) -> Subject:
    """R: reverse note order, keep durations in new order."""
    base_onset = new_onset if new_onset is not None else subject.notes[0].onset
    reversed_midis = [n.midi for n in reversed(subject.notes)]
    durations = [n.duration for n in subject.notes]  # keep original duration sequence

    new_notes = []
    onset = base_onset
    for midi, dur in zip(reversed_midis, durations):
        new_notes.append(Note(midi=midi, onset=onset, duration=dur))
        onset += dur
    return Subject(notes=new_notes, key_midi=reversed_midis[0])


# ═══════════════════════════════════════════════════════════════
# Answer generation (real vs tonal)
# ═══════════════════════════════════════════════════════════════

def real_answer(subject: Subject, new_onset: float = 0.0) -> Subject:
    """
    Real answer: transpose up a P5 (7 semitones).
    Exact transposition — all intervals preserved.
    """
    return transpose(subject, 7, new_onset)


def tonal_answer(subject: Subject, key_pcs: set = None,
                 new_onset: float = 0.0) -> Subject:
    """
    Tonal answer: transpose to dominant, but adjust intervals
    to keep the answer within the tonic key's framework while
    the answer starts on the dominant.

    The Baroque convention (simplified):
    - Subject notes on scale degree 1 → answer on degree 5
    - Subject notes on scale degree 5 → answer on degree 1
    - The "head" of the subject (first few notes) gets tonal adjustment
    - The "tail" often switches to a real (exact) transposition
    - Leading tone of dominant key (e.g. F# in G major) is allowed
      as a chromatic passing tone

    This implementation uses a two-zone approach:
    - Zone 1 (head): tonic↔dominant swap, keep diatonic
    - Zone 2 (tail): real transposition, allow dominant-key accidentals

    The boundary is after the first note that reaches the dominant.
    """
    if key_pcs is None:
        key_pcs = {0, 2, 4, 5, 7, 9, 11}  # C major

    tonic_pc = subject.key_midi % 12
    dominant_pc = (tonic_pc + 7) % 12

    # Dominant key PCs (e.g., G major for C major subject)
    # Shift by +7 semitones: C major → G major (F→F#)
    dominant_key_pcs = set((pc + 7) % 12 for pc in key_pcs)

    # Find the "head/tail" boundary: first note that reaches the dominant
    head_end = len(subject.notes)
    for i, n in enumerate(subject.notes):
        if n.midi % 12 == dominant_pc and i > 0:
            head_end = i + 1
            break

    new_notes = []
    onset_offset = new_onset - subject.notes[0].onset

    for i, n in enumerate(subject.notes):
        if i == 0:
            new_midi = _nearest_above(n.midi, dominant_pc)
        elif i < head_end:
            # HEAD ZONE: tonal adjustment (tonic↔dominant swap)
            raw_midi = n.midi + 7
            raw_pc = raw_midi % 12
            orig_pc = n.midi % 12

            if orig_pc == tonic_pc:
                target_pc = dominant_pc
            elif orig_pc == dominant_pc:
                target_pc = tonic_pc
            elif raw_pc in key_pcs:
                target_pc = raw_pc
            else:
                target_pc = _nearest_diatonic_pc(raw_pc, key_pcs)

            new_midi = _nearest(raw_midi, target_pc)
        else:
            # TAIL ZONE: real transposition, allow dominant-key notes
            raw_midi = n.midi + 7
            raw_pc = raw_midi % 12

            if raw_pc in dominant_key_pcs or raw_pc in key_pcs:
                # Diatonic in either key — keep as-is
                new_midi = raw_midi
            else:
                # Snap to dominant key
                target_pc = _nearest_diatonic_pc(raw_pc, dominant_key_pcs)
                new_midi = _nearest(raw_midi, target_pc)

        new_notes.append(Note(
            midi=new_midi,
            onset=n.onset + onset_offset,
            duration=n.duration,
        ))

    return Subject(notes=new_notes, key_midi=new_notes[0].midi)


def _nearest_above(reference: int, target_pc: int) -> int:
    """Find nearest MIDI note at or above reference with given PC."""
    midi = reference + ((target_pc - reference % 12) % 12)
    return midi


def _nearest(reference: int, target_pc: int) -> int:
    """Find nearest MIDI note to reference with given PC."""
    up = reference + ((target_pc - reference % 12) % 12)
    down = up - 12
    if abs(up - reference) <= abs(down - reference):
        return up
    return down


def _nearest_diatonic_pc(pc: int, key_pcs: set) -> int:
    """Snap a pitch class to nearest diatonic PC."""
    for delta in range(1, 7):
        if (pc + delta) % 12 in key_pcs:
            return (pc + delta) % 12
        if (pc - delta) % 12 in key_pcs:
            return (pc - delta) % 12
    return pc  # shouldn't reach here


# ═══════════════════════════════════════════════════════════════
# Exposition assembly
# ═══════════════════════════════════════════════════════════════

@dataclass
class FugueVoice:
    """A single voice in the fugue."""
    name: str              # e.g. "Soprano", "Alto"
    notes: list[Note] = field(default_factory=list)
    range_low: int = 48    # MIDI range
    range_high: int = 84

    def add_notes(self, notes: list[Note]):
        self.notes.extend(notes)

    def add_rest(self, onset: float, duration: float):
        """Rests are implicit (gaps), but we track them for clarity."""
        pass  # gaps in note list = rests


@dataclass
class FugueScore:
    """Complete fugue score with multiple voices."""
    voices: list[FugueVoice]
    key_str: str = "C"
    time_sig: str = "4/4"
    tempo: int = 80

    def all_notes(self) -> list[Note]:
        """All notes across all voices, sorted by onset."""
        all_n = []
        for v in self.voices:
            all_n.extend(v.notes)
        return sorted(all_n, key=lambda n: n.onset)


# Standard voice ranges (MIDI)
VOICE_RANGES = {
    "Soprano": (60, 84),   # C4 - C6
    "Alto":    (53, 77),   # F3 - F5
    "Tenor":   (48, 72),   # C3 - C5
    "Bass":    (40, 64),   # E2 - E4
}


def build_exposition(
    subject: Subject,
    n_voices: int = 4,
    answer_type: str = "tonal",
    voice_names: list[str] = None,
    entry_order: list[int] = None,
    key_pcs: set = None,
) -> FugueScore:
    """
    Assemble a fugue exposition.

    The exposition is where each voice enters with the subject (dux)
    or answer (comes), from first to last.

    Standard 4-voice order: Alto → Soprano → Tenor → Bass
    (or any permutation).

    Args:
        subject: the fugue subject (dux)
        n_voices: number of voices (3 or 4)
        answer_type: "real" or "tonal"
        voice_names: names for each voice
        entry_order: which voice enters when (0-indexed)
        key_pcs: pitch classes in the key

    Returns:
        FugueScore with the exposition
    """
    if voice_names is None:
        if n_voices == 4:
            voice_names = ["Soprano", "Alto", "Tenor", "Bass"]
        elif n_voices == 3:
            voice_names = ["Soprano", "Alto", "Tenor"]
        else:
            voice_names = [f"Voice {i+1}" for i in range(n_voices)]

    if entry_order is None:
        # Classic order: middle voice first, then up, then down
        if n_voices == 4:
            entry_order = [1, 0, 2, 3]  # Alto, Soprano, Tenor, Bass
        elif n_voices == 3:
            entry_order = [1, 0, 2]      # Alto, Soprano, Tenor
        else:
            entry_order = list(range(n_voices))

    # Create voices
    voices = []
    for name in voice_names:
        low, high = VOICE_RANGES.get(name, (48, 84))
        voices.append(FugueVoice(name=name, range_low=low, range_high=high))

    # Generate answer
    if answer_type == "real":
        answer = real_answer(subject)
    else:
        answer = tonal_answer(subject, key_pcs)

    # Schedule entries + continuation (countersubject / free counterpoint)
    subject_dur = subject.duration_beats
    current_onset = 0.0

    # Track when each voice entered (for continuation)
    voice_entries = {}  # voice_idx → (entry_subject, onset)

    for entry_idx, voice_idx in enumerate(entry_order):
        # Alternate subject and answer
        is_answer = (entry_idx % 2 == 1)

        if is_answer:
            entry = transpose(answer, 0, current_onset)
            entry = _fit_to_range(entry, voices[voice_idx])
        else:
            entry = transpose(subject, 0, current_onset)
            if entry_idx > 0:
                entry = _fit_to_range(entry, voices[voice_idx])

        voices[voice_idx].add_notes(entry.notes)
        voice_entries[voice_idx] = (entry, current_onset)

        # Collect all notes that will be playing during this entry
        # (the entry itself + any previously generated continuations)
        all_simultaneous_notes = list(entry.notes)
        for vi in range(len(voices)):
            if vi == voice_idx:
                continue
            for n in voices[vi].notes:
                if n.onset >= current_onset - 0.01 and n.onset < current_onset + subject_dur:
                    all_simultaneous_notes.append(n)

        # Add continuation for ALL previously entered voices
        for prev_voice_idx, (prev_entry, prev_onset) in voice_entries.items():
            if prev_voice_idx == voice_idx:
                continue
            last_note_end = (voices[prev_voice_idx].notes[-1].onset +
                             voices[prev_voice_idx].notes[-1].duration
                             if voices[prev_voice_idx].notes else 0)
            if last_note_end <= current_onset + 0.01:
                continuation = _generate_continuation(
                    prev_entry, voices[prev_voice_idx],
                    current_onset, subject_dur, key_pcs or {0,2,4,5,7,9,11},
                    entering_notes=all_simultaneous_notes,
                )
                voices[prev_voice_idx].add_notes(continuation)
                # Add the new continuation to simultaneous notes for next voice
                all_simultaneous_notes.extend(continuation)

        current_onset += subject_dur

    return FugueScore(voices=voices)


def _generate_continuation(prev_entry: Subject, voice: FugueVoice,
                           onset: float, duration: float,
                           key_pcs: set,
                           entering_notes: list[Note] = None) -> list[Note]:
    """
    Generate simple free counterpoint for a voice while another enters.

    Strategy: contrary-motion stepwise line using half notes,
    with parallel-checking against the entering voice.
    """
    if not voice.notes:
        return []

    last_note = voice.notes[-1]
    current_midi = last_note.midi

    # Determine contrary motion direction
    profile = prev_entry.interval_profile
    total_motion = sum(profile[:len(profile)//2])
    step_dir = -1 if total_motion > 0 else 1

    # Build lookup for entering voice: onset → midi
    entering_map = {}
    if entering_notes:
        for n in entering_notes:
            entering_map[round(n.onset, 2)] = n.midi

    notes = []
    prev_midi = current_midi
    t = onset

    while t < onset + duration - 0.01:
        dur = min(2.0, onset + duration - t)
        if dur < 0.25:
            break

        # Generate candidate notes (up to 5 options)
        candidates = []
        for step in [2, -2, 1, -1, 3, -3, 4, -4, 0]:
            proposed = current_midi + step * (1 if step == 0 else np.sign(step_dir * step))
            proposed = current_midi + step

            # Snap to key
            pp = proposed % 12
            if pp not in key_pcs:
                pp = _nearest_diatonic_pc(pp, key_pcs)
                proposed = _nearest(proposed, pp)

            # Clamp
            proposed = max(voice.range_low, min(voice.range_high, proposed))
            if proposed not in [c for c, _ in candidates]:
                candidates.append((proposed, abs(step)))

        # Check each candidate against entering voice for parallels
        best = None
        for cand_midi, step_size in candidates:
            has_parallel = False

            # Check: if prev note and entering voice at prev time formed
            # a perfect interval, and now they'd form the same → parallel
            if entering_notes and len(notes) > 0:
                t_prev = round(notes[-1].onset, 2)
                t_curr = round(t, 2)
                entering_prev = entering_map.get(t_prev)
                entering_curr = entering_map.get(t_curr)

                if entering_prev is not None and entering_curr is not None:
                    int_prev = abs(prev_midi - entering_prev) % 12
                    int_curr = abs(cand_midi - entering_curr) % 12

                    if (int_prev in (0, 7) and int_curr in (0, 7) and
                            int_prev == int_curr):
                        d1 = cand_midi - prev_midi
                        d2 = entering_curr - entering_prev
                        if d1 != 0 and d2 != 0 and np.sign(d1) == np.sign(d2):
                            has_parallel = True

            if not has_parallel:
                best = cand_midi
                break

        if best is None:
            best = candidates[0][0] if candidates else current_midi

        notes.append(Note(midi=best, onset=t, duration=dur))
        prev_midi = current_midi
        current_midi = best
        t += dur

    return notes


def _fit_to_range(subject: Subject, voice: FugueVoice) -> Subject:
    """
    Transpose subject up/down by octaves to fit within voice range.
    Tries to center the subject in the voice's range.
    """
    pitches = [n.midi for n in subject.notes]
    avg_pitch = sum(pitches) / len(pitches)
    range_center = (voice.range_low + voice.range_high) / 2

    # Transpose by octaves to get close to center
    octave_shift = round((range_center - avg_pitch) / 12) * 12

    if octave_shift != 0:
        return transpose(subject, octave_shift)
    return subject


# ═══════════════════════════════════════════════════════════════
# Quality evaluation
# ═══════════════════════════════════════════════════════════════

def evaluate_subject(subject: Subject) -> dict:
    """
    Evaluate the quality of a fugue subject.

    Good subjects have:
    1. Clear tonal center (starts/ends on tonic or dominant)
    2. Memorable melodic profile (mix of steps and leaps)
    3. Rhythmic variety (not all same duration)
    4. Moderate range (4th to octave typical)
    5. Good balance of ascending/descending motion
    """
    notes = subject.notes
    if len(notes) < 3:
        return {"score": 0, "issues": ["Subject too short"]}

    profile = subject.interval_profile
    abs_intervals = [abs(i) for i in profile]

    # 1. Tonal clarity: starts/ends on key center
    start_pc = notes[0].midi % 12
    end_pc = notes[-1].midi % 12
    key_pc = subject.key_midi % 12
    dominant_pc = (key_pc + 7) % 12

    tonal_score = 0
    if start_pc == key_pc:
        tonal_score += 2
    elif start_pc == dominant_pc:
        tonal_score += 1
    if end_pc == key_pc:
        tonal_score += 2
    elif end_pc == dominant_pc:
        tonal_score += 1

    # 2. Melodic interest: mix of steps and leaps
    steps = sum(1 for i in abs_intervals if i <= 2)
    leaps = sum(1 for i in abs_intervals if i > 2)
    step_ratio = steps / max(len(abs_intervals), 1)
    # Ideal: ~60-80% stepwise
    melodic_score = 0
    if 0.5 <= step_ratio <= 0.85:
        melodic_score = 3
    elif 0.3 <= step_ratio <= 0.95:
        melodic_score = 1

    # 3. Rhythmic variety
    durations = [n.duration for n in notes]
    unique_durs = len(set(durations))
    rhythmic_score = min(unique_durs - 1, 3)  # 0-3

    # 4. Range
    pitch_range = subject.pitch_range
    range_score = 0
    if 5 <= pitch_range <= 12:
        range_score = 3  # 4th to octave — ideal
    elif 3 <= pitch_range <= 16:
        range_score = 1

    # 5. Directional balance
    ups = sum(1 for i in profile if i > 0)
    downs = sum(1 for i in profile if i < 0)
    balance = min(ups, downs) / max(ups + downs, 1)
    balance_score = 2 if balance > 0.3 else (1 if balance > 0.15 else 0)

    total = tonal_score + melodic_score + rhythmic_score + range_score + balance_score
    max_total = 2 + 2 + 3 + 3 + 3 + 2  # = 15

    issues = []
    if tonal_score < 2:
        issues.append("Weak tonal center")
    if melodic_score == 0:
        issues.append(f"Step ratio {step_ratio:.0%} outside ideal range")
    if rhythmic_score == 0:
        issues.append("No rhythmic variety (all same duration)")
    if range_score == 0:
        issues.append(f"Range {pitch_range} semitones — too narrow or wide")
    if balance_score == 0:
        issues.append("Motion heavily biased in one direction")

    return {
        "total_score": total,
        "max_score": max_total,
        "percentage": round(total / max_total * 100),
        "tonal": tonal_score,
        "melodic": melodic_score,
        "rhythmic": rhythmic_score,
        "range": range_score,
        "balance": balance_score,
        "step_ratio": round(step_ratio, 2),
        "pitch_range": pitch_range,
        "n_notes": len(notes),
        "duration_beats": subject.duration_beats,
        "issues": issues,
    }


def evaluate_exposition(score: FugueScore, verbose: bool = False) -> dict:
    """
    Evaluate a fugue exposition.

    Checks:
    1. Subject integrity — does the answer preserve the subject's profile?
    2. Counterpoint — are voice pairs following the rules?
    3. Voice independence — do voices sound distinct?
    4. Structural completeness — did all voices enter?
    """
    report = {
        "voices_entered": 0,
        "subject_integrity": [],
        "counterpoint_issues": [],
        "voice_independence": 0.0,
    }

    # 1. Count entries
    active_voices = [v for v in score.voices if len(v.notes) > 0]
    report["voices_entered"] = len(active_voices)

    # 2. Counterpoint between each pair of active voices
    total_errors = 0
    total_warnings = 0
    for i in range(len(active_voices)):
        for j in range(i + 1, len(active_voices)):
            v1_notes = active_voices[i].notes
            v2_notes = active_voices[j].notes
            result = validate_two_voices(v1_notes, v2_notes, verbose=False)
            n_err = len(result["errors"])
            n_warn = len(result["warnings"])
            total_errors += n_err
            total_warnings += n_warn
            report["counterpoint_issues"].append({
                "voices": (active_voices[i].name, active_voices[j].name),
                "errors": n_err,
                "warnings": n_warn,
            })

    report["total_cp_errors"] = total_errors
    report["total_cp_warnings"] = total_warnings

    if verbose:
        print(f"\n═══ Fugue Exposition Report ═══")
        print(f"  Voices entered: {report['voices_entered']}/{len(score.voices)}")
        print(f"  Counterpoint errors: {total_errors}")
        print(f"  Counterpoint warnings: {total_warnings}")
        for cp in report["counterpoint_issues"]:
            v1, v2 = cp["voices"]
            print(f"    {v1}↔{v2}: {cp['errors']} errors, {cp['warnings']} warnings")

    return report


# ═══════════════════════════════════════════════════════════════
# Helper: notes to MIDI-compatible format
# ═══════════════════════════════════════════════════════════════

def score_to_midi_events(score: FugueScore) -> list[dict]:
    """
    Convert FugueScore to a flat list of MIDI events.

    Each event: {"voice": str, "midi": int, "onset": float,
                 "duration": float, "velocity": int}
    """
    events = []
    for voice in score.voices:
        for note in voice.notes:
            events.append({
                "voice": voice.name,
                "midi": note.midi,
                "onset": note.onset,
                "duration": note.duration,
                "velocity": 80,
            })
    return sorted(events, key=lambda e: e["onset"])

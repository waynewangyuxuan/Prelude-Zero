"""
Audio preview: render MIDI to WAV using simple additive synthesis.
(FluidSynth not available in this VM — using scipy-based fallback.)

Good enough to judge harmony; for real listening, import MIDI into GarageBand.
"""
import numpy as np
from scipy.io import wavfile
import pretty_midi


SAMPLE_RATE = 44100


def midi_note_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def synthesize_note(freq: float, duration: float, velocity: int = 80,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesize a single note using additive synthesis (piano-like timbre).
    Includes fundamental + harmonics with ADSR envelope.
    """
    n_samples = int(sample_rate * duration)
    if n_samples == 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Additive synthesis: fundamental + harmonics (decreasing amplitude)
    signal = np.zeros(n_samples)
    harmonics = [1.0, 0.5, 0.3, 0.15, 0.08, 0.04]
    for i, amp in enumerate(harmonics):
        h_freq = freq * (i + 1)
        if h_freq > sample_rate / 2:
            break  # Nyquist limit
        signal += amp * np.sin(2 * np.pi * h_freq * t)

    # ADSR envelope
    attack = min(0.01, duration * 0.1)
    decay = min(0.1, duration * 0.3)
    sustain_level = 0.6
    release = min(0.05, duration * 0.2)

    envelope = np.ones(n_samples)
    # Attack
    a_samples = int(attack * sample_rate)
    if a_samples > 0:
        envelope[:a_samples] = np.linspace(0, 1, a_samples)
    # Decay
    d_samples = int(decay * sample_rate)
    d_start = a_samples
    d_end = min(d_start + d_samples, n_samples)
    if d_end > d_start:
        envelope[d_start:d_end] = np.linspace(1, sustain_level, d_end - d_start)
    # Sustain
    if d_end < n_samples:
        envelope[d_end:] = sustain_level
    # Release
    r_samples = int(release * sample_rate)
    if r_samples > 0 and n_samples > r_samples:
        envelope[-r_samples:] *= np.linspace(1, 0, r_samples)

    # Apply velocity scaling and envelope
    vel_scale = velocity / 127.0
    return signal * envelope * vel_scale


def midi_to_wav(midi_path: str, wav_path: str,
                sample_rate: int = SAMPLE_RATE):
    """
    Render a MIDI file to WAV using simple additive synthesis.

    Args:
        midi_path: path to .mid file
        wav_path: path for output .wav file
        sample_rate: audio sample rate
    """
    pm = pretty_midi.PrettyMIDI(midi_path)
    duration = pm.get_end_time() + 1.0  # add 1s tail
    n_samples = int(sample_rate * duration)
    audio = np.zeros(n_samples)

    for instrument in pm.instruments:
        for note in instrument.notes:
            freq = midi_note_to_freq(note.pitch)
            note_dur = note.end - note.start
            note_audio = synthesize_note(freq, note_dur, note.velocity,
                                         sample_rate)
            start_sample = int(note.start * sample_rate)
            end_sample = start_sample + len(note_audio)
            if end_sample > n_samples:
                note_audio = note_audio[:n_samples - start_sample]
                end_sample = n_samples
            audio[start_sample:end_sample] += note_audio

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.8

    # Convert to int16
    audio_int16 = np.int16(audio * 32767)
    wavfile.write(wav_path, sample_rate, audio_int16)
    print(f"Saved WAV: {wav_path} ({duration:.1f}s, {sample_rate}Hz)")


def prettymidi_to_wav(pm: pretty_midi.PrettyMIDI, wav_path: str,
                      sample_rate: int = SAMPLE_RATE):
    """Render a PrettyMIDI object directly to WAV (without saving MIDI first)."""
    duration = pm.get_end_time() + 1.0
    n_samples = int(sample_rate * duration)
    audio = np.zeros(n_samples)

    for instrument in pm.instruments:
        for note in instrument.notes:
            freq = midi_note_to_freq(note.pitch)
            note_dur = note.end - note.start
            note_audio = synthesize_note(freq, note_dur, note.velocity,
                                         sample_rate)
            start_sample = int(note.start * sample_rate)
            end_sample = start_sample + len(note_audio)
            if end_sample > n_samples:
                note_audio = note_audio[:n_samples - start_sample]
                end_sample = n_samples
            audio[start_sample:end_sample] += note_audio

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.8

    audio_int16 = np.int16(audio * 32767)
    wavfile.write(wav_path, sample_rate, audio_int16)
    print(f"Saved WAV: {wav_path} ({duration:.1f}s, {sample_rate}Hz)")

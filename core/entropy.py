"""
Information-theoretic engine — measure musical surprise and predictability.

The core insight: good music lives in an entropy sweet spot.
Too low entropy → boring, predictable.
Too high entropy → random, incoherent.
Bach lives in the sweet spot: enough structure to be parseable,
enough surprise to be interesting.

Four measurements:
  1. Pitch transition entropy  — H(P_n | P_{n-1}) per voice
  2. Rhythm entropy            — H of IOI (inter-onset-interval) distribution
  3. Interval entropy          — H of interval-class transitions
  4. Cross-voice surprise      — how predictable is voice B given voice A?

Reference ranges (empirical, from music cognition literature):
  - Bach inventions/fugues: pitch H ≈ 2.5-3.2 bits
  - Random chromatic:        pitch H ≈ 3.58 bits (log2(12))
  - Single repeated note:    pitch H = 0 bits
  - Pop music:              pitch H ≈ 1.8-2.5 bits

Usage:
    profile = compute_entropy(pm, bpm=80)
    print(summary(profile))
    # → Pitch entropy: 2.81 bits (sweet spot: 2.5-3.2)
"""

import numpy as np
import pretty_midi
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Core data structure
# ═══════════════════════════════════════════════════════════════

@dataclass
class EntropyProfile:
    """Information-theoretic profile of a piece."""

    # Per-voice measurements
    pitch_entropy: dict[str, float]      # H(pitch class) per voice
    transition_entropy: dict[str, float]  # H(P_n | P_{n-1}) per voice
    rhythm_entropy: dict[str, float]      # H(IOI) per voice
    interval_entropy: dict[str, float]    # H(interval class) per voice

    # Global measurements
    pitch_bigram_entropy: float  # H of (pc_from, pc_to) bigrams, all voices
    global_rhythm_entropy: float  # H of all IOIs combined
    cross_voice_mi: float         # mutual information between voice pairs

    # Windowed entropy (tracks how entropy changes over time)
    beats: np.ndarray             # time axis
    windowed_pitch_h: np.ndarray  # pitch entropy in sliding window
    windowed_rhythm_h: np.ndarray # rhythm entropy in sliding window

    # Reference ranges
    sweet_spot: tuple[float, float] = (2.3, 3.2)  # bits

    def overall_pitch_h(self) -> float:
        """Average pitch transition entropy across voices."""
        vals = list(self.transition_entropy.values())
        return np.mean(vals) if vals else 0.0

    def predictability_score(self) -> float:
        """0 = random, 1 = totally predictable. Sweet spot ≈ 0.3-0.6."""
        max_h = np.log2(12)  # max entropy for 12 pitch classes
        h = self.overall_pitch_h()
        return 1.0 - (h / max_h) if max_h > 0 else 0.0

    def surprise_profile(self) -> str:
        """Human-readable assessment."""
        h = self.overall_pitch_h()
        low, high = self.sweet_spot
        if h < low:
            return f"TOO PREDICTABLE (H={h:.2f} < {low})"
        elif h > high:
            return f"TOO RANDOM (H={h:.2f} > {high})"
        else:
            balance = (h - low) / (high - low)
            if balance < 0.3:
                return f"STRUCTURED (H={h:.2f}, low end of sweet spot)"
            elif balance > 0.7:
                return f"ADVENTUROUS (H={h:.2f}, high end of sweet spot)"
            else:
                return f"BALANCED (H={h:.2f}, center of sweet spot)"

    def to_dict(self) -> dict:
        return {
            "pitch_entropy": self.pitch_entropy,
            "transition_entropy": self.transition_entropy,
            "rhythm_entropy": self.rhythm_entropy,
            "interval_entropy": self.interval_entropy,
            "pitch_bigram_entropy": self.pitch_bigram_entropy,
            "global_rhythm_entropy": self.global_rhythm_entropy,
            "cross_voice_mi": self.cross_voice_mi,
            "beats": self.beats.tolist(),
            "windowed_pitch_h": self.windowed_pitch_h.tolist(),
            "windowed_rhythm_h": self.windowed_rhythm_h.tolist(),
            "overall_pitch_h": self.overall_pitch_h(),
            "predictability": self.predictability_score(),
            "assessment": self.surprise_profile(),
        }


# ═══════════════════════════════════════════════════════════════
# Main computation
# ═══════════════════════════════════════════════════════════════

def compute_entropy(
    pm: pretty_midi.PrettyMIDI,
    bpm: float = 80.0,
    window_beats: float = 8.0,
    resolution: float = 1.0,
) -> EntropyProfile:
    """
    Compute information-theoretic profile from a PrettyMIDI.

    Args:
        pm: input MIDI
        bpm: tempo
        window_beats: sliding window size for windowed entropy
        resolution: sampling interval for windowed measurements
    """
    beat_dur = 60.0 / bpm

    # ── Collect notes per voice ──
    voices = {}
    for inst in pm.instruments:
        name = inst.name or f"Voice_{len(voices)}"
        notes = sorted(inst.notes, key=lambda n: n.start)
        voices[name] = [{
            "pitch": n.pitch,
            "pc": n.pitch % 12,
            "onset": n.start,
            "onset_beat": n.start / beat_dur,
            "duration": n.end - n.start,
            "dur_beat": (n.end - n.start) / beat_dur,
        } for n in notes]

    # ── Per-voice measurements ──
    pitch_h = {}
    trans_h = {}
    rhythm_h = {}
    interval_h = {}

    all_pcs = []
    all_bigrams = []
    all_iois = []

    for name, notes in voices.items():
        if len(notes) < 2:
            pitch_h[name] = 0.0
            trans_h[name] = 0.0
            rhythm_h[name] = 0.0
            interval_h[name] = 0.0
            continue

        pcs = [n["pc"] for n in notes]
        onsets = [n["onset_beat"] for n in notes]
        all_pcs.extend(pcs)

        # 1. Pitch class entropy H(PC)
        pitch_h[name] = _shannon_entropy(pcs)

        # 2. Transition entropy H(PC_n | PC_{n-1})
        # Approximated as H(bigram) - H(unigram)
        bigrams = [(pcs[i], pcs[i+1]) for i in range(len(pcs)-1)]
        all_bigrams.extend(bigrams)
        h_bigram = _shannon_entropy(bigrams)
        h_unigram = _shannon_entropy(pcs)
        trans_h[name] = max(0, h_bigram - h_unigram)

        # 3. Rhythm entropy H(IOI)
        iois = []
        for i in range(len(onsets) - 1):
            ioi = round(onsets[i+1] - onsets[i], 3)
            if ioi > 0:
                iois.append(ioi)
        all_iois.extend(iois)
        rhythm_h[name] = _shannon_entropy(iois)

        # 4. Interval entropy H(IC)
        intervals = [abs(pcs[i+1] - pcs[i]) % 12 for i in range(len(pcs)-1)]
        # Convert to interval class (0-6)
        ics = [min(iv, 12 - iv) for iv in intervals]
        interval_h[name] = _shannon_entropy(ics)

    # ── Global measurements ──
    pitch_bigram_h = _shannon_entropy(all_bigrams) if all_bigrams else 0.0
    global_rhythm_h = _shannon_entropy(all_iois) if all_iois else 0.0

    # Cross-voice mutual information
    cross_mi = _cross_voice_mi(voices, beat_dur)

    # ── Windowed entropy over time ──
    end_time = pm.get_end_time()
    end_beat = end_time / beat_dur
    beats = np.arange(0, end_beat, resolution)

    win_pitch = np.zeros(len(beats))
    win_rhythm = np.zeros(len(beats))

    all_notes_flat = []
    for name, notes in voices.items():
        for n in notes:
            all_notes_flat.append(n)

    for i, t in enumerate(beats):
        # Collect notes starting within window
        window_notes = [n for n in all_notes_flat
                        if t <= n["onset_beat"] < t + window_beats]
        if len(window_notes) < 3:
            continue

        # Pitch entropy in window
        pcs_w = [n["pc"] for n in window_notes]
        win_pitch[i] = _shannon_entropy(pcs_w)

        # Rhythm entropy in window
        sorted_onsets = sorted(n["onset_beat"] for n in window_notes)
        iois_w = [round(sorted_onsets[j+1] - sorted_onsets[j], 3)
                  for j in range(len(sorted_onsets)-1)
                  if sorted_onsets[j+1] > sorted_onsets[j]]
        win_rhythm[i] = _shannon_entropy(iois_w) if iois_w else 0.0

    return EntropyProfile(
        pitch_entropy=pitch_h,
        transition_entropy=trans_h,
        rhythm_entropy=rhythm_h,
        interval_entropy=interval_h,
        pitch_bigram_entropy=pitch_bigram_h,
        global_rhythm_entropy=global_rhythm_h,
        cross_voice_mi=cross_mi,
        beats=beats,
        windowed_pitch_h=win_pitch,
        windowed_rhythm_h=win_rhythm,
    )


# ═══════════════════════════════════════════════════════════════
# Shannon entropy
# ═══════════════════════════════════════════════════════════════

def _shannon_entropy(sequence) -> float:
    """
    Shannon entropy H = -Σ p(x) log2 p(x).

    Works on any hashable sequence.
    """
    if not sequence:
        return 0.0

    counts = Counter(sequence)
    total = sum(counts.values())
    h = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            h -= p * np.log2(p)
    return h


# ═══════════════════════════════════════════════════════════════
# Cross-voice mutual information
# ═══════════════════════════════════════════════════════════════

def _cross_voice_mi(voices: dict, beat_dur: float) -> float:
    """
    Mutual information between voice pairs at simultaneous points.

    High MI = voices are correlated (move together).
    Low MI = voices are independent.

    In Bach: moderate MI — voices are related but have independence.
    """
    voice_names = list(voices.keys())
    if len(voice_names) < 2:
        return 0.0

    # Sample at onset points of all voices
    all_onsets = sorted(set(
        n["onset_beat"] for notes in voices.values() for n in notes
    ))

    if len(all_onsets) < 5:
        return 0.0

    # For each pair, collect simultaneous pitch classes
    total_mi = 0.0
    pair_count = 0

    for i in range(len(voice_names)):
        for j in range(i+1, len(voice_names)):
            vi_notes = voices[voice_names[i]]
            vj_notes = voices[voice_names[j]]

            joint = []  # (pc_i, pc_j) pairs
            for t in all_onsets:
                pc_i = _pc_at_time(vi_notes, t)
                pc_j = _pc_at_time(vj_notes, t)
                if pc_i is not None and pc_j is not None:
                    joint.append((pc_i, pc_j))

            if len(joint) < 5:
                continue

            # MI = H(X) + H(Y) - H(X,Y)
            xs = [p[0] for p in joint]
            ys = [p[1] for p in joint]
            h_x = _shannon_entropy(xs)
            h_y = _shannon_entropy(ys)
            h_xy = _shannon_entropy(joint)
            mi = max(0, h_x + h_y - h_xy)
            total_mi += mi
            pair_count += 1

    return total_mi / pair_count if pair_count > 0 else 0.0


def _pc_at_time(notes: list[dict], t_beat: float) -> Optional[int]:
    """Find pitch class sounding at beat t."""
    for n in reversed(notes):
        if n["onset_beat"] <= t_beat < n["onset_beat"] + n["dur_beat"]:
            return n["pc"]
    return None


# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════

def summarize(profile: EntropyProfile, sections: list[tuple] = None) -> str:
    """Human-readable entropy summary."""
    lines = []
    lines.append("Entropy Profile")
    lines.append(f"  Assessment: {profile.surprise_profile()}")
    lines.append(f"  Predictability: {profile.predictability_score():.3f}")
    lines.append(f"  Sweet spot: {profile.sweet_spot[0]:.1f}-{profile.sweet_spot[1]:.1f} bits")

    lines.append("\n  Per-voice pitch entropy (H):")
    for name, h in profile.pitch_entropy.items():
        t_h = profile.transition_entropy.get(name, 0)
        lines.append(f"    {name:12s}: H(pc)={h:.3f}  H(trans)={t_h:.3f}")

    lines.append(f"\n  Per-voice rhythm entropy:")
    for name, h in profile.rhythm_entropy.items():
        lines.append(f"    {name:12s}: H(ioi)={h:.3f}")

    lines.append(f"\n  Per-voice interval-class entropy:")
    for name, h in profile.interval_entropy.items():
        lines.append(f"    {name:12s}: H(ic)={h:.3f}")

    lines.append(f"\n  Global:")
    lines.append(f"    Pitch bigram H:  {profile.pitch_bigram_entropy:.3f}")
    lines.append(f"    Rhythm H:        {profile.global_rhythm_entropy:.3f}")
    lines.append(f"    Cross-voice MI:  {profile.cross_voice_mi:.3f}")

    if sections:
        lines.append(f"\n  Per-section windowed pitch entropy:")
        for name, start, end in sections:
            mask = (profile.beats >= start) & (profile.beats < end)
            if mask.any():
                sec_h = profile.windowed_pitch_h[mask]
                lines.append(f"    {name:20s} [{start:.0f}-{end:.0f}] "
                             f"mean={sec_h.mean():.3f} range={sec_h.min():.3f}-{sec_h.max():.3f}")

    return "\n".join(lines)

"""
Tension Budget — prescriptive tension targets per section.

Instead of measuring tension after the fact (diagnostic),
we set targets BEFORE composing and let every decision serve them.

Usage:
    budget = FugueBudget()
    targets = budget["Stretto"]
    # targets.harmonic = 0.6  → use more distant chords
    # targets.dissonance = 0.5 → prefer voicings with m2/tritone
    # targets.registral = 0.7 → widen the spread
    # targets.density = 0.7 → more active voices
    # targets.melodic = 0.3 → allow larger leaps

    # Feed to voicing engine:
    scorer = tension_voicing_scorer(targets)
    voicing = find_best_voicing(..., extra_scorer=scorer)
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class SectionTargets:
    """Target tension values for a single section (all in [0, 1])."""
    harmonic: float = 0.3
    dissonance: float = 0.2
    melodic: float = 0.15
    registral: float = 0.3
    density: float = 0.3

    @property
    def combined(self) -> float:
        """Weighted combination (same weights as tension.py)."""
        return (0.30 * self.harmonic +
                0.25 * self.dissonance +
                0.20 * self.melodic +
                0.10 * self.registral +
                0.15 * self.density)


class TensionBudget:
    """
    Maps section names → target tension values.

    This is deliberately not a framework — it's a dict with helpers.
    """

    def __init__(self):
        self.sections: dict[str, SectionTargets] = {}

    def __getitem__(self, section: str) -> SectionTargets:
        return self.sections[section]

    def __setitem__(self, section: str, targets: SectionTargets):
        self.sections[section] = targets

    def __contains__(self, section: str) -> bool:
        return section in self.sections

    def summary(self) -> str:
        lines = ["Tension Budget:"]
        lines.append(f"  {'Section':20s} {'Harm':>5s} {'Diss':>5s} {'Melo':>5s} {'Reg':>5s} {'Dens':>5s} │ {'Comb':>5s}")
        lines.append("  " + "─" * 60)
        for name, t in self.sections.items():
            lines.append(f"  {name:20s} {t.harmonic:5.2f} {t.dissonance:5.2f} "
                         f"{t.melodic:5.2f} {t.registral:5.2f} {t.density:5.2f} │ {t.combined:5.3f}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Pre-built budgets for our pieces
# ═══════════════════════════════════════════════════════════════

def fugue_budget() -> TensionBudget:
    """
    Tension budget for a 4-voice C major fugue.

    Design principles:
    - Exposition: gradually builds as voices enter
    - Episodes: moderate, fluctuating (developmental)
    - Middle entries: slightly higher (new key areas)
    - Stretto: PEAK — maximum tension before resolution
    - Final cadence: dramatic release
    """
    b = TensionBudget()

    b["Exposition"]     = SectionTargets(harmonic=0.20, dissonance=0.15, melodic=0.10, registral=0.25, density=0.25)
    b["Episode 1"]      = SectionTargets(harmonic=0.35, dissonance=0.25, melodic=0.15, registral=0.45, density=0.40)
    b["Middle Entry 1"] = SectionTargets(harmonic=0.40, dissonance=0.30, melodic=0.15, registral=0.50, density=0.45)
    b["Episode 2"]      = SectionTargets(harmonic=0.35, dissonance=0.25, melodic=0.20, registral=0.40, density=0.35)
    b["Middle Entry 2"] = SectionTargets(harmonic=0.45, dissonance=0.35, melodic=0.20, registral=0.55, density=0.50)
    b["Episode 3"]      = SectionTargets(harmonic=0.50, dissonance=0.40, melodic=0.25, registral=0.50, density=0.55)
    # ↑ Episode 3 is the BUILD — it should ramp up toward Stretto
    b["Stretto"]        = SectionTargets(harmonic=0.60, dissonance=0.50, melodic=0.30, registral=0.70, density=0.70)
    # ↑ PEAK: this is where everything converges
    b["Final Cadence"]  = SectionTargets(harmonic=0.15, dissonance=0.10, melodic=0.10, registral=0.60, density=0.20)
    # ↑ RELEASE: wide registral spread at final chord, everything else drops

    return b


def prelude_budget() -> TensionBudget:
    """
    Tension budget for BWV 846-style arpeggiated prelude.

    Design principles:
    - Gradual build through harmonic adventurousness
    - Dom pedal (Section F) must be the PEAK
    - Resolution (G) is dramatic release
    """
    b = TensionBudget()

    b["A: Statement"]      = SectionTargets(harmonic=0.15, dissonance=0.10, melodic=0.10, registral=0.25, density=0.40)
    b["B: Expansion"]      = SectionTargets(harmonic=0.25, dissonance=0.15, melodic=0.15, registral=0.30, density=0.45)
    b["C: Tonicize V"]     = SectionTargets(harmonic=0.40, dissonance=0.25, melodic=0.15, registral=0.35, density=0.50)
    b["D: Return"]         = SectionTargets(harmonic=0.30, dissonance=0.20, melodic=0.15, registral=0.30, density=0.45)
    b["E: Build tension"]  = SectionTargets(harmonic=0.55, dissonance=0.40, melodic=0.25, registral=0.40, density=0.60)
    b["F: Dom pedal"]      = SectionTargets(harmonic=0.70, dissonance=0.55, melodic=0.30, registral=0.45, density=0.65)
    # ↑ PEAK: dominant pedal creates maximum harmonic tension
    b["G: Resolution"]     = SectionTargets(harmonic=0.10, dissonance=0.05, melodic=0.10, registral=0.35, density=0.30)

    return b


# ═══════════════════════════════════════════════════════════════
# Voicing integration — extra_scorer for find_best_voicing
# ═══════════════════════════════════════════════════════════════

# Interval-class dissonance (same as tension.py)
_IC_DISSONANCE = {
    0: 0.0, 1: 1.0, 2: 0.3, 3: 0.2,
    4: 0.15, 5: 0.05, 6: 0.8
}


def _voicing_dissonance(voicing: np.ndarray, bass: int) -> float:
    """Compute dissonance of a voicing (0 to 1)."""
    pitches = [bass] + voicing.tolist()
    total = 0.0
    count = 0
    for i in range(len(pitches)):
        for j in range(i + 1, len(pitches)):
            ic = abs(pitches[i] - pitches[j]) % 12
            if ic > 6:
                ic = 12 - ic
            total += _IC_DISSONANCE.get(ic, 0.3)
            count += 1
    return total / count if count > 0 else 0.0


def _voicing_spread(voicing: np.ndarray, bass: int) -> float:
    """Registral spread of a voicing, normalized to [0, 1]."""
    all_notes = [bass] + voicing.tolist()
    spread = max(all_notes) - min(all_notes)
    return min(spread / 48.0, 1.0)


def tension_voicing_scorer(targets: SectionTargets, bass: int):
    """
    Create an extra_scorer callback for find_best_voicing()
    that biases toward voicings matching the tension targets.

    Higher target.dissonance → prefer voicings with more dissonant intervals.
    Higher target.registral → prefer wider voicings.

    Returns a scorer function: candidate_voicing → penalty (lower = better)

    Integration:
        scorer = tension_voicing_scorer(budget["Stretto"], bass_midi=43)
        voicing = find_best_voicing(pcs, bass, ..., extra_scorer=scorer)
    """
    def scorer(candidate: np.ndarray) -> float:
        # How far is this voicing's dissonance from the target?
        actual_diss = _voicing_dissonance(candidate, bass)
        diss_delta = targets.dissonance - actual_diss
        # Negative delta = we want MORE dissonance than this voicing has → penalize
        # Positive delta = this voicing is already dissonant enough → ok
        diss_penalty = max(-diss_delta, 0) * 30  # penalize insufficiently dissonant
        diss_bonus = max(diss_delta, 0) * 5      # mild bonus for meeting target

        # Registral spread
        actual_spread = _voicing_spread(candidate, bass)
        spread_delta = targets.registral - actual_spread
        spread_penalty = max(-spread_delta, 0) * 20
        spread_bonus = max(spread_delta, 0) * 3

        return diss_penalty - diss_bonus + spread_penalty - spread_bonus

    return scorer


# ═══════════════════════════════════════════════════════════════
# Compositional guidance — what choices match the budget?
# ═══════════════════════════════════════════════════════════════

# Distance from C major diatonic for common chords (Roman numerals)
# Higher = more harmonically tense
HARMONIC_DISTANCE = {
    "I": 0.0, "IV": 0.1, "V": 0.1, "vi": 0.15, "ii": 0.2, "iii": 0.2,
    "V7": 0.25, "viio": 0.3, "V/V": 0.4, "V7/V": 0.45,
    "iv": 0.35, "bVI": 0.5, "bVII": 0.45,
    "viio7": 0.5, "viio7/V": 0.55, "#ivo7": 0.6,
    "N6": 0.65, "It6": 0.7, "Fr6": 0.75, "Ger6": 0.8,
}


def suggest_chords(targets: SectionTargets, key_str: str = "C") -> list[str]:
    """
    Suggest chord types that match the harmonic tension target.

    Low harmonic target → I, IV, V, vi
    Medium → V7, ii, viio, V/V
    High → viio7, augmented 6ths, Neapolitan
    """
    target_h = targets.harmonic
    margin = 0.15

    suggestions = []
    for chord, dist in HARMONIC_DISTANCE.items():
        if abs(dist - target_h) < margin:
            suggestions.append(chord)

    # Sort by closeness to target
    suggestions.sort(key=lambda c: abs(HARMONIC_DISTANCE[c] - target_h))
    return suggestions


def density_guidance(targets: SectionTargets) -> dict:
    """
    Suggest rhythmic density parameters based on density target.

    Returns dict with:
    - min_note_dur: shortest note value (in beats)
    - voices_active: how many voices should have independent lines
    - ornaments: whether to add passing tones, turns, etc.
    """
    d = targets.density

    if d < 0.2:
        return {"min_note_dur": 2.0, "voices_active": 2, "ornaments": False}
    elif d < 0.4:
        return {"min_note_dur": 1.0, "voices_active": 3, "ornaments": False}
    elif d < 0.6:
        return {"min_note_dur": 0.5, "voices_active": 4, "ornaments": False}
    else:
        return {"min_note_dur": 0.5, "voices_active": 4, "ornaments": True}


def melodic_guidance(targets: SectionTargets) -> dict:
    """
    Suggest melodic parameters based on melodic tension target.

    Returns dict with:
    - max_leap: largest allowed interval in semitones
    - prefer_stepwise: probability of choosing stepwise motion
    - allow_chromatic: whether chromatic passing tones are OK
    """
    m = targets.melodic

    if m < 0.15:
        return {"max_leap": 4, "prefer_stepwise": 0.8, "allow_chromatic": False}
    elif m < 0.25:
        return {"max_leap": 7, "prefer_stepwise": 0.6, "allow_chromatic": False}
    else:
        return {"max_leap": 12, "prefer_stepwise": 0.4, "allow_chromatic": True}

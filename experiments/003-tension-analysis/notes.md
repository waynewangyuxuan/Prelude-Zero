# Experiment 003: Tension Curve Analysis

**Date:** 2026-02-12
**Goal:** Diagnose why our music sounds "correct but flat" using a multi-dimensional tension model

## Setup

Built `core/tension.py`: 5-dimensional tension function
- T(t) = 0.30·harmonic + 0.25·dissonance + 0.20·melodic + 0.10·registral + 0.15·density
- Harmonic: DFT f₅ magnitude + phase distance from key
- Dissonance: interval-class roughness (Hindemith/Huron model)
- Melodic: average interval sizes across voices
- Registral: vertical spread (max - min) / 48
- Density: note onsets per window / 8

Built `core/tension_budget.py`: prescriptive targets per section

## Key Finding: Tension Peaks Are In The Wrong Place

### Prelude
| Section | Combined | Expected Role |
|---------|----------|---------------|
| A: Statement | 0.210 | Low (intro) ✓ |
| B: Expansion | 0.216 | Moderate ✓ |
| C: Tonicize V | 0.263 | Moderate ✓ |
| D: Return | 0.231 | Dip ✓ |
| E: Build tension | 0.320 | **Highest!** But should be 2nd |
| F: Dom pedal | 0.200 | **Should be PEAK, is below average** |
| G: Resolution | 0.186 | Low (release) ✓ |

**Peak at beat 52 (Section C), should be at Section F (Dom pedal)**
Distance from ideal: 0.303

### Fugue (after v2 stretto rewrite)
| Section | Combined | Expected Role |
|---------|----------|---------------|
| Exposition | 0.176 | Low (intro) ✓ |
| Episode 1 | 0.331 | Moderate ✓ |
| Middle Entry 1 | 0.291 | Moderate ✓ |
| Episode 2 | 0.344 | **Highest!** |
| Middle Entry 2 | 0.324 | High ✓ |
| Episode 3 | 0.297 | **Should be BUILD toward stretto** |
| Stretto | 0.182 | **Should be PEAK, is nearly lowest** |
| Final Cadence | 0.221 | Low (release) ~ |

**Peak at beat 41 (Episode 1), should be at Stretto**
Distance from ideal: 0.231

## Stretto Rewrite Experiment

### v1 (original): 3 entries + G2 pedal
- Entry delay: 4.5 beats
- Soprano: +5 (P4), Tenor: -12 (octave), Bass: G2 pedal
- Stretto beat range: 78-96

### v2 (tension-driven): 4 entries + G2 pedal
- Entry delay: 3.0 beats (33% tighter overlap)
- Soprano: +7 (P5, creates F# vs F♮ clash)
- Tenor: -12 (octave)
- Bass: G2 pedal (78-87) THEN active entry at -19 (F transposition, Bb vs B♮ clash)
- Parallel 5th fix: +1 semitone on note[1] of soprano/tenor/bass entries
- 305 notes, 0 counterpoint errors

### Results
| Dimension | v1 (wrong boundaries) | v2 (correct boundaries) | Budget Target |
|-----------|----------------------|------------------------|---------------|
| Harmonic | 0.187* | 0.194 | 0.60 |
| Dissonance | 0.131* | 0.179 | 0.50 |
| Melodic | 0.053* | 0.084 | 0.30 |
| Registral | 0.502* | 0.299 | 0.70 |
| Density | 0.163* | 0.215 | 0.70 |
| **Combined** | **0.174*** | **0.182** | **~0.65** |

*v1 values were measured with wrong section boundaries (88-96 instead of 78-96)

**Verdict: marginal improvement. The gap between actual (0.182) and target (~0.65) is still huge.**

## Root Cause Analysis

The stretto's low tension is NOT a tuning problem — it's a structural one:

1. **The subject itself is too "safe"**: C E D G F E D C B C — mostly diatonic, mostly stepwise. When you overlap 3-4 copies, the resulting harmonies are still mostly consonant.

2. **Transposition preserves consonance**: Entries at P5, octave, and P4 create mostly consonant vertical intervals. Bach's real stretti often use entries at the 2nd or 3rd for maximum friction.

3. **Density ceiling**: The subject has only 10 notes over 9 beats (~1.1 notes/beat). Even with 4 overlapping entries, peak density is ~4 notes/beat. The episodes achieve similar density with 16th-note sequences.

4. **No free counterpoint**: Real Bach stretti add free voices with chromatic passing tones, suspensions, and diminutions. Our stretto is just "stack the subjects" — mechanical, not compositional.

## What The Tension Engine Taught Us

The diagnostic is working perfectly:
- It correctly identifies that the climactic sections are underpowered
- It tells us WHICH dimensions are lacking (harmonic, density for stretto; dissonance for prelude)
- It quantifies the gap between actual and ideal (distance from target)

But the PRESCRIPTIVE step requires compositional changes beyond transposition:
- Chromatic countermelodies between stretto entries
- Suspensions (hold a note into the next harmony = dissonance)
- Diminution of subject fragments (shorter note values = density)
- Strategic use of secondary dominants and augmented 6ths

## Stretto v3: Free Counterpoint (2026-02-13)

### What changed
Replaced mechanical "stack the subjects" with compositional writing:
- **Layer 1 (structural backbone)**: Kept 2 subject entries — Alto at C maj, Soprano at +7 (G maj)
- **Layer 2 (free voices)**: Replaced Tenor & Bass subject entries with fully free chromatic counterpoint
  - Tenor: 27 notes, ascending chromatic with diminution (8th + 16th notes), 4 phases
  - Bass: 16 notes, chromatic pedal (G/Ab/F#) then staggered ascending chromatic line
- **Layer 3 (free tails)**: After subject entries end, Alto (15 notes, chromatic arch) and Soprano (8 notes, ascending chromatic) continue with free material
- Total: 305 → **350 notes**, 8 initial counterpoint errors → 0 after 4 targeted fixes

### Error fixes
All 8 errors were parallel 5ths/8ves from chromatic lines moving in parallel:
1. Alto tail beat 87: B3→C4 (oblique motion, creates tritone with soprano F#4)
2. Alto tail beat 93: C#4→C4 (hold, breaks parallel 8ve with soprano)
3. Tenor beat 87.5: B3→Bb3 (repeated note, breaks parallel 5th)
4. Bass phase 2: staggered chromatic ascent — hold G2 longer (89.5-91.0) to break ∥8ves with soprano

### Results: v2 → v3

| Dimension | v2 | v3 | Δ | Budget Target |
|-----------|-----|-----|-----|---------------|
| Harmonic | 0.194 | 0.251 | +29% | 0.60 |
| Dissonance | 0.179 | 0.169 | -6% | 0.50 |
| Melodic | 0.084 | 0.075 | -11% | 0.30 |
| Registral | 0.299 | 0.462 | +55% | 0.70 |
| Density | 0.215 | 0.404 | +88% | 0.70 |
| **Combined** | **0.182** | **0.240** | **+32%** | **~0.65** |

### Entropy (Information-Theoretic Balance)

Built `core/entropy.py` — Shannon entropy of pitch transitions, rhythm IOIs, interval classes, cross-voice MI.

| Metric | v2 | v3 | Sweet Spot |
|--------|-----|-----|-----------|
| Stretto pitch H | 2.783 | **3.113** | 2.3-3.2 |
| Fugue overall H | 1.79 | TBD | 2.3-3.2 |
| Cross-voice MI | 0.649 | **0.719** | — |

The free counterpoint pushed stretto pitch entropy from "barely in sweet spot" to "adventurous zone" — the music became less predictable without becoming random.

### Judgment

**What worked**: Free counterpoint is the right structural fix. Density and registral spread responded dramatically. The stretto went from 2nd lowest to 3rd highest section.

**What didn't work enough**: Harmonic tension and dissonance barely moved. The chromatic lines add melodic interest but don't fundamentally change the vertical harmonies. Need secondary dominants (V/V, viio7) and real suspensions (prepare → dissonance → resolve) to push harmonic and dissonance dimensions.

**Gap remaining**: Stretto at 0.240 vs target ~0.65. Episode 1 still peaks at 0.349. Two strategies:
1. Boost stretto further: secondary dominants, augmented 6ths, suspensions
2. Reduce episode tension: simplify episode material to create contrast

## Next Steps

1. **Harmonic boost for stretto**: Secondary dominants and diminished 7th chords in free counterpoint
2. **Suspensions**: Prepare-dissonance-resolve patterns in stretto voices
3. **Episode rebalancing**: Consider whether episodes are accidentally too tense
4. **Prelude tension fix**: Dom pedal section still underpowered
5. **Pink Floyd direction**: The tension + entropy engines are form-agnostic — apply to progressive rock

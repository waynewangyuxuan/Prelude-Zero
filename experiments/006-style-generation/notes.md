# Experiment 006 — Style Generation

## Goal
Generate ~1 minute audio pieces in three styles (Bach, Chopin, Floyd) using the
metric-guided melody generator, and evaluate against Experiment 005 benchmarks.

## v1: Hand-Composed (generate_three_styles.py)

### Setup
- Bach: 108 BPM, A minor, Two-Part Invention — hand-composed subjects, countersubjects, episodes
- Chopin: 72 BPM, Eb major, Nocturne — hand-composed melody + arpeggiated LH
- Floyd: 76 BPM, E Phrygian — hand-composed themes + pad + bass

### Results
- Bach 54s/658 notes, Chopin 61s/176 notes, Floyd 87s/224 notes
- **Metric match: Bach 6/8, Chopin 4/8, Floyd 4/8**
- Cross-style: Bach incorrectly maps to Floyd (diagonal broken)

### Wayne's Feedback
- "chopin 太难听了" — mainly audio quality (additive synth)
- "bach太快了有点" — 108 BPM too fast
- "floyd还行"

## v2: Engine-Generated (gen_v2.py)

### New Infrastructure
Two new core modules built for this experiment:

1. **core/scales.py** — Scale/Mode Engine
   - 17 templates (church modes, pentatonics, blues, symmetric)
   - snap(), step(), contains(), chromatic_neighbors(), triad(), seventh()

2. **core/melody_gen.py** — Metric-Guided Melody Generator
   - StyleTarget dataclass with 14 parameters
   - 4-step algorithm: rhythm → pitch walk → phrase shaping → repetition
   - Three presets calibrated from Experiment 005 data

### Setup
- Bach: **92 BPM** (slower per feedback), A minor, two generated voices (RH + LH)
- Chopin: 72 BPM, Eb major, generated melody + algorithmic arpeggios
- Floyd: 76 BPM, E Phrygian, generated lead + pad + bass

### Iteration History

**Run 1** (initial): dur_cv way too high (Chopin 0.93, Floyd 2.21), chromaticism too high
- Root cause: rhythm generator spread too aggressive, chromaticism probability not calibrated

**Fix 1**: Rewrote `_generate_rhythm()` with controlled geomspace:
```
max_ratio = 2.0 ** (target.duration_cv * 3), capped at 16
palette = geomspace(shortest, longest, n_types)
```

**Fix 2**: Reduced chromaticism probability (×0.5 → ×0.15):
- chromaticism metric counts unique chromatic PCs / total unique PCs
- Even few chromatic notes introduce many unique chromatic PCs
- Low per-note probability needed to keep metric near target

**Fix 3**: Scale-snapped repetition transpositions:
- `_apply_repetition` transposes motifs by [0,0,0,2,-2,5,7] semitones
- Transposed pitches can land off-scale → snap back to scale

**Fix 4**: Chopin final chord kept in accompaniment track (not melody)

### Final Results

| Style  | Duration | Notes | Metrics Match | σ-distance |
|--------|----------|-------|---------------|------------|
| Bach   | 49.6s    | 396   | **8/8**       | 0.86       |
| Chopin | 58.2s    | 214   | **8/8**       | 0.65       |
| Floyd  | 56.9s    | 165   | **8/8**       | 0.85       |

### Cross-Style Distance Matrix (★ = closest)
```
                 → Bach    → Chopin   → Floyd
Bach             0.86 ★     2.23      1.69
Chopin           0.92       0.65 ★    1.90
Floyd            2.65       2.65      0.85 ★
```
**All stars on the diagonal — each piece correctly identifies as its target style.**

### Key Metrics Comparison (v1 → v2)

| Metric         | Bach v1→v2     | Chopin v1→v2    | Floyd v1→v2     |
|----------------|----------------|-----------------|-----------------|
| Match score    | 6/8 → **8/8**  | 4/8 → **8/8**  | 4/8 → **8/8**  |
| dur_cv         | 0.47 → 0.05   | 0.71 → 0.29    | 0.91 → 0.60    |
| chromaticism   | 0.11 → 0.00   | 0.00 → 0.12    | 0.27 → 0.14    |
| step_ratio     | 0.80 → 0.84   | 0.47 → 0.80    | 0.63 → 0.29    |
| density        | 8.76 → 3.00   | 0.74 → 1.27    | 1.12 → 0.54    |

## Key Insights

1. **Metric-guided generation >> hand-composition** for style matching.
   Hand-composing note-by-note is fragile and hard to control across many metrics
   simultaneously. The generator's constrained random walk naturally produces
   statistically correct distributions.

2. **The chromaticism metric is non-linear.** It measures unique chromatic PCs,
   not per-note frequency. A tiny per-note probability (1.8%) produces the right
   fraction of unique chromatic pitch classes (~12%).

3. **Rhythm generation needs controlled spread.** Using geomspace with a CV-derived
   ratio (2^(cv×3)) gives intuitive control: cv=0.08 → near-uniform motor rhythm,
   cv=0.35 → moderate variety, cv=0.90 → extreme contrast.

4. **Repetition transposition breaks tonality.** Transposing motifs by fixed
   semitones without scale-snapping introduces unintended chromatic notes.

5. **Audio quality ≠ composition quality.** The additive synth makes everything
   sound bad, especially Chopin. MIDI files are the real deliverable — render in
   GarageBand/Logic for proper assessment.

## Files
- `gen_v2.py` — Engine-generated v2 (using core/scales.py + core/melody_gen.py)
- `generate_three_styles.py` — Hand-composed v1 (archived)
- `evaluate.py` — Evaluation against Experiment 005 benchmarks
- `bach_v2.mid/.wav`, `chopin_v2.mid/.wav`, `floyd_v2.mid/.wav` — v2 outputs
- `bach_invention.mid/.wav`, `chopin_nocturne.mid/.wav`, `floyd_phrygian.mid/.wav` — v1 outputs

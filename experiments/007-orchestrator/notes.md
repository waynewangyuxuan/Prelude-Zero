# Experiment 007 — Orchestrator Validation

## Goal
Validate the new tension-driven orchestrator engine by generating a 3+ minute
Floyd long-form piece with progressive multi-voice layering.

## New Engine Modules

### core/tension_curve.py
- **PieceForm**: Define sections with (name, beats, tension, transition)
- **TensionCurve**: Per-beat tension array with query interface (.at(), .section_at(), .mean_tension())
- **Smooth interpolation**: Cosine (ease in/out), linear, or sudden transitions
- **Presets**: long_form_build (Floyd/post-rock), arch_form (Chopin Nocturne), ramp_form (Bach fugue)

### core/orchestrator.py
- **tension_to_target()**: Map [0,1] tension → StyleTarget per voice role (lead, counter, bass, pad)
- **VoicePlan**: Hysteresis-based voice entry/exit (enter at threshold, exit below lower threshold)
- **Orchestrator.arrange()**: Full pipeline — plan voices → generate per-section → assemble MIDI → humanize
- **Pad generator**: Sustained chords from scale triads/sevenths, chord frequency varies with tension

### melody_gen.py fix: Density control
- **Bug**: Previous rhythm generator filled beats by accumulating durations → note count depended on average duration, not density target. High CV (bimodal weights) produced fewer notes than intended.
- **Fix**: Compute n_notes = density × total_beats first, generate n_notes durations from palette, then scale to fill total_beats. This preserves relative duration distribution (CV) while hitting exact note count.

## Validation Piece: Floyd Long-Form

### Structure
| Section | Beats | Tension | Voices |
|---------|-------|---------|--------|
| Intro | 40 | 0.10 | Lead, Bass |
| Build | 48 | 0.32 | + Pad |
| Development | 48 | 0.55 | + Counter |
| Climax | 48 | 0.80 | All 4 |
| Descent | 32 | 0.40 | All 4 → Counter exits |
| Fade | 32 | 0.08 | Lead, Bass, Pad → Pad exits |

### Results
- **Duration**: 195.7s (3m16s)
- **Total notes**: 454 across 4 instruments
- **Lead melody**: 168 notes, 8/8 Floyd metrics within 2σ

### Density follows tension arc ✓
```
Intro    (T=0.12): 0.47 notes/beat  ← sparse solo
Build    (T=0.32): 0.62 notes/beat
Dev      (T=0.55): 0.79 notes/beat
Climax   (T=0.73): 0.92 notes/beat  ← peak density
Descent  (T=0.40): 0.69 notes/beat
Fade     (T=0.11): 0.47 notes/beat  ← sparse again
```

### Voice entry/exit timing ✓
```
Lead:    beats   0-248  (always present)
Bass:    beats  34-248  (enters late Intro)
Pad:     beats  48-225  (enters Build, exits mid-Fade)
Counter: beats  95-213  (enters Development, exits Descent)
```

### Floyd reference comparison (8/8 ✓)
All metrics within 2σ of Experiment 005 Floyd reference distribution.

## Key Findings

1. **Tension→density mapping works**: Monotonic density increase from Intro to Climax,
   then decrease through Descent and Fade. The `tension_to_target()` function correctly
   modulates StyleTarget parameters based on tension.

2. **Progressive layering creates narrative**: Starting solo, adding bass drone, then
   pad atmosphere, then countermelody at the peak — this is the structure of a
   Floyd-style piece, and it emerges naturally from tension thresholds.

3. **Hysteresis prevents flicker**: Entry at 0.48, exit at 0.30 for counter means
   it doesn't rapidly toggle on/off near the threshold.

4. **Rhythm generator density fix was critical**: Without explicit note count control,
   high-CV sections (bimodal weights) produced fewer notes despite higher density targets.
   The fix decouples "how many notes" from "what rhythm".

5. **Backward compatible**: Experiment 006 still passes 24/24 after the rhythm fix.

## Files
- `generate.py` — Orchestrator validation script
- `floyd_longform.mid` — 3m16s Floyd piece (4 voices)
- `floyd_longform.wav` — Preview audio (additive synth, render MIDI in GarageBand)

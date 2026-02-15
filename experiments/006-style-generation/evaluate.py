"""
Evaluate the three generated pieces against their target style profiles.
Compare with Experiment 005 benchmarks.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pretty_midi
from core.melody import compute_melody_profile, summarize

OUT_DIR = os.path.dirname(__file__)

# Reference ranges from Experiment 005 (mean ± std)
STYLE_REFS = {
    'bach': {
        'pitch_range': (9.8, 2.1),
        'step_ratio': (0.631, 0.296),
        'direction_change_ratio': (0.546, 0.298),
        'rhythm_density': (3.075, 1.109),
        'chromaticism': (0.0, 0.0),
        'duration_cv': (0.168, 0.148),
        'mean_run_length': (2.096, 1.029),
        'tonal_clarity': (0.777, 0.061),
    },
    'chopin': {
        'pitch_range': (10.2, 3.49),
        'step_ratio': (0.720, 0.165),
        'direction_change_ratio': (0.289, 0.071),
        'rhythm_density': (1.513, 0.374),
        'chromaticism': (0.150, 0.137),
        'duration_cv': (0.274, 0.158),
        'mean_run_length': (3.050, 0.660),
        'tonal_clarity': (0.711, 0.189),
    },
    'floyd': {
        'pitch_range': (27.42, 10.36),
        'step_ratio': (0.421, 0.211),
        'direction_change_ratio': (0.617, 0.100),
        'rhythm_density': (1.100, 0.832),
        'chromaticism': (0.245, 0.104),
        'duration_cv': (0.967, 0.390),
        'mean_run_length': (1.649, 0.249),
        'tonal_clarity': (0.779, 0.084),
    }
}

def sigma_distance(val, mean, std):
    """How many σ away is val from the reference mean?"""
    if std == 0:
        # For zero-variance references (e.g. Bach chromaticism = 0±0),
        # use absolute difference as a proxy σ-distance
        return abs(val - mean) * 10.0  # 0.1 diff → 1σ equivalent
    return (val - mean) / std

def evaluate_piece(midi_path, style_name, bpm, track_idx=0):
    """Load MIDI, extract melody from specified track, compute metrics, compare."""
    pm = pretty_midi.PrettyMIDI(midi_path)
    inst = pm.instruments[track_idx]

    # Extract melody data
    notes = sorted(inst.notes, key=lambda n: n.start)
    pitches = [n.pitch for n in notes]
    onsets = [n.start for n in notes]
    durations = [n.end - n.start for n in notes]

    profile = compute_melody_profile(pitches, onsets, durations, bpm)

    print(f"\n{'='*60}")
    print(f"  {style_name.upper()} — {os.path.basename(midi_path)}")
    print(f"  Track: {inst.name}, {len(notes)} notes, {pm.get_end_time():.1f}s")
    print(f"{'='*60}")
    print(summarize(profile))

    # Compare with reference
    refs = STYLE_REFS.get(style_name, {})
    if refs:
        print(f"\n  {'Metric':<25} {'Generated':>10} {'Reference':>12} {'σ dist':>8} {'Match?':>8}")
        print(f"  {'-'*63}")

        matches = 0
        total = 0
        for key, (ref_mean, ref_std) in refs.items():
            val = getattr(profile, key, None)
            if val is None:
                continue
            total += 1
            sd = sigma_distance(val, ref_mean, ref_std)
            ok = abs(sd) < 2.0  # within 2σ
            if ok: matches += 1
            marker = '✓' if ok else '✗'
            print(f"  {key:<25} {val:>10.3f} {ref_mean:>8.3f}±{ref_std:.3f} {sd:>+7.1f}σ {marker:>8}")

        print(f"\n  Score: {matches}/{total} metrics within 2σ of reference")

    return profile


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  EXPERIMENT 006 — Style Generation Evaluation")
    print("="*60)

    results = {}

    # Detect which version to evaluate
    v2_exists = os.path.exists(os.path.join(OUT_DIR, 'bach_v2.mid'))

    if v2_exists:
        print("  (evaluating v2 — engine-generated)")
        # Bach: evaluate RH (track 0)
        p = evaluate_piece(
            os.path.join(OUT_DIR, 'bach_v2.mid'),
            'bach', bpm=92, track_idx=0
        )
        results['bach'] = p

        # Chopin: evaluate Melody (track 0)
        p = evaluate_piece(
            os.path.join(OUT_DIR, 'chopin_v2.mid'),
            'chopin', bpm=72, track_idx=0
        )
        results['chopin'] = p

        # Floyd: evaluate Lead Guitar (track 0)
        p = evaluate_piece(
            os.path.join(OUT_DIR, 'floyd_v2.mid'),
            'floyd', bpm=76, track_idx=0
        )
        results['floyd'] = p
    else:
        print("  (evaluating v1 — hand-composed)")
        p = evaluate_piece(
            os.path.join(OUT_DIR, 'bach_invention.mid'),
            'bach', bpm=108, track_idx=0
        )
        results['bach'] = p

        p = evaluate_piece(
            os.path.join(OUT_DIR, 'chopin_nocturne.mid'),
            'chopin', bpm=72, track_idx=0
        )
        results['chopin'] = p

        p = evaluate_piece(
            os.path.join(OUT_DIR, 'floyd_phrygian.mid'),
            'floyd', bpm=76, track_idx=0
        )
        results['floyd'] = p

    # Cross-style check: does each piece match its OWN style better than others?
    print("\n" + "="*60)
    print("  CROSS-STYLE DISTANCE MATRIX")
    print("="*60)
    header = 'Piece / Style'
    print(f"\n  {header:<18} {'-> Bach':>10} {'-> Chopin':>10} {'-> Floyd':>10}")
    print(f"  {'-'*48}")

    for piece_name, profile in results.items():
        dists = {}
        for style_name, refs in STYLE_REFS.items():
            total_sq = 0
            count = 0
            for key, (ref_mean, ref_std) in refs.items():
                val = getattr(profile, key, None)
                if val is None:
                    continue
                sd = sigma_distance(val, ref_mean, ref_std)
                total_sq += sd ** 2
                count += 1
            dists[style_name] = (total_sq / count) ** 0.5 if count > 0 else float('inf')

        closest = min(dists, key=dists.get)
        cells = []
        for sn in ['bach', 'chopin', 'floyd']:
            d = dists[sn]
            marker = ' ★' if sn == closest else ''
            cells.append(f"{d:>7.2f}{marker}")
        print(f"  {piece_name:<18} {''.join(f'{c:>10}' for c in cells)}")

    print(f"\n  ★ = closest match (should be on the diagonal)")
    print()

"""
Experiment 006: Generate ~1 minute audio for each of three styles.
Target metric profiles from Experiment 005's real data analysis.

Bach  — Two-Part Invention in A minor, 108 BPM, continuous 16ths
Chopin — Nocturne in Eb major, 72 BPM, singing melody + arpeggios
Floyd  — Phrygian meditation in E, 76 BPM, spacious + ornamental
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pretty_midi
from core.audio import prettymidi_to_wav
from core.humanize import humanize, HumanizeConfig

OUT_DIR = os.path.dirname(__file__)


# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════

def add_note(inst, pitch, start, end, velocity=80):
    """Add a note with boundary checks."""
    pitch = max(21, min(108, int(pitch)))
    velocity = max(30, min(120, int(velocity)))
    if end > start + 0.01:
        inst.notes.append(pretty_midi.Note(
            velocity=velocity, pitch=pitch,
            start=float(start), end=float(end)
        ))


# ═══════════════════════════════════════════════════════════════
# BACH — Two-Part Invention in A minor
# Target: ~60s, density ~3 n/beat, stepwise, zero chromaticism
# ═══════════════════════════════════════════════════════════════

def generate_bach():
    BPM = 108
    beat = 60.0 / BPM       # 0.556s
    s16 = beat / 4           # sixteenth = 0.139s
    bar = beat * 4           # 2.222s
    # Target ~60s = ~27 bars

    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    rh = pretty_midi.Instrument(program=0, name='Right Hand')
    lh = pretty_midi.Instrument(program=0, name='Left Hand')

    # A natural minor scale pitches
    AM = [45, 47, 48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81]

    def snap(p):
        return min(AM, key=lambda x: abs(x - p))

    def step(p, d, n=1):
        idx = AM.index(snap(p))
        return AM[max(0, min(len(AM)-1, idx + d*n))]

    # ── Subject: 16 sixteenths, compact and motoric ──
    # A4 B C5 D E D C B | A B C D E F E D  (mostly stepwise, some direction changes)
    SUBJ = [0, 1, 1, 1, 1, -1, -1, -1, -1, 1, 1, 1, 1, 1, -1, -1]

    def write_subj(inst, t, start_p, inv=False):
        p = snap(start_p)
        for i, d in enumerate(SUBJ):
            dd = -d if inv else d
            if i > 0: p = step(p, dd)
            add_note(inst, p, t, t + s16*0.93, 75)
            t += s16
        return t

    # ── Countersubject: 8th-note rhythm, complementary ──
    CS_DUR = [2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1]  # in 16ths (total=16)
    CS_DIR = [1, 1, -1, 1, -1, -1, -1, -1, 1, -1, 1, 1]

    def write_cs(inst, t, start_p, inv=False):
        p = snap(start_p)
        for dur16, d in zip(CS_DUR, CS_DIR):
            dd = -d if inv else d
            dur = s16 * dur16
            add_note(inst, p, t, t + dur*0.90, 68)
            t += dur
            p = step(p, dd)
        return t

    # ── Episode: sequential motif, 2 bars ──
    MOTIF = [1, 1, -1, 1, 1, -1, 1, -1]  # 8 sixteenths

    def write_episode(inst, t, start_p, seqs=4, asc=True):
        p = snap(start_p)
        shift = 1 if asc else -1
        for _ in range(seqs):
            for iv in MOTIF:
                add_note(inst, p, t, t + s16*0.92, 72)
                t += s16
                p = step(p, iv)
            p = step(p, shift, 2)
        return t

    # ── Free running counterpoint ──
    def write_free(inst, t, start_p, n_16ths=16, seed=0):
        rng = np.random.RandomState(seed)
        p = snap(start_p)
        center = start_p
        for _ in range(n_16ths):
            add_note(inst, p, t, t + s16*0.91, 70)
            t += s16
            d = 1 if p < center else -1
            if rng.random() < 0.4: d = -d
            p = step(p, d)
        return t

    # ══════════════ STRUCTURE (27 bars ≈ 60s) ══════════════
    t = 0.0
    sbeats = [0]

    # ── Exposition: bars 1-6 (subject + answer + countersubject) ──
    # Bar 1-2: RH subject alone (A4=69)
    write_subj(rh, t, 69)
    t += s16 * 16  # 4 beats

    # Bar 3-4: LH answer (E4=64) + RH countersubject
    write_subj(lh, t, 64)
    write_cs(rh, t, 72)
    t += s16 * 16

    # Bar 5-6: RH subject again (A4=69) + LH countersubject
    write_subj(rh, t, 69, inv=False)
    write_cs(lh, t, 60)
    t += s16 * 16
    sbeats.append(t / beat)

    # ── Episode 1: bars 7-8 (ascending sequences) ──
    write_episode(rh, t, 72, seqs=4, asc=True)
    write_episode(lh, t, 60, seqs=4, asc=True)
    t += s16 * 32
    sbeats.append(t / beat)

    # ── Middle Entry 1 (C major): bars 9-12 ──
    write_subj(lh, t, 60)  # C4
    write_cs(rh, t, 76)
    t += s16 * 16
    write_subj(rh, t, 72, inv=True)
    write_free(lh, t, 60, 16, seed=1)
    t += s16 * 16
    sbeats.append(t / beat)

    # ── Episode 2: bars 13-14 (descending) ──
    write_episode(rh, t, 76, seqs=4, asc=False)
    write_episode(lh, t, 64, seqs=4, asc=False)
    t += s16 * 32
    sbeats.append(t / beat)

    # ── Middle Entry 2 (D minor): bars 15-18 ──
    write_subj(rh, t, 74)  # D5
    write_cs(lh, t, 62)
    t += s16 * 16
    write_subj(lh, t, 62, inv=True)
    write_free(rh, t, 74, 16, seed=2)
    t += s16 * 16
    sbeats.append(t / beat)

    # ── Episode 3: bars 19-20 ──
    write_episode(rh, t, 74, seqs=4, asc=False)
    write_free(lh, t, 57, 32, seed=3)
    t += s16 * 32
    sbeats.append(t / beat)

    # ── Middle Entry 3 (F major): bars 21-24 ──
    write_subj(lh, t, 65)  # F4
    write_cs(rh, t, 77)
    t += s16 * 16
    write_subj(rh, t, 77)  # F5
    write_free(lh, t, 65, 16, seed=4)
    t += s16 * 16
    sbeats.append(t / beat)

    # ── Episode 4: bars 25-26 (descending, preparing return to Am) ──
    write_episode(rh, t, 77, seqs=4, asc=False)
    write_episode(lh, t, 65, seqs=4, asc=False)
    t += s16 * 32
    sbeats.append(t / beat)

    # ── Return: bars 27-28 (subject in Am, both voices) ──
    write_subj(rh, t, 69)
    write_cs(lh, t, 57)
    t += s16 * 16
    write_subj(lh, t, 57, inv=True)
    write_cs(rh, t, 72, inv=True)
    t += s16 * 16
    sbeats.append(t / beat)

    # ── Stretto: bars 29-32 (entries 1 beat apart) ──
    t_s = t
    write_subj(rh, t_s, 69)
    write_subj(lh, t_s + s16*4, 64)  # 1 beat later
    t = t_s + s16 * 20  # 16 + 4 overlap
    # Second stretto pair
    write_subj(lh, t, 60)
    write_subj(rh, t + s16*4, 72, inv=True)
    t += s16 * 20
    sbeats.append(t / beat)

    # ── Coda: bars 25-27 ──
    # LH pedal on A
    add_note(lh, 57, t, t + bar * 2, 65)  # A3 pedal
    # RH descending scale flourish
    p = 81  # A5
    for i in range(16):
        add_note(rh, p, t, t + s16*0.88, 80 - i*2)
        t += s16
        p = step(p, -1)
    # Ascending scale to final
    for i in range(8):
        add_note(rh, p, t, t + s16*0.88, 65 + i*2)
        t += s16
        p = step(p, 1)
    t += beat  # pause
    # Final A minor chord
    for p in [45, 57, 64, 69, 76]:
        add_note(rh if p > 60 else lh, p, t, t + bar, 85)
    t += bar
    sbeats.append(t / beat)

    pm.instruments.extend([rh, lh])

    config = HumanizeConfig(
        bpm=BPM, velocity_jitter=4, phrase_arc_strength=0.06,
        timing_sigma=0.006, default_legato=0.85,
        cadence_rubato=0.05, cadence_window=2.0,
    )
    pm = humanize(pm, config=config, section_beats=sbeats)

    mid = os.path.join(OUT_DIR, 'bach_invention.mid')
    wav = os.path.join(OUT_DIR, 'bach_invention.wav')
    pm.write(mid)
    prettymidi_to_wav(pm, wav)
    dur = pm.get_end_time()
    nn = sum(len(i.notes) for i in pm.instruments)
    print(f"  Bach: {dur:.1f}s, {nn} notes")
    return pm


# ═══════════════════════════════════════════════════════════════
# CHOPIN — Nocturne in Eb major
# Target: ~65s, density ~1.5, stepwise, long arcs, chromatic color
# ═══════════════════════════════════════════════════════════════

def generate_chopin():
    BPM = 72
    beat = 60.0 / BPM  # 0.833s
    bar = beat * 4      # 3.333s
    eighth = beat / 2
    # Target ~65s = ~19 bars. Structure: A(8) + B(8) + coda(2) = 18 bars = 60s

    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    mel = pretty_midi.Instrument(program=0, name='Melody')
    acc = pretty_midi.Instrument(program=0, name='Accompaniment')

    # ── LH arpeggio pattern: 8 eighths per bar ──
    def arp_bar(inst, t, root, quality='maj'):
        ivs = {'maj': [0,4,7,12,16,12,7,4], 'min': [0,3,7,12,15,12,7,3],
               'dom7': [0,4,7,10,16,12,7,4], 'maj7': [0,4,7,11,16,12,7,4],
               'dim': [0,3,6,12,15,12,6,3]}
        for iv in ivs.get(quality, ivs['maj']):
            add_note(inst, root+iv, t, t+eighth*0.88, 42)
            t += eighth
        return t

    # ── Melody: hand-composed for maximum Romantic feel ──
    # Each (pitch, duration_in_beats, velocity)
    # Section A: Bb4→up to Ab5→down to Bb4. Long singing arc.
    melody_a = [
        # Bar 1-2: gentle ascent
        (70, 2.0, 58),   # Bb4 — half note
        (72, 1.5, 62),   # C5
        (74, 1.0, 65),   # D5
        (75, 1.5, 68),   # Eb5
        # Bar 3-4: continue up, chromatic touch
        (77, 2.0, 72),   # F5
        (78, 1.0, 75),   # F#5 (chromatic!)
        (79, 2.0, 78),   # G5
        (80, 1.0, 80),   # Ab5
        # Bar 5-6: peak + descent
        (80, 2.0, 82),   # Ab5 — linger at peak
        (79, 1.5, 78),   # G5
        (77, 1.5, 74),   # F5
        (75, 1.5, 70),   # Eb5
        # Bar 7-8: resolve
        (74, 1.5, 66),   # D5
        (73, 1.0, 64),   # Db5 (chromatic passing)
        (72, 1.5, 60),   # C5
        (70, 2.5, 55),   # Bb4 — long resolution
    ]

    # Section B: higher, more intense, more chromatic
    melody_b = [
        # Bar 9-10: B theme entry
        (79, 1.5, 72),   # G5
        (80, 2.0, 76),   # Ab5
        (81, 1.0, 80),   # A5 (chromatic!)
        (82, 2.5, 85),   # Bb5 — climax
        # Bar 11-12: passionate descent
        (82, 1.0, 83),   # Bb5
        (80, 1.5, 78),   # Ab5
        (79, 1.0, 75),   # G5
        (77, 1.5, 72),   # F5
        (75, 1.0, 68),   # Eb5
        # Bar 13-14: chromatic sighing figures
        (75, 1.0, 66),   # Eb5
        (74, 1.0, 63),   # D5
        (73, 1.5, 60),   # Db5 (chromatic)
        (72, 1.5, 58),   # C5
        (70, 2.0, 55),   # Bb4
        # Bar 15-16: quiet ending
        (68, 1.5, 52),   # Ab4
        (67, 2.0, 48),   # G4
        (68, 1.5, 45),   # Ab4
        (70, 3.0, 42),   # Bb4 — long final
    ]

    # Chord progressions (root, quality) per bar
    chords_a = [
        (51,'maj'), (51,'maj'),     # Eb
        (56,'maj'), (53,'min'),     # Ab, Fm
        (58,'dom7'), (58,'dom7'),   # Bb7
        (56,'maj'), (51,'maj'),     # Ab, Eb
    ]
    chords_b = [
        (51,'maj7'), (48,'min'),    # Eb△7, Cm
        (53,'dom7'), (58,'dom7'),   # F7, Bb7
        (48,'min'), (56,'maj'),     # Cm, Ab
        (58,'dom7'), (51,'maj'),    # Bb7, Eb
    ]

    sbeats = [0]
    t = 0.0

    # ── Section A ──
    t_m = t
    for p, dur_b, v in melody_a:
        dur_s = dur_b * beat
        add_note(mel, p, t_m, t_m + dur_s * 0.95, v)
        t_m += dur_s

    for root, q in chords_a:
        arp_bar(acc, t, root, q)
        t += bar
    sbeats.append(t / beat)

    # ── Section B ──
    t_m = t
    for p, dur_b, v in melody_b:
        dur_s = dur_b * beat
        add_note(mel, p, t_m, t_m + dur_s * 0.95, v)
        t_m += dur_s

    for root, q in chords_b:
        arp_bar(acc, t, root, q)
        t += bar
    sbeats.append(t / beat)

    # ── Coda: 2 bars ──
    # Final Eb chord, sustained
    arp_bar(acc, t, 51, 'maj')
    add_note(mel, 75, t, t + bar * 0.9, 50)  # Eb5
    t += bar
    for p in [51, 58, 63, 67, 75]:
        add_note(acc if p < 63 else mel, p, t, t + bar * 1.5, 45)
    t += bar * 1.5
    sbeats.append(t / beat)

    pm.instruments.extend([mel, acc])

    config = HumanizeConfig(
        bpm=BPM, velocity_jitter=6, phrase_arc_strength=0.12,
        timing_sigma=0.010, default_legato=0.93,
        cadence_rubato=0.10, cadence_window=3.0,
    )
    pm = humanize(pm, config=config, section_beats=sbeats)

    mid = os.path.join(OUT_DIR, 'chopin_nocturne.mid')
    wav = os.path.join(OUT_DIR, 'chopin_nocturne.wav')
    pm.write(mid)
    prettymidi_to_wav(pm, wav)
    dur = pm.get_end_time()
    nn = sum(len(i.notes) for i in pm.instruments)
    print(f"  Chopin: {dur:.1f}s, {nn} notes")
    return pm


# ═══════════════════════════════════════════════════════════════
# PINK FLOYD — Phrygian Meditation in E
# Target: ~70s, wide range, high dur CV, Phrygian, spacious
# ═══════════════════════════════════════════════════════════════

def generate_floyd():
    BPM = 76
    beat = 60.0 / BPM     # 0.789s
    whole = beat * 4       # 3.158s
    half = beat * 2
    quarter = beat
    eighth = beat / 2
    s16 = beat / 4

    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    lead = pretty_midi.Instrument(program=25, name='Lead Guitar')
    pad  = pretty_midi.Instrument(program=89, name='Pad')
    bass = pretty_midi.Instrument(program=33, name='Bass')

    # E Phrygian: E F G A B C D
    EP = [40,41,43,45,47,48,50,52,53,55,57,59,60,62,64,65,67,69,71,72,74,76,77,79,81,83,84]

    def snap(p): return min(EP, key=lambda x: abs(x-p))
    def stp(p, d, n=1):
        i = EP.index(snap(p))
        return EP[max(0, min(len(EP)-1, i+d*n))]

    # Chords: Em, F, D, Am
    CHORDS = {
        'Em':  [40,47,52,55,59,64],
        'F':   [41,48,53,57,60,65],
        'D':   [38,45,50,54,57,62],
        'Am':  [45,52,57,60,64,69],
    }

    def write_pad(t, name, dur, vel=38):
        for p in CHORDS[name]:
            add_note(pad, p, t, t+dur, vel)
        add_note(bass, CHORDS[name][0], t, t+dur, 52)

    # ── Theme A: spacious, long sustains + rapid bursts ──
    theme_a = [
        # (pitch, dur_beats, vel)
        (64, 6.0, 75),    # E5 — very long sustain
        (65, 2.0, 70),    # F5 (Phrygian b2)
        (64, 1.0, 68),    # E5
        # rapid ornament
        (62, 0.25, 65), (64, 0.25, 68), (65, 0.25, 72), (67, 0.25, 75),
        (69, 4.0, 80),    # A5 — sustain
        # descent
        (69, 2.0, 75), (67, 1.0, 70), (65, 4.0, 68),  # F5 long
        (64, 1.0, 65),
        # climax reach
        (71, 0.5, 78), (72, 0.5, 82),
        (74, 4.0, 88),    # D6 — peak sustain
        (72, 1.0, 75), (69, 2.0, 70), (67, 4.0, 65),  # G5 rest
    ]

    # ── Theme B: higher, more chromatic, wider leaps ──
    theme_b = [
        (76, 4.0, 82),    # E6
        (77, 2.0, 80),    # F6
        (76, 1.0, 75), (74, 0.5, 72), (72, 0.5, 70),
        # chromatic descent burst
        (71, 0.25, 75), (70, 0.25, 73), (69, 0.25, 71), (67, 0.25, 69),
        (65, 0.25, 67), (64, 6.0, 70),  # E5 long sustain
        # riff: repeated figure
        (64, 1.0, 72), (65, 1.0, 75), (67, 2.0, 78),
        (64, 1.0, 72), (65, 1.0, 75), (69, 2.0, 80),  # variation
        # resolve with huge leap
        (69, 1.0, 78),
        (52, 4.0, 72),    # E3 — huge downward leap
        (53, 4.0, 60),    # F3 — low Phrygian
    ]

    # ── Theme A' — abbreviated ──
    theme_a2 = [
        (64, 6.0, 68),    # E5
        (65, 2.0, 63),    # F5
        (64, 1.0, 60),    # E5
        (62, 0.25, 58), (64, 0.25, 60), (65, 0.25, 63), (67, 0.25, 66),
        (69, 4.0, 70),    # A5
        (67, 2.0, 65),
        (65, 4.0, 58),    # F5
        (64, 8.0, 50),    # E5 — very long fade
    ]

    def write_theme(inst, t, notes):
        for p, dur_b, v in notes:
            dur_s = dur_b * beat
            add_note(inst, p, t, t + dur_s * 0.96, v)
            t += dur_s
        return t

    # ══════════════ STRUCTURE ══════════════
    sbeats = [0]
    t = 0.0

    # Intro: 2 bars drone
    write_pad(t, 'Em', whole*2, 32)
    t += whole * 2
    sbeats.append(t / beat)

    # Theme A (~34 beats)
    ta_end = write_theme(lead, t, theme_a)
    # Pad: 2 bars each
    pad_seq_a = ['Em','Em','F','F','Am','Am','Em','Em']
    tp = t
    for ch in pad_seq_a:
        write_pad(tp, ch, whole, 36)
        tp += whole
    t = ta_end
    sbeats.append(t / beat)

    # Theme B (~32 beats)
    tb_end = write_theme(lead, t, theme_b)
    pad_seq_b = ['Em','F','D','D','Em','F','Am','Em']
    tp = t
    for ch in pad_seq_b:
        write_pad(tp, ch, whole, 40)
        tp += whole
    t = tb_end
    sbeats.append(t / beat)

    # Theme A' (~28 beats)
    tc_end = write_theme(lead, t, theme_a2)
    pad_seq_c = ['Em','Em','F','Am','Em','Em','Em']
    tp = t
    for ch in pad_seq_c:
        write_pad(tp, ch, whole, 33)
        tp += whole
    t = tc_end
    sbeats.append(t / beat)

    # Outro: 2 bars fade
    write_pad(t, 'Em', whole*2, 25)
    t += whole * 2
    sbeats.append(t / beat)

    pm.instruments.extend([lead, pad, bass])

    config = HumanizeConfig(
        bpm=BPM, velocity_jitter=8, phrase_arc_strength=0.10,
        timing_sigma=0.014, default_legato=0.92,
        cadence_rubato=0.08, cadence_window=2.5,
        voice_timing_bias={0: 0.005, 1: 0.000, 2: -0.003},
    )
    pm = humanize(pm, config=config, section_beats=sbeats)

    mid = os.path.join(OUT_DIR, 'floyd_phrygian.mid')
    wav = os.path.join(OUT_DIR, 'floyd_phrygian.wav')
    pm.write(mid)
    prettymidi_to_wav(pm, wav)
    dur = pm.get_end_time()
    nn = sum(len(i.notes) for i in pm.instruments)
    print(f"  Floyd: {dur:.1f}s, {nn} notes")
    return pm


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    print("\n=== Generating Three Styles ===\n")

    print("1. Bach — Two-Part Invention in A minor")
    pm_bach = generate_bach()

    print("\n2. Chopin — Nocturne in Eb major")
    pm_chopin = generate_chopin()

    print("\n3. Pink Floyd — Phrygian Meditation in E")
    pm_floyd = generate_floyd()

    print(f"\n=== Done! Files in {OUT_DIR} ===")

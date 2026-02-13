import { useState, useMemo, useCallback } from "react";

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const NOTES = ["C","C♯","D","D♯","E","F","F♯","G","G♯","A","A♯","B"];
const TAU = 2 * Math.PI;

// Preset pitch-class sets
const PRESETS = {
  "C major triad":      [1,0,0,0,1,0,0,1,0,0,0,0],
  "C minor triad":      [1,0,0,1,0,0,0,1,0,0,0,0],
  "C major scale":      [1,0,1,0,1,1,0,1,0,1,0,1],
  "C minor scale":      [1,0,1,1,0,1,0,1,1,0,1,0],
  "Whole tone":         [1,0,1,0,1,0,1,0,1,0,1,0],
  "Chromatic":          [1,1,1,1,1,1,1,1,1,1,1,1],
  "Diminished 7th":     [1,0,0,1,0,0,1,0,0,1,0,0],
  "Augmented triad":    [1,0,0,0,1,0,0,0,1,0,0,0],
  "Pentatonic":         [1,0,1,0,1,0,0,1,0,1,0,0],
  "V7 → I (BWV 846)":  null, // special: animated
};

// BWV 846 progression (our version) as pitch-class sets
const BWV846_CHORDS = [
  { name: "I",      pcs: [0,4,7],     label: "C" },
  { name: "vi7",    pcs: [9,0,4,7],   label: "Am7" },
  { name: "IV",     pcs: [5,9,0],     label: "F" },
  { name: "V7",     pcs: [7,11,2,5],  label: "G7" },
  { name: "I",      pcs: [0,4,7],     label: "C" },
  { name: "IVmaj7", pcs: [5,9,0,4],   label: "Fmaj7" },
  { name: "viio",   pcs: [11,2,5],    label: "Bdim" },
  { name: "iii",    pcs: [4,7,11],    label: "Em" },
  { name: "vi7",    pcs: [9,0,4,7],   label: "Am7" },
  { name: "ii7",    pcs: [2,5,9,0],   label: "Dm7" },
  { name: "V",      pcs: [7,11,2],    label: "G" },
  { name: "V7/V",   pcs: [2,6,9,0],   label: "D7" },
  { name: "V",      pcs: [7,11,2],    label: "G" },
  { name: "viio7/V",pcs: [6,9,0,3],   label: "F♯dim7" },
  { name: "V7",     pcs: [7,11,2,5],  label: "G7" },
  { name: "I6",     pcs: [0,4,7],     label: "C/E" },
  { name: "IVmaj7", pcs: [5,9,0,4],   label: "Fmaj7" },
  { name: "ii7",    pcs: [2,5,9,0],   label: "Dm7" },
  { name: "V7",     pcs: [7,11,2,5],  label: "G7" },
  { name: "I",      pcs: [0,4,7],     label: "C" },
];

// Colors
const BG = "#0a0a1a";
const RING = "#1a1a3a";
const ACCENT = "#6366f1";  // indigo
const ACCENT2 = "#ec4899"; // pink
const ACCENT3 = "#10b981"; // emerald
const TEXT = "#e2e8f0";
const DIM = "#475569";
const GRID = "#1e293b";

// ═══════════════════════════════════════════════════════════════
// Math: DFT on Z₁₂
// ═══════════════════════════════════════════════════════════════

function dft12(pcVector) {
  // pcVector: array of 12 values (0 or 1, or weights)
  // Returns: array of 7 complex coefficients (k=0..6)
  // X_k = Σ x_n · e^{-2πi·k·n/12}
  const result = [];
  for (let k = 0; k <= 6; k++) {
    let re = 0, im = 0;
    for (let n = 0; n < 12; n++) {
      const angle = -TAU * k * n / 12;
      re += pcVector[n] * Math.cos(angle);
      im += pcVector[n] * Math.sin(angle);
    }
    result.push({ re, im, mag: Math.sqrt(re*re + im*im), phase: Math.atan2(im, re) });
  }
  return result;
}

// Fourier coefficient musical meanings
const FOURIER_LABELS = [
  "f₀: cardinality",
  "f₁: chromatic cluster",
  "f₂: whole-tone",
  "f₃: octatonic (dim7)",
  "f₄: hexatonic (aug)",
  "f₅: diatonic (fifths)",
  "f₆: tritone",
];

const FOURIER_COLORS = ["#94a3b8", "#f59e0b", "#3b82f6", "#ef4444", "#a855f7", ACCENT3, ACCENT2];

// ═══════════════════════════════════════════════════════════════
// Math: Tonnetz coordinates
// ═══════════════════════════════════════════════════════════════

function tonnetzCoords(pc) {
  // Map pitch class to Tonnetz (x = fifths axis, y = thirds axis)
  // Using the standard tonnetz: x = major thirds (0,4,8), y = minor thirds (0,3,6,9)
  const fifthsPos = (pc * 7) % 12; // position on circle of fifths
  const x = fifthsPos;
  const y = pc;
  return { x, y };
}

// Convert pitch-class set to 12-dim binary vector
function pcsToVector(pcs) {
  const v = new Array(12).fill(0);
  pcs.forEach(pc => { v[pc % 12] = 1; });
  return v;
}

// ═══════════════════════════════════════════════════════════════
// Components
// ═══════════════════════════════════════════════════════════════

function ChromaticCircle({ pcVector, onToggle, highlightIntervals }) {
  const cx = 200, cy = 200, r = 150;

  const activeIndices = pcVector.reduce((acc, v, i) => v ? [...acc, i] : acc, []);

  // Draw interval lines between active pitch classes
  const intervalLines = [];
  for (let i = 0; i < activeIndices.length; i++) {
    for (let j = i + 1; j < activeIndices.length; j++) {
      const a = activeIndices[i], b = activeIndices[j];
      const interval = (b - a + 12) % 12;
      const angleA = -Math.PI/2 + TAU * a / 12;
      const angleB = -Math.PI/2 + TAU * b / 12;

      let color = DIM;
      let width = 0.5;
      if (interval === 7 || interval === 5) { color = ACCENT3; width = 2; } // P5/P4
      else if (interval === 4 || interval === 8) { color = ACCENT; width = 1.5; } // M3/m6
      else if (interval === 3 || interval === 9) { color = ACCENT2; width = 1.5; } // m3/M6

      intervalLines.push(
        <line key={`${a}-${b}`}
          x1={cx + r * Math.cos(angleA)} y1={cy + r * Math.sin(angleA)}
          x2={cx + r * Math.cos(angleB)} y2={cy + r * Math.sin(angleB)}
          stroke={color} strokeWidth={width} opacity={0.6} />
      );
    }
  }

  return (
    <svg viewBox="0 0 400 400" style={{ width: "100%", maxWidth: 400 }}>
      {/* Background circle */}
      <circle cx={cx} cy={cy} r={r+20} fill="none" stroke={RING} strokeWidth={1} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={RING} strokeWidth={0.5} />

      {/* Interval lines */}
      {intervalLines}

      {/* Pitch class nodes */}
      {NOTES.map((name, i) => {
        const angle = -Math.PI/2 + TAU * i / 12;
        const x = cx + r * Math.cos(angle);
        const y = cy + r * Math.sin(angle);
        const lx = cx + (r + 28) * Math.cos(angle);
        const ly = cy + (r + 28) * Math.sin(angle);
        const active = pcVector[i] > 0;

        return (
          <g key={i} onClick={() => onToggle(i)} style={{ cursor: "pointer" }}>
            <circle cx={x} cy={y} r={active ? 14 : 8}
              fill={active ? ACCENT : RING}
              stroke={active ? "#818cf8" : DIM}
              strokeWidth={active ? 2 : 1} />
            {active && <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="central"
              fill="white" fontSize={11} fontWeight="bold">{name}</text>}
            {!active && <text x={lx} y={ly + 1} textAnchor="middle" dominantBaseline="central"
              fill={DIM} fontSize={9}>{name}</text>}
          </g>
        );
      })}

      {/* Center: interval class vector */}
      <text x={cx} y={cy - 10} textAnchor="middle" fill={DIM} fontSize={10}>
        Z₁₂ = ⟨ℤ/12ℤ, +⟩
      </text>
      <text x={cx} y={cy + 8} textAnchor="middle" fill={TEXT} fontSize={11}>
        {activeIndices.length} pitch classes
      </text>

      {/* Legend */}
      <g transform="translate(10, 370)">
        <line x1={0} y1={0} x2={20} y2={0} stroke={ACCENT3} strokeWidth={2} />
        <text x={25} y={4} fill={DIM} fontSize={8}>P5/P4</text>
        <line x1={70} y1={0} x2={90} y2={0} stroke={ACCENT} strokeWidth={1.5} />
        <text x={95} y={4} fill={DIM} fontSize={8}>M3/m6</text>
        <line x1={140} y1={0} x2={160} y2={0} stroke={ACCENT2} strokeWidth={1.5} />
        <text x={165} y={4} fill={DIM} fontSize={8}>m3/M6</text>
      </g>
    </svg>
  );
}


function FourierSpectrum({ pcVector, comparisonVector, comparisonLabel }) {
  const spectrum = useMemo(() => dft12(pcVector), [pcVector]);
  const compSpectrum = useMemo(
    () => comparisonVector ? dft12(comparisonVector) : null,
    [comparisonVector]
  );

  const maxMag = Math.max(
    ...spectrum.map(c => c.mag),
    ...(compSpectrum ? compSpectrum.map(c => c.mag) : [0])
  );
  const scale = maxMag > 0 ? 160 / maxMag : 1;

  // Radar chart
  const cx = 200, cy = 180, maxR = 140;

  function polarPoint(k, mag, total) {
    const angle = -Math.PI/2 + TAU * k / total;
    const rr = (mag / (maxMag || 1)) * maxR;
    return { x: cx + rr * Math.cos(angle), y: cy + rr * Math.sin(angle) };
  }

  const radarPoints = spectrum.slice(1).map((c, i) => polarPoint(i, c.mag, 6));
  const radarPath = radarPoints.map((p, i) => `${i===0?'M':'L'}${p.x},${p.y}`).join(' ') + 'Z';

  let compPath = null;
  if (compSpectrum) {
    const compPoints = compSpectrum.slice(1).map((c, i) => polarPoint(i, c.mag, 6));
    compPath = compPoints.map((p, i) => `${i===0?'M':'L'}${p.x},${p.y}`).join(' ') + 'Z';
  }

  // Axis labels
  const axisLabels = ["chromatic", "whole-tone", "dim7", "aug", "diatonic", "tritone"];

  return (
    <svg viewBox="0 0 400 400" style={{ width: "100%", maxWidth: 400 }}>
      {/* Grid rings */}
      {[0.25, 0.5, 0.75, 1.0].map(frac => (
        <circle key={frac} cx={cx} cy={cy} r={maxR * frac}
          fill="none" stroke={GRID} strokeWidth={0.5} />
      ))}

      {/* Axes */}
      {axisLabels.map((label, i) => {
        const p = polarPoint(i, maxMag, 6);
        const lp = polarPoint(i, maxMag * 1.18, 6);
        return (
          <g key={i}>
            <line x1={cx} y1={cy} x2={p.x} y2={p.y}
              stroke={GRID} strokeWidth={0.5} />
            <text x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="central"
              fill={FOURIER_COLORS[i+1]} fontSize={9} fontWeight="bold">
              f{i+1}: {label}
            </text>
          </g>
        );
      })}

      {/* Comparison shape */}
      {compPath && (
        <path d={compPath} fill={ACCENT2} fillOpacity={0.1}
          stroke={ACCENT2} strokeWidth={1.5} strokeDasharray="4,3" />
      )}

      {/* Main shape */}
      <path d={radarPath} fill={ACCENT} fillOpacity={0.15}
        stroke={ACCENT} strokeWidth={2} />

      {/* Dots on vertices */}
      {radarPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4}
          fill={FOURIER_COLORS[i+1]} />
      ))}

      {/* Title */}
      <text x={cx} y={15} textAnchor="middle" fill={TEXT} fontSize={12} fontWeight="bold">
        DFT Spectrum on Z₁₂
      </text>
      <text x={cx} y={32} textAnchor="middle" fill={DIM} fontSize={9}>
        X_k = Σ x_n · e^(-2πi·k·n/12)
      </text>

      {/* Magnitude readout */}
      <g transform="translate(10, 350)">
        {spectrum.slice(1).map((c, i) => (
          <text key={i} x={i * 65} y={0} fill={FOURIER_COLORS[i+1]} fontSize={8}>
            |f{i+1}|={c.mag.toFixed(2)}
          </text>
        ))}
      </g>

      {/* Phase of f5 = key indicator */}
      <text x={cx} y={370} textAnchor="middle" fill={ACCENT3} fontSize={10}>
        f₅ phase = {(spectrum[5].phase * 180 / Math.PI).toFixed(0)}° → key indicator
      </text>

      {comparisonLabel && (
        <g transform="translate(300, 50)">
          <line x1={0} y1={0} x2={20} y2={0} stroke={ACCENT2} strokeWidth={1.5} strokeDasharray="4,3" />
          <text x={25} y={4} fill={ACCENT2} fontSize={9}>{comparisonLabel}</text>
        </g>
      )}
    </svg>
  );
}


function TonnetzView({ pcVector, chordHistory }) {
  // Tonnetz: rows = minor thirds axis, cols = major thirds axis
  // Standard layout: each row shifts by +1 semitone
  const rows = 5, cols = 8;
  const cellW = 52, cellH = 46;
  const offsetX = 30, offsetY = 30;

  // Build tonnetz grid: row r, col c → pitch class
  // Standard tonnetz: right = +4 (M3), up-right = +7 (P5), up = +3 (m3)
  function pcAt(r, c) {
    return ((4 * c) + (3 * r) + 12 * 10) % 12;
  }

  // Find triads (triangles)
  const triads = [];
  const activeSet = new Set(pcVector.reduce((acc, v, i) => v ? [...acc, i] : acc, []));

  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      // Major triad: ▲ (root, root+4, root+7)
      const a = pcAt(r, c), b = pcAt(r, c+1), d = pcAt(r+1, c);
      // Check upward triangle (major-ish)
      if (activeSet.has(a) && activeSet.has(b) && activeSet.has(d)) {
        triads.push({ r, c, type: "up", pcs: [a, b, d] });
      }
      // Downward triangle
      const e = pcAt(r+1, c+1);
      if (activeSet.has(b) && activeSet.has(d) && activeSet.has(e)) {
        triads.push({ r, c, type: "down", pcs: [b, d, e] });
      }
    }
  }

  return (
    <svg viewBox="0 0 460 300" style={{ width: "100%", maxWidth: 460 }}>
      {/* Title */}
      <text x={230} y={16} textAnchor="middle" fill={TEXT} fontSize={12} fontWeight="bold">
        Tonnetz — harmony as geometry on a torus
      </text>

      {/* Triad highlights */}
      {triads.map((t, i) => {
        const x0 = offsetX + t.c * cellW + (t.type === "down" ? cellW/2 : 0);
        const y0 = offsetY + 20 + t.r * cellH;
        let points;
        if (t.type === "up") {
          points = `${x0},${y0+cellH} ${x0+cellW},${y0+cellH} ${x0+cellW/2},${y0}`;
        } else {
          points = `${x0},${y0} ${x0+cellW/2},${y0+cellH} ${x0-cellW/2},${y0+cellH}`;
        }
        return (
          <polygon key={i} points={points}
            fill={t.type === "up" ? ACCENT : ACCENT2} fillOpacity={0.2}
            stroke={t.type === "up" ? ACCENT : ACCENT2} strokeWidth={1} />
        );
      })}

      {/* Grid nodes */}
      {Array.from({length: rows}, (_, r) =>
        Array.from({length: cols}, (_, c) => {
          const pc = pcAt(r, c);
          const x = offsetX + c * cellW + (r % 2) * (cellW / 2);
          const y = offsetY + 20 + r * cellH;
          const active = activeSet.has(pc);
          return (
            <g key={`${r}-${c}`}>
              {/* Connection lines */}
              {c < cols - 1 && (
                <line x1={x} y1={y}
                  x2={offsetX + (c+1) * cellW + (r % 2) * (cellW/2)} y2={y}
                  stroke={GRID} strokeWidth={0.5} />
              )}
              {r < rows - 1 && (
                <line x1={x} y1={y}
                  x2={offsetX + c * cellW + ((r+1) % 2) * (cellW/2)}
                  y2={offsetY + 20 + (r+1) * cellH}
                  stroke={GRID} strokeWidth={0.5} />
              )}
              <circle cx={x} cy={y} r={active ? 16 : 10}
                fill={active ? ACCENT : "#111827"}
                stroke={active ? "#818cf8" : GRID}
                strokeWidth={active ? 2 : 0.5} />
              <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="central"
                fill={active ? "white" : DIM} fontSize={active ? 10 : 8}
                fontWeight={active ? "bold" : "normal"}>
                {NOTES[pc]}
              </text>
            </g>
          );
        })
      )}

      {/* Axis labels */}
      <text x={offsetX + cols * cellW / 2} y={offsetY + rows * cellH + 30}
        textAnchor="middle" fill={ACCENT} fontSize={9}>
        → Major 3rd (4 semitones) — period 3 (wraps: 4×3=12)
      </text>
      <text x={8} y={offsetY + rows * cellH / 2}
        textAnchor="middle" fill={ACCENT2} fontSize={9}
        transform={`rotate(-90, 8, ${offsetY + rows * cellH / 2})`}>
        ↑ Minor 3rd (3 semi) — period 4
      </text>

      {/* Legend */}
      <g transform="translate(300, 275)">
        <polygon points="0,12 12,12 6,0" fill={ACCENT} fillOpacity={0.3} stroke={ACCENT} strokeWidth={1} />
        <text x={18} y={10} fill={DIM} fontSize={8}>major ▲</text>
        <polygon points="75,0 81,12 69,12" fill={ACCENT2} fillOpacity={0.3} stroke={ACCENT2} strokeWidth={1} />
        <text x={87} y={10} fill={DIM} fontSize={8}>minor ▼</text>
      </g>
    </svg>
  );
}


function BachPathView({ currentChordIdx, setCurrentChordIdx }) {
  const chord = BWV846_CHORDS[currentChordIdx];
  const pcVector = pcsToVector(chord.pcs);

  // Timeline
  const timelineW = 440, barH = 30;

  // DFT for each chord — precompute
  const allSpectra = useMemo(() =>
    BWV846_CHORDS.map(c => dft12(pcsToVector(c.pcs))),
  []);

  // f5 magnitude over time (diatonic quality)
  const f5Values = allSpectra.map(s => s[5].mag);
  const f5Max = Math.max(...f5Values);

  // f5 phase over time (key indicator)
  const f5Phases = allSpectra.map(s => s[5].phase);

  return (
    <div>
      {/* Timeline */}
      <svg viewBox="0 0 460 120" style={{ width: "100%", maxWidth: 460 }}>
        <text x={230} y={14} textAnchor="middle" fill={TEXT} fontSize={12} fontWeight="bold">
          BWV 846 Harmonic Path — f₅ diatonic quality over time
        </text>

        {/* f5 magnitude plot */}
        {f5Values.map((v, i) => {
          const x = 20 + (i / (BWV846_CHORDS.length - 1)) * (timelineW - 40);
          const h = (v / f5Max) * 50;
          const isActive = i === currentChordIdx;
          return (
            <g key={i} onClick={() => setCurrentChordIdx(i)} style={{ cursor: "pointer" }}>
              <rect x={x - 8} y={75 - h} width={16} height={h}
                fill={isActive ? ACCENT3 : RING}
                stroke={isActive ? ACCENT3 : DIM}
                strokeWidth={isActive ? 2 : 0.5}
                rx={2} />
              <text x={x} y={90} textAnchor="middle" fill={isActive ? TEXT : DIM}
                fontSize={7} fontWeight={isActive ? "bold" : "normal"}>
                {BWV846_CHORDS[i].name}
              </text>
              <text x={x} y={100} textAnchor="middle" fill={DIM} fontSize={6}>
                {BWV846_CHORDS[i].label}
              </text>
            </g>
          );
        })}

        {/* Y axis */}
        <text x={8} y={30} fill={ACCENT3} fontSize={8}>|f₅|</text>
        <line x1={18} y1={25} x2={18} y2={75} stroke={GRID} strokeWidth={0.5} />

        {/* Section labels */}
        {[
          [0, 4, "Statement"],
          [4, 10, "Expansion"],
          [10, 14, "Tonicize V"],
          [14, 20, "Return"],
        ].map(([s, e, label]) => {
          const x1 = 20 + (s / (BWV846_CHORDS.length - 1)) * (timelineW - 40);
          const x2 = 20 + ((e-1) / (BWV846_CHORDS.length - 1)) * (timelineW - 40);
          return (
            <text key={label} x={(x1+x2)/2} y={115} textAnchor="middle"
              fill={DIM} fontSize={7}>{label}</text>
          );
        })}
      </svg>

      {/* Current chord info */}
      <div style={{ display: "flex", gap: 16, alignItems: "center", justifyContent: "center",
                    padding: "8px 0", color: TEXT, fontSize: 13 }}>
        <button onClick={() => setCurrentChordIdx(Math.max(0, currentChordIdx - 1))}
          style={{ background: RING, border: `1px solid ${DIM}`, color: TEXT,
                   padding: "4px 12px", borderRadius: 4, cursor: "pointer" }}>
          ← prev
        </button>
        <span style={{ fontWeight: "bold", color: ACCENT, fontSize: 16 }}>
          m.{currentChordIdx + 1}: {chord.name} ({chord.label})
        </span>
        <span style={{ color: ACCENT3 }}>
          |f₅| = {allSpectra[currentChordIdx][5].mag.toFixed(2)}
        </span>
        <button onClick={() => setCurrentChordIdx(Math.min(BWV846_CHORDS.length - 1, currentChordIdx + 1))}
          style={{ background: RING, border: `1px solid ${DIM}`, color: TEXT,
                   padding: "4px 12px", borderRadius: 4, cursor: "pointer" }}>
          next →
        </button>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════
// Math explanation panel
// ═══════════════════════════════════════════════════════════════

function MathPanel() {
  return (
    <div style={{ padding: "12px 16px", background: "#0f172a", borderRadius: 8,
                  border: `1px solid ${GRID}`, fontSize: 12, lineHeight: 1.7, color: TEXT }}>
      <h3 style={{ color: ACCENT, margin: "0 0 8px", fontSize: 14 }}>
        The Mathematics of 12-TET
      </h3>
      <p style={{ color: DIM, margin: "0 0 6px" }}>
        <strong style={{ color: TEXT }}>Why 12?</strong>{" "}
        2^(7/12) ≈ 1.4983 ≈ 3/2 (pure fifth = 1.5). No equal division below 12 approximates
        the fifth this well. 12-TET is the smallest EDO where the fifth-generator
        visits all 12 classes before cycling: gcd(7, 12) = 1.
      </p>
      <p style={{ color: DIM, margin: "0 0 6px" }}>
        <strong style={{ color: TEXT }}>Group structure:</strong>{" "}
        Pitch classes form Z₁₂ = (ℤ/12ℤ, +). Intervals are group elements.
        The circle of fifths is the orbit of generator 7: 0→7→2→9→4→11→6→1→8→3→10→5→0.
        Transposition T_n(x) = x + n mod 12 is a group automorphism.
      </p>
      <p style={{ color: DIM, margin: "0 0 6px" }}>
        <strong style={{ color: ACCENT3 }}>DFT on Z₁₂</strong>{" "}
        (Lewin 1959, Quinn 2006): Any chord = vector in ℝ¹².
        The DFT decomposes it into 7 Fourier components. Each |f_k| measures
        alignment with a specific cyclic partition: f₅ = diatonic quality
        (max for the major scale), f₃ = diminished content, f₂ = whole-tone.
        The <em>phase</em> of f₅ rotates with transposition — it literally encodes the key.
      </p>
      <p style={{ color: DIM, margin: 0 }}>
        <strong style={{ color: ACCENT2 }}>Tonnetz</strong>{" "}
        (Euler 1739, Riemann 1880): Pitch classes on a lattice where x-axis = M3,
        y-axis = m3, diagonal = P5. In 12-TET the lattice wraps into a torus
        (period 3 horizontally, period 4 vertically). Triads are triangles;
        neo-Riemannian P/L/R transforms = triangle flips on the torus.
      </p>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════
// Main App
// ═══════════════════════════════════════════════════════════════

const TABS = ["Z₁₂ Circle", "DFT Spectrum", "Tonnetz", "Bach's Path", "Math"];

export default function App() {
  const [tab, setTab] = useState(0);
  const [pcVector, setPcVector] = useState([1,0,0,0,1,0,0,1,0,0,0,0]); // C major
  const [preset, setPreset] = useState("C major triad");
  const [comparison, setComparison] = useState(null);
  const [bachIdx, setBachIdx] = useState(0);

  const togglePC = useCallback((i) => {
    setPcVector(prev => {
      const next = [...prev];
      next[i] = 1 - next[i];
      return next;
    });
    setPreset(null);
  }, []);

  const applyPreset = useCallback((name) => {
    const p = PRESETS[name];
    if (p) {
      setPcVector(p);
      setPreset(name);
    }
  }, []);

  // For Bach's Path tab, override pcVector with current chord
  const displayVector = tab === 3
    ? pcsToVector(BWV846_CHORDS[bachIdx].pcs)
    : pcVector;

  return (
    <div style={{
      background: BG, minHeight: "100vh", color: TEXT,
      fontFamily: "'Inter', 'SF Pro', -apple-system, sans-serif",
      padding: "16px 20px",
    }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: TEXT, margin: "0 0 4px",
                     letterSpacing: "-0.02em" }}>
          The Geometry of Twelve-Tone Equal Temperament
        </h1>
        <p style={{ color: DIM, fontSize: 12, margin: 0 }}>
          Group theory · Fourier analysis · Tonnetz topology — applied to BWV 846
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, justifyContent: "center", marginBottom: 16 }}>
        {TABS.map((t, i) => (
          <button key={i} onClick={() => setTab(i)}
            style={{
              padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600,
              border: "none", cursor: "pointer",
              background: tab === i ? ACCENT : RING,
              color: tab === i ? "white" : DIM,
              transition: "all 0.15s",
            }}>
            {t}
          </button>
        ))}
      </div>

      {/* Preset selector (for tabs 0-2) */}
      {tab < 3 && (
        <div style={{ display: "flex", gap: 4, justifyContent: "center",
                      marginBottom: 12, flexWrap: "wrap" }}>
          {Object.keys(PRESETS).filter(k => PRESETS[k] !== null).map(name => (
            <button key={name} onClick={() => applyPreset(name)}
              style={{
                padding: "3px 10px", borderRadius: 12, fontSize: 10,
                border: `1px solid ${preset === name ? ACCENT : DIM}`,
                background: preset === name ? ACCENT + "33" : "transparent",
                color: preset === name ? ACCENT : DIM,
                cursor: "pointer",
              }}>
              {name}
            </button>
          ))}
        </div>
      )}

      {/* Main content */}
      <div style={{ display: "flex", justifyContent: "center" }}>
        {tab === 0 && (
          <div>
            <ChromaticCircle pcVector={displayVector} onToggle={togglePC} />
            <div style={{ textAlign: "center", color: DIM, fontSize: 10, marginTop: 4 }}>
              Click nodes to toggle pitch classes. Lines show interval relationships.
            </div>
          </div>
        )}

        {tab === 1 && (
          <div>
            <FourierSpectrum pcVector={displayVector}
              comparisonVector={comparison ? PRESETS[comparison] : null}
              comparisonLabel={comparison} />
            <div style={{ display: "flex", gap: 4, justifyContent: "center", marginTop: 8 }}>
              <span style={{ color: DIM, fontSize: 10 }}>Compare with:</span>
              {["C major scale", "Whole tone", "Diminished 7th", "Pentatonic"].map(name => (
                <button key={name}
                  onClick={() => setComparison(comparison === name ? null : name)}
                  style={{
                    padding: "2px 8px", borderRadius: 10, fontSize: 9,
                    border: `1px solid ${comparison === name ? ACCENT2 : DIM}`,
                    background: comparison === name ? ACCENT2 + "33" : "transparent",
                    color: comparison === name ? ACCENT2 : DIM,
                    cursor: "pointer",
                  }}>
                  {name}
                </button>
              ))}
            </div>
          </div>
        )}

        {tab === 2 && (
          <TonnetzView pcVector={displayVector} />
        )}

        {tab === 3 && (
          <div style={{ width: "100%", maxWidth: 460 }}>
            <BachPathView currentChordIdx={bachIdx} setCurrentChordIdx={setBachIdx} />
            <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 8 }}>
              <ChromaticCircle pcVector={displayVector} onToggle={() => {}} />
              <FourierSpectrum pcVector={displayVector} />
            </div>
          </div>
        )}

        {tab === 4 && (
          <div style={{ maxWidth: 600 }}>
            <MathPanel />
          </div>
        )}
      </div>
    </div>
  );
}

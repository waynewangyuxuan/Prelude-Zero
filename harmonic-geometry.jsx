import { useState, useEffect, useMemo } from "react";

// ═══════════════════════════════════════════════════════════════════
// DATA — voicing engine output for Experiment 001 (Bach-style Prelude)
// [measure, roman, rootPc, bass, [tenor,alto,soprano], section]
// ═══════════════════════════════════════════════════════════════════
const RAW = [
  [1,"I",0,48,[64,67,72],"Statement"],[2,"vi7",9,57,[64,67,72],"Statement"],
  [3,"IV",5,53,[65,69,72],"Statement"],[4,"V7",7,55,[62,65,71],"Statement"],
  [5,"I",0,48,[64,67,72],"Expansion"],[6,"IVmaj7",5,53,[64,69,72],"Expansion"],
  [7,"viio",11,59,[65,71,74],"Expansion"],[8,"iii",4,52,[67,71,76],"Expansion"],
  [9,"vi7",9,57,[67,72,76],"Expansion"],[10,"ii7",2,50,[69,72,77],"Expansion"],
  [11,"V",7,55,[67,71,74],"Tonicize V"],[12,"V7/V",2,50,[66,69,72],"Tonicize V"],
  [13,"V",7,55,[67,71,74],"Tonicize V"],[14,"viio7/V",6,54,[69,72,75],"Tonicize V"],
  [15,"V7",7,55,[71,74,77],"Return"],[16,"I6",0,52,[72,76,79],"Return"],
  [17,"IVmaj7",5,53,[64,69,72],"Return"],[18,"ii7",2,50,[65,69,72],"Return"],
  [19,"V7",7,55,[65,71,74],"Return"],[20,"I",0,48,[67,72,76],"Return"],
  [21,"V7/IV",0,48,[67,70,76],"Build tension"],[22,"IV",5,53,[69,72,77],"Build tension"],
  [23,"viio7",11,59,[68,74,77],"Build tension"],[24,"viio7/V",6,54,[69,72,75],"Build tension"],
  [25,"V7",7,55,[71,74,77],"Build tension"],
  [26,"I6/4",0,55,[72,76,79],"Dom pedal"],[27,"V7",7,55,[71,74,77],"Dom pedal"],
  [28,"vi",9,55,[69,72,76],"Dom pedal"],[29,"V7",7,55,[71,74,77],"Dom pedal"],
  [30,"V9",7,55,[69,74,77],"Dom pedal"],
  [31,"I",0,48,[67,72,76],"Resolution"],[32,"IV",5,48,[65,69,77],"Resolution"],
  [33,"V7",7,48,[65,67,74],"Resolution"],[34,"I",0,48,[64,67,72],"Resolution"],
];

const M = RAW.map(d => ({
  m: d[0], roman: d[1], rootPc: d[2], bass: d[3], upper: d[4], section: d[5],
  pcs: [...new Set([d[3], ...d[4]].map(n => n % 12))],
  voices: [d[3], ...d[4]], // [B, T, A, S]
}));

const SECTIONS = [
  { name: "Statement", start: 0, end: 3 },
  { name: "Expansion", start: 4, end: 9 },
  { name: "Tonicize V", start: 10, end: 13 },
  { name: "Return", start: 14, end: 19 },
  { name: "Build tension", start: 20, end: 24 },
  { name: "Dom pedal", start: 25, end: 29 },
  { name: "Resolution", start: 30, end: 33 },
];

const SEC_COLORS = {
  "Statement": "#60a5fa",
  "Expansion": "#2dd4bf",
  "Tonicize V": "#a78bfa",
  "Return": "#4ade80",
  "Build tension": "#fb923c",
  "Dom pedal": "#f87171",
  "Resolution": "#facc15",
};

const NOTE_NAMES = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"];
const midiName = n => NOTE_NAMES[n % 12] + (Math.floor(n / 12) - 1);
const VOICE_LABELS = ["Bass", "Tenor", "Alto", "Soprano"];
const VOICE_COLORS = ["#818cf8", "#22d3ee", "#34d399", "#fbbf24"];

// ═══════════════════════════════════════════════════════════════════
// TONNETZ — Tymoczko's harmonic geometry
// Grid: pc(col,row) = (7*col + 4*row) mod 12
// Right = P5, Up = M3, diagonal = m3
// ═══════════════════════════════════════════════════════════════════
const CW = 72, RH = 62, TOX = 160, TOY = 170;
const gp = (c, r) => [TOX + c * CW + r * CW * 0.5, TOY - r * RH];
const pcAt = (c, r) => ((7 * c + 4 * r) % 12 + 12) % 12;

// Grid nodes (3 rows × 6 cols = 18 nodes)
const GRID = [];
for (let r = 0; r < 3; r++)
  for (let c = -2; c <= 3; c++)
    GRID.push({ c, r, pc: pcAt(c, r) });

// Upward triangles (major triads) and downward (minor triads)
const TRIS = [];
for (let r = 0; r < 2; r++)
  for (let c = -2; c < 3; c++) {
    TRIS.push({ verts: [[c,r],[c+1,r],[c,r+1]], type: "up" });
    if (c + 1 <= 3) TRIS.push({ verts: [[c+1,r],[c,r+1],[c+1,r+1]], type: "down" });
  }

// Edges between adjacent nodes
const EDGES = [];
for (let r = 0; r < 3; r++)
  for (let c = -2; c <= 3; c++) {
    if (c < 3) EDGES.push([[c,r],[c+1,r]]);
    if (r < 2) EDGES.push([[c,r],[c,r+1]]);
    if (r < 2 && c < 3) EDGES.push([[c+1,r],[c,r+1]]);
  }

// Preferred root position on grid (closest to center)
const ROOT_POS = {
  0:[0,0], 2:[2,0], 4:[0,1], 5:[-1,0], 6:[2,1], 7:[1,0],
  9:[-1,1], 11:[1,1], 8:[0,2], 3:[1,2], 10:[-2,0], 1:[3,1],
};

// ═══════════════════════════════════════════════════════════════════
// VOICE CHART constants
// ═══════════════════════════════════════════════════════════════════
const VCL = 52, VCR = 575, VCT = 14, VCB = 160;
const MIDI_LO = 46, MIDI_HI = 82;
const mx = i => VCL + (i / 33) * (VCR - VCL);
const my = n => VCB - ((n - MIDI_LO) / (MIDI_HI - MIDI_LO)) * (VCB - VCT);

// ═══════════════════════════════════════════════════════════════════
// TONNETZ PANEL
// ═══════════════════════════════════════════════════════════════════
function Tonnetz({ step }) {
  const cur = M[step];
  const color = SEC_COLORS[cur.section];
  const pcsSet = new Set(cur.pcs);
  const [rc, rr] = ROOT_POS[cur.rootPc];

  // Build path up to current step
  const path = M.slice(0, step + 1).map(m => {
    const [c, r] = ROOT_POS[m.rootPc];
    return gp(c, r);
  });

  return (
    <svg viewBox="0 0 560 210" className="w-full" style={{ maxHeight: 240 }}>
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="softglow">
          <feGaussianBlur stdDeviation="2.5" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Axis labels */}
      <text x={TOX + 3.5 * CW + 8} y={TOY + 4} fill="#475569" fontSize="9" textAnchor="start">→ P5</text>
      <text x={TOX - 2.2 * CW - 4} y={TOY - 2.2 * RH + 2} fill="#475569" fontSize="9" textAnchor="end" transform={`rotate(-50, ${TOX - 2.2 * CW - 4}, ${TOY - 2.2 * RH + 2})`}>↗ M3</text>

      {/* Background edges (triangular mesh) */}
      {EDGES.map(([a, b], i) => {
        const [x1, y1] = gp(...a);
        const [x2, y2] = gp(...b);
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1e293b" strokeWidth={1} />;
      })}

      {/* Active triangles (filled when all 3 vertices are chord tones) */}
      {TRIS.map((tri, i) => {
        const triPcs = tri.verts.map(([c, r]) => pcAt(c, r));
        if (!triPcs.every(pc => pcsSet.has(pc))) return null;
        const pts = tri.verts.map(v => gp(...v).join(",")).join(" ");
        return <polygon key={i} points={pts} fill={color} opacity={0.2} />;
      })}

      {/* Active edges (between adjacent chord tones) */}
      {EDGES.map(([a, b], i) => {
        if (!pcsSet.has(pcAt(...a)) || !pcsSet.has(pcAt(...b))) return null;
        const [x1, y1] = gp(...a);
        const [x2, y2] = gp(...b);
        return <line key={`ae${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={color} strokeWidth={2} opacity={0.5} />;
      })}

      {/* Path trail */}
      {path.map((pos, i) => {
        if (i === 0) return null;
        const opacity = Math.max(0.08, 1 - (step - i) * 0.07);
        const width = i === step ? 2.5 : 1.5;
        return <line key={`p${i}`}
          x1={path[i-1][0]} y1={path[i-1][1]} x2={pos[0]} y2={pos[1]}
          stroke="white" strokeWidth={width} opacity={opacity}
          strokeLinecap="round" />;
      })}

      {/* Grid nodes */}
      {GRID.map((node, i) => {
        const [x, y] = gp(node.c, node.r);
        const active = pcsSet.has(node.pc);
        const isRoot = node.c === rc && node.r === rr;
        return (
          <g key={i}>
            <circle cx={x} cy={y}
              r={isRoot ? 16 : active ? 12 : 8}
              fill={isRoot ? color : active ? color : "#0f172a"}
              stroke={active ? color : "#334155"}
              strokeWidth={isRoot ? 2 : active ? 1.5 : 1}
              opacity={isRoot ? 1 : active ? 0.75 : 0.4}
              filter={isRoot ? "url(#glow)" : active ? "url(#softglow)" : undefined}
              style={{ transition: "all 0.25s ease" }}
            />
            <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="central"
              fill={active ? "#fff" : "#64748b"} fontSize={isRoot ? 12 : active ? 11 : 9}
              fontWeight={isRoot ? 700 : active ? 600 : 400}
              style={{ transition: "all 0.25s ease", pointerEvents: "none" }}>
              {NOTE_NAMES[node.pc]}
            </text>
          </g>
        );
      })}

      {/* Current position pulse ring */}
      {(() => {
        const [x, y] = gp(rc, rr);
        return <circle cx={x} cy={y} r={20} fill="none" stroke={color}
          strokeWidth={1.5} opacity={0.6}
          style={{ animation: "pulse 2s ease-in-out infinite" }} />;
      })()}
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════════
// VOICE LEADING CHART
// ═══════════════════════════════════════════════════════════════════
function VoiceChart({ step, onClickMeasure }) {
  // Y-axis labels
  const yLabels = [48, 55, 60, 67, 72, 79].map(n => ({ midi: n, label: midiName(n) }));

  return (
    <svg viewBox="0 0 590 178" className="w-full" style={{ maxHeight: 200 }}>
      {/* Section background bands */}
      {SECTIONS.map((sec, i) => {
        const x1 = mx(sec.start);
        const x2 = mx(sec.end) + (VCR - VCL) / 33;
        return <rect key={i} x={x1} y={VCT - 4} width={x2 - x1} height={VCB - VCT + 8}
          fill={SEC_COLORS[sec.name]} opacity={0.06} rx={3} />;
      })}

      {/* Horizontal grid lines */}
      {yLabels.map(({ midi }, i) => (
        <line key={i} x1={VCL} y1={my(midi)} x2={VCR} y2={my(midi)}
          stroke="#1e293b" strokeWidth={0.5} />
      ))}

      {/* Y-axis labels */}
      {yLabels.map(({ midi, label }, i) => (
        <text key={i} x={VCL - 6} y={my(midi) + 1} textAnchor="end"
          fill="#475569" fontSize="8" dominantBaseline="central">{label}</text>
      ))}

      {/* Voice lines (B, T, A, S) */}
      {[0, 1, 2, 3].map(v => {
        const pts = M.map((m, i) => `${mx(i)},${my(m.voices[v])}`).join(" ");
        return <polyline key={v} points={pts} fill="none"
          stroke={VOICE_COLORS[v]} strokeWidth={1.5} opacity={0.5}
          strokeLinejoin="round" />;
      })}

      {/* Current measure highlight */}
      <line x1={mx(step)} y1={VCT - 4} x2={mx(step)} y2={VCB + 4}
        stroke="white" strokeWidth={1} opacity={0.3} />

      {/* Current voice positions (dots) */}
      {M[step].voices.map((note, v) => (
        <circle key={v} cx={mx(step)} cy={my(note)} r={4}
          fill={VOICE_COLORS[v]} filter="url(#softglow)"
          style={{ transition: "all 0.25s ease" }} />
      ))}

      {/* Clickable measure areas */}
      {M.map((_, i) => (
        <rect key={i} x={mx(i) - 7} y={VCT - 6} width={14} height={VCB - VCT + 12}
          fill="transparent" cursor="pointer"
          onClick={() => onClickMeasure(i)} />
      ))}

      {/* X-axis measure labels */}
      {[0, 4, 9, 14, 19, 24, 29, 33].map(i => (
        <text key={i} x={mx(i)} y={VCB + 14} textAnchor="middle"
          fill="#475569" fontSize="8">{i + 1}</text>
      ))}
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════
export default function App() {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(700);

  // Playback
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      setStep(s => {
        if (s >= 33) { setPlaying(false); return 33; }
        return s + 1;
      });
    }, speed);
    return () => clearInterval(timer);
  }, [playing, speed]);

  // Keyboard
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "ArrowLeft") setStep(s => Math.max(0, s - 1));
      else if (e.key === "ArrowRight") setStep(s => Math.min(33, s + 1));
      else if (e.key === " ") { e.preventDefault(); setPlaying(p => !p); }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const cur = M[step];
  const prev = step > 0 ? M[step - 1] : null;
  const color = SEC_COLORS[cur.section];

  // Displacement from previous
  const displacement = prev
    ? cur.voices.reduce((sum, v, i) => sum + Math.abs(v - prev.voices[i]), 0)
    : 0;

  // Common tones
  const commonTones = prev
    ? cur.pcs.filter(pc => prev.pcs.includes(pc)).length
    : cur.pcs.length;

  return (
    <div className="bg-slate-950 min-h-screen text-slate-200 select-none"
      style={{ fontFamily: "'Inter', 'SF Pro', system-ui, sans-serif" }}>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; r: 20; }
          50% { opacity: 0.2; r: 26; }
        }
      `}</style>

      {/* ── Header ── */}
      <div className="px-5 pt-4 pb-2 flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-white">Harmonic Geometry</h1>
          <p className="text-xs text-slate-500 mt-0.5">Experiment 001 — C Major Prelude (Bach-style) — Tonnetz + Voice Leading</p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-light text-white tracking-tighter">m.{cur.m}</span>
            <span className="text-lg font-mono font-bold" style={{ color }}>{cur.roman}</span>
          </div>
        </div>
      </div>

      {/* ── Section timeline ── */}
      <div className="px-5 pb-1">
        <div className="flex gap-0.5 rounded overflow-hidden h-5">
          {SECTIONS.map((sec, i) => {
            const w = ((sec.end - sec.start + 1) / 34) * 100;
            const active = step >= sec.start && step <= sec.end;
            return (
              <div key={i}
                className="flex items-center justify-center cursor-pointer transition-all duration-200"
                style={{
                  width: `${w}%`,
                  backgroundColor: SEC_COLORS[sec.name],
                  opacity: active ? 0.9 : 0.2,
                }}
                onClick={() => setStep(sec.start)}>
                <span className="text-[8px] font-medium text-white truncate px-1"
                  style={{ opacity: active ? 1 : 0 }}>
                  {sec.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Tonnetz ── */}
      <div className="px-3 pt-1">
        <Tonnetz step={step} />
      </div>

      {/* ── Voice info strip ── */}
      <div className="px-5 flex items-center gap-4 text-[10px] text-slate-500 pb-1">
        <span className="font-medium text-slate-400">SATB:</span>
        {cur.voices.map((v, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: VOICE_COLORS[i] }} />
            <span style={{ color: VOICE_COLORS[i] }}>{VOICE_LABELS[i]}</span>
            <span className="text-slate-500 font-mono">{midiName(v)}</span>
            {prev && (
              <span className={`font-mono ${v > prev.voices[i] ? "text-emerald-600" : v < prev.voices[i] ? "text-rose-600" : "text-slate-700"}`}>
                {v === prev.voices[i] ? "·" : (v > prev.voices[i] ? `+${v - prev.voices[i]}` : `${v - prev.voices[i]}`)}
              </span>
            )}
          </span>
        ))}
      </div>

      {/* ── Voice Chart ── */}
      <div className="px-3">
        <VoiceChart step={step} onClickMeasure={setStep} />
      </div>

      {/* ── Controls ── */}
      <div className="px-5 pt-2 pb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => { setStep(0); setPlaying(false); }}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 flex items-center justify-center text-xs transition">
            ⏮
          </button>
          <button onClick={() => setStep(s => Math.max(0, s - 1))}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 flex items-center justify-center text-sm transition">
            ◀
          </button>
          <button onClick={() => setPlaying(p => !p)}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-lg transition"
            style={{ backgroundColor: playing ? color : "#1e293b", color: playing ? "#fff" : color }}>
            {playing ? "⏸" : "▶"}
          </button>
          <button onClick={() => setStep(s => Math.min(33, s + 1))}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 flex items-center justify-center text-sm transition">
            ▶
          </button>
          <button onClick={() => { setStep(33); setPlaying(false); }}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 flex items-center justify-center text-xs transition">
            ⏭
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>Speed</span>
          <input type="range" min={200} max={1500} step={100} value={speed}
            onChange={e => setSpeed(Number(e.target.value))}
            className="w-20 accent-slate-500" style={{ accentColor: color }} />
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="text-center">
            <div className="text-slate-600 text-[9px]">displacement</div>
            <div className="font-mono text-sm" style={{ color }}>
              {displacement}<span className="text-slate-600 text-[9px] ml-0.5">st</span>
            </div>
          </div>
          <div className="text-center">
            <div className="text-slate-600 text-[9px]">common tones</div>
            <div className="font-mono text-sm text-slate-300">
              {commonTones}<span className="text-slate-600 text-[9px]">/{cur.pcs.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Progress bar ── */}
      <div className="px-5 pb-4 pt-1">
        <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-200"
            style={{ width: `${((step + 1) / 34) * 100}%`, backgroundColor: color }} />
        </div>
      </div>
    </div>
  );
}

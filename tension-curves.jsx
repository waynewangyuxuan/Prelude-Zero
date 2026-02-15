import { useState, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, ReferenceArea, BarChart, Bar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";

// ═══════════════════════════════════════════════════════════════
// Tension data from our analysis
// ═══════════════════════════════════════════════════════════════

const PRELUDE_SECTIONS = [
  { name: "A: Statement", start: 0, end: 16, color: "#3b82f6" },
  { name: "B: Expansion", start: 16, end: 40, color: "#8b5cf6" },
  { name: "C: Tonicize V", start: 40, end: 56, color: "#ec4899" },
  { name: "D: Return", start: 56, end: 80, color: "#f59e0b" },
  { name: "E: Build tension", start: 80, end: 100, color: "#ef4444" },
  { name: "F: Dom pedal", start: 100, end: 120, color: "#dc2626" },
  { name: "G: Resolution", start: 120, end: 136, color: "#10b981" },
];

const FUGUE_SECTIONS = [
  { name: "Exposition", start: 0, end: 36, color: "#3b82f6" },
  { name: "Episode 1", start: 36, end: 44, color: "#8b5cf6" },
  { name: "Mid Entry 1", start: 44, end: 53, color: "#ec4899" },
  { name: "Episode 2", start: 53, end: 61, color: "#f59e0b" },
  { name: "Mid Entry 2", start: 61, end: 70, color: "#a855f7" },
  { name: "Episode 3", start: 70, end: 78, color: "#64748b" },
  { name: "Stretto", start: 78, end: 96, color: "#ef4444" },
  { name: "Final Cad.", start: 96, end: 104, color: "#10b981" },
];

const PRELUDE_DATA = {
  sections: PRELUDE_SECTIONS,
  sectionMeans: [
    { section: "A: Statement", harmonic: 0.217, dissonance: 0.060, melodic: 0.115, registral: 0.276, density: 0.529, combined: 0.210 },
    { section: "B: Expansion", harmonic: 0.252, dissonance: 0.074, melodic: 0.117, registral: 0.221, density: 0.510, combined: 0.216 },
    { section: "C: Tonicize V", harmonic: 0.344, dissonance: 0.132, melodic: 0.098, registral: 0.272, density: 0.536, combined: 0.263 },
    { section: "D: Return", harmonic: 0.246, dissonance: 0.081, melodic: 0.159, registral: 0.290, density: 0.507, combined: 0.231 },
    { section: "E: Build", harmonic: 0.408, dissonance: 0.168, melodic: 0.239, registral: 0.279, density: 0.531, combined: 0.320 },
    { section: "F: Dom pedal", harmonic: 0.185, dissonance: 0.069, melodic: 0.142, registral: 0.222, density: 0.508, combined: 0.200 },
    { section: "G: Resolution", harmonic: 0.073, dissonance: 0.056, melodic: 0.208, registral: 0.309, density: 0.518, combined: 0.186 },
  ],
  peak: { beat: 52.0, tension: 0.552, section: "C: Tonicize V" },
  expectedPeak: { start: 100, end: 120, section: "F: Dom pedal" },
  distance: 0.3026,
  variance: 0.0943,
  bpm: 66,
};

const FUGUE_DATA = {
  sections: FUGUE_SECTIONS,
  sectionMeans: [
    { section: "Exposition", harmonic: 0.257, dissonance: 0.130, melodic: 0.058, registral: 0.175, density: 0.198, combined: 0.168 },
    { section: "Episode 1", harmonic: 0.422, dissonance: 0.321, melodic: 0.108, registral: 0.600, density: 0.399, combined: 0.349 },
    { section: "Mid Entry 1", harmonic: 0.398, dissonance: 0.270, melodic: 0.090, registral: 0.670, density: 0.244, combined: 0.309 },
    { section: "Episode 2", harmonic: 0.386, dissonance: 0.270, melodic: 0.124, registral: 0.683, density: 0.375, combined: 0.333 },
    { section: "Mid Entry 2", harmonic: 0.375, dissonance: 0.245, melodic: 0.109, registral: 0.408, density: 0.296, combined: 0.281 },
    { section: "Episode 3", harmonic: 0.491, dissonance: 0.209, melodic: 0.058, registral: 0.499, density: 0.271, combined: 0.302 },
    { section: "Stretto", harmonic: 0.251, dissonance: 0.169, melodic: 0.075, registral: 0.462, density: 0.404, combined: 0.240 },
    { section: "Final Cad.", harmonic: 0.262, dissonance: 0.116, melodic: 0.050, registral: 0.795, density: 0.118, combined: 0.215 },
  ],
  peak: { beat: 41.5, tension: 0.510, section: "Episode 1" },
  expectedPeak: { start: 78, end: 96, section: "Stretto" },
  distance: 0.2086,
  variance: 0.1080,
  bpm: 80,
};

// Generate synthetic tension curve data (smooth representations of analysis results)
function generateCurveData(sectionMeans, sections) {
  const data = [];
  const resolution = 0.5;

  for (const sec of sections) {
    const mean = sectionMeans.find(s => s.section === sec.name);
    if (!mean) continue;

    for (let b = sec.start; b < sec.end; b += resolution) {
      // Add some natural-looking variation around the mean
      const progress = (b - sec.start) / (sec.end - sec.start);
      const wave = Math.sin(progress * Math.PI * 2) * 0.05;
      const ramp = progress < 0.2 ? progress * 5 : (progress > 0.8 ? (1 - progress) * 5 : 1);

      data.push({
        beat: b,
        harmonic: Math.max(0, Math.min(1, mean.harmonic + wave * 0.3)),
        dissonance: Math.max(0, Math.min(1, mean.dissonance + wave * 0.2)),
        melodic: Math.max(0, Math.min(1, mean.melodic + Math.sin(b * 0.5) * 0.04)),
        registral: Math.max(0, Math.min(1, mean.registral + wave * 0.1)),
        density: Math.max(0, Math.min(1, mean.density + Math.cos(b * 0.3) * 0.03)),
        combined: Math.max(0, Math.min(1, mean.combined + wave * 0.2)),
      });
    }
  }
  return data;
}

// Generate target curve
function generateTargetCurve(form, totalBeats) {
  const data = [];
  const resolution = 0.5;

  for (let b = 0; b < totalBeats; b += resolution) {
    const t = b / totalBeats;
    let tension;

    if (form === "prelude") {
      const base = 0.3 + 0.5 * Math.sin(Math.PI * Math.pow(t, 0.8));
      const peak = 0.2 * Math.exp(-Math.pow((t - 0.75) / 0.08, 2));
      const res = t > 0.9 ? -0.3 * (t - 0.9) / 0.1 : 0;
      tension = Math.max(0, Math.min(1, base + peak + res));
    } else {
      // fugue
      if (t < 0.35) {
        tension = 0.2 + 0.3 * (t / 0.35);
      } else if (t < 0.75) {
        tension = 0.5 + 0.15 * Math.sin(6 * Math.PI * (t - 0.35));
      } else if (t < 0.92) {
        tension = 0.7 + 0.2 * ((t - 0.75) / 0.17);
      } else {
        tension = 0.9 - 0.7 * ((t - 0.92) / 0.08);
      }
    }

    data.push({ beat: b, target: tension });
  }
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Components
// ═══════════════════════════════════════════════════════════════

const DIMS = [
  { key: "harmonic", color: "#ef4444", label: "Harmonic" },
  { key: "dissonance", color: "#f59e0b", label: "Dissonance" },
  { key: "melodic", color: "#3b82f6", label: "Melodic" },
  { key: "registral", color: "#10b981", label: "Registral" },
  { key: "density", color: "#8b5cf6", label: "Density" },
  { key: "combined", color: "#ffffff", label: "Combined" },
];

function DiagnosticBadge({ label, value, status }) {
  const colors = {
    good: "bg-emerald-900 text-emerald-300 border-emerald-700",
    warn: "bg-amber-900 text-amber-300 border-amber-700",
    bad: "bg-red-900 text-red-300 border-red-700",
  };
  return (
    <div className={`px-3 py-2 rounded-lg border ${colors[status]} text-center`}>
      <div className="text-xs opacity-70">{label}</div>
      <div className="text-lg font-mono font-bold">{value}</div>
    </div>
  );
}

function TensionChart({ curveData, targetData, sections, title, peakInfo, expectedPeak }) {
  // Merge curve and target
  const merged = curveData.map((d, i) => {
    const tgt = targetData.find(t => Math.abs(t.beat - d.beat) < 0.01);
    return { ...d, target: tgt ? tgt.target : null };
  });

  const [hoveredDim, setHoveredDim] = useState(null);
  const [showTarget, setShowTarget] = useState(true);
  const [visibleDims, setVisibleDims] = useState(new Set(["combined", "harmonic", "dissonance"]));

  const toggleDim = (key) => {
    setVisibleDims(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="mb-8">
      <h3 className="text-lg font-bold text-gray-200 mb-2">{title}</h3>

      {/* Dimension toggles */}
      <div className="flex flex-wrap gap-2 mb-3">
        {DIMS.map(d => (
          <button
            key={d.key}
            onClick={() => toggleDim(d.key)}
            className={`px-2 py-1 text-xs rounded border transition-all ${
              visibleDims.has(d.key)
                ? "border-gray-500 bg-gray-800"
                : "border-gray-700 bg-gray-900 opacity-40"
            }`}
            style={{ color: d.color, borderColor: visibleDims.has(d.key) ? d.color : undefined }}
          >
            {d.label}
          </button>
        ))}
        <button
          onClick={() => setShowTarget(!showTarget)}
          className={`px-2 py-1 text-xs rounded border transition-all ${
            showTarget ? "border-yellow-600 bg-yellow-900/30 text-yellow-400" : "border-gray-700 bg-gray-900 opacity-40 text-gray-500"
          }`}
        >
          Target
        </button>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={merged} margin={{ top: 5, right: 10, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="beat" stroke="#9ca3af" tick={{ fontSize: 11 }} label={{ value: "Beat", position: "bottom", fill: "#9ca3af", fontSize: 11 }} />
          <YAxis domain={[0, 1]} stroke="#9ca3af" tick={{ fontSize: 11 }} label={{ value: "Tension", angle: -90, position: "insideLeft", fill: "#9ca3af", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", fontSize: "12px" }}
            labelStyle={{ color: "#9ca3af" }}
            labelFormatter={(v) => `Beat ${v}`}
          />

          {/* Section backgrounds */}
          {sections.map((sec, i) => (
            <ReferenceArea
              key={i}
              x1={sec.start}
              x2={sec.end}
              fill={sec.color}
              fillOpacity={0.06}
              label={{ value: sec.name.split(":").pop().trim(), position: "top", fill: sec.color, fontSize: 9, opacity: 0.7 }}
            />
          ))}

          {/* Peak marker */}
          <ReferenceLine x={peakInfo.beat} stroke="#ef4444" strokeDasharray="5 5" label={{ value: `Peak`, fill: "#ef4444", fontSize: 10 }} />

          {/* Expected peak zone */}
          <ReferenceArea x1={expectedPeak.start} x2={expectedPeak.end} fill="#ef4444" fillOpacity={0.08} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.3} />

          {/* Target curve */}
          {showTarget && (
            <Line type="monotone" dataKey="target" stroke="#fbbf24" strokeWidth={2} strokeDasharray="8 4" dot={false} opacity={0.6} name="Target" />
          )}

          {/* Actual dimension curves */}
          {DIMS.map(d => visibleDims.has(d.key) && (
            <Line
              key={d.key}
              type="monotone"
              dataKey={d.key}
              stroke={d.color}
              strokeWidth={d.key === "combined" ? 2.5 : 1.5}
              dot={false}
              opacity={hoveredDim && hoveredDim !== d.key ? 0.2 : 1}
              name={d.label}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SectionRadar({ sectionMeans, title }) {
  const [selected, setSelected] = useState(0);
  const dims = ["harmonic", "dissonance", "melodic", "registral", "density"];

  const radarData = dims.map(d => ({
    dimension: d.charAt(0).toUpperCase() + d.slice(1),
    value: sectionMeans[selected][d],
    fullMark: 1,
  }));

  return (
    <div>
      <h3 className="text-lg font-bold text-gray-200 mb-2">{title}</h3>
      <div className="flex flex-wrap gap-1 mb-3">
        {sectionMeans.map((s, i) => (
          <button
            key={i}
            onClick={() => setSelected(i)}
            className={`px-2 py-1 text-xs rounded border transition-all ${
              selected === i ? "border-blue-500 bg-blue-900/40 text-blue-300" : "border-gray-700 text-gray-400"
            }`}
          >
            {s.section}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width="60%" height={220}>
          <RadarChart data={radarData}>
            <PolarGrid stroke="#374151" />
            <PolarAngleAxis dataKey="dimension" tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 1]} tick={{ fontSize: 9, fill: "#6b7280" }} />
            <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
          </RadarChart>
        </ResponsiveContainer>
        <div className="text-sm text-gray-400 space-y-1">
          <div className="text-gray-200 font-bold">{sectionMeans[selected].section}</div>
          {dims.map(d => (
            <div key={d} className="flex justify-between gap-4">
              <span className="capitalize">{d}:</span>
              <span className="font-mono text-gray-300">{sectionMeans[selected][d].toFixed(3)}</span>
            </div>
          ))}
          <div className="border-t border-gray-700 pt-1 flex justify-between gap-4">
            <span className="font-bold">Combined:</span>
            <span className="font-mono text-white font-bold">{sectionMeans[selected].combined.toFixed(3)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionBarChart({ sectionMeans, title }) {
  return (
    <div>
      <h3 className="text-lg font-bold text-gray-200 mb-2">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={sectionMeans} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="section" tick={{ fontSize: 9, fill: "#9ca3af" }} angle={-20} textAnchor="end" height={50} />
          <YAxis domain={[0, 0.5]} tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", fontSize: "12px" }} />
          <Bar dataKey="harmonic" fill="#ef4444" opacity={0.8} name="Harmonic" />
          <Bar dataKey="dissonance" fill="#f59e0b" opacity={0.8} name="Dissonance" />
          <Bar dataKey="melodic" fill="#3b82f6" opacity={0.8} name="Melodic" />
          <Bar dataKey="registral" fill="#10b981" opacity={0.8} name="Registral" />
          <Bar dataKey="density" fill="#8b5cf6" opacity={0.8} name="Density" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FindingsPanel({ piece, data }) {
  const findings = piece === "prelude" ? [
    {
      label: "Peak Misplacement",
      status: "bad",
      text: `Peak at beat ${data.peak.beat} (${data.peak.section}) — should be at Section F (Dom pedal, beats 100-120). The climactic dominant pedal is actually LESS tense than Section E.`
    },
    {
      label: "Flat Density",
      status: "warn",
      text: "Density is nearly uniform (~0.51 everywhere) because the arpeggiation pattern never changes. Bach varies density — this is a dimension we're not using."
    },
    {
      label: "Dissonance Too Low",
      status: "warn",
      text: "Mean dissonance only 0.091. The diminished chords (Sections C, E) create brief spikes, but not enough. Bach uses more suspensions and passing tones."
    },
    {
      label: "Harmonic Arc OK",
      status: "good",
      text: "Harmonic tension does rise through E (0.408) and falls at resolution G (0.073). The overall shape is reasonable, just not dramatic enough."
    },
  ] : [
    {
      label: "Peak Still Misplaced",
      status: "bad",
      text: `Peak at beat ${data.peak.beat} (${data.peak.section}) — should be at Stretto (beats 78-96). Stretto v3 climbed to 0.240 (+32% from v2's 0.182), now 3rd highest section, but Episode 1 (0.349) still dominates.`
    },
    {
      label: "Stretto v3: Free Counterpoint",
      status: "warn",
      text: "Free counterpoint replaced 2 of 4 subject entries with chromatic lines + diminution. Density +88% (0.215→0.404), registral +55% (0.299→0.462). Pitch entropy rose to 3.113 bits (\"adventurous\" sweet spot). 350 notes, 0 errors. Still below target ~0.65."
    },
    {
      label: "Registral Shape Good",
      status: "good",
      text: "Registral spread grows naturally (0.175 → 0.795) as voices enter and spread. Stretto now 0.462 — free bass chromatic line widened the spread. Final cadence has maximum spread — correct for Bach."
    },
    {
      label: "Gap Closing But Not There",
      status: "warn",
      text: "Distance from ideal dropped 0.236→0.209 (-10%). Variance 0.108 is moderate contrast. Next: reduce episode tension OR further boost stretto (secondary dominants, augmented 6ths, more suspensions)."
    },
  ];

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-bold text-gray-200">Diagnostic Findings</h3>
      {findings.map((f, i) => {
        const borderColor = f.status === "bad" ? "border-red-700" : f.status === "warn" ? "border-amber-700" : "border-emerald-700";
        const bgColor = f.status === "bad" ? "bg-red-950" : f.status === "warn" ? "bg-amber-950" : "bg-emerald-950";
        const labelColor = f.status === "bad" ? "text-red-400" : f.status === "warn" ? "text-amber-400" : "text-emerald-400";
        return (
          <div key={i} className={`p-3 rounded-lg border ${borderColor} ${bgColor}`}>
            <div className={`text-sm font-bold ${labelColor} mb-1`}>{f.label}</div>
            <div className="text-xs text-gray-300 leading-relaxed">{f.text}</div>
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Main App
// ═══════════════════════════════════════════════════════════════

export default function TensionDashboard() {
  const [piece, setPiece] = useState("prelude");

  const data = piece === "prelude" ? PRELUDE_DATA : FUGUE_DATA;
  const totalBeats = piece === "prelude" ? 136 : 104;

  const curveData = useMemo(() => generateCurveData(data.sectionMeans, data.sections), [piece]);
  const targetData = useMemo(() => generateTargetCurve(piece, totalBeats), [piece]);

  const peakStatus = (piece === "prelude" && data.peak.beat >= 100 && data.peak.beat <= 120) ||
                     (piece === "fugue" && data.peak.beat >= 78 && data.peak.beat <= 96) ? "good" : "bad";
  const varianceStatus = data.variance > 0.12 ? "good" : data.variance > 0.09 ? "warn" : "bad";

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Tension Curve Analysis</h1>
          <p className="text-sm text-gray-400 mt-1">
            T(t) = 0.30 harmonic + 0.25 dissonance + 0.20 melodic + 0.10 registral + 0.15 density
          </p>
        </div>

        {/* Piece toggle */}
        <div className="flex gap-2 mb-6">
          {["prelude", "fugue"].map(p => (
            <button
              key={p}
              onClick={() => setPiece(p)}
              className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                piece === p
                  ? "border-blue-500 bg-blue-900/40 text-blue-300"
                  : "border-gray-700 bg-gray-900 text-gray-400 hover:border-gray-500"
              }`}
            >
              {p === "prelude" ? "C Major Prelude" : "C Major Fugue"}
            </button>
          ))}
        </div>

        {/* Summary badges */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <DiagnosticBadge
            label="Peak Location"
            value={`Beat ${data.peak.beat}`}
            status={peakStatus}
          />
          <DiagnosticBadge
            label="Distance from Ideal"
            value={data.distance.toFixed(3)}
            status={data.distance > 0.25 ? "bad" : data.distance > 0.15 ? "warn" : "good"}
          />
          <DiagnosticBadge
            label="Tension Variance"
            value={data.variance.toFixed(4)}
            status={varianceStatus}
          />
          <DiagnosticBadge
            label={piece === "prelude" ? "BPM" : "BPM"}
            value={data.bpm}
            status="good"
          />
        </div>

        {/* Main tension curve */}
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
          <TensionChart
            curveData={curveData}
            targetData={targetData}
            sections={data.sections}
            title={piece === "prelude" ? "Prelude Tension Over Time" : "Fugue Tension Over Time"}
            peakInfo={data.peak}
            expectedPeak={data.expectedPeak}
          />
          <div className="flex items-center gap-4 text-xs text-gray-500 mt-1 px-4">
            <span className="flex items-center gap-1">
              <span className="w-4 h-0.5 bg-red-500 inline-block" style={{ borderTop: "2px dashed #ef4444" }} /> Actual peak
            </span>
            <span className="flex items-center gap-1">
              <span className="w-8 h-3 bg-red-500/10 border border-red-500/30 inline-block rounded" /> Expected peak zone
            </span>
            <span className="flex items-center gap-1">
              <span className="w-6 h-0.5 inline-block" style={{ borderTop: "2px dashed #fbbf24" }} /> Target curve
            </span>
          </div>
        </div>

        {/* Bottom grid: radar + findings */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <SectionRadar
              sectionMeans={data.sectionMeans}
              title="Section Tension Profile"
            />
          </div>
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <FindingsPanel piece={piece} data={data} />
          </div>
        </div>

        {/* Section bar chart */}
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
          <SectionBarChart
            sectionMeans={data.sectionMeans}
            title="Per-Section Dimension Breakdown"
          />
        </div>

        {/* What this means */}
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <h3 className="text-lg font-bold text-white mb-3">What This Tells Us</h3>
          <div className="text-sm text-gray-300 leading-relaxed space-y-3">
            <p>
              <span className="text-red-400 font-medium">Core problem:</span> Both pieces have their tension peaks in the wrong place.
              The Prelude peaks at the tonicization of V (Section C) instead of the dramatic dominant pedal.
              The Fugue peaks at Episode 1 instead of the Stretto climax — though stretto v3's free counterpoint
              closed the gap from 0.182 to 0.240 (+32%).
            </p>
            <p>
              <span className="text-amber-400 font-medium">What worked:</span> Free counterpoint — replacing obligatory subject entries
              with chromatic lines and diminution — was the right structural fix. Density +88%, registral +55%,
              and pitch entropy rose to 3.113 bits ("adventurous" sweet spot, up from 2.783). The music got
              more interesting <em>and</em> stayed error-free (0 counterpoint errors, 350 notes).
            </p>
            <p>
              <span className="text-blue-400 font-medium">Path forward:</span> Two strategies: (1) further boost
              stretto with secondary dominants and suspensions, (2) reduce episode tension to make stretto relatively
              peak. The information-theoretic engine (entropy) now provides a second dimension of quality measurement
              alongside the tension curve.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

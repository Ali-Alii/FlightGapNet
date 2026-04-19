import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Legend,
} from "recharts";
import { TrendingDown, Award, Target, Layers, FlaskConical, Info } from "lucide-react";

const ALL_MODELS = [
  { id: "great_circle", label: "GreatCircle", type: "baseline", color: "#6b7280" },
  { id: "last_hold",    label: "LastHold",    type: "baseline", color: "#8b5cf6" },
  { id: "const_vel",   label: "ConstVel",    type: "baseline", color: "#f59e0b" },
  { id: "kalman",      label: "Kalman",       type: "baseline", color: "#06b6d4" },
  { id: "lstm",        label: "LSTM",         type: "ml",       color: "#00c8ff" },
  { id: "gru",         label: "GRU",          type: "ml",       color: "#00e87a" },
];

const BENCHMARK = [
  { id: "great_circle", label: "GreatCircle", mean_geo: 0.9831, rmse: 0.0099, p90: 1.5602, max_geo: 1.8039, alt_mae: 37.4855, path_err: 0.2485, mae: 0.00625 },
  { id: "last_hold",    label: "LastHold",    mean_geo: 21.8537, rmse: 0.2120, p90: 35.6236, max_geo: 39.1712, alt_mae: 390.9628, path_err: 35.2266, mae: 0.13345 },
  { id: "const_vel",    label: "ConstVel",    mean_geo: 1.5078, rmse: 0.0126, p90: 3.0845, max_geo: 3.8739, alt_mae: 67.0939, path_err: 3.2981, mae: 0.00945 },
  { id: "kalman",       label: "Kalman",      mean_geo: 1.2121, rmse: 0.0090, p90: 2.1815, max_geo: 2.6658, alt_mae: 295.2793, path_err: 2.3612, mae: 0.00750 },
  { id: "lstm",         label: "LSTM",        mean_geo: 2.2889, rmse: 0.0190, p90: 4.4097, max_geo: 5.3414, alt_mae: 129.6012, path_err: 3.8621, mae: 0.01525 },
  { id: "gru",          label: "GRU",         mean_geo: 4.1165, rmse: 0.0300, p90: 7.4159, max_geo: 8.4246, alt_mae: 182.7065, path_err: 6.4994, mae: 0.02515 },
];

const METRICS_META = [
  { key: "mean_geo", label: "Mean Geodesic (km)", unit: "km", lower: true },
  { key: "rmse",     label: "RMSE (km)",           unit: "km", lower: true },
  { key: "p90",      label: "P90 Geodesic (km)",   unit: "km", lower: true },
  { key: "max_geo",  label: "Max Geodesic (km)",   unit: "km", lower: true },
  { key: "alt_mae",  label: "Altitude MAE (m)",    unit: "m",  lower: true },
  { key: "path_err", label: "Path Length Err (km)","unit": "km", lower: true },
  { key: "mae",      label: "MAE (lat/lon °)",      unit: "°",  lower: true },
];

const CHART_METRICS = [
  { key: "mean_geo", label: "Mean Geodesic Error (km)" },
  { key: "p90",      label: "P90 Geodesic Error (km)" },
  { key: "alt_mae",  label: "Altitude MAE (m)" },
  { key: "path_err", label: "Path Length Error (km)" },
];

function getColor(id) {
  return ALL_MODELS.find((m) => m.id === id)?.color ?? "#fff";
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#080e1a] border border-[#0d1f35] rounded-lg p-3 shadow-xl">
      <p className="text-[11px] font-semibold text-[#c8d8ec] mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="text-[10px] font-mono" style={{ color: p.fill }}>
          {p.name}: <span className="font-bold">{typeof p.value === "number" ? p.value.toFixed(2) : p.value}</span>
        </p>
      ))}
    </div>
  );
};

export default function BenchmarkPage() {
  const [activeMetric, setActiveMetric] = useState("mean_geo");
  const [compareIds, setCompareIds] = useState(new Set(ALL_MODELS.map((m) => m.id)));

  const sorted = [...BENCHMARK]
    .filter((d) => compareIds.has(d.id))
    .sort((a, b) => a[activeMetric] - b[activeMetric]);

  const best = sorted[0];
  const bestBaseline = sorted.filter((d) => {
    const m = ALL_MODELS.find((x) => x.id === d.id);
    return m?.type === "baseline";
  })[0];

  const toggleModel = (id) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { if (next.size > 1) next.delete(id); }
      else next.add(id);
      return next;
    });
  };

  // Radar normalization
  const radarData = ["mean_geo", "rmse", "p90", "alt_mae", "path_err"].map((key) => {
    const maxVal = Math.max(...BENCHMARK.map((d) => d[key]));
    const entry = { metric: key.replace("_", " ").toUpperCase() };
    BENCHMARK.forEach((d) => {
      if (compareIds.has(d.id)) {
        entry[d.label] = +(100 - (d[key] / maxVal) * 100).toFixed(1);
      }
    });
    return entry;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[13px] text-[#3a5a7a] font-mono mt-1">
            Full benchmark comparison using your latest saved AeroTrack evaluation results
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#f5a62315] border border-[#f5a62330] rounded-lg">
          <Info size={11} className="text-[#f5a623]" />
          <span className="text-[10px] font-mono text-[#f5a623]">Latest saved evaluation values</span>
        </div>
      </div>

      {/* Filter row */}
      <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-[10px] text-[#3a5a7a] font-mono uppercase tracking-widest">Filter models:</span>
          {ALL_MODELS.map((m) => (
            <button
              key={m.id}
              onClick={() => toggleModel(m.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono transition-all border ${
                compareIds.has(m.id)
                  ? "border-[#1a3050] text-white"
                  : "border-[#0d1f35] text-[#3a5a7a] opacity-50"
              }`}
              style={
                compareIds.has(m.id)
                  ? { backgroundColor: `${m.color}15`, borderColor: `${m.color}40`, color: m.color }
                  : {}
              }
            >
              {m.type === "ml" ? <FlaskConical size={9} /> : <Layers size={9} />}
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Win cards */}
      {best && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <div className="bg-[#080e1a] border border-[#ffd70030] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Award size={14} className="text-[#ffd700]" />
              <span className="text-[10px] font-mono text-[#3a5a7a] uppercase tracking-widest">Best Overall</span>
            </div>
            <div className="text-[18px] font-bold" style={{ color: getColor(best.id) }}>{best.label}</div>
            <div className="text-[11px] text-[#3a5a7a] mt-1 font-mono">{best.mean_geo.toFixed(2)} km avg geo error</div>
          </div>
          {bestBaseline && (
            <div className="bg-[#080e1a] border border-[#06b6d430] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Target size={14} className="text-[#06b6d4]" />
                <span className="text-[10px] font-mono text-[#3a5a7a] uppercase tracking-widest">Best Baseline</span>
              </div>
              <div className="text-[18px] font-bold" style={{ color: getColor(bestBaseline.id) }}>{bestBaseline.label}</div>
              <div className="text-[11px] text-[#3a5a7a] mt-1 font-mono">{bestBaseline.mean_geo.toFixed(2)} km avg geo error</div>
            </div>
          )}
          {best && bestBaseline && (
            <div className="bg-[#080e1a] border border-[#00e87a30] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown size={14} className="text-[#00e87a]" />
                <span className="text-[10px] font-mono text-[#3a5a7a] uppercase tracking-widest">ML vs Best Baseline</span>
              </div>
              <div className="text-[18px] font-bold text-[#00e87a]">
                {Math.abs(((best.mean_geo - bestBaseline.mean_geo) / bestBaseline.mean_geo) * 100).toFixed(1)}% {best.mean_geo < bestBaseline.mean_geo ? "better" : "worse"}
              </div>
              <div className="text-[11px] text-[#3a5a7a] mt-1 font-mono">{best.label} vs {bestBaseline.label}</div>
            </div>
          )}
        </div>
      )}

      {/* Chart + metric selector */}
      <div className="grid lg:grid-cols-[240px_1fr] gap-4">
        {/* Metric selector */}
        <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4 space-y-1">
          <p className="text-[10px] text-[#3a5a7a] font-mono uppercase tracking-widest mb-3">Chart Metric</p>
          {CHART_METRICS.map((m) => (
            <button
              key={m.key}
              onClick={() => setActiveMetric(m.key)}
              className={`w-full text-left px-3 py-2 rounded-lg text-[11px] font-mono transition-all ${
                activeMetric === m.key
                  ? "bg-[#0d2040] text-[#00c8ff] border border-[#00c8ff]/30"
                  : "text-[#3a5a7a] hover:text-[#c8d8ec] hover:bg-[#0d1f35] border border-transparent"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Bar chart */}
        <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-5">
          <p className="text-[11px] font-semibold text-[#8a9ab0] mb-4 font-mono">
            {CHART_METRICS.find((m) => m.key === activeMetric)?.label} — All Models
          </p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sorted} margin={{ top: 5, right: 10, bottom: 20, left: 0 }} barSize={32}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0d1f35" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "#3a5a7a", fontSize: 10, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#3a5a7a", fontSize: 9, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
                width={45}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey={activeMetric} radius={[4, 4, 0, 0]}>
                {sorted.map((entry) => (
                  <rect key={entry.id} fill={getColor(entry.id)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Radar chart */}
      <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-5">
        <p className="text-[11px] font-semibold text-[#8a9ab0] mb-1 font-mono">Overall Performance Radar</p>
        <p className="text-[10px] text-[#2a4a6a] mb-4 font-mono">Higher = better (normalized, lower error inverted)</p>
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
            <PolarGrid stroke="#0d1f35" />
            <PolarAngleAxis dataKey="metric" tick={{ fill: "#3a5a7a", fontSize: 10, fontFamily: "monospace" }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            {[...compareIds].map((id) => {
              const m = ALL_MODELS.find((x) => x.id === id);
              return m ? (
                <Radar
                  key={id}
                  name={m.label}
                  dataKey={m.label}
                  stroke={m.color}
                  fill={m.color}
                  fillOpacity={0.08}
                  strokeWidth={2}
                />
              ) : null;
            })}
            <Legend
              wrapperStyle={{ fontSize: 10, fontFamily: "monospace", paddingTop: 10 }}
            />
            <Tooltip content={<CustomTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Full table */}
      <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-[#0d1f35] bg-[#05080f] flex items-center justify-between">
          <p className="text-[11px] font-semibold text-[#8a9ab0] font-mono">Full Metrics Table</p>
          <span className="text-[10px] text-[#2a4a6a] font-mono">Sorted by Mean Geodesic Error</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="border-b border-[#0d1f35]">
                <th className="text-left px-4 py-2.5 text-[10px] text-[#3a5a7a] uppercase tracking-widest font-normal">#</th>
                <th className="text-left px-4 py-2.5 text-[10px] text-[#3a5a7a] uppercase tracking-widest font-normal">Model</th>
                <th className="text-left px-4 py-2.5 text-[10px] text-[#3a5a7a] uppercase tracking-widest font-normal">Type</th>
                {METRICS_META.map((m) => (
                  <th key={m.key} className="text-right px-3 py-2.5 text-[10px] text-[#3a5a7a] uppercase tracking-widest font-normal whitespace-nowrap">
                    {m.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...BENCHMARK].sort((a, b) => a.mean_geo - b.mean_geo).map((row, i) => {
                const model = ALL_MODELS.find((m) => m.id === row.id);
                if (!model) return null;
                const isFirst = i === 0;
                return (
                  <tr
                    key={row.id}
                    className={`border-b border-[#0d1f35]/40 last:border-0 hover:bg-[#0d1f35]/30 transition-colors ${isFirst ? "bg-[#00e87a]/3" : ""}`}
                  >
                    <td className="px-4 py-2.5 text-[#3a5a7a]">{i + 1}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: model.color }} />
                        <span style={{ color: model.color }} className="font-semibold">{model.label}</span>
                        {isFirst && <span className="text-[#ffd700] text-[8px]">★ Best</span>}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className="px-1.5 py-0.5 rounded text-[9px]"
                        style={{ backgroundColor: `${model.color}15`, color: model.color }}
                      >
                        {model.type === "ml" ? "ML" : "Baseline"}
                      </span>
                    </td>
                    {METRICS_META.map((m) => {
                      const v = row[m.key];
                      const allVals = BENCHMARK.map((d) => d[m.key]);
                      const minV = Math.min(...allVals);
                      const isBest = v === minV;
                      return (
                        <td key={m.key} className={`px-3 py-2.5 text-right ${isBest ? "text-[#00e87a] font-bold" : "text-[#8a9ab0]"}`}>
                          {typeof v === "number" ? v.toFixed(m.key === "mae" ? 3 : 2) : v}
                          <span className="text-[9px] text-[#3a5a7a] ml-0.5">{m.unit}</span>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

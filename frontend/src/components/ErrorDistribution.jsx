import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";

/**
 * ErrorDistribution — Per-point geodesic error across the gap.
 * Also shows mean error reference lines.
 */
export default function ErrorDistribution({ geoErrorData, modelType = "gru" }) {
  if (!geoErrorData) return null;

  const baselineErrors = geoErrorData.baseline || [];
  const modelErrors = geoErrorData[modelType] || [];
  const maxLen = Math.max(baselineErrors.length, modelErrors.length);
  if (maxLen === 0) return null;

  const data = Array.from({ length: maxLen }, (_, i) => ({
    point: i + 1,
    Baseline: baselineErrors[i] != null ? +baselineErrors[i].toFixed(4) : 0,
    [modelType.toUpperCase()]: modelErrors[i] != null ? +modelErrors[i].toFixed(4) : 0,
  }));

  const meanBaseline =
    baselineErrors.length > 0
      ? baselineErrors.reduce((a, b) => a + b, 0) / baselineErrors.length
      : null;
  const meanModel =
    modelErrors.length > 0
      ? modelErrors.reduce((a, b) => a + b, 0) / modelErrors.length
      : null;

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-[#0a1828] border border-[#0e2040] rounded p-2 font-mono text-[10px]">
        <p className="text-[#3a5a7a] mb-1">Gap point {label}</p>
        {payload.map((p) => (
          <p key={p.name} style={{ color: p.stroke || p.fill }}>
            {p.name}: {p.value} km
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-[#0a1828] border border-[#0e2040] rounded-md p-4">
      <div className="flex items-center justify-between mb-4">
        <p className="font-mono text-[10px] text-[#3a5a7a] uppercase tracking-widest">
          Geodesic Error per Gap Point
        </p>
        <div className="flex gap-4 font-mono text-[10px]">
          {meanBaseline != null && (
            <span className="text-[#f5a623]">
              Baseline mean: {meanBaseline.toFixed(3)} km
            </span>
          )}
          {meanModel != null && (
            <span className="text-[#00c8ff]">
              {modelType.toUpperCase()} mean: {meanModel.toFixed(3)} km
            </span>
          )}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 5, right: 8, bottom: 5, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0e2040" />
          <XAxis
            dataKey="point"
            tick={{ fill: "#3a5a7a", fontSize: 9, fontFamily: "monospace" }}
          />
          <YAxis
            tick={{ fill: "#3a5a7a", fontSize: 9, fontFamily: "monospace" }}
            width={48}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 10, fontFamily: "monospace" }} />
          {meanBaseline != null && (
            <ReferenceLine
              y={meanBaseline}
              stroke="#f5a623"
              strokeDasharray="4 2"
              strokeOpacity={0.6}
            />
          )}
          {meanModel != null && (
            <ReferenceLine
              y={meanModel}
              stroke="#00c8ff"
              strokeDasharray="4 2"
              strokeOpacity={0.6}
            />
          )}
          <Bar dataKey="Baseline" fill="#f5a62344" stroke="#f5a623" strokeWidth={1} />
          <Bar
            dataKey={modelType.toUpperCase()}
            fill="#00c8ff33"
            stroke="#00c8ff"
            strokeWidth={1}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
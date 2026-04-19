import {
  RadarChart, PolarGrid, PolarAngleAxis,
  Radar, ResponsiveContainer, Legend, Tooltip
} from "recharts";

/**
 * ModelComparison — Spider/radar chart comparing Baseline vs LSTM vs GRU.
 * Uses inverted/normalized scores so "higher = better" on the chart.
 */
export default function ModelComparison({ lstmMetrics, gruMetrics, baselineMetrics }) {
  if (!lstmMetrics && !gruMetrics) return null;

  const safeVal = (obj, key, scale = 1) => {
    const v = obj?.[key];
    return v != null ? Math.min(100, parseFloat((scale / (v + 0.0001)).toFixed(2))) : 0;
  };

  const dimensions = [
    { key: "mean_geodesic_error_km", label: "Geo Accuracy", scale: 0.01 },
    { key: "lat_mae", label: "Lat Accuracy", scale: 0.0001 },
    { key: "lon_mae", label: "Lon Accuracy", scale: 0.0001 },
    { key: "path_length_error_km", label: "Path Accuracy", scale: 0.1 },
    { key: "lat_rmse", label: "RMSE Lat", scale: 0.0001 },
  ];

  const data = dimensions.map(({ key, label, scale }) => ({
    dimension: label,
    Baseline: safeVal(baselineMetrics, key, scale),
    LSTM: safeVal(lstmMetrics, key, scale),
    GRU: safeVal(gruMetrics, key, scale),
  }));

  return (
    <div className="bg-radar-panel border border-radar-border rounded p-4">
      <h3 className="font-display font-semibold text-xs tracking-widest uppercase text-radar-muted mb-4">
        Model Comparison (Higher = Better)
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data}>
          <PolarGrid stroke="#0f2847" />
          <PolarAngleAxis dataKey="dimension" tick={{ fill: "#4a6b8a", fontSize: 10, fontFamily: "JetBrains Mono" }} />
          <Radar name="Baseline" dataKey="Baseline" stroke="#ffaa00" fill="#ffaa00" fillOpacity={0.1} />
          <Radar name="LSTM" dataKey="LSTM" stroke="#00d4ff" fill="#00d4ff" fillOpacity={0.15} />
          <Radar name="GRU" dataKey="GRU" stroke="#00ff88" fill="#00ff88" fillOpacity={0.1} />
          <Legend wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono" }} />
          <Tooltip
            contentStyle={{ background: "#0a1628", border: "1px solid #0f2847", borderRadius: 4, fontSize: 11 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
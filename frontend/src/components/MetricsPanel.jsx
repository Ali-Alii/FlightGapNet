/**
 * MetricsPanel — All-model metrics comparison table.
 */

const ALL_MODELS = [
  { id: "great_circle", label: "GCircle", color: "#6b7280" },
  { id: "last_hold",    label: "LastHold", color: "#8b5cf6" },
  { id: "const_vel",   label: "ConstVel", color: "#f59e0b" },
  { id: "kalman",      label: "Kalman",   color: "#06b6d4" },
  { id: "lstm",        label: "LSTM",     color: "#00c8ff" },
  { id: "gru",         label: "GRU",      color: "#00e87a" },
];

const ROWS = [
  { key: "mean_geodesic_error_km", label: "Mean Geodesic",   unit: "km", dec: 3 },
  { key: "p90_geodesic_error_km",  label: "P90 Geodesic",    unit: "km", dec: 3 },
  { key: "max_geodesic_error_km",  label: "Max Geodesic",    unit: "km", dec: 2 },
  { key: "lat_mae",                label: "Latitude MAE",    unit: "°",  dec: 5 },
  { key: "lon_mae",                label: "Longitude MAE",   unit: "°",  dec: 5 },
  { key: "path_length_error_km",   label: "Path Length Err", unit: "km", dec: 3 },
  { key: "altitude_mae_m",         label: "Altitude MAE",    unit: "m",  dec: 1 },
];

const fmt = (v, dec) => (v != null && !isNaN(v) ? v.toFixed(dec) : "—");

export default function MetricsPanel({ metrics, modelType = "gru" }) {
  if (!metrics) return null;

  const baseline = metrics.baseline || {};
  const model = metrics[modelType] || {};

  const pct = (b, m) => {
    if (b == null || m == null || b === 0) return null;
    return (((b - m) / b) * 100).toFixed(1);
  };

  const modelMeta = ALL_MODELS.find((m) => m.id === modelType);

  return (
    <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <p className="font-mono text-[10px] text-[#3a5a7a] uppercase tracking-widest">
          Evaluation Metrics
        </p>
        {modelMeta && (
          <span
            className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded"
            style={{ backgroundColor: `${modelMeta.color}15`, color: modelMeta.color }}
          >
            {modelMeta.label} vs Baseline
          </span>
        )}
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[1fr_75px_75px_48px] gap-2 pb-2 border-b border-[#0d1f35] font-mono text-[9px] text-[#3a5a7a] uppercase tracking-widest">
        <div>Metric</div>
        <div className="text-right">Baseline</div>
        <div className="text-right" style={{ color: modelMeta?.color ?? "#00c8ff" }}>
          {modelType.toUpperCase()}
        </div>
        <div className="text-right">Δ</div>
      </div>

      {ROWS.map(({ key, label, unit, dec }) => {
        const b = baseline[key];
        const m = model[key];
        const improved = m != null && b != null && m < b;
        const degraded = m != null && b != null && m > b;
        const delta = pct(b, m);

        return (
          <div
            key={key}
            className="grid grid-cols-[1fr_75px_75px_48px] gap-2 py-2 border-b border-[#0d1f35]/40 last:border-0 font-mono text-[11px]"
          >
            <div className="text-[#3a5a7a] truncate">{label}</div>
            <div className="text-right text-[#5a7a9a]">
              {fmt(b, dec)}{b != null ? <span className="text-[9px] ml-0.5 text-[#2a4a6a]">{unit}</span> : ""}
            </div>
            <div
              className={`text-right font-semibold ${
                improved ? "text-[#00e87a]" : degraded ? "text-red-400" : "text-[#c8d8ec]"
              }`}
            >
              {fmt(m, dec)}{m != null ? <span className="text-[9px] ml-0.5 opacity-60">{unit}</span> : ""}
            </div>
            <div
              className={`text-right text-[10px] ${
                improved ? "text-[#00e87a]" : degraded ? "text-red-400" : "text-[#3a5a7a]"
              }`}
            >
              {delta != null ? (
                <>
                  {improved ? "↓" : "↑"}{Math.abs(delta)}%
                </>
              ) : "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

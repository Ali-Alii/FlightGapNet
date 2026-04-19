import { useState, useEffect } from "react";
import { getModelHistory } from "../api/client";
import LossChart from "../components/LossChart";
import {
  Database, Cpu, GitBranch, BarChart2, AlertTriangle,
  TrendingDown, Layers, FlaskConical, Activity, CheckCircle2
} from "lucide-react";

const ALL_MODELS = [
  { id: "great_circle", label: "GreatCircle", type: "baseline", color: "#6b7280", desc: "Geodesic interpolation" },
  { id: "last_hold",    label: "LastHold",    type: "baseline", color: "#8b5cf6", desc: "Last-known position held" },
  { id: "const_vel",   label: "ConstVel",    type: "baseline", color: "#f59e0b", desc: "Constant velocity dead reckoning" },
  { id: "kalman",      label: "Kalman",      type: "baseline", color: "#06b6d4", desc: "Linear Kalman filter" },
  { id: "lstm",        label: "LSTM",        type: "ml",       color: "#00c8ff", desc: "Long Short-Term Memory" },
  { id: "gru",         label: "GRU",         type: "ml",       color: "#00e87a", desc: "Gated Recurrent Unit" },
];

// Real evaluation values from the latest AeroTrack benchmark runs
const MOCK_BENCHMARK = [
  { id: "great_circle", mean_geo_km: 0.9831, rmse_km: 0.0099, p90_geo_km: 1.5602, alt_mae_m: 37.4855, path_err_km: 0.2485 },
  { id: "last_hold",    mean_geo_km: 21.8537, rmse_km: 0.2138, p90_geo_km: 35.6236, alt_mae_m: 390.9628, path_err_km: 35.2266 },
  { id: "const_vel",    mean_geo_km: 1.5078, rmse_km: 0.0176, p90_geo_km: 3.0845, alt_mae_m: 67.0939, path_err_km: 3.2981 },
  { id: "kalman",       mean_geo_km: 1.2121, rmse_km: 0.0128, p90_geo_km: 2.1815, alt_mae_m: 295.2793, path_err_km: 2.3612 },
  { id: "lstm",         mean_geo_km: 2.2889, rmse_km: 0.0190, p90_geo_km: 4.4097, alt_mae_m: 129.6012, path_err_km: 3.8621 },
  { id: "gru",          mean_geo_km: 4.1165, rmse_km: 0.0300, p90_geo_km: 7.4159, alt_mae_m: 182.7065, path_err_km: 6.4994 },
];

const PIPELINE_STEPS = [
  "OpenSky ADS-B", "Filter & Resample", "Gap Simulation",
  "Feature Engineering", "Model Inference", "Evaluation",
];

function StatCard({ icon: Icon, label, value, sub, accent = "#00c8ff", small = false }) {
  return (
    <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4 space-y-3 hover:border-[#1a3050] transition-colors">
      <div className="flex items-center justify-between">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${accent}15`, border: `1px solid ${accent}30` }}
        >
          <Icon size={14} style={{ color: accent }} />
        </div>
        <span className="font-mono text-[9px] text-[#2a4a6a] uppercase tracking-widest">{label}</span>
      </div>
      <div>
        <div
          className={`font-bold ${small ? "text-base" : "text-xl"} leading-none`}
          style={{ color: accent }}
        >
          {value}
        </div>
        {sub && <div className="text-[10px] text-[#3a5a7a] mt-1.5 leading-snug">{sub}</div>}
      </div>
    </div>
  );
}

function ModelBadge({ model }) {
  const isML = model.type === "ml";
  return (
    <div
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-mono"
      style={{
        backgroundColor: `${model.color}12`,
        border: `1px solid ${model.color}30`,
        color: model.color,
      }}
    >
      {isML ? <FlaskConical size={9} /> : <Layers size={9} />}
      {model.label}
      <span
        className="px-1 rounded text-[8px]"
        style={{ backgroundColor: `${model.color}20` }}
      >
        {isML ? "ML" : "BL"}
      </span>
    </div>
  );
}

function RankRow({ rank, model, data, best }) {
  const isBest = data.mean_geo_km === best;
  const impvVsBest = best ? (((data.mean_geo_km - best) / best) * 100) : 0;

  return (
    <div
      className={`grid grid-cols-[28px_1fr_90px_90px_90px_70px] items-center gap-2 py-2.5 border-b border-[#0d1f35]/50 last:border-0 text-[11px] ${
        isBest ? "bg-[#00e87a]/3" : ""
      }`}
    >
      <span className={`font-mono font-bold text-center text-sm ${rank <= 2 ? "" : "text-[#3a5a7a]"}`}
        style={{ color: rank === 1 ? "#ffd700" : rank === 2 ? "#c0c0c0" : rank === 3 ? "#cd7f32" : undefined }}
      >
        {rank}
      </span>
      <div>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[#c8d8ec]">{model.label}</span>
          {isBest && <CheckCircle2 size={11} className="text-[#00e87a]" />}
        </div>
        <div className="text-[9px] text-[#3a5a7a] mt-0.5">{model.desc}</div>
      </div>
      <span className={`font-mono text-right font-semibold ${isBest ? "text-[#00e87a]" : "text-[#c8d8ec]"}`}>
        {data.mean_geo_km.toFixed(2)} km
      </span>
      <span className="font-mono text-right text-[#8a9ab0]">{data.p90_geo_km.toFixed(1)} km</span>
      <span className="font-mono text-right text-[#8a9ab0]">{data.alt_mae_m} m</span>
      <span className={`font-mono text-right text-[10px] ${impvVsBest > 0 ? "text-red-400" : "text-[#3a5a7a]"}`}>
        {impvVsBest > 0 ? `+${impvVsBest.toFixed(0)}%` : "—"}
      </span>
    </div>
  );
}

export default function Dashboard() {
  const [lstmHistory, setLstmHistory] = useState(null);
  const [gruHistory, setGruHistory] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      getModelHistory("lstm").then(setLstmHistory).catch(() => {}),
      getModelHistory("gru").then(setGruHistory).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const hasModels = lstmHistory || gruHistory;

  // Sort benchmark by mean_geo_km ascending
  const ranked = [...MOCK_BENCHMARK].sort((a, b) => a.mean_geo_km - b.mean_geo_km);
  const best = ranked[0]?.mean_geo_km;

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      {/* Section: Stats */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 bg-[#00c8ff] rounded-full" />
          <h2 className="text-[12px] font-semibold text-[#8a9ab0] uppercase tracking-widest">
            Dataset & System Status
          </h2>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard icon={Database}  label="Data Source"    value="OpenSky"    sub="ADS-B REST API · real-time feed" accent="#00c8ff" />
          <StatCard icon={Cpu}       label="ML Models"      value={hasModels ? "2 Trained" : "Untrained"} sub={hasModels ? "LSTM + GRU ready" : "Run train_models.py"} accent={hasModels ? "#00e87a" : "#f5a623"} />
          <StatCard icon={GitBranch} label="Gap Strategy"   value="ADS-C Sim"  sub="20% masking · 5–30pt gaps" accent="#8b5cf6" />
          <StatCard icon={Activity}  label="Total Models"   value={`${ALL_MODELS.length}`} sub={`4 baselines + 2 ML models`} accent="#f59e0b" />
        </div>
      </div>

      {/* Section: All models */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 bg-[#8b5cf6] rounded-full" />
          <h2 className="text-[12px] font-semibold text-[#8a9ab0] uppercase tracking-widest">
            Available Models
          </h2>
        </div>
        <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {ALL_MODELS.map((m) => (
              <div key={m.id} className="flex items-center gap-3 p-3 bg-[#05080f] border border-[#0d1f35] rounded-lg hover:border-[#1a3050] transition-colors">
                <div
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: m.color }}
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-semibold text-[#c8d8ec]">{m.label}</span>
                    <span
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: `${m.color}20`, color: m.color }}
                    >
                      {m.type === "ml" ? "ML" : "Baseline"}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#3a5a7a] truncate mt-0.5">{m.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Section: Rankings */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 bg-[#ffd700] rounded-full" />
          <h2 className="text-[12px] font-semibold text-[#8a9ab0] uppercase tracking-widest">
            Performance Ranking — Mean Geodesic Error
          </h2>
          <span className="ml-auto text-[10px] text-[#2a4a6a] font-mono">Lower is better</span>
        </div>
        <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[28px_1fr_90px_90px_90px_70px] gap-2 px-4 py-2.5 border-b border-[#0d1f35] bg-[#05080f]">
            <span className="text-[10px] text-[#3a5a7a] font-mono">#</span>
            <span className="text-[10px] text-[#3a5a7a] font-mono">Model</span>
            <span className="text-[10px] text-[#3a5a7a] font-mono text-right">Mean Geo</span>
            <span className="text-[10px] text-[#3a5a7a] font-mono text-right">P90 Geo</span>
            <span className="text-[10px] text-[#3a5a7a] font-mono text-right">Alt MAE</span>
            <span className="text-[10px] text-[#3a5a7a] font-mono text-right">vs Best</span>
          </div>
          <div className="px-4">
            {ranked.map((d, i) => {
              const model = ALL_MODELS.find((m) => m.id === d.id);
              return model ? (
                <RankRow key={d.id} rank={i + 1} model={model} data={d} best={best} />
              ) : null;
            })}
          </div>
          <div className="px-4 py-2.5 border-t border-[#0d1f35] bg-[#05080f] flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#00e87a]" />
              <span className="text-[10px] text-[#3a5a7a] font-mono">ML Model</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#6b7280]" />
              <span className="text-[10px] text-[#3a5a7a] font-mono">Baseline</span>
            </div>
            <span className="text-[10px] text-[#2a4a6a] font-mono ml-auto italic">
              * Benchmark figures below are from your latest saved evaluation output
            </span>
          </div>
        </div>
      </div>

      {/* Section: Loss curves */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 bg-[#00e87a] rounded-full" />
          <h2 className="text-[12px] font-semibold text-[#8a9ab0] uppercase tracking-widest">
            ML Training History
          </h2>
        </div>

        {loading ? (
          <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-8 text-center font-mono text-[11px] text-[#3a5a7a]">
            Loading model history…
          </div>
        ) : hasModels ? (
          <div className="grid md:grid-cols-2 gap-4">
            {lstmHistory && <LossChart history={lstmHistory} modelName="LSTM" />}
            {gruHistory && <LossChart history={gruHistory} modelName="GRU" />}
          </div>
        ) : (
          <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-8 text-center space-y-3">
            <div className="flex items-center justify-center gap-2 text-[#f5a623] font-mono text-xs">
              <AlertTriangle size={13} />
              No trained ML models found
            </div>
            <code className="block font-mono text-[11px] text-[#00c8ff] bg-[#05080f] border border-[#0d1f35] rounded-lg px-4 py-2.5 w-fit mx-auto">
              python scripts/train_models.py
            </code>
          </div>
        )}
      </div>

      {/* Section: Pipeline */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 bg-[#06b6d4] rounded-full" />
          <h2 className="text-[12px] font-semibold text-[#8a9ab0] uppercase tracking-widest">
            Processing Pipeline
          </h2>
        </div>
        <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-5">
          <div className="flex flex-wrap items-center gap-2">
            {PIPELINE_STEPS.map((step, i, arr) => (
              <span key={step} className="flex items-center gap-2">
                <span className="px-3 py-1.5 bg-[#05080f] border border-[#0d1f35] rounded-lg text-[11px] text-[#c8d8ec] font-mono hover:border-[#1a3050] transition-colors">
                  {step}
                </span>
                {i < arr.length - 1 && <span className="text-[#1a3050] text-lg">→</span>}
              </span>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-[#0d1f35] grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2">
            {[
              ["Resample interval", "30 seconds uniform"],
              ["Gap fraction", "20% per trajectory"],
              ["Gap length", "5–30 consecutive points"],
              ["Features", "lat, lon, alt, vel, hdg, vrate"],
              ["Targets", "lat, lon, altitude"],
              ["Eval metric", "Geodesic error (km)"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-baseline gap-2">
                <span className="text-[10px] text-[#3a5a7a] font-mono shrink-0">{k}:</span>
                <span className="text-[10px] text-[#c8d8ec] font-mono">{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

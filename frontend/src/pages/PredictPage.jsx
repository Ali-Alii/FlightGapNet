import { useState, useEffect } from "react";
import SearchBar from "../components/SearchBar";
import TrajectoryMap from "../components/TrajectoryMap";
import MetricsPanel from "../components/MetricsPanel";
import ErrorDistribution from "../components/ErrorDistribution";
import RouteAnalytics from "../components/RouteAnalytics";
import { predictTrajectory, computeRouteAnalytics, fetchAvailableAircraft } from "../api/client";
import {
  AlertTriangle, ChevronRight, Layers, FlaskConical,
  Play, RotateCcw, Info
} from "lucide-react";

const MODELS = [
  { id: "great_circle", label: "GreatCircle", type: "baseline", color: "#6b7280", desc: "Geodesic interpolation" },
  { id: "last_hold",    label: "LastHold",    type: "baseline", color: "#8b5cf6", desc: "Hold last position" },
  { id: "const_vel",   label: "ConstVel",    type: "baseline", color: "#f59e0b", desc: "Constant velocity" },
  { id: "kalman",      label: "Kalman",       type: "baseline", color: "#06b6d4", desc: "Kalman filter" },
  { id: "lstm",        label: "LSTM",         type: "ml",       color: "#00c8ff", desc: "Long Short-Term Memory" },
  { id: "gru",         label: "GRU",          type: "ml",       color: "#00e87a", desc: "Gated Recurrent Unit" },
];

function ModelCard({ model, selected, onClick }) {
  const isML = model.type === "ml";
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex flex-col gap-1.5 p-3 rounded-xl border text-left transition-all ${
        selected
          ? "border-opacity-60 bg-opacity-10"
          : "border-[#0d1f35] hover:border-[#1a3050] bg-[#05080f]"
      }`}
      style={
        selected
          ? {
              borderColor: model.color,
              backgroundColor: `${model.color}10`,
            }
          : {}
      }
    >
      <div className="flex items-center gap-2">
        {isML ? (
          <FlaskConical size={11} style={{ color: selected ? model.color : "#3a5a7a" }} />
        ) : (
          <Layers size={11} style={{ color: selected ? model.color : "#3a5a7a" }} />
        )}
        <span
          className="text-[11px] font-semibold"
          style={{ color: selected ? model.color : "#8a9ab0" }}
        >
          {model.label}
        </span>
        <span
          className="ml-auto text-[8px] px-1 rounded"
          style={{
            backgroundColor: selected ? `${model.color}25` : "#0d1f35",
            color: selected ? model.color : "#3a5a7a",
          }}
        >
          {isML ? "ML" : "BL"}
        </span>
      </div>
      <div className="text-[9px] text-[#3a5a7a] font-mono">{model.desc}</div>
    </button>
  );
}

export default function PredictPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [modelType, setModelType] = useState("gru");
  const [availableAircraft, setAvailableAircraft] = useState([]);

  useEffect(() => {
    fetchAvailableAircraft()
      .then((data) => setAvailableAircraft(data.icao24_list || []))
      .catch(() => {});
  }, []);

  const handleSearch = async (icao24) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setAnalytics(null);
    try {
      const data = await predictTrajectory({ icao24, model_type: modelType, steps_ahead: 10 });
      setResult(data);
      if (data.full_track?.length) {
        const an = await computeRouteAnalytics(data.full_track);
        setAnalytics(an);
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail || err.message || "Request failed. Is the backend running?";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const selectedModel = MODELS.find((m) => m.id === modelType);

  return (
    <div className="p-6 space-y-5 max-w-7xl">
      {/* Config Panel */}
      <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-5 space-y-5">
        {/* Model selector */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1 h-4 bg-[#00c8ff] rounded-full" />
            <p className="text-[11px] font-semibold text-[#8a9ab0] uppercase tracking-widest font-mono">
              Select Model
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            {MODELS.map((m) => (
              <ModelCard
                key={m.id}
                model={m}
                selected={modelType === m.id}
                onClick={() => setModelType(m.id)}
              />
            ))}
          </div>
          {selectedModel && (
            <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-[#05080f] border border-[#0d1f35] rounded-lg">
              <Info size={11} style={{ color: selectedModel.color }} />
              <span className="text-[10px] font-mono text-[#3a5a7a]">
                Selected: <span style={{ color: selectedModel.color }}>{selectedModel.label}</span>
                {" · "}{selectedModel.desc}
                {" · "}<span className="text-[#2a4a6a]">{selectedModel.type === "ml" ? "Machine Learning model" : "Classical baseline"}</span>
              </span>
            </div>
          )}
        </div>

        {/* Aircraft input */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1 h-4 bg-[#8b5cf6] rounded-full" />
            <p className="text-[11px] font-semibold text-[#8a9ab0] uppercase tracking-widest font-mono">
              Aircraft ICAO24
            </p>
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <SearchBar onSearch={handleSearch} loading={loading} />
            </div>
          </div>
        </div>

        {/* Quick aircraft select */}
        {availableAircraft.length > 0 && (
          <div>
            <p className="text-[10px] font-mono text-[#2a4a6a] uppercase tracking-widest mb-2">
              Available in dataset ({availableAircraft.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {availableAircraft.slice(0, 20).map((id) => (
                <button
                  key={id}
                  onClick={() => handleSearch(id)}
                  disabled={loading}
                  className="flex items-center gap-1 px-2.5 py-1 bg-[#05080f] border border-[#0d1f35] rounded-lg font-mono text-[11px] text-[#3a5a7a] hover:text-[#00c8ff] hover:border-[#00c8ff]/30 transition-all disabled:opacity-40"
                >
                  {id}
                  <ChevronRight size={9} />
                </button>
              ))}
              {availableAircraft.length > 20 && (
                <span className="text-[10px] text-[#2a4a6a] font-mono px-2 py-1">
                  +{availableAircraft.length - 20} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-8 text-center">
          <div className="inline-flex items-center gap-3 text-[#00c8ff] font-mono text-[12px]">
            <Play size={14} className="animate-pulse" />
            Running {selectedModel?.label} inference…
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-start gap-3 border border-red-900/40 bg-red-950/15 rounded-xl p-4">
          <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-mono text-[12px] font-semibold text-red-400">Prediction Failed</p>
            <p className="font-mono text-[11px] text-red-400/70 mt-1">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-[#3a5a7a] hover:text-[#c8d8ec] transition-colors"
          >
            <RotateCcw size={13} />
          </button>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-4">
          {/* Result header */}
          <div className="flex items-center gap-3">
            <div className="w-1 h-4 rounded-full" style={{ backgroundColor: selectedModel?.color ?? "#00c8ff" }} />
            <span className="text-[12px] font-semibold text-[#c8d8ec]">
              Results — <span style={{ color: selectedModel?.color }}>{selectedModel?.label}</span>
            </span>
            <span className="font-mono text-[11px] text-[#3a5a7a]">
              ICAO24: <span className="text-[#00c8ff]">{result.icao24}</span>
              {" · "}Gap: {result.gap_region?.length} pts @ idx {result.gap_region?.start_idx}
            </span>
          </div>

          {/* Map */}
          <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4">
            <p className="font-mono text-[10px] text-[#3a5a7a] uppercase tracking-widest mb-3">
              Trajectory Visualization
            </p>
            <TrajectoryMap data={result} />
          </div>

          {/* Metrics + analytics */}
          <div className="grid md:grid-cols-2 gap-4">
            <MetricsPanel metrics={result.metrics} modelType={result.model_type} />
            <RouteAnalytics analytics={analytics} />
          </div>

          {/* Error distribution */}
          <ErrorDistribution
            geoErrorData={result.geo_error_distribution}
            modelType={result.model_type}
          />
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import PredictPage from "./pages/PredictPage";
import BenchmarkPage from "./pages/BenchmarkPage";
import {
  LayoutDashboard,
  Activity,
  BarChart3,
  Plane,
  ChevronRight,
  Radio,
} from "lucide-react";

const NAV = [
  { id: "dashboard", icon: LayoutDashboard, label: "Dashboard", sub: "Overview & Stats" },
  { id: "benchmark", icon: BarChart3, label: "Benchmark", sub: "Model Comparison" },
  { id: "predict", icon: Activity, label: "Test Model", sub: "Run Predictions" },
];

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [sideCollapsed, setSideCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-[#05080f] text-[#c8d8ec] flex">
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,180,255,0.06) 0%, transparent 60%)`,
        }}
      />

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 bottom-0 z-50 flex flex-col border-r border-[#0d1f35] bg-[#05080f] transition-all duration-300 ${
          sideCollapsed ? "w-16" : "w-56"
        }`}
      >
        <div className="flex items-center gap-3 px-4 py-4 border-b border-[#0d1f35] h-14">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-[#0085cc] to-[#00c8ff] flex items-center justify-center shrink-0">
            <Plane size={13} className="text-white" strokeWidth={2.5} />
          </div>
          {!sideCollapsed && (
            <div>
              <div className="font-bold text-[13px] text-white tracking-tight leading-none">AeroTrack</div>
              <div className="text-[9px] text-[#2a4a6a] font-mono tracking-widest uppercase mt-0.5">Trajectory AI</div>
            </div>
          )}
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map(({ id, icon: Icon, label, sub }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group relative ${
                page === id
                  ? "bg-[#0d2040] text-white"
                  : "text-[#3a5a7a] hover:text-[#c8d8ec] hover:bg-[#0d1f35]"
              }`}
            >
              <Icon size={16} className={`shrink-0 ${page === id ? "text-[#00c8ff]" : ""}`} />
              {!sideCollapsed && (
                <div className="text-left min-w-0">
                  <div className={`text-[12px] font-semibold leading-none ${page === id ? "text-white" : ""}`}>{label}</div>
                  <div className="text-[10px] text-[#2a4a6a] mt-0.5 truncate">{sub}</div>
                </div>
              )}
              {page === id && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[#00c8ff] rounded-r-full" />
              )}
            </button>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-[#0d1f35]">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[#00e87a] shrink-0" />
            {!sideCollapsed && (
              <span className="font-mono text-[10px] text-[#2a4a6a]">System Online</span>
            )}
          </div>
        </div>

        <button
          onClick={() => setSideCollapsed(!sideCollapsed)}
          className="absolute -right-3 top-16 w-6 h-6 bg-[#0d1f35] border border-[#1a3050] rounded-full flex items-center justify-center text-[#3a5a7a] hover:text-[#c8d8ec] transition-colors"
        >
          <ChevronRight size={11} className={`transition-transform ${sideCollapsed ? "" : "rotate-180"}`} />
        </button>
      </aside>

      {/* Main */}
      <div className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${sideCollapsed ? "ml-16" : "ml-56"}`}>
        <header className="sticky top-0 z-40 h-14 border-b border-[#0d1f35] bg-[#05080f]/95 backdrop-blur-sm flex items-center px-6">
          <h1 className="text-[14px] font-semibold text-white">{NAV.find((n) => n.id === page)?.label}</h1>
          <div className="ml-auto flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#0d1f35] border border-[#1a3050] rounded-full">
              <Radio size={10} className="text-[#00e87a]" />
              <span className="font-mono text-[10px] text-[#3a6a4a]">ADS-B Live</span>
            </div>
          </div>
        </header>

        <main className="flex-1 relative z-10">
          {page === "dashboard" && <Dashboard />}
          {page === "benchmark" && <BenchmarkPage />}
          {page === "predict" && <PredictPage />}
        </main>
      </div>
    </div>
  );
}

import {
  AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Route, Mountain, Zap, Hash } from "lucide-react";

export default function RouteAnalytics({ analytics }) {
  if (!analytics) {
    return (
      <div className="bg-[#0a1828] border border-[#0e2040] rounded-md p-4 flex items-center justify-center">
        <p className="font-mono text-[11px] text-[#3a5a7a]">Route analytics unavailable</p>
      </div>
    );
  }

  const stats = [
    {
      icon: Route,
      label: "Path Length",
      value: `${analytics.path_length_km} km`,
      color: "#00c8ff",
    },
    {
      icon: Mountain,
      label: "Avg Altitude",
      value: `${Math.round(analytics.avg_altitude_m).toLocaleString()} m`,
      color: "#00e87a",
    },
    {
      icon: Zap,
      label: "Fuel Index",
      value: analytics.fuel_proxy_index?.toFixed(1),
      color: "#f5a623",
    },
    {
      icon: Hash,
      label: "Points",
      value: analytics.point_count,
      color: "#b8d0e8",
    },
  ];

  const altData =
    analytics.altitude_profile?.map((alt, i) => ({
      idx: i,
      alt: Math.round(alt),
    })) || [];

  return (
    <div className="bg-[#0a1828] border border-[#0e2040] rounded-md p-4 space-y-4">
      <p className="font-mono text-[10px] text-[#3a5a7a] uppercase tracking-widest">
        Route Analytics
      </p>

      <div className="grid grid-cols-2 gap-2">
        {stats.map(({ icon: Icon, label, value, color }) => (
          <div
            key={label}
            className="bg-[#060d18] border border-[#0e2040] rounded p-3 space-y-1"
          >
            <div className="flex items-center gap-1.5">
              <Icon size={10} style={{ color }} />
              <span className="font-mono text-[9px] text-[#3a5a7a] uppercase tracking-widest">
                {label}
              </span>
            </div>
            <div className="font-mono font-bold text-sm" style={{ color }}>
              {value ?? "—"}
            </div>
          </div>
        ))}
      </div>

      {altData.length > 0 && (
        <>
          <p className="font-mono text-[10px] text-[#3a5a7a]">Altitude profile (m)</p>
          <ResponsiveContainer width="100%" height={110}>
            <AreaChart data={altData} margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0e2040" />
              <XAxis dataKey="idx" hide />
              <YAxis
                tick={{ fill: "#3a5a7a", fontSize: 9, fontFamily: "monospace" }}
                width={44}
              />
              <Tooltip
                contentStyle={{
                  background: "#0a1828",
                  border: "1px solid #0e2040",
                  borderRadius: 4,
                  fontSize: 10,
                  fontFamily: "monospace",
                }}
                formatter={(v) => [`${v.toLocaleString()} m`, "Altitude"]}
              />
              <Area
                type="monotone"
                dataKey="alt"
                stroke="#00e87a"
                fill="#00e87a1a"
                strokeWidth={1.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
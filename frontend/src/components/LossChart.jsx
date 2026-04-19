import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { AlertTriangle } from "lucide-react";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#080e1a] border border-[#0d1f35] rounded-lg p-3 shadow-xl">
      <p className="text-[10px] text-[#3a5a7a] font-mono mb-2">Epoch {label}</p>
      {payload.map((p) => (
        <p key={p.name} className="text-[11px] font-mono" style={{ color: p.color }}>
          {p.name}: <span className="font-bold">{p.value}</span>
        </p>
      ))}
    </div>
  );
};

export default function LossChart({ history, modelName = "LSTM" }) {
  if (!history?.train_losses) return null;

  const valEqualsTrainBug =
    history.val_losses?.length > 0 &&
    history.train_losses.every((v, i) => v === history.val_losses[i]);

  const data = history.train_losses.map((tl, i) => ({
    epoch: i + 1,
    train: +tl.toFixed(6),
    val: +(history.val_losses?.[i] ?? 0).toFixed(6),
  }));

  const accentColor = modelName === "LSTM" ? "#00c8ff" : "#00e87a";

  return (
    <div className="bg-[#080e1a] border border-[#0d1f35] rounded-xl p-4">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: accentColor }} />
          <p className="font-mono text-[11px] font-semibold text-[#8a9ab0]">{modelName} Loss Curves</p>
        </div>
        {history.best_epoch && (
          <span className="font-mono text-[10px] text-[#00e87a]">
            Best @ epoch {history.best_epoch}
          </span>
        )}
      </div>

      {valEqualsTrainBug && (
        <div className="flex items-center gap-2 bg-[#f5a623]/8 border border-[#f5a623]/20 rounded-lg px-3 py-2 mb-3 font-mono text-[10px] text-[#f5a623]">
          <AlertTriangle size={11} />
          Val loss mirrors train — validation set may have been empty.
        </div>
      )}

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0d1f35" />
          <XAxis dataKey="epoch" tick={{ fill: "#3a5a7a", fontSize: 9, fontFamily: "monospace" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#3a5a7a", fontSize: 9, fontFamily: "monospace" }} width={55} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 10, fontFamily: "monospace", color: "#3a5a7a" }} />
          <Line type="monotone" dataKey="train" stroke={accentColor} strokeWidth={2} dot={false} name="Train" />
          {!valEqualsTrainBug && (
            <Line type="monotone" dataKey="val" stroke="#ff4d6d" strokeWidth={2} dot={false} name="Val" strokeDasharray="4 2" />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

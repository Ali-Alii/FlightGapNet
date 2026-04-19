// SearchBar.jsx
import { useState } from "react";
import { Search, Loader2 } from "lucide-react";

export default function SearchBar({ onSearch, loading, placeholder = "e.g. 39de46, 4bc8c4..." }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim().toLowerCase();
    if (trimmed) onSearch(trimmed);
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <Search
          size={13}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[#3a5a7a]"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-[#060d18] border border-[#0e2040] rounded px-9 py-2 font-mono text-[12px] text-[#b8d0e8] placeholder-[#3a5a7a] focus:outline-none focus:border-[#00c8ff]/40 transition-colors"
        />
      </div>
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="px-5 py-2 bg-[#00c8ff]/10 border border-[#00c8ff]/30 rounded font-mono text-[11px] text-[#00c8ff] hover:bg-[#00c8ff]/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-2"
      >
        {loading && <Loader2 size={11} className="animate-spin" />}
        {loading ? "Running..." : "Analyze"}
      </button>
    </form>
  );
}
import { useEffect, useRef, useState } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";

export default function DashboardSearch({ value, onChange, suggestions = [], onSelectSuggestion }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const showSuggestions = open && value.trim().length > 0 && suggestions.length > 0;

  return (
    <div className="relative" ref={containerRef}>
      <MagnifyingGlass
        size={18}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none"
      />
      <input
        type="search"
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="Search area, category, equipment, tag no, parameter, verified by…"
        className="w-full border border-zinc-200 bg-white py-3 pl-10 pr-4 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#002FA7] rounded-lg"
        autoComplete="off"
      />

      {showSuggestions && (
        <ul className="absolute z-20 mt-1 w-full bg-white border border-zinc-200 shadow-lg max-h-64 overflow-y-auto rounded-lg">
          {suggestions.map((item, idx) => (
            <li key={`${item.type}-${item.value}-${idx}`}>
              <button
                type="button"
                className="w-full text-left px-4 py-3 text-sm hover:bg-zinc-50 border-b border-zinc-100 last:border-b-0"
                onClick={() => {
                  onChange(item.value);
                  onSelectSuggestion?.(item);
                  setOpen(false);
                }}
              >
                <span className="font-medium text-zinc-950">{item.label}</span>
                <span className="block text-xs text-zinc-500 mt-0.5">
                  {[item.area, item.category, item.equipment].filter(Boolean).join(" · ")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

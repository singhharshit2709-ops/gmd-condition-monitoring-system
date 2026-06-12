export default function TrendStatsGrid({ stats, parameterLabel }) {
  const items = [
    { label: "Readings", value: stats.count ?? 0 },
    { label: "Latest", value: stats.latest != null ? `${stats.latest}${stats.unit ? ` ${stats.unit}` : ""}` : "—" },
    { label: "Average", value: stats.avg != null ? `${stats.avg.toFixed(2)}${stats.unit ? ` ${stats.unit}` : ""}` : "—" },
    { label: "Min", value: stats.min != null ? `${stats.min}${stats.unit ? ` ${stats.unit}` : ""}` : "—" },
    { label: "Max", value: stats.max != null ? `${stats.max}${stats.unit ? ` ${stats.unit}` : ""}` : "—" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {items.map((item) => (
        <div key={item.label} className="border border-zinc-200 bg-zinc-50/50 rounded-lg p-4">
          <p className="text-[10px] uppercase tracking-[0.15em] text-zinc-500">{item.label}</p>
          <p className="mt-2 text-lg font-mono font-medium text-zinc-950">{item.value}</p>
        </div>
      ))}
      {parameterLabel && (
        <div className="col-span-full text-xs text-zinc-500 mt-1">
          Statistics for: {parameterLabel}
          {stats.latestTime ? ` · Last reading ${new Date(stats.latestTime).toLocaleString("en-GB")}` : ""}
        </div>
      )}
    </div>
  );
}

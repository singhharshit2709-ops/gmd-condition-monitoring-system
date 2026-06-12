import { formatTrendTimestamp } from "@/lib/trendsAnalytics";
import StatusBadge from "@/components/dashboard/StatusBadge";

export default function TrendDataTable({ readings, limit = 15 }) {
  const rows = (readings || []).slice(-limit).reverse();

  if (!rows.length) return null;

  return (
    <div className="overflow-x-auto border border-zinc-200 rounded-lg">
      <table className="w-full text-sm">
        <thead className="bg-zinc-50 text-left">
          <tr>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-zinc-500 font-medium">Time</th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-zinc-500 font-medium">Value</th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-zinc-500 font-medium">Status</th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-zinc-500 font-medium">Verified By</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.timestamp}-${idx}`} className="border-t border-zinc-100 hover:bg-zinc-50/50">
              <td className="px-4 py-2.5 font-mono text-xs text-zinc-600">{formatTrendTimestamp(row.timestamp)}</td>
              <td className="px-4 py-2.5 font-mono font-medium text-zinc-900">
                {row.value}
                {row.unit ? ` ${row.unit}` : ""}
              </td>
              <td className="px-4 py-2.5">
                <StatusBadge status={row.status} />
              </td>
              <td className="px-4 py-2.5 text-zinc-700">{row.verified_by || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

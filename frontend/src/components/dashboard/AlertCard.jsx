import RelativeTime from "@/components/dashboard/RelativeTime";
import StatusBadge from "@/components/dashboard/StatusBadge";
import { getParameterDisplay } from "@/lib/dashboardAnalytics";

export default function AlertCard({ alert, area, onAcknowledge }) {
  const isAlarm = String(alert.status).toUpperCase() === "ALARM";

  return (
    <div
      data-testid="alarm-card"
      className={`border-l-4 p-4 rounded-r-lg ${
        isAlarm ? "border-[#E11D48] bg-red-50/60" : "border-yellow-500 bg-yellow-50/60"
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-mono text-zinc-500">
            <RelativeTime value={alert.timestamp} />
          </p>
          <p className="text-sm font-medium text-zinc-950 mt-1">
            {area} · {alert.equipment}
          </p>
          <p className="text-xs text-zinc-600 mt-0.5">{alert.category || "—"}</p>

          <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-zinc-500 text-xs">Parameter</dt>
              <dd className="font-mono text-zinc-900">{getParameterDisplay(alert)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500 text-xs">Current Value</dt>
              <dd className={`font-mono font-bold ${isAlarm ? "text-[#E11D48]" : "text-yellow-700"}`}>
                {alert.value ?? "—"}
                {alert.unit ? ` ${alert.unit}` : ""}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500 text-xs">Verified By</dt>
              <dd className="text-zinc-900">{alert.verified_by || "—"}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-2 shrink-0">
          <StatusBadge status={alert.status} />
          {alert.id && onAcknowledge && (
            <button
              type="button"
              onClick={() => onAcknowledge(alert.id)}
              className="px-3 py-1.5 bg-zinc-900 text-white text-xs uppercase tracking-[0.12em] hover:bg-zinc-800 rounded-sm"
            >
              Acknowledge
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

import AlertCard from "@/components/dashboard/AlertCard";
import RelativeTime from "@/components/dashboard/RelativeTime";
import StatusBadge from "@/components/dashboard/StatusBadge";
import { getParameterDisplay, resolveReadingArea } from "@/lib/dashboardAnalytics";

function ResolvedAlertBanner({ alert }) {
  return (
    <div className="border border-zinc-200 bg-zinc-50 p-4 rounded-lg">
      <p className="text-xs uppercase tracking-[0.15em] text-zinc-500 mb-2">Most Recent Resolved Alert</p>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-zinc-950">
            {alert.area} · {alert.equipment}
          </p>
          <p className="text-xs text-zinc-600 mt-1">
            {getParameterDisplay(alert)} · {alert.value ?? "—"}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            <RelativeTime value={alert.timestamp} />
          </p>
        </div>
        <StatusBadge status={alert.status} />
      </div>
    </div>
  );
}

export default function RecentAlertsPanel({ alerts, resolvedAlert, lookups, onAcknowledge }) {
  return (
    <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg">
      <div className="mb-5">
        <h3 className="text-xl font-light tracking-tight text-zinc-900">Recent Alerts</h3>
        <p className="text-sm text-zinc-500 mt-1">Active warning and alarm events</p>
      </div>

      {alerts.length === 0 ? (
        <div className="space-y-4">
          <div className="text-center py-10 border border-dashed border-zinc-200 rounded-lg px-4">
            <p className="text-sm font-medium text-zinc-700">No active warnings or alarms.</p>
            <p className="text-xs text-zinc-500 mt-2">No recent alerts requiring attention.</p>
          </div>
          {resolvedAlert && <ResolvedAlertBanner alert={resolvedAlert} />}
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert, idx) => (
            <AlertCard
              key={alert.id || `${alert.equipment}-${alert.parameter}-${idx}`}
              alert={alert}
              area={resolveReadingArea(alert, lookups)}
              onAcknowledge={onAcknowledge}
            />
          ))}
          {resolvedAlert && <ResolvedAlertBanner alert={resolvedAlert} />}
        </div>
      )}
    </section>
  );
}

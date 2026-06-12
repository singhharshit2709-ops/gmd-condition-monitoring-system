import AreaStatusBadge from "@/components/dashboard/AreaStatusBadge";
import RelativeTime from "@/components/dashboard/RelativeTime";
import { DASHBOARD_STATUS } from "@/lib/dashboardAnalytics";

const BORDER = {
  PENDING: "border-zinc-200 hover:border-zinc-300",
  NORMAL: "border-green-200 hover:border-green-300",
  WARNING: "border-yellow-300 hover:border-yellow-400",
  ALARM: "border-red-300 hover:border-red-400",
};

/**
 * Area health summary card — structured for future drill-down:
 * Area → Category → Equipment → Tag → Parameters → Status → Media
 */
export default function AreaCard({ area, onSelect }) {
  const border = BORDER[area.areaStatus] || BORDER.PENDING;
  const pending = !area.hasTodayReadings;

  return (
    <button
      type="button"
      onClick={() => onSelect?.(area)}
      data-testid={`area-health-${area.area.replace(/\s+/g, "-")}`}
      data-area={area.area}
      data-area-status={area.areaStatus}
      className={`text-left bg-white border ${border} p-5 rounded-lg transition-all hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#002FA7]`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <h3 className="text-lg font-medium text-zinc-950">{area.area}</h3>
          <p className="text-xs text-zinc-500 mt-1">
            Last update:{" "}
            {area.lastUpdated ? (
              <RelativeTime value={area.lastUpdated} />
            ) : (
              <span>{area.lastUpdatedLabel}</span>
            )}
          </p>
        </div>
        {!pending && area.healthPercent != null && (
          <span
            className={`text-2xl font-mono font-light shrink-0 ${
              area.healthPercent >= 90
                ? "text-[#16A34A]"
                : area.healthPercent >= 70
                  ? "text-yellow-700"
                  : "text-[#E11D48]"
            }`}
            title={`${area.healthPercent}% of inspected equipment is normal`}
          >
            {area.healthPercent}%
          </span>
        )}
      </div>

      <AreaStatusBadge status={area.areaStatus} className="mb-4" />

      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt className="text-zinc-500 text-xs">Equipment</dt>
          <dd className="font-mono font-medium text-zinc-900">{area.configuredCount}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 text-xs">Normal</dt>
          <dd className="font-mono font-medium text-[#16A34A]">{pending ? "—" : area.normal}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 text-xs">Warning</dt>
          <dd className="font-mono font-medium text-yellow-700">{pending ? "—" : area.warning}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 text-xs">Alarm</dt>
          <dd className="font-mono font-medium text-[#E11D48]">{pending ? "—" : area.alarm}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 text-xs">Pending</dt>
          <dd className="font-mono font-medium text-zinc-700">{area.pendingToday}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 text-xs">Health</dt>
          <dd className="font-medium text-zinc-900 text-xs leading-snug">{area.healthLabel}</dd>
        </div>
      </dl>

      {pending && (
        <p className="text-xs text-zinc-600 mt-4 pt-3 border-t border-zinc-100 flex items-center gap-1.5">
          <span aria-hidden>{DASHBOARD_STATUS.PENDING.emoji}</span>
          {DASHBOARD_STATUS.PENDING.label} — {area.pendingToday} equipment awaiting inspection
        </p>
      )}
    </button>
  );
}

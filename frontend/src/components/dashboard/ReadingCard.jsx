import { Camera, MapPin, User } from "@phosphor-icons/react";
import RelativeTime from "@/components/dashboard/RelativeTime";
import StatusBadge from "@/components/dashboard/StatusBadge";
import { getParameterDisplay, resolveReadingArea } from "@/lib/dashboardAnalytics";

export default function ReadingCard({ reading, lookups, onSelect }) {
  const area = resolveReadingArea(reading, lookups);
  const hasMedia = Boolean(reading.media_url || reading.media_name);
  const paramLabel = getParameterDisplay(reading);
  const valueOnly =
    reading.value != null && reading.value !== "" ? String(reading.value) : "—";
  const unit = reading.unit ? String(reading.unit).trim() : "";

  return (
    <button
      type="button"
      onClick={() => onSelect?.(reading)}
      data-testid="recent-reading-row"
      data-equipment={reading.equipment || ""}
      data-area={area}
      className="w-full text-left border border-zinc-200 hover:border-[#002FA7]/30 hover:bg-zinc-50/80 p-5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#002FA7]/30"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <p className="inline-flex items-center gap-2 text-sm font-medium text-zinc-950">
            <MapPin size={16} weight="duotone" className="text-[#002FA7] shrink-0" />
            <span>{area}</span>
          </p>
          <StatusBadge status={reading.status} />
        </div>

        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-[0.12em] text-zinc-500 mb-0.5">Equipment</dt>
            <dd className="font-medium text-zinc-900">{reading.equipment || "—"}</dd>
          </div>
          {reading.tag_no ? (
            <div>
              <dt className="text-xs uppercase tracking-[0.12em] text-zinc-500 mb-0.5">Tag No</dt>
              <dd className="font-mono text-zinc-900">{reading.tag_no}</dd>
            </div>
          ) : null}
          <div>
            <dt className="text-xs uppercase tracking-[0.12em] text-zinc-500 mb-0.5">Parameter</dt>
            <dd className="text-zinc-900">{paramLabel}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.12em] text-zinc-500 mb-0.5">Value</dt>
            <dd className="font-mono font-semibold text-zinc-950">
              {valueOnly}
              {unit ? <span className="font-normal text-zinc-600 ml-1">{unit}</span> : null}
            </dd>
          </div>
        </dl>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-zinc-100 text-xs text-zinc-600">
          <span className="inline-flex items-center gap-1.5">
            <User size={14} className="text-zinc-400" />
            <span>
              Verified by: <span className="font-medium text-zinc-800">{reading.verified_by || "—"}</span>
            </span>
          </span>
          <RelativeTime value={reading.timestamp} className="font-mono text-zinc-500" />
        </div>

        {reading.remarks ? (
          <p className="text-xs text-zinc-600 bg-zinc-50 px-3 py-2 rounded border border-zinc-100 leading-relaxed">
            {reading.remarks}
          </p>
        ) : null}

        {hasMedia ? (
          <p className="inline-flex items-center gap-1.5 text-xs font-medium text-[#002FA7]">
            <Camera size={16} weight="duotone" />
            Media attached
          </p>
        ) : null}
      </div>
    </button>
  );
}

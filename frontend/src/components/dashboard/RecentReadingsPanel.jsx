import { ArrowClockwise } from "@phosphor-icons/react";
import ReadingCard from "@/components/dashboard/ReadingCard";

export default function RecentReadingsPanel({ readings, lookups, onSelectReading, onRefresh }) {
  return (
    <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg">
      <div className="flex items-center justify-between gap-4 mb-5">
        <div>
          <h3 className="text-xl font-light tracking-tight text-zinc-900">Recent Readings</h3>
          <p className="text-sm text-zinc-500 mt-1">Latest submissions from Google Sheets</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex items-center gap-2 px-3 py-2 border border-[#002FA7] text-[#002FA7] text-sm hover:bg-[#002FA7] hover:text-white transition-colors rounded"
        >
          <ArrowClockwise size={16} />
          Refresh
        </button>
      </div>

      {readings.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-zinc-200 rounded-lg px-4">
          <p className="text-sm font-medium text-zinc-700">No readings match the current filters.</p>
          <p className="text-xs text-zinc-500 mt-2">
            Clear filters or submit readings from Add Reading to populate this panel.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {readings.map((reading, idx) => (
            <ReadingCard
              key={`${reading.timestamp}-${reading.equipment}-${reading.parameter}-${idx}`}
              reading={reading}
              lookups={lookups}
              onSelect={onSelectReading}
            />
          ))}
        </div>
      )}
    </section>
  );
}

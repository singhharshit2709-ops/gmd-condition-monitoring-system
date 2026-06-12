import AreaCard from "@/components/dashboard/AreaCard";
import { DASHBOARD_STATUS } from "@/lib/dashboardAnalytics";

export default function AreaHealthGrid({ areaSummaries, onSelectArea }) {
  if (!areaSummaries?.length) {
    return (
      <div className="border border-dashed border-zinc-200 bg-white p-10 text-center rounded-lg">
        <p className="text-sm font-medium text-zinc-700 flex items-center justify-center gap-1.5">
          {DASHBOARD_STATUS.PENDING.emoji} Awaiting today&apos;s inspection round
        </p>
        <p className="text-xs text-zinc-500 mt-2">
          Submit readings from Add Reading to populate area health.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {areaSummaries.map((area) => (
        <AreaCard key={area.area} area={area} onSelect={onSelectArea} />
      ))}
    </div>
  );
}

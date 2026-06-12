import { Progress } from "@/components/ui/progress";
import { DASHBOARD_STATUS, getProgressBarClass } from "@/lib/dashboardAnalytics";

export default function ProgressCard({ area, completed, total, remaining, percent, hasTodaySubmissions }) {
  const pending = !hasTodaySubmissions;

  return (
    <div
      className="bg-zinc-50/50 border border-zinc-200 rounded-lg p-4 hover:border-[#002FA7]/20 transition-colors"
      data-area={area}
      data-round-completed={completed}
      data-round-total={total}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h4 className="font-medium text-zinc-950">{area}</h4>
        <span className="font-mono text-sm text-zinc-700 whitespace-nowrap">
          {completed} / {total}
        </span>
      </div>

      <Progress
        value={pending ? 0 : percent}
        className={getProgressBarClass(percent, { pending })}
      />

      <div className="flex items-center justify-between mt-2.5 text-xs">
        {pending ? (
          <span className="font-medium text-zinc-600 flex items-center gap-1.5">
            {DASHBOARD_STATUS.PENDING.emoji} {DASHBOARD_STATUS.PENDING.label}
          </span>
        ) : (
          <span className="font-mono font-medium text-[#002FA7]">{percent}%</span>
        )}
        <span className="text-zinc-500">
          {pending
            ? `${total} remaining`
            : remaining > 0
              ? `${remaining} remaining`
              : "Round complete"}
        </span>
      </div>
    </div>
  );
}

import ProgressCard from "@/components/dashboard/ProgressCard";
import { DASHBOARD_STATUS } from "@/lib/dashboardAnalytics";

export default function RoundCompletionPanel({ roundCompletion }) {
  const allPending = roundCompletion.every((row) => !row.hasTodaySubmissions);
  const totalCompleted = roundCompletion.reduce((sum, row) => sum + row.completed, 0);
  const totalConfigured = roundCompletion.reduce((sum, row) => sum + row.total, 0);

  return (
    <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-5">
        <div>
          <h3 className="text-xl font-light tracking-tight text-zinc-900">Today&apos;s Round Completion</h3>
          <p className="text-sm text-zinc-500 mt-1">
            Equipment with at least one reading submitted today
          </p>
        </div>
        {!allPending && (
          <p className="text-sm font-mono text-zinc-700">
            {totalCompleted} / {totalConfigured} equipment inspected
          </p>
        )}
      </div>

      {allPending && (
        <div className="text-center py-6 border border-dashed border-zinc-200 text-sm text-zinc-600 rounded-lg mb-4 px-4">
          <p className="font-medium flex items-center justify-center gap-1.5">
            {DASHBOARD_STATUS.PENDING.emoji} Awaiting today&apos;s inspection round
          </p>
          <p className="text-xs text-zinc-500 mt-2">No readings submitted today.</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {roundCompletion.map((row) => (
          <ProgressCard
            key={row.area}
            area={row.area}
            completed={row.completed}
            total={row.total}
            remaining={row.remaining}
            percent={row.percent}
            hasTodaySubmissions={row.hasTodaySubmissions}
          />
        ))}
      </div>
    </section>
  );
}

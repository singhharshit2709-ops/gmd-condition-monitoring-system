import RelativeTime from "@/components/dashboard/RelativeTime";

export default function DashboardFooter({
  totalAreas,
  totalEquipment,
  totalParameters,
  todayEntryCount,
  todayCompletedRounds,
  lastRefresh,
  sheetsConnected,
}) {
  return (
    <footer className="border-t border-zinc-200 bg-white px-4 py-5 md:px-6 mt-auto">
      <div className="max-w-[1920px] mx-auto grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-x-4 gap-y-5 text-sm">
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Total Areas</p>
          <p className="font-mono text-zinc-900 mt-1">{totalAreas}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Total Equipment</p>
          <p className="font-mono text-zinc-900 mt-1">{totalEquipment}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Configured Parameters</p>
          <p className="font-mono text-zinc-900 mt-1">{totalParameters}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Today&apos;s Entries</p>
          <p className="font-mono text-zinc-900 mt-1">{todayEntryCount}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Today&apos;s Completed Rounds</p>
          <p className="font-mono text-zinc-900 mt-1">{todayCompletedRounds}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Last Google Sheets Sync</p>
          <p className="font-mono text-zinc-900 mt-1">
            {lastRefresh ? <RelativeTime value={lastRefresh} /> : "—"}
          </p>
        </div>
      </div>

      <div className="max-w-[1920px] mx-auto mt-4 pt-4 border-t border-zinc-100 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="text-xs uppercase tracking-[0.15em] text-zinc-500">Google Sheets Status</span>
        <span
          className={`inline-flex items-center gap-1.5 font-medium ${
            sheetsConnected ? "text-[#16A34A]" : "text-[#E11D48]"
          }`}
        >
          <span aria-hidden>{sheetsConnected ? "🟢" : "🔴"}</span>
          {sheetsConnected ? "Google Sheets Connected" : "Google Sheets Disconnected"}
        </span>
      </div>
    </footer>
  );
}

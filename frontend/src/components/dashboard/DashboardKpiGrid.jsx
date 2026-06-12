import {
  Bell,
  CheckCircle,
  Clock,
  Factory,
  Gauge,
  ListChecks,
  MapPin,
  WarningCircle,
} from "@phosphor-icons/react";
import KpiCard from "@/components/dashboard/KpiCard";
import { DASHBOARD_STATUS } from "@/lib/dashboardAnalytics";

export default function DashboardKpiGrid({
  totalAreas,
  totalEquipment,
  todayEntryCount,
  lastUpdatedLabel,
  lastUpdatedTitle,
  hasTodaySubmissions,
  summary,
  pendingRoundCount,
}) {
  const lastUpdatedDisplay =
    lastUpdatedLabel && lastUpdatedLabel !== "—"
      ? lastUpdatedLabel
      : `${DASHBOARD_STATUS.PENDING.emoji} Awaiting data`;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard icon={MapPin} title="Total Areas" value={totalAreas} description="Monitored tank and process areas" />
        <KpiCard icon={Factory} title="Total Equipment" value={totalEquipment} description="Configured round sheet assets" />
        <KpiCard
          icon={ListChecks}
          title="Today's Entries"
          value={todayEntryCount}
          description={
            todayEntryCount === 0
              ? "No readings submitted today"
              : "Parameter readings submitted today"
          }
          accent={todayEntryCount === 0 ? "border-zinc-200" : "border-[#002FA7]/20"}
        />
        <KpiCard
          icon={Clock}
          title="Last Updated"
          value={lastUpdatedDisplay}
          valueTitle={lastUpdatedTitle}
          description="Latest Google Sheets reading"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard
          icon={CheckCircle}
          title="Normal"
          value={hasTodaySubmissions ? (summary?.ok ?? 0) : "—"}
          description={
            hasTodaySubmissions ? "Equipment within limits" : "Awaiting today's inspection"
          }
          accent="border-green-200"
        />
        <KpiCard
          icon={WarningCircle}
          title="Warning"
          value={hasTodaySubmissions ? (summary?.warning ?? 0) : "—"}
          description={hasTodaySubmissions ? "Needs inspection" : "—"}
          accent="border-yellow-200"
        />
        <KpiCard
          icon={Bell}
          title="Alarm"
          value={hasTodaySubmissions ? (summary?.alarm ?? 0) : "—"}
          description={hasTodaySubmissions ? "Immediate action required" : "—"}
          accent="border-red-200"
        />
        <KpiCard
          icon={Gauge}
          title="Equipment Pending"
          value={pendingRoundCount}
          description="Equipment awaiting today's round inspection"
          accent="border-[#002FA7]/20"
        />
      </div>
    </div>
  );
}

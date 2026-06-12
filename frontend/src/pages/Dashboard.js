import { useMemo, useState } from "react";
import { useDashboardData } from "@/hooks/useDashboardData";
import { formatRelativeTime } from "@/lib/dashboardAnalytics";
import AreaHealthGrid from "@/components/dashboard/AreaHealthGrid";
import DashboardFilters from "@/components/dashboard/DashboardFilters";
import DashboardFooter from "@/components/dashboard/DashboardFooter";
import DashboardKpiGrid from "@/components/dashboard/DashboardKpiGrid";
import DashboardSearch from "@/components/dashboard/DashboardSearch";
import EquipmentSummaryDrawer from "@/components/dashboard/EquipmentSummaryDrawer";
import PlantHealthBanner from "@/components/dashboard/PlantHealthBanner";
import RecentAlertsPanel from "@/components/dashboard/RecentAlertsPanel";
import RecentReadingsPanel from "@/components/dashboard/RecentReadingsPanel";
import RoundCompletionPanel from "@/components/dashboard/RoundCompletionPanel";
import TodayRoundBanner from "@/components/dashboard/TodayRoundBanner";

export default function Dashboard() {
  const {
    loading,
    summary,
    recentReadings,
    equipmentHealth,
    lastRefresh,
    sheetsConnected,
    filters,
    setFilters,
    searchQuery,
    setSearchQuery,
    searchSuggestions,
    applySearchSuggestion,
    fetchData,
    acknowledgeAlarm,
    lookups,
    areaSummaries,
    roundCompletion,
    todayMetrics,
    pendingRoundCount,
    todayCompletedRounds,
    lastUpdated,
    banner,
    todayRoundBanner,
    filterOptions,
    recentPanel,
    alertsPanel,
    resolvedAlert,
    totalAreas,
    totalEquipment,
    totalParameters,
  } = useDashboardData();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selection, setSelection] = useState(null);

  const lastUpdatedMeta = useMemo(
    () => (lastUpdated ? formatRelativeTime(lastUpdated) : { label: "—", title: "" }),
    [lastUpdated]
  );

  const lastRefreshMeta = useMemo(
    () => (lastRefresh ? formatRelativeTime(lastRefresh) : { label: "—", title: "" }),
    [lastRefresh]
  );

  const hasTodaySubmissions = todayMetrics.todayEntryCount > 0;

  const openArea = (area) => {
    setSelection({ type: "area", data: area });
    setDrawerOpen(true);
  };

  const openReading = (reading) => {
    setSelection({ type: "reading", data: reading });
    setDrawerOpen(true);
  };

  if (loading && summary === null) {
    return (
      <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
        <div className="text-sm text-zinc-600">Loading dashboard…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8 space-y-6">
        <header>
          <h1 className="text-3xl md:text-4xl font-light tracking-tight text-zinc-950">
            Condition Monitoring Dashboard
          </h1>
          <p className="text-sm text-zinc-700 mt-2">
            General Maintenance Department · Neutral Glass · Area-first plant health overview
          </p>
        </header>

        <PlantHealthBanner banner={banner} lastRefreshLabel={lastRefreshMeta.label} />

        <TodayRoundBanner banner={todayRoundBanner} />

        <DashboardKpiGrid
          totalAreas={totalAreas}
          totalEquipment={totalEquipment}
          todayEntryCount={todayMetrics.todayEntryCount}
          lastUpdatedLabel={lastUpdatedMeta.label}
          lastUpdatedTitle={lastUpdatedMeta.title}
          hasTodaySubmissions={hasTodaySubmissions}
          summary={summary}
          pendingRoundCount={pendingRoundCount}
        />

        <DashboardSearch
          value={searchQuery}
          onChange={setSearchQuery}
          suggestions={searchSuggestions}
          onSelectSuggestion={applySearchSuggestion}
        />

        <DashboardFilters filters={filters} filterOptions={filterOptions} onChange={setFilters} />

        <section>
          <div className="mb-4">
            <h2 className="text-2xl font-light tracking-tight text-zinc-900">Area Health Overview</h2>
            <p className="text-sm text-zinc-500 mt-1">Click an area for category and equipment drill-down</p>
          </div>
          <AreaHealthGrid areaSummaries={areaSummaries} onSelectArea={openArea} />
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <RecentReadingsPanel
            readings={recentPanel}
            lookups={lookups}
            onSelectReading={openReading}
            onRefresh={fetchData}
          />
          <RecentAlertsPanel
            alerts={alertsPanel}
            resolvedAlert={resolvedAlert}
            lookups={lookups}
            onAcknowledge={acknowledgeAlarm}
          />
        </div>

        <RoundCompletionPanel roundCompletion={roundCompletion} />
      </div>

      <DashboardFooter
        totalAreas={totalAreas}
        totalEquipment={totalEquipment}
        totalParameters={totalParameters}
        todayEntryCount={todayMetrics.todayEntryCount}
        todayCompletedRounds={todayCompletedRounds}
        lastRefresh={lastRefresh}
        sheetsConnected={sheetsConnected}
      />
    </div>
  );
}

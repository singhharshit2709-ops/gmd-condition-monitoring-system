import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import axios from "axios";

import { getApiBase } from "@/lib/api";

import {

  buildCascadingFilterOptions,

  buildConfigLookups,

  buildPlantBanner,

  buildTodayRoundBanner,

  buildSearchIndex,

  computeAreaSummaries,

  computePendingRoundCount,

  computeRoundCompletion,

  computeTodayCompletedEquipment,

  computeTodayMetrics,

  dedupeRecentReadings,

  filterDashboardData,

  findMostRecentResolvedAlert,

  getLastUpdatedTime,

  sanitizeFilters,

  searchSuggestions,

} from "@/lib/dashboardAnalytics";



const API = getApiBase();

const REFRESH_MS = 30000;



function isValidSummary(payload) {

  return (

    payload &&

    typeof payload === "object" &&

    typeof payload.total === "number" &&

    typeof payload.ok === "number" &&

    typeof payload.warning === "number" &&

    typeof payload.alarm === "number"

  );

}



export function useDashboardData() {

  const [summary, setSummary] = useState(() => {

    try {

      const cached = window.localStorage.getItem("dashboardSummary");

      return cached ? JSON.parse(cached) : null;

    } catch {

      return null;

    }

  });

  const [recentReadings, setRecentReadings] = useState([]);

  const [activeAlarms, setActiveAlarms] = useState([]);

  const [equipmentHealth, setEquipmentHealth] = useState([]);

  const [loading, setLoading] = useState(() => summary === null);

  const [lastRefresh, setLastRefresh] = useState(null);

  const [sheetsConnected, setSheetsConnected] = useState(true);

  const [filters, setFiltersState] = useState({

    area: "all",

    category: "all",

    equipment: "all",

    tagNo: "all",

    status: "all",

    verifiedBy: "all",

  });

  const [searchQuery, setSearchQuery] = useState("");

  const summaryRef = useRef(summary);



  useEffect(() => {

    summaryRef.current = summary;

  }, [summary]);



  const fetchData = useCallback(async () => {

    const firstLoad = summaryRef.current === null;

    if (firstLoad) setLoading(true);



    try {

      const [summaryResult, recentResult, alarmsResult, healthResult] = await Promise.allSettled([

        axios.get(`${API}/dashboard/summary`),

        axios.get(`${API}/dashboard/recent-readings`, { params: { limit: 200 } }),

        axios.get(`${API}/dashboard/active-alarms`),

        axios.get(`${API}/dashboard/equipment-health`),

      ]);



      const anySuccess =

        (summaryResult.status === "fulfilled" && isValidSummary(summaryResult.value.data)) ||

        (recentResult.status === "fulfilled" && Array.isArray(recentResult.value.data)) ||

        (alarmsResult.status === "fulfilled" && Array.isArray(alarmsResult.value.data)) ||

        (healthResult.status === "fulfilled" && Array.isArray(healthResult.value.data));



      setSheetsConnected(anySuccess);



      if (summaryResult.status === "fulfilled" && isValidSummary(summaryResult.value.data)) {

        setSummary(summaryResult.value.data);

        window.localStorage.setItem("dashboardSummary", JSON.stringify(summaryResult.value.data));

      }



      if (recentResult.status === "fulfilled" && Array.isArray(recentResult.value.data)) {

        setRecentReadings(recentResult.value.data);

      }

      if (alarmsResult.status === "fulfilled" && Array.isArray(alarmsResult.value.data)) {

        setActiveAlarms(alarmsResult.value.data);

      }

      if (healthResult.status === "fulfilled" && Array.isArray(healthResult.value.data)) {

        setEquipmentHealth(healthResult.value.data);

      }



      setLastRefresh(new Date());

    } catch (error) {

      console.error("Dashboard fetch error:", error);

      setSheetsConnected(false);

    } finally {

      if (firstLoad) setLoading(false);

    }

  }, []);



  useEffect(() => {

    fetchData();

    const interval = setInterval(fetchData, REFRESH_MS);

    const onReadingsUpdated = () => {
      try {
        window.localStorage.removeItem("dashboardSummary");
      } catch {
        /* ignore */
      }
      fetchData();
    };
    window.addEventListener("gmd-readings-updated", onReadingsUpdated);

    return () => {
      clearInterval(interval);
      window.removeEventListener("gmd-readings-updated", onReadingsUpdated);
    };

  }, [fetchData]);



  const lookups = useMemo(() => buildConfigLookups(), []);

  const searchIndex = useMemo(

    () => buildSearchIndex(lookups, recentReadings),

    [lookups, recentReadings]

  );



  const filterOptions = useMemo(

    () => buildCascadingFilterOptions(recentReadings, lookups, filters),

    [recentReadings, lookups, filters]

  );



  const setFilters = useCallback(

    (next) => {

      setFiltersState((prev) => {

        const merged = typeof next === "function" ? next(prev) : next;

        return sanitizeFilters(merged, buildCascadingFilterOptions(recentReadings, lookups, merged));

      });

    },

    [recentReadings, lookups]

  );



  const derived = useMemo(() => {

    const areaSummaries = computeAreaSummaries(equipmentHealth, recentReadings, lookups);

    const roundCompletion = computeRoundCompletion(recentReadings, lookups);

    const todayMetrics = computeTodayMetrics(recentReadings, lookups);

    const pendingRoundCount = computePendingRoundCount(roundCompletion);

    const todayCompletedRounds = computeTodayCompletedEquipment(recentReadings, lookups);

    const lastUpdated = getLastUpdatedTime(recentReadings);

    const banner = buildPlantBanner(summary, activeAlarms, lastRefresh, todayMetrics);

    const todayRoundBanner = buildTodayRoundBanner(todayMetrics, lastUpdated);

    const resolvedAlert = findMostRecentResolvedAlert(recentReadings, activeAlarms, lookups);



    const filtered = filterDashboardData({

      recentReadings,

      activeAlarms,

      equipmentHealth,

      lookups,

      filters,

      searchQuery,

    });



    return {

      areaSummaries,

      roundCompletion,

      todayMetrics,

      pendingRoundCount,

      todayCompletedRounds,

      lastUpdated,

      banner,

      todayRoundBanner,

      resolvedAlert,

      recentPanel: dedupeRecentReadings(filtered.filteredReadings, 10),

      alertsPanel: filtered.filteredAlarms.slice(0, 10),

      filteredHealth: filtered.filteredHealth,

      totalAreas: areaSummaries.length,

      totalEquipment: lookups.totalEquipment,

      totalParameters: lookups.totalParameters,

    };

  }, [

    equipmentHealth,

    recentReadings,

    activeAlarms,

    summary,

    lookups,

    filters,

    searchQuery,

    lastRefresh,

  ]);



  const suggestions = useMemo(

    () => searchSuggestions(searchIndex, searchQuery),

    [searchIndex, searchQuery]

  );



  const acknowledgeAlarm = useCallback(

    async (alarmId) => {

      if (!alarmId) return;

      await axios.post(`${API}/dashboard/acknowledge-alarm/${alarmId}`);

      await fetchData();

    },

    [fetchData]

  );



  const applySearchSuggestion = useCallback(

    (item) => {

      if (item.type === "area") {

        setFilters((prev) => ({ ...prev, area: item.value, category: "all", equipment: "all", tagNo: "all" }));

      } else if (item.type === "category") {

        setFilters((prev) => ({

          ...prev,

          area: item.area || prev.area,

          category: item.value,

          equipment: "all",

          tagNo: "all",

        }));

      } else if (item.type === "equipment" || item.type === "tag") {

        setFilters((prev) => ({

          ...prev,

          area: item.area || prev.area,

          category: item.category && item.category !== "" ? item.category : prev.category,

          equipment: item.equipment || item.value,

          tagNo: item.tagNo || prev.tagNo,

        }));

      }

    },

    [setFilters]

  );



  return {

    loading,

    summary,

    recentReadings,

    activeAlarms,

    equipmentHealth,

    lastRefresh,

    sheetsConnected,

    filters,

    setFilters,

    searchQuery,

    setSearchQuery,

    searchSuggestions: suggestions,

    applySearchSuggestion,

    fetchData,

    acknowledgeAlarm,

    lookups,

    filterOptions,

    ...derived,

  };

}


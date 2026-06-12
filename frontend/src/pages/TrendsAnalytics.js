import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ArrowClockwise } from "@phosphor-icons/react";
import { getApiBase } from "@/lib/api";
import TrendsFilterPanel from "@/components/trends/TrendsFilterPanel";
import TrendLineChart from "@/components/trends/TrendLineChart";
import TrendStatsGrid from "@/components/trends/TrendStatsGrid";
import TrendDataTable from "@/components/trends/TrendDataTable";
import {
  buildChartSeries,
  buildTrendRequestParams,
  computeTrendStats,
  findParameterMeta,
  getCategoriesForArea,
  getEquipmentForTrendsArea,
  getParametersForEquipment,
  getThresholdLines,
  getTrendsAreaOptions,
} from "@/lib/trendsAnalytics";

const API = getApiBase();

export default function TrendsAnalytics() {
  const areaOptions = useMemo(() => getTrendsAreaOptions(), []);

  const [selectedArea, setSelectedArea] = useState(areaOptions[0] || "");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedEquipmentId, setSelectedEquipmentId] = useState("");
  const [selectedParameter, setSelectedParameter] = useState("");
  const [compareParameters, setCompareParameters] = useState([]);
  const [windowOption, setWindowOption] = useState("30");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const equipmentEntries = useMemo(() => {
    const all = getEquipmentForTrendsArea(selectedArea);
    if (!selectedCategory) return all;
    return all.filter((eq) => eq.category === selectedCategory);
  }, [selectedArea, selectedCategory]);

  const categories = useMemo(
    () => getCategoriesForArea(selectedArea, getEquipmentForTrendsArea(selectedArea)),
    [selectedArea]
  );

  const selectedEquipment = useMemo(
    () => equipmentEntries.find((eq) => eq.id === selectedEquipmentId) || null,
    [equipmentEntries, selectedEquipmentId]
  );

  const parameters = useMemo(
    () => getParametersForEquipment(selectedEquipment),
    [selectedEquipment]
  );

  const activeParameterKeys = useMemo(() => {
    const keys = new Set([selectedParameter, ...compareParameters].filter(Boolean));
    return [...keys];
  }, [selectedParameter, compareParameters]);

  const parameterMeta = useMemo(
    () => findParameterMeta(selectedEquipment, selectedParameter),
    [selectedEquipment, selectedParameter]
  );

  const loadTrendData = useCallback(async () => {
    if (!selectedEquipment || !selectedParameter) {
      setReadings([]);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const params = buildTrendRequestParams({
        area: selectedArea,
        equipmentEntry: selectedEquipment,
        parameterKey: null,
        category: selectedCategory || undefined,
        windowOption,
        startDate,
        endDate,
      });

      const response = await axios.get(`${API}/trends/readings`, { params });
      setReadings(response.data || []);
    } catch (loadError) {
      console.error("Failed to load trend data:", loadError);
      setError("Unable to load trend data. Check filters and time range, then try again.");
      setReadings([]);
    } finally {
      setLoading(false);
    }
  }, [
    selectedArea,
    selectedCategory,
    selectedEquipment,
    selectedParameter,
    windowOption,
    startDate,
    endDate,
  ]);

  useEffect(() => {
    loadTrendData();
  }, [loadTrendData]);

  useEffect(() => {
    if (!equipmentEntries.length) {
      setSelectedEquipmentId("");
      return;
    }
    if (!equipmentEntries.some((eq) => eq.id === selectedEquipmentId)) {
      setSelectedEquipmentId(equipmentEntries[0].id);
    }
  }, [equipmentEntries, selectedEquipmentId]);

  useEffect(() => {
    if (!parameters.length) {
      setSelectedParameter("");
      setCompareParameters([]);
      return;
    }
    if (!parameters.some((p) => p.key === selectedParameter)) {
      setSelectedParameter(parameters[0].key);
      setCompareParameters([]);
    }
  }, [parameters, selectedParameter]);

  const handleAreaChange = (area) => {
    setSelectedArea(area);
    setSelectedCategory("");
    setSelectedEquipmentId("");
    setSelectedParameter("");
    setCompareParameters([]);
  };

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
    setSelectedEquipmentId("");
    setSelectedParameter("");
    setCompareParameters([]);
  };

  const handleEquipmentChange = (equipmentId) => {
    setSelectedEquipmentId(equipmentId);
    setSelectedParameter("");
    setCompareParameters([]);
  };

  const handleParameterChange = (paramKey) => {
    setSelectedParameter(paramKey);
    setCompareParameters([]);
  };

  const filteredReadings = useMemo(
    () =>
      readings.filter((row) =>
        activeParameterKeys.includes(row.parameter_key || row.parameter)
      ),
    [readings, activeParameterKeys]
  );

  const { rows: chartRows, series: chartSeries } = useMemo(
    () => buildChartSeries(filteredReadings, activeParameterKeys),
    [filteredReadings, activeParameterKeys]
  );

  const stats = useMemo(
    () => computeTrendStats(filteredReadings, selectedParameter),
    [filteredReadings, selectedParameter]
  );

  const thresholdLines = useMemo(() => getThresholdLines(parameterMeta), [parameterMeta]);

  const chartTitle = useMemo(() => {
    if (!selectedEquipment || !selectedParameter) return "Parameter Trend";
    const param = parameters.find((p) => p.key === selectedParameter);
    return `${selectedEquipment.display_name} — ${param?.label || selectedParameter}`;
  }, [selectedEquipment, selectedParameter, parameters]);

  const yAxisLabel = parameterMeta?.unit || chartSeries[0]?.unit || "";

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8 space-y-6">
      <header>
        <h1 className="text-3xl md:text-4xl font-light tracking-tight text-zinc-950">
          Trends & Analytics
        </h1>
        <p className="text-sm text-zinc-700 mt-2">
          General Maintenance Department · Graphical history for any tank, equipment, and parameter
        </p>
      </header>

      <TrendsFilterPanel
        areas={areaOptions}
        categories={categories}
        equipmentOptions={equipmentEntries}
        parameters={parameters}
        selectedArea={selectedArea}
        selectedCategory={selectedCategory}
        selectedEquipmentId={selectedEquipmentId}
        selectedParameter={selectedParameter}
        compareParameters={compareParameters}
        windowOption={windowOption}
        startDate={startDate}
        endDate={endDate}
        onAreaChange={handleAreaChange}
        onCategoryChange={handleCategoryChange}
        onEquipmentChange={handleEquipmentChange}
        onParameterChange={handleParameterChange}
        onCompareChange={setCompareParameters}
        onWindowChange={setWindowOption}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-zinc-600">
          {selectedEquipment && selectedParameter
            ? `${filteredReadings.length} readings loaded for chart`
            : "Select equipment and parameter to view trends"}
        </p>
        <button
          type="button"
          onClick={loadTrendData}
          disabled={!selectedEquipment || !selectedParameter}
          className="inline-flex items-center gap-2 px-4 py-2 border border-[#002FA7] text-[#002FA7] text-sm rounded hover:bg-[#002FA7] hover:text-white transition-colors disabled:opacity-40"
        >
          <ArrowClockwise size={16} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="border border-red-200 bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {loading ? (
        <div className="border border-zinc-200 bg-white p-12 text-center text-sm text-zinc-500 rounded-lg">
          Loading trend data…
        </div>
      ) : (
        <>
          <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg space-y-5">
            <div>
              <h2 className="text-xl font-medium text-zinc-900">{chartTitle}</h2>
              <p className="text-sm text-zinc-500 mt-1">
                {selectedArea}
                {selectedCategory ? ` · ${selectedCategory}` : ""}
                {selectedEquipment?.tag_no ? ` · Tag ${selectedEquipment.tag_no}` : ""}
              </p>
            </div>

            <TrendStatsGrid
              stats={stats}
              parameterLabel={parameters.find((p) => p.key === selectedParameter)?.label}
            />

            <TrendLineChart
              rows={chartRows}
              series={chartSeries}
              thresholdLines={activeParameterKeys.length === 1 ? thresholdLines : []}
              yAxisLabel={yAxisLabel}
            />
          </section>

          {filteredReadings.length > 0 && (
            <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg">
              <h3 className="text-lg font-medium text-zinc-900 mb-4">Recent Readings</h3>
              <TrendDataTable readings={filteredReadings} />
            </section>
          )}
        </>
      )}
    </div>
  );
}

import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { getApiBase } from "../lib/api";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Label,
} from "recharts";

const API = getApiBase();

const WINDOW_OPTIONS = [
  { label: "All history", value: "all" },
  { label: "Last 7 days", value: "7" },
  { label: "Last 30 days", value: "30" },
  { label: "Last 90 days", value: "90" },
  { label: "Custom range", value: "custom" },
];

export default function TrendsAnalytics() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [windowOption, setWindowOption] = useState("all");
  const [equipmentFilter, setEquipmentFilter] = useState("");
  const [parameterFilter, setParameterFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const loadTrendData = async () => {
    setLoading(true);
    setError("");

    try {
      const params = {};

      if (equipmentFilter) {
        params.equipment = equipmentFilter;
      }

      if (parameterFilter) {
        params.parameter = parameterFilter;
      }

      if (categoryFilter) {
        params.category = categoryFilter;
      }

      if (["7", "30", "90"].includes(windowOption)) {
        params.window = Number(windowOption);
      }

      if (windowOption === "custom") {
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
      }

      const response = await axios.get(`${API}/trends/readings`, {
        params,
      });

      setData(response.data || []);
    } catch (loadError) {
      console.error("Failed to load trend data:", loadError);
      setError("Unable to load trend data. Please verify the selected range and try again.");
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrendData();
  }, [windowOption, equipmentFilter, parameterFilter, categoryFilter, startDate, endDate]);

  const equipmentOptions = useMemo(
    () =>
      Array.from(
        new Set(
          data
            .map((item) => item.equipment)
            .filter((item) => typeof item === "string" && item.trim() !== "")
        )
      ).sort(),
    [data]
  );

  const parameterOptions = useMemo(
    () =>
      Array.from(
        new Set(
          data
            .map((item) => item.parameter)
            .filter((item) => typeof item === "string" && item.trim() !== "")
        )
      ).sort(),
    [data]
  );

  const categoryOptions = useMemo(
    () =>
      Array.from(
        new Set(
          data
            .map((item) => item.category)
            .filter((item) => typeof item === "string" && item.trim() !== "")
        )
      ).sort(),
    [data]
  );

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return String(timestamp || "-");
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  const tooltipLabelFormatter = (label) => `Time: ${label}`;
  const tooltipFormatter = (value, name) => [value, name];

  const lastReadingTimestamp = useMemo(() => {
    if (!data.length) return "";
    const latest = data.reduce((current, next) => {
      const currentTs = new Date(current.timestamp).getTime();
      const nextTs = new Date(next.timestamp).getTime();
      return nextTs > currentTs ? next : current;
    }, data[0]);
    return formatTimestamp(latest.timestamp);
  }, [data]);

  const selectedEquipmentLabel = equipmentFilter || "All equipment";
  const parametersAvailable = parameterOptions.length;
  const totalHistoricalRecords = data.length;

  const temperatureData = useMemo(
    () => data.filter((item) => String(item.parameter).toLowerCase() === "temperature"),
    [data]
  );

  const vibrationData = useMemo(
    () =>
      data.filter((item) => {
        const param = String(item.parameter).toLowerCase();
        return ["vertical_vibration", "horizontal_vibration", "axial_vibration"].includes(param);
      }),
    [data]
  );

  const vibrationSeries = useMemo(() => {
    const seriesMap = {};

    vibrationData.forEach((item) => {
      const key = formatTimestamp(item.timestamp);
      if (!seriesMap[key]) {
        seriesMap[key] = { timestamp: key, rawTimestamp: item.timestamp };
      }

      const param = String(item.parameter).toLowerCase();
      if (param.includes("vertical")) seriesMap[key].vertical = Number(item.value);
      if (param.includes("horizontal")) seriesMap[key].horizontal = Number(item.value);
      if (param.includes("axial")) seriesMap[key].axial = Number(item.value);
    });

    return Object.values(seriesMap).sort((a, b) => new Date(a.rawTimestamp) - new Date(b.rawTimestamp));
  }, [vibrationData]);

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-light tracking-tight text-zinc-950">
          Condition Monitoring Trends & Analytics
        </h1>
        <p className="text-sm text-zinc-700 mt-2">
          Use full historical readings to analyze equipment performance over multiple windows and custom ranges.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-6 mb-8">
        <div className="rounded-3xl border border-zinc-200 bg-white p-4 shadow-sm xl:col-span-3">
          <label className="text-xs uppercase tracking-[0.2em] text-zinc-500">Time range</label>
          <select
            value={windowOption}
            onChange={(event) => setWindowOption(event.target.value)}
            className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
          >
            {WINDOW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          {windowOption === "custom" && (
            <div className="grid gap-4 mt-4 sm:grid-cols-2">
              <div>
                <label className="text-xs uppercase tracking-[0.2em] text-zinc-500">Start date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.2em] text-zinc-500">End date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
                />
              </div>
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-zinc-200 bg-white p-4 shadow-sm xl:col-span-2">
          <label className="text-xs uppercase tracking-[0.2em] text-zinc-500">Equipment</label>
          <select
            value={equipmentFilter}
            onChange={(event) => setEquipmentFilter(event.target.value)}
            className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
          >
            <option value="">All equipment</option>
            {equipmentOptions.map((equipment) => (
              <option key={equipment} value={equipment}>
                {equipment}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-3xl border border-zinc-200 bg-white p-4 shadow-sm xl:col-span-2">
          <label className="text-xs uppercase tracking-[0.2em] text-zinc-500">Category</label>
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
          >
            <option value="">All categories</option>
            {categoryOptions.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-3xl border border-zinc-200 bg-white p-4 shadow-sm xl:col-span-2">
          <label className="text-xs uppercase tracking-[0.2em] text-zinc-500">Parameter</label>
          <select
            value={parameterFilter}
            onChange={(event) => setParameterFilter(event.target.value)}
            className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
          >
            <option value="">All parameters</option>
            {parameterOptions.map((parameter) => (
              <option key={parameter} value={parameter}>
                {parameter}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 w-full">
          <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Total Historical Records</p>
            <p className="mt-3 text-2xl font-semibold text-zinc-950">{totalHistoricalRecords}</p>
          </div>
          <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Selected Equipment</p>
            <p className="mt-3 text-2xl font-semibold text-zinc-950">{selectedEquipmentLabel}</p>
          </div>
          <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Parameters Available</p>
            <p className="mt-3 text-2xl font-semibold text-zinc-950">{parametersAvailable}</p>
          </div>
          <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Last Reading Timestamp</p>
            <p className="mt-3 text-2xl font-semibold text-zinc-950">{lastReadingTimestamp || "No data"}</p>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <p className="text-sm text-zinc-600">
            Showing {data.length} historical readings. Use the controls above to narrow the window.
          </p>
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </div>
        <button
          onClick={loadTrendData}
          className="inline-flex items-center justify-center rounded-xl border border-[#002FA7] bg-white px-5 py-3 text-sm font-medium text-[#002FA7] transition hover:bg-[#002FA7] hover:text-white"
        >
          Refresh Trends
        </button>
      </div>

      {loading ? (
        <div className="rounded-3xl border border-zinc-200 bg-white p-8 text-center text-sm text-zinc-500 shadow-sm">
          Loading trend data...
        </div>
      ) : (
        <>
          <div className="rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm mb-8">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-6">
              <div>
                <h2 className="text-2xl font-medium text-zinc-900">Temperature Trend</h2>
                <p className="text-sm text-zinc-500">Plotting all historical temperature readings in the selected window.</p>
              </div>
            </div>
            {temperatureData.length === 0 ? (
              <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-12 text-center text-sm text-zinc-600">
                No temperature trend data is available for the selected filters. Adjust the date range or equipment selection to load the chart.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={450}>
                <LineChart data={temperatureData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} tickFormatter={(tick) => formatTimestamp(tick)}>
                    <Label value="Time" position="insideBottom" offset={-5} />
                  </XAxis>
                  <YAxis tick={{ fontSize: 12 }}>
                    <Label value="Temperature (°C)" angle={-90} position="insideLeft" offset={-5} />
                  </YAxis>
                  <Tooltip labelFormatter={tooltipLabelFormatter} formatter={tooltipFormatter} />
                  <Legend verticalAlign="top" height={32} />
                  <Line type="monotone" dataKey="value" name="Temperature" stroke="#002FA7" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-6">
              <div>
                <h2 className="text-2xl font-medium text-zinc-900">Vibration Trend</h2>
                <p className="text-sm text-zinc-500">Combined vertical, horizontal, and axial vibration history for clearer fault analysis.</p>
              </div>
            </div>
            {vibrationSeries.length === 0 ? (
              <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-12 text-center text-sm text-zinc-600">
                No vibration trend data is available for the selected filters. Try selecting a broader date range or different equipment.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={450}>
                <LineChart data={vibrationSeries}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} tickFormatter={(tick) => formatTimestamp(tick)}>
                    <Label value="Time" position="insideBottom" offset={-5} />
                  </XAxis>
                  <YAxis tick={{ fontSize: 12 }}>
                    <Label value="Velocity (mm/s)" angle={-90} position="insideLeft" offset={-5} />
                  </YAxis>
                  <Tooltip labelFormatter={tooltipLabelFormatter} formatter={tooltipFormatter} />
                  <Legend verticalAlign="top" height={32} />
                  <Line type="monotone" dataKey="vertical" name="Vertical Vibration" stroke="#002FA7" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="horizontal" name="Horizontal Vibration" stroke="#E11D48" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="axial" name="Axial Vibration" stroke="#047857" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}
    </div>
  );
} 
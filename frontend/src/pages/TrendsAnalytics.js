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
              <h2 className="text-2xl font-medium text-zinc-900">Temperature Trend</h2>
              <p className="text-sm text-zinc-500">Plotting all historical temperature readings in the selected window.</p>
            </div>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={temperatureData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" name="Temperature" stroke="#002FA7" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-6">
              <h2 className="text-2xl font-medium text-zinc-900">Vibration Trend</h2>
              <p className="text-sm text-zinc-500">Plotting vertical, horizontal, and axial vibration history.</p>
            </div>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={vibrationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" name="Vibration" stroke="#E11D48" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
} 
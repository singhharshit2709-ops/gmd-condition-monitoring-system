import { useEffect, useMemo, useState } from "react";
import axios from "axios";
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
import { getApiBase } from "@/lib/api";
import {
  buildConfigLookups,
  matchConfiguredEquipmentInArea,
  parseTimestamp,
  readingVisibleInDashboardArea,
  resolveReadingArea,
} from "@/lib/dashboardAnalytics";
import {
  getEquipmentForTrendsArea,
  getTrendsAreaOptions,
} from "@/lib/trendsAnalytics";

const API = getApiBase();
const STANDARD_PARAMETERS = [
  "Vertical Vibration",
  "Horizontal Vibration",
  "Axial Vibration",
  "Temperature",
  "Current",
  "Voltage",
  "Pressure",
];

const normalizeParameterKey = (parameter) =>
  String(parameter || "")
    .trim()
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\s+/g, " ");

const PARAMETER_LABELS = {
  "vertical vibration": "Vertical Vibration",
  "horizontal vibration": "Horizontal Vibration",
  "axial vibration": "Axial Vibration",
  temperature: "Temperature",
  current: "Current",
  voltage: "Voltage",
  pressure: "Pressure",
};

const formatParameterLabel = (parameter) => {
  const key = normalizeParameterKey(parameter);
  return PARAMETER_LABELS[key] ||
    key
      .split(" ")
      .filter(Boolean)
      .map((word) => word[0].toUpperCase() + word.slice(1))
      .join(" ");
};

const formatParameterDisplayValue = (parameter, value) => {
  if (value === null || value === undefined || String(value).trim() === "") {
    return "N/A";
  }

  const parsed = Number(String(value).trim());
  const key = normalizeParameterKey(parameter);

  const suffix =
    key === "temperature"
      ? " °C"
      : key === "current"
      ? " A"
      : key === "voltage"
      ? " V"
      : "";

  return Number.isNaN(parsed) ? String(value) : `${parsed}${suffix}`;
};

const STANDARD_PARAMETER_KEYS = STANDARD_PARAMETERS.map(normalizeParameterKey);

const formatTimestamp = (value) => {
  if (!value) {
    return "—";
  }

  const date = parseTimestamp(value);
  if (!date) {
    return value;
  }

  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

function readingMatchesEquipment(row, equipmentEntry, area, lookups) {
  if (!row || !equipmentEntry || !area) return false;
  if (!readingVisibleInDashboardArea(row, area, lookups)) return false;

  const meta = matchConfiguredEquipmentInArea(row, area, lookups);
  if (!meta || meta.display_name !== equipmentEntry.display_name) return false;

  if (equipmentEntry.tag_no) {
    const rowTag = String(row.tag_no || "").trim();
    if (rowTag && rowTag !== equipmentEntry.tag_no) return false;
  }

  return true;
}

const ConditionMonitoring = () => {
  const lookups = useMemo(() => buildConfigLookups(), []);
  const areaOptions = useMemo(() => getTrendsAreaOptions(), []);

  const [readings, setReadings] = useState([]);
  const [selectedArea, setSelectedArea] = useState("");
  const [selectedEquipmentEntry, setSelectedEquipmentEntry] = useState(null);
  const [selectedParameter, setSelectedParameter] = useState("Temperature");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const selectedEquipment = selectedEquipmentEntry?.display_name || "";

  const equipmentEntries = useMemo(
    () => (selectedArea ? getEquipmentForTrendsArea(selectedArea) : []),
    [selectedArea]
  );

  const equipmentWithReadings = useMemo(() => {
    if (!selectedArea) return new Set();
    const names = new Set();
    for (const row of readings) {
      if (!readingVisibleInDashboardArea(row, selectedArea, lookups)) continue;
      const meta = matchConfiguredEquipmentInArea(row, selectedArea, lookups);
      if (meta) names.add(meta.display_name);
    }
    return names;
  }, [readings, selectedArea, lookups]);

  const dataSourceLabel = "Google Sheets";
  const dataSourceStatus = "Connected";

  useEffect(() => {
    loadReadings();
    const onReadingsUpdated = () => loadReadings();
    window.addEventListener("gmd-readings-updated", onReadingsUpdated);
    return () => window.removeEventListener("gmd-readings-updated", onReadingsUpdated);
  }, []);

  const handleAreaChange = (area) => {
    setSelectedArea(area);
    setSelectedEquipmentEntry(null);
  };

  const loadReadings = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await axios.get(`${API}/reports/readings`);
      const rows = Array.isArray(response.data) ? response.data : [];
      setReadings(rows);
    } catch (e) {
      console.error("Failed to load condition monitoring readings:", e);
      setError("Unable to load equipment readings. Please try again later.");
      setReadings([]);
    } finally {
      setLoading(false);
    }
  };

  const parameterOptions = useMemo(() => {
    if (!selectedEquipmentEntry) return [];

    const equipmentRows = readings.filter((row) =>
      readingMatchesEquipment(row, selectedEquipmentEntry, selectedArea, lookups)
    );

    const parameterKeys = new Map();
    for (const row of equipmentRows) {
      const key = normalizeParameterKey(row.parameter);
      if (!key) continue;
      parameterKeys.set(key, row.parameter);
    }

    const standard = STANDARD_PARAMETER_KEYS.filter((key) => parameterKeys.has(key));
    const others = Array.from(parameterKeys.keys()).filter(
      (key) => !STANDARD_PARAMETER_KEYS.includes(key)
    );
    others.sort();

    return [
      ...standard.map((key) => formatParameterLabel(key)),
      ...others.map((key) => formatParameterLabel(key)),
    ];
  }, [readings, selectedEquipmentEntry, selectedArea, lookups]);

  useEffect(() => {
    if (
      parameterOptions.length > 0 &&
      !parameterOptions.includes(selectedParameter)
    ) {
      setSelectedParameter(parameterOptions[0]);
    }
  }, [parameterOptions, selectedParameter]);

  useEffect(() => {
    if (!selectedEquipmentEntry) return;
    const stillValid = equipmentEntries.some(
      (entry) =>
        entry.display_name === selectedEquipmentEntry.display_name &&
        entry.tag_no === selectedEquipmentEntry.tag_no
    );
    if (!stillValid) setSelectedEquipmentEntry(null);
  }, [equipmentEntries, selectedEquipmentEntry]);

  const equipmentRows = useMemo(
    () =>
      selectedEquipmentEntry
        ? readings
            .filter((row) =>
              readingMatchesEquipment(row, selectedEquipmentEntry, selectedArea, lookups)
            )
            .sort((a, b) => {
              const left = parseTimestamp(a.timestamp)?.getTime() ?? 0;
              const right = parseTimestamp(b.timestamp)?.getTime() ?? 0;
              return right - left;
            })
        : [],
    [readings, selectedEquipmentEntry, selectedArea, lookups]
  );

  const latestTimestamp = useMemo(() => equipmentRows[0]?.timestamp || null, [equipmentRows]);

  const latestReadingsByParameter = useMemo(() => {
    if (!latestTimestamp) {
      return [];
    }

    const latestRows = equipmentRows.filter((row) => row.timestamp === latestTimestamp);
    const uniqueLatest = new Map();

    for (const row of latestRows) {
      const key = normalizeParameterKey(row.parameter);
      if (!key || uniqueLatest.has(key)) {
        continue;
      }

      uniqueLatest.set(key, row);
    }

    const standard = STANDARD_PARAMETER_KEYS.filter((key) => uniqueLatest.has(key));
    const others = Array.from(uniqueLatest.keys()).filter(
      (key) => !STANDARD_PARAMETER_KEYS.includes(key)
    );
    others.sort();

    return [...standard, ...others].map((key) => uniqueLatest.get(key));
  }, [equipmentRows, latestTimestamp]);

  const equipmentSummary = useMemo(() => {
    const latestRow = equipmentRows[0] || {};
    return {
      name: selectedEquipment || "—",
      category: latestRow.category || "—",
      parametersMonitoredCount: parameterOptions.length,
      historicalRecordsCount: equipmentRows.length,
      latestReadingTimestamp: formatTimestamp(latestTimestamp),
      lastVerifiedBy: latestRow.verified_by || "—",
    };
  }, [equipmentRows, parameterOptions.length, selectedEquipment, latestTimestamp]);

  const totalEquipments = selectedArea ? equipmentEntries.length : null;
  const totalParameters = parameterOptions.length;
  const historicalRecords = equipmentRows.length;
  const lastUpdatedText = latestTimestamp ? formatTimestamp(latestTimestamp) : "—";

  const equipmentCountLabel = selectedArea
    ? `${totalEquipments} Equipment in ${selectedArea}`
    : "Select an area";
  const parameterCountLabel = selectedEquipment ? `${totalParameters} Parameters` : "—";
  const historicalRecordsLabel = selectedEquipment ? `${historicalRecords} Readings` : "—";

  const chartData = useMemo(() => {
    return equipmentRows
      .filter(
        (row) =>
          normalizeParameterKey(row.parameter) ===
          normalizeParameterKey(selectedParameter)
      )
      .map((row) => {
        const value = Number(row.value);
        if (Number.isNaN(value)) {
          return null;
        }

        return {
          time: formatTimestamp(row.timestamp),
          value,
          timestamp: row.timestamp,
        };
      })
      .filter(Boolean)
      .sort((a, b) => {
        const left = parseTimestamp(a.timestamp)?.getTime() ?? 0;
        const right = parseTimestamp(b.timestamp)?.getTime() ?? 0;
        return left - right;
      });
  }, [equipmentRows, selectedParameter]);

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-4xl font-light tracking-tight text-zinc-950">Condition Monitoring</h1>
          <p className="text-sm text-zinc-700 mt-2">View equipment readings and historical trends from Google Sheets.</p>
        </div>
        <button
          onClick={loadReadings}
          className="inline-flex items-center justify-center rounded-none border border-[#002FA7] bg-[#002FA7] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#002FA7]/90"
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5 mb-6">
        <div className="rounded-none border border-zinc-200 bg-white px-5 py-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Area Equipment</p>
          <p className="mt-3 text-2xl font-semibold text-zinc-950">{equipmentCountLabel}</p>
        </div>
        <div className="rounded-none border border-zinc-200 bg-white px-5 py-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Parameters Monitored</p>
          <p className="mt-3 text-3xl font-semibold text-zinc-950">{parameterCountLabel}</p>
        </div>
        <div className="rounded-none border border-zinc-200 bg-white px-5 py-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Historical Records</p>
          <p className="mt-3 text-3xl font-semibold text-zinc-950">{historicalRecordsLabel}</p>
        </div>
        <div className="rounded-none border border-zinc-200 bg-white px-5 py-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Latest Update</p>
          <p className="mt-3 text-3xl font-semibold text-zinc-950">{lastUpdatedText}</p>
        </div>
        <div className="rounded-none border border-zinc-200 bg-white px-5 py-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Data Source</p>
          <p className="mt-3 text-sm font-medium text-zinc-950">{dataSourceLabel}</p>
          <p className="mt-1 inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-emerald-700 font-semibold">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-sm"></span>
            {dataSourceStatus}
          </p>
        </div>
      </div>

      {error ? (
        <div className="mb-6 rounded-none border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <div className="rounded-none border border-zinc-200 bg-white p-6 mb-4">
            <h2 className="text-lg font-medium text-zinc-900 mb-1">Area / Tank</h2>
            <p className="text-xs text-zinc-500 mb-4">Select an area to browse its equipment</p>
            <select
              value={selectedArea}
              onChange={(event) => handleAreaChange(event.target.value)}
              className="w-full rounded-none border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
            >
              <option value="">Choose area…</option>
              {areaOptions.map((area) => (
                <option key={area} value={area}>
                  {area}
                </option>
              ))}
            </select>
            {selectedArea ? (
              <p className="mt-3 text-xs text-zinc-600">
                {equipmentEntries.length} configured equipment
                {equipmentWithReadings.size > 0
                  ? ` · ${equipmentWithReadings.size} with historical readings`
                  : ""}
              </p>
            ) : null}
          </div>

          <div className="rounded-none border border-zinc-200 bg-white p-6 mb-4">
            <h2 className="text-lg font-medium text-zinc-900 mb-4">Equipment</h2>
            {!selectedArea ? (
              <div className="text-sm text-zinc-500">Select an area to view equipment.</div>
            ) : loading ? (
              <div className="text-sm text-zinc-600">Loading equipment list...</div>
            ) : equipmentEntries.length === 0 ? (
              <div className="text-sm text-zinc-500">No equipment configured for this area.</div>
            ) : (
              <div className="space-y-2 max-h-[28rem] overflow-y-auto pr-1">
                {equipmentEntries.map((entry) => {
                  const isSelected =
                    selectedEquipmentEntry?.display_name === entry.display_name &&
                    selectedEquipmentEntry?.tag_no === entry.tag_no;
                  const hasReadings = equipmentWithReadings.has(entry.display_name);

                  return (
                    <button
                      key={`${entry.id}-${entry.tag_no || entry.display_name}`}
                      onClick={() => setSelectedEquipmentEntry(entry)}
                      className={`w-full text-left rounded-none border px-4 py-3 text-sm transition ${
                        isSelected
                          ? "border-[#002FA7] bg-[#002FA7] text-white"
                          : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400"
                      }`}
                    >
                      <span className="font-medium block">{entry.display_name}</span>
                      <span
                        className={`mt-1 block text-xs ${
                          isSelected ? "text-white/80" : "text-zinc-500"
                        }`}
                      >
                        {entry.category}
                        {entry.tag_no ? ` · ${entry.tag_no}` : ""}
                        {!hasReadings ? " · No readings yet" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="rounded-none border border-zinc-200 bg-white p-6">
            <h2 className="text-lg font-medium text-zinc-900 mb-4">Parameter</h2>
            <select
              value={selectedParameter}
              onChange={(event) => setSelectedParameter(event.target.value)}
              disabled={!selectedEquipment}
              className="w-full rounded-none border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {!selectedEquipment ? (
                <option value="">Select equipment first</option>
              ) : parameterOptions.length > 0 ? (
                parameterOptions.map((parameter) => (
                  <option key={parameter} value={parameter}>
                    {parameter}
                  </option>
                ))
              ) : (
                <option value="">No parameters available</option>
              )}
            </select>
          </div>
        </div>

        <div className="lg:col-span-9">
          <div className="rounded-none border border-zinc-200 bg-white p-6">
            <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-lg font-medium text-zinc-900">
                  {!selectedArea
                    ? "Select an area to begin"
                    : !selectedEquipment
                    ? `${selectedArea} — Select equipment to view readings`
                    : `${selectedArea} · ${selectedEquipment} — Historical ${selectedParameter} Trend`}
                </h2>
                {selectedEquipment && (
                  <p className="text-sm text-zinc-600 mt-1">{equipmentRows.length} readings available.</p>
                )}
              </div>
            </div>

            {!selectedArea ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-sm text-zinc-500">Choose an area / tank from the left panel.</p>
              </div>
            ) : !selectedEquipment ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-sm text-zinc-500">
                  {equipmentEntries.length} equipment in {selectedArea}. Select one to view monitoring data.
                </p>
              </div>
            ) : loading ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-sm text-zinc-600">Loading data...</p>
              </div>
            ) : (
              <>
                <div className="rounded-none border border-zinc-200 bg-white p-6 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-medium text-zinc-900">Latest Reading Snapshot</h3>
                    <p className="text-xs text-zinc-500">As of {equipmentSummary.latestReadingTimestamp}</p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {latestReadingsByParameter.length === 0 ? (
                      <div className="col-span-full text-sm text-zinc-500">No latest snapshot data available.</div>
                    ) : (
                      latestReadingsByParameter.map((row) => (
                        <div key={normalizeParameterKey(row.parameter)} className="rounded-none border border-zinc-200 bg-zinc-50 p-4">
                          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-bold">{formatParameterLabel(row.parameter)}</p>
                          <p className="mt-3 text-2xl font-semibold text-zinc-950">{formatParameterDisplayValue(row.parameter, row.value)}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-none border border-zinc-200 bg-white p-5 mb-6">
                  <h3 className="text-sm font-medium text-zinc-900 mb-4">Equipment Summary</h3>
                  <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Area / Tank</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{selectedArea}</dd>
                    </div>
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Equipment Name</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{equipmentSummary.name}</dd>
                    </div>
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Category</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{equipmentSummary.category}</dd>
                    </div>
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Parameters Monitored</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{equipmentSummary.parametersMonitoredCount} Parameters</dd>
                    </div>
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Historical Records Count</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{equipmentSummary.historicalRecordsCount}</dd>
                    </div>
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Latest Reading Timestamp</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{equipmentSummary.latestReadingTimestamp}</dd>
                    </div>
                    <div className="space-y-1">
                      <dt className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-bold">Last Verified By</dt>
                      <dd className="text-sm text-zinc-900 font-medium">{equipmentSummary.lastVerifiedBy}</dd>
                    </div>
                  </dl>
                </div>

                {chartData.length === 0 ? (
                  <div className="h-96 flex items-center justify-center">
                    <p className="text-sm text-zinc-500">No readings available for selected equipment</p>
                  </div>
                ) : (
                  <div data-testid="chart-container">
                    <ResponsiveContainer width="100%" height={450}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                        <XAxis dataKey="time" tick={{ fontSize: 12, fill: "#71717a" }} stroke="#a1a1aa" />
                        <YAxis tick={{ fontSize: 12, fill: "#71717a", fontFamily: "IBMPlexMono, monospace" }} stroke="#a1a1aa" />
                        <Tooltip contentStyle={{ backgroundColor: "white", border: "1px solid #e4e4e7", borderRadius: 0, fontSize: 12 }} />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                        <Line type="monotone" dataKey="value" stroke="#002FA7" strokeWidth={2} dot={{ fill: "#002FA7", r: 4 }} activeDot={{ r: 6 }} name={selectedParameter} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                <div className="mt-6 border-t border-zinc-200 pt-6">
                  <h3 className="text-sm font-medium text-zinc-900 mb-3">Latest Readings</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-zinc-200">
                          <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Parameter</th>
                          <th className="text-right px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Value</th>
                          <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Status</th>
                          <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {latestReadingsByParameter.length === 0 ? (
                          <tr>
                            <td colSpan={4} className="px-4 py-4 text-sm text-zinc-500 text-center">No latest readings available for selected equipment.</td>
                          </tr>
                        ) : (
                          latestReadingsByParameter.map((row, idx) => (
                            <tr key={idx} className="even:bg-zinc-50/50 border-b border-zinc-100">
                              <td className="px-4 py-2 text-sm text-zinc-700">{formatParameterLabel(row.parameter)}</td>
                              <td className="px-4 py-2 text-sm font-mono text-zinc-950 text-right">{formatParameterDisplayValue(row.parameter, row.value)}</td>
                              <td className="px-4 py-2">
                                <span className={`px-2 py-1 text-xs font-bold uppercase tracking-wider rounded-none ${
                                  row.status?.toLowerCase() === "alarm"
                                    ? "bg-red-50 text-red-700"
                                    : row.status?.toLowerCase() === "warning"
                                    ? "bg-yellow-50 text-yellow-800"
                                    : "bg-emerald-50 text-emerald-700"
                                }`}>
                                  {row.status || "Unknown"}
                                </span>
                              </td>
                              <td className="px-4 py-2 text-sm text-zinc-700 whitespace-nowrap">{formatTimestamp(row.timestamp)}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConditionMonitoring;

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

const formatTimestamp = (value) => {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
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

const ConditionMonitoring = () => {
  const [readings, setReadings] = useState([]);
  const [equipmentList, setEquipmentList] = useState([]);
  const [selectedEquipment, setSelectedEquipment] = useState("");
  const [selectedParameter, setSelectedParameter] = useState("Temperature");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadReadings();
  }, []);

  useEffect(() => {
    if (!selectedEquipment && equipmentList.length > 0) {
      setSelectedEquipment(equipmentList[0]);
    }
  }, [equipmentList, selectedEquipment]);

  const loadReadings = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await axios.get(`${API}/reports/readings`);
      const rows = Array.isArray(response.data) ? response.data : [];
      setReadings(rows);

      const equipment = Array.from(
        new Set(
          rows
            .map((row) => (row.equipment || "").trim())
            .filter(Boolean)
        )
      ).sort();

      setEquipmentList(equipment);
    } catch (e) {
      console.error("Failed to load condition monitoring readings:", e);
      setError("Unable to load equipment readings. Please try again later.");
      setReadings([]);
      setEquipmentList([]);
    } finally {
      setLoading(false);
    }
  };

  const parameterOptions = useMemo(() => {
    const equipmentRows = readings.filter(
      (row) => row.equipment === selectedEquipment
    );

    const available = Array.from(
      new Set(
        equipmentRows
          .map((row) => String(row.parameter || "").trim())
          .filter(Boolean)
      )
    );

    const sortedStandard = STANDARD_PARAMETERS.filter((param) =>
      available.includes(param)
    );
    const others = available.filter((param) => !STANDARD_PARAMETERS.includes(param));
    return [...sortedStandard, ...others];
  }, [readings, selectedEquipment]);

  useEffect(() => {
    if (
      parameterOptions.length > 0 &&
      !parameterOptions.includes(selectedParameter)
    ) {
      setSelectedParameter(parameterOptions[0]);
    }
  }, [parameterOptions, selectedParameter]);

  const equipmentRows = useMemo(
    () =>
      readings
        .filter((row) => row.equipment === selectedEquipment)
        .sort((a, b) => {
          const left = new Date(a.timestamp || "");
          const right = new Date(b.timestamp || "");
          return right - left;
        }),
    [readings, selectedEquipment]
  );

  const latestReadings = useMemo(() => equipmentRows.slice(0, 15), [equipmentRows]);

  const chartData = useMemo(() => {
    return equipmentRows
      .filter((row) => row.parameter === selectedParameter)
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
        const left = new Date(a.timestamp);
        const right = new Date(b.timestamp);
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

      {error ? (
        <div className="mb-6 rounded-none border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <div className="rounded-none border border-zinc-200 bg-white p-6 mb-4">
            <h2 className="text-lg font-medium text-zinc-900 mb-4">Equipment</h2>
            {loading ? (
              <div className="text-sm text-zinc-600">Loading equipment list...</div>
            ) : equipmentList.length === 0 ? (
              <div className="text-sm text-zinc-500">No equipment available.</div>
            ) : (
              <div className="space-y-2">
                {equipmentList.map((equipment) => (
                  <button
                    key={equipment}
                    onClick={() => setSelectedEquipment(equipment)}
                    className={`w-full text-left rounded-none border px-4 py-3 text-sm font-medium transition ${
                      selectedEquipment === equipment
                        ? "border-[#002FA7] bg-[#002FA7] text-white"
                        : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400"
                    }`}
                  >
                    {equipment}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-none border border-zinc-200 bg-white p-6">
            <h2 className="text-lg font-medium text-zinc-900 mb-4">Parameter</h2>
            <select
              value={selectedParameter}
              onChange={(event) => setSelectedParameter(event.target.value)}
              className="w-full rounded-none border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
            >
              {parameterOptions.length > 0 ? (
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
                  {selectedEquipment ? `${selectedEquipment} — ${selectedParameter} trend` : "Select equipment to view readings"}
                </h2>
                {selectedEquipment && (
                  <p className="text-sm text-zinc-600 mt-1">{equipmentRows.length} readings available.</p>
                )}
              </div>
            </div>

            {!selectedEquipment ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-sm text-zinc-500">Select equipment to view its readings.</p>
              </div>
            ) : loading ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-sm text-zinc-600">Loading data...</p>
              </div>
            ) : chartData.length === 0 ? (
              <div className="h-96 flex items-center justify-center">
                <p className="text-sm text-zinc-500">No readings available for selected equipment</p>
              </div>
            ) : (
              <div data-testid="chart-container">
                <ResponsiveContainer width="100%" height={400}>
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

            {selectedEquipment && !loading && (
              <div className="mt-6 border-t border-zinc-200 pt-6">
                <h3 className="text-sm font-medium text-zinc-900 mb-3">Latest Readings</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-zinc-200">
                        <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Timestamp</th>
                        <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Parameter</th>
                        <th className="text-right px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Value</th>
                        <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Status</th>
                        <th className="text-left px-4 py-2 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">Verified By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {latestReadings.map((row, idx) => (
                        <tr key={idx} className="even:bg-zinc-50/50 border-b border-zinc-100">
                          <td className="px-4 py-2 text-sm text-zinc-700 whitespace-nowrap">{formatTimestamp(row.timestamp)}</td>
                          <td className="px-4 py-2 text-sm text-zinc-700">{row.parameter || "—"}</td>
                          <td className="px-4 py-2 text-sm font-mono text-zinc-950 text-right">{row.value ?? "—"}</td>
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
                          <td className="px-4 py-2 text-sm text-zinc-700">{row.verified_by || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConditionMonitoring;

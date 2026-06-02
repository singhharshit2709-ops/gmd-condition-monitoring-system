import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { getApiBase } from "@/lib/api";

const API = getApiBase();

const Reports = () => {
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [equipmentFilter, setEquipmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await axios.get(`${API}/reports/readings`);
      setReadings(response.data || []);
    } catch (loadError) {
      console.error("Reports fetch failed:", loadError);
      setError("Unable to load reports. Please try again.");
      setReadings([]);
    } finally {
      setLoading(false);
    }
  };

  const categories = useMemo(
    () =>
      Array.from(
        new Set(
          readings
            .map((row) => row.category)
            .filter((value) => typeof value === "string" && value.trim() !== "")
        )
      ).sort(),
    [readings]
  );

  const equipmentList = useMemo(
    () =>
      Array.from(
        new Set(
          readings
            .map((row) => row.equipment)
            .filter((value) => typeof value === "string" && value.trim() !== "")
        )
      ).sort(),
    [readings]
  );

  const filteredReadings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const start = startDate ? new Date(`${startDate}T00:00:00`) : null;
    const end = endDate ? new Date(`${endDate}T23:59:59`) : null;

    return readings.filter((row) => {
      if (categoryFilter && row.category !== categoryFilter) {
        return false;
      }

      if (equipmentFilter && row.equipment !== equipmentFilter) {
        return false;
      }

      if (statusFilter && row.status !== statusFilter) {
        return false;
      }

      if (start || end) {
        const timestamp = row.timestamp ? new Date(row.timestamp) : null;
        if (!timestamp || Number.isNaN(timestamp.getTime())) {
          return false;
        }
        if (start && timestamp < start) {
          return false;
        }
        if (end && timestamp > end) {
          return false;
        }
      }

      if (!query) {
        return true;
      }

      return [
        row.timestamp,
        row.category,
        row.equipment,
        row.parameter,
        row.value,
        row.status,
        row.verified_by,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [readings, searchQuery, categoryFilter, equipmentFilter, statusFilter, startDate, endDate]);

  const summary = useMemo(() => {
    return filteredReadings.reduce(
      (acc, row) => {
        acc.total += 1;
        const status = String(row.status || "").toUpperCase();
        if (status === "NORMAL") acc.normal += 1;
        else if (status === "WARNING") acc.warning += 1;
        else if (status === "ALARM") acc.alarm += 1;
        return acc;
      },
      { total: 0, normal: 0, warning: 0, alarm: 0 }
    );
  }, [filteredReadings]);

  const exportCsv = () => {
    const headers = [
      "Timestamp",
      "Category",
      "Equipment",
      "Parameter",
      "Value",
      "Status",
      "Verified By",
    ];
    const rows = filteredReadings.map((row) => [
      row.timestamp || "",
      row.category || "",
      row.equipment || "",
      row.parameter || "",
      row.value ?? "",
      row.status || "",
      row.verified_by || "",
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((cell) => {
            const escaped = String(cell).replace(/"/g, '""');
            return `"${escaped}"`;
          })
          .join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `reports_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-4xl font-light tracking-tight text-zinc-950">
              Condition Monitoring Reports & Historical Data
            </h1>
            <p className="text-sm text-zinc-700 mt-2">
              Explore historical readings, filter records, and export report data for analysis.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              onClick={loadReports}
              className="inline-flex items-center justify-center rounded-md border border-[#002FA7] bg-white px-4 py-2 text-sm font-medium text-[#002FA7] transition hover:bg-[#002FA7] hover:text-white"
            >
              Refresh
            </button>
            <button
              onClick={exportCsv}
              className="inline-flex items-center justify-center rounded-md border border-zinc-200 bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800"
            >
              Export CSV
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4 mb-6">
        <div className="rounded-3xl border border-zinc-200 bg-white px-6 py-5 shadow-sm">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Total Readings</p>
          <p className="mt-3 text-3xl font-light text-zinc-950">{summary.total}</p>
        </div>
        <div className="rounded-3xl border border-zinc-200 bg-white px-6 py-5 shadow-sm">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Normal</p>
          <p className="mt-3 text-3xl font-light text-[#16A34A]">{summary.normal}</p>
        </div>
        <div className="rounded-3xl border border-zinc-200 bg-white px-6 py-5 shadow-sm">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Warning</p>
          <p className="mt-3 text-3xl font-light text-yellow-700">{summary.warning}</p>
        </div>
        <div className="rounded-3xl border border-zinc-200 bg-white px-6 py-5 shadow-sm">
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">Alarm</p>
          <p className="mt-3 text-3xl font-light text-[#E11D48]">{summary.alarm}</p>
        </div>
      </div>

      <div className="rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm mb-6">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Search
            </label>
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search by category, equipment, status, or verified by"
              className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Category
            </label>
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
              className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Equipment
            </label>
            <select
              value={equipmentFilter}
              onChange={(event) => setEquipmentFilter(event.target.value)}
              className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
            >
              <option value="">All equipment</option>
              {equipmentList.map((equipment) => (
                <option key={equipment} value={equipment}>
                  {equipment}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
            >
              <option value="">All statuses</option>
              <option value="NORMAL">Normal</option>
              <option value="WARNING">Warning</option>
              <option value="ALARM">Alarm</option>
            </select>
          </div>

          <div className="grid gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
                Start date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
                End date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                className="mt-2 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-[#002FA7] focus:ring-2 focus:ring-[#002FA7]/10"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-zinc-200 bg-white shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-zinc-200">
            <thead className="bg-zinc-50">
              <tr className="text-left text-xs uppercase tracking-[0.18em] text-zinc-500">
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Timestamp</th>
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Category</th>
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Equipment</th>
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Parameter</th>
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Value</th>
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Status</th>
                <th className="sticky top-0 border-b border-zinc-200 bg-zinc-50 px-4 py-3">Verified By</th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-sm text-zinc-500">
                    Loading reports...
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-sm text-red-600">
                    {error}
                  </td>
                </tr>
              ) : filteredReadings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-sm text-zinc-500">
                    No records match the current filters.
                  </td>
                </tr>
              ) : (
                filteredReadings.map((row, index) => (
                  <tr
                    key={`${row.timestamp}-${row.equipment}-${row.parameter}-${index}`}
                    className={index % 2 === 0 ? "bg-white hover:bg-zinc-50" : "bg-zinc-50 hover:bg-zinc-100"}
                  >
                    <td className="whitespace-nowrap px-4 py-4 text-sm text-zinc-700">
                      {row.timestamp || "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">{row.category || "—"}</td>
                    <td className="px-4 py-4 text-sm text-zinc-700">{row.equipment || "—"}</td>
                    <td className="px-4 py-4 text-sm text-zinc-700">{row.parameter || "—"}</td>
                    <td className="px-4 py-4 text-sm text-zinc-700">{row.value ?? "—"}</td>
                    <td className="px-4 py-4 text-sm">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                          row.status === "ALARM"
                            ? "bg-[#FEE2E2] text-[#B91C1C]"
                            : row.status === "WARNING"
                            ? "bg-[#FEF3C7] text-[#B45309]"
                            : "bg-[#DCFCE7] text-[#166534]"
                        }`}
                      >
                        {row.status || "—"}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">{row.verified_by || "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Reports;
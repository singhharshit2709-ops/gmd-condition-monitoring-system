import { useEffect, useState } from "react";
import axios from "axios";
import { GearSix, Warning } from "@phosphor-icons/react";
import { PLANT_ID, PLANT_LABEL } from "@/lib/gtConfig";
import { getApiBase } from "@/lib/api";

const API = getApiBase();

const Dashboard = () => {
  const [areaHealth, setAreaHealth] = useState([]);
  const [equipmentSummary, setEquipmentSummary] = useState({ total: 0, ok: 0, warning: 0, alarm: 0 });
  const [activeAlarms, setActiveAlarms] = useState([]);
  const [recentReadings, setRecentReadings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [
  summaryResponse,
  recentResponse,
  alarmsResponse,
  healthResponse
] = await Promise.all([
  axios.get(`${API}/dashboard/summary`),
  axios.get(`${API}/dashboard/recent-readings`),
  axios.get(`${API}/dashboard/active-alarms`),
  axios.get(`${API}/dashboard/equipment-health`)
]); 

      setEquipmentSummary(summaryResponse.data);
      setAreaHealth(healthResponse.data); 
      setActiveAlarms(alarmsResponse.data);
      setRecentReadings(recentResponse.data);
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlarm = async (alarmId) => {
    try {
      await axios.post(`${API}/acknowledge-alarm/${alarmId}`);
      await fetchData();
    } catch (e) {
      console.error("POST FAILED:", e);
    }
  };

  const getStatusBadge = (status) => {
    if (!status) return null;
    const s = status.toLowerCase();
    if (s === "alarm" || s === "critical")
      return <span className="px-2 py-1 bg-[#E11D48] text-white text-xs font-bold uppercase tracking-wider">ALARM</span>;
    if (s === "warning")
      return <span className="px-2 py-1 bg-yellow-500 text-white text-xs font-bold uppercase tracking-wider">WARNING</span>;
    return <span className="px-2 py-1 bg-[#16A34A] text-white text-xs font-bold uppercase tracking-wider">NORMAL</span>;
  };



  if (loading) {
    return (
      <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
        <div className="text-sm text-zinc-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-light tracking-tight text-zinc-950">
          Neutral Glass
        </h1>
        <p className="text-sm text-zinc-700 mt-2">
          General Maintenance Department Condition Monitoring System
        </p>
        <p className="text-sm text-zinc-700 mt-2">
          Monitoring equipment health, condition parameters, and maintenance trends across the facility
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 lg:gap-6">
        {activeAlarms.length > 0 ? (
          <div className="col-span-1 md:col-span-12">
            <div className="border-2 border-[#E11D48] bg-red-50 p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Warning size={28} weight="fill" className="text-[#E11D48]" />
                <div>
                  <h3 className="text-xl font-medium tracking-tight text-[#E11D48]">
                    {activeAlarms.length} active alarm{activeAlarms.length > 1 ? "s" : ""} — immediate action required
                  </h3>
                  <p className="text-sm text-red-700 mt-1">Equipment exceeding configured thresholds</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {activeAlarms.map((alarm, idx) => (
                  <div key={alarm.id || idx} className="bg-white border-2 border-red-300 p-4" data-testid="alarm-card">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-base font-medium text-zinc-950">
                          {alarm.equipment}
                        </p>
                        <p className="text-xs text-zinc-500 mt-1">{alarm.category || "—"}</p>
                      </div>
                      <span className="px-2 py-1 bg-[#E11D48] text-white text-xs font-bold uppercase">ALARM</span>
                    </div>
                    <button
                      onClick={() => acknowledgeAlarm(alarm.id)}
                      className="mb-3 px-3 py-1 bg-zinc-900 text-white text-xs uppercase tracking-[0.2em]"
                    >
                      Acknowledge
                    </button>
                    <div className="mt-3 space-y-2">
                      {alarm.parameter && (
                        <div className="border-l-2 border-red-200 pl-3">
                          <p className="text-sm text-zinc-700">
                            <span className="font-bold">Parameter:</span>
                            <span className="font-mono text-[#E11D48] font-bold ml-2">{alarm.parameter}</span>
                          </p>
                        </div>
                      )}
                      {alarm.value != null && alarm.value !== "" && (
                        <div className="border-l-2 border-red-200 pl-3">
                          <p className="text-sm text-zinc-700">
                            <span className="font-bold">Value:</span>
                            <span className="font-mono text-[#E11D48] font-bold ml-2">{alarm.value}</span>
                          </p>
                        </div>
                      )}
                      <p className="text-xs text-zinc-500 pt-2 border-t border-zinc-100">
                        {alarm.timestamp ? new Date(alarm.timestamp).toLocaleString() : ""}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="col-span-1 md:col-span-12">
            <div className="border-2 border-[#16A34A] bg-green-50 p-6">
              <div className="flex items-center space-x-3">
                <GearSix size={28} weight="fill" className="text-[#16A34A]" />
                <div>
                  <h3 className="text-xl font-medium tracking-tight text-[#16A34A]">All systems normal</h3>
                  <p className="text-sm text-green-700 mt-1">No active alarms on monitored equipment</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="col-span-1 md:col-span-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white border border-zinc-200 p-6 rounded-lg">
            <p className="text-sm uppercase tracking-[0.2em] text-zinc-500 mb-2">Total equipment</p>
            <h2 className="text-4xl font-light text-zinc-950">{equipmentSummary.total}</h2>
            <p className="text-sm text-zinc-500 mt-2">{PLANT_LABEL}</p>
          </div>
          <div className="bg-white border border-green-200 p-6 rounded-lg">
            <p className="text-sm uppercase tracking-[0.2em] text-green-700 mb-2">Normal</p>
            <h2 className="text-4xl font-light text-green-700">{equipmentSummary.ok}</h2>
            <p className="text-sm text-green-600 mt-2">Within limits</p>
          </div>
          <div className="bg-white border border-yellow-200 p-6 rounded-lg">
            <p className="text-sm uppercase tracking-[0.2em] text-yellow-700 mb-2">Warning</p>
            <h2 className="text-4xl font-light text-yellow-700">{equipmentSummary.warning}</h2>
            <p className="text-sm text-yellow-600 mt-2">Needs inspection</p>
          </div>
          <div className="bg-white border border-red-200 p-6 rounded-lg">
            <p className="text-sm uppercase tracking-[0.2em] text-red-700 mb-2">Alarm</p>
            <h2 className="text-4xl font-light text-red-700">{equipmentSummary.alarm}</h2>
            <p className="text-sm text-red-600 mt-2">Immediate action</p>
          </div>
        </div>

        <div className="col-span-1 md:col-span-12">
          <div className="border border-zinc-200 bg-white p-6">
            <h3 className="text-2xl font-light tracking-tight text-zinc-900 mb-6">Area health overview</h3>
            {areaHealth.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                {areaHealth.map((area) => (
                  <div
                    key={area.equipment}
                    className="border-l-4 border-[#002FA7] pl-4 py-3"
                    data-testid={`area-health-${area.equipment}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-zinc-950 leading-tight">{area.equipment}</h4>
                      <span
                        className={`text-2xl font-mono font-light ${
                          area.health_percentage >= 90 ? "text-[#16A34A]" : area.health_percentage >= 70 ? "text-yellow-700" : "text-[#E11D48]"
                        }`}
                      >
                        {area.health_percentage}%
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-xs">
                      <span className="text-zinc-600">OK: <span className="font-mono font-bold">{area.normal_count}</span></span>
                      <span className="text-zinc-600">Warn: <span className="font-mono font-bold">{area.warning_count}</span></span>
                      <span className="text-zinc-600">Alarm: <span className="font-mono font-bold">{area.alarm_count}</span></span>
                      <span className="text-zinc-600">Total: <span className="font-mono font-bold">{area.total_readings}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-zinc-500">No monitoring data yet. Add readings from Bulk Entry.</p>
              </div>
            )}
          </div>
        </div>

        <div className="col-span-1 md:col-span-12">
          <div className="border border-zinc-200 bg-white p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-light tracking-tight text-zinc-900">Recent readings</h3>
                <p className="text-sm text-zinc-500 mt-1">Latest equipment data — {PLANT_LABEL}</p>
              </div>
              <button
                onClick={fetchData}
                className="px-4 py-2 border border-[#002FA7] text-[#002FA7] text-sm font-medium hover:bg-[#002FA7] hover:text-white transition-colors duration-150"
              >
                Refresh
              </button>
            </div>

            {recentReadings.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-zinc-200">
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Timestamp</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Category</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Equipment</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Parameter</th>
                      <th className="text-right py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Value</th>
                      <th className="text-center py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Status</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-[0.15em] text-zinc-500 font-medium">Verified By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentReadings.map((reading, idx) => (
                      <tr
                        key={idx}
                        className={`border-b border-zinc-100 hover:bg-zinc-50 transition-colors duration-100 ${
                          idx % 2 === 0 ? "bg-white" : "bg-zinc-50/40"
                        }`}
                        data-testid="recent-reading-row"
                      >
                        <td className="py-3 px-4 font-mono text-xs text-zinc-500 whitespace-nowrap">
                          {reading.timestamp
                            ? new Date(reading.timestamp).toLocaleString("en-GB", {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "—"}
                        </td>
                        <td className="py-3 px-4 text-zinc-700">{reading.category || "—"}</td>
                        <td className="py-3 px-4 text-zinc-600 text-xs">{reading.equipment || "—"}</td>
                        <td className="py-3 px-4 text-zinc-600 text-xs">{reading.parameter || "—"}</td>
                        <td className="py-3 px-4 text-right font-mono font-medium">
                          {reading.value != null && reading.value !== "" ? <span>{reading.value}</span> : <span className="text-zinc-400">—</span>}
                        </td>
                        <td className="py-3 px-4 text-center">{getStatusBadge(reading.status)}</td>
                        <td className="py-3 px-4 text-xs text-zinc-600">{reading.verified_by || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-16 border border-dashed border-zinc-200">
                <p className="text-zinc-400 text-sm">No readings recorded yet.</p>
                <p className="text-zinc-400 text-xs mt-1">Use Bulk Entry to submit area readings.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

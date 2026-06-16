/**
 * Trends & Analytics helpers — config-driven filters and chart transforms.
 */

import {
  collectActiveEquipmentFromConfig,
  collectEquipmentByArea,
  collectRenderableParameters,
  getPlantAreas,
  loadGmdConfigV2,
} from "@/lib/gmdConfigV2";

const DM_WATER_CATEGORIES = new Set([
  "DM Water Electrode Cooling",
  "DM Water Batch Charger",
]);

export const TRENDS_AREA_ORDER = [
  "A Tank",
  "E Tank",
  "G Tank",
  "K Tank",
  "Utility Area",
  "DM Water Electrode Cooling",
];

export const WINDOW_OPTIONS = [
  { label: "All history", value: "all" },
  { label: "Last 7 days", value: "7" },
  { label: "Last 30 days", value: "30" },
  { label: "Last 90 days", value: "90" },
  { label: "Custom range", value: "custom" },
];

const CHART_COLORS = ["#002FA7", "#E11D48", "#16A34A", "#D97706", "#7C3AED", "#0891B2"];

export function getTrendsAreaOptions(config = loadGmdConfigV2()) {
  const physical = getPlantAreas(config).map((a) => a.display_name);
  const ordered = TRENDS_AREA_ORDER.filter(
    (name) => physical.includes(name) || name === "DM Water Electrode Cooling"
  );
  return ordered.length ? ordered : TRENDS_AREA_ORDER;
}

export function getEquipmentForTrendsArea(areaName, config = loadGmdConfigV2()) {
  if (areaName === "DM Water Electrode Cooling") {
    return collectActiveEquipmentFromConfig(config)
      .filter((eq) => DM_WATER_CATEGORIES.has(eq.category_display_name))
      .map((eq) => ({
        id: eq.id,
        display_name: eq.display_name,
        tag_no: eq.tag_no || "",
        category: eq.category_display_name,
        area: "DM Water Electrode Cooling",
        equipment: eq,
      }))
      .sort((a, b) => a.display_name.localeCompare(b.display_name));
  }

  return collectEquipmentByArea(areaName, config).map(({ category, equipment }) => ({
    id: equipment.id,
    display_name: equipment.display_name,
    tag_no: equipment.tag_no || "",
    category: category.display_name,
    area: areaName,
    equipment,
  }));
}

export function getCategoriesForArea(areaName, equipmentEntries) {
  const categories = new Set(equipmentEntries.map((e) => e.category).filter(Boolean));
  return [...categories].sort();
}

export function getParametersForEquipment(equipmentEntry) {
  if (!equipmentEntry?.equipment) return [];
  return collectRenderableParameters(equipmentEntry.equipment).map(({ param, group, section }) => ({
    key: param.key,
    label: param.display_short_label || param.display_full_label || param.key,
    unit: param.unit || "",
    group: group?.label || "",
    section: section?.label || "",
    validation: param.validation || {},
  }));
}

export function findParameterMeta(equipmentEntry, parameterKey) {
  return getParametersForEquipment(equipmentEntry).find((p) => p.key === parameterKey) || null;
}

export function buildTrendRequestParams({ area, equipmentEntry, parameterKey, category, windowOption, startDate, endDate }) {
  const params = {};

  if (area && area !== "DM Water Electrode Cooling") {
    params.area_tank = area;
  }
  if (equipmentEntry) {
    params.equipment = equipmentEntry.display_name;
    if (equipmentEntry.tag_no) params.tag_no = equipmentEntry.tag_no;
  }
  if (parameterKey) params.parameter = parameterKey;
  if (category) params.category = category;

  if (["7", "30", "90"].includes(windowOption)) {
    params.window = Number(windowOption);
  }
  if (windowOption === "custom") {
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
  }

  return params;
}

import { parseTimestamp } from "@/lib/dashboardAnalytics";

export function formatTrendTimestamp(timestamp) {
  const date = parseTimestamp(timestamp);
  if (Number.isNaN(date.getTime())) return String(timestamp || "—");
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatChartTick(timestamp) {
  const date = parseTimestamp(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Build chart rows for one or more parameters (same equipment). */
export function buildChartSeries(readings, parameterKeys) {
  const keys = parameterKeys?.length ? parameterKeys : [];
  if (!keys.length || !readings?.length) return { rows: [], series: [] };

  const byTime = new Map();

  for (const row of readings) {
    const paramKey = row.parameter_key || row.parameter;
    if (!keys.includes(paramKey)) continue;

    const ts = row.timestamp;
    if (!byTime.has(ts)) {
      byTime.set(ts, {
        timestamp: ts,
        label: formatChartTick(ts),
        rawTime: parseTimestamp(ts)?.getTime() ?? 0,
      });
    }
    const point = byTime.get(ts);
    point[paramKey] = Number(row.value);
    point[`${paramKey}_status`] = row.status;
  }

  const rows = [...byTime.values()].sort((a, b) => a.rawTime - b.rawTime);
  const series = keys.map((key, index) => {
    const sample = readings.find((r) => (r.parameter_key || r.parameter) === key);
    return {
      key,
      name: sample?.parameter_display_name || key,
      color: CHART_COLORS[index % CHART_COLORS.length],
      unit: sample?.unit || "",
    };
  });

  return { rows, series };
}

export function computeTrendStats(readings, parameterKey) {
  const filtered = (readings || []).filter(
    (r) => (r.parameter_key || r.parameter) === parameterKey
  );
  if (!filtered.length) {
    return { count: 0, min: null, max: null, avg: null, latest: null, unit: "" };
  }

  const values = filtered.map((r) => Number(r.value)).filter((v) => !Number.isNaN(v));
  const sum = values.reduce((a, b) => a + b, 0);
  const latest = filtered.reduce((best, row) => {
    const t = parseTimestamp(row.timestamp)?.getTime() ?? 0;
    const bestT = parseTimestamp(best.timestamp)?.getTime() ?? 0;
    return t > bestT ? row : best;
  }, filtered[0]);

  return {
    count: values.length,
    min: Math.min(...values),
    max: Math.max(...values),
    avg: values.length ? sum / values.length : null,
    latest: latest.value,
    latestStatus: latest.status,
    latestTime: latest.timestamp,
    unit: latest.unit || "",
  };
}

export function getThresholdLines(parameterMeta) {
  if (!parameterMeta?.validation) return [];
  const lines = [];
  const { warning_limit, alarm_limit } = parameterMeta.validation;
  if (typeof warning_limit === "number") {
    lines.push({ value: warning_limit, label: "Warning", color: "#EAB308" });
  }
  if (typeof alarm_limit === "number") {
    lines.push({ value: alarm_limit, label: "Alarm", color: "#E11D48" });
  }
  return lines;
}

export function groupReadingsByParameter(readings) {
  const groups = new Map();
  for (const row of readings || []) {
    const key = row.parameter_key || row.parameter;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return groups;
}

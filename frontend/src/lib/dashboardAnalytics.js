/**
 * Client-side dashboard analytics derived from existing API payloads + V2 config.
 * No additional API calls — pure transformations for area-first engineering views.
 */

import {
  collectActiveEquipmentFromConfig,
  getEquipmentCountByArea,
  getPlantAreas,
  getTotalEquipmentCount,
  loadGmdConfigV2,
} from "@/lib/gmdConfigV2";

const DM_WATER_CATEGORIES = new Set([
  "DM Water Electrode Cooling",
  "DM Water Batch Charger",
]);

const STATUS_RANK = { NORMAL: 0, WARNING: 1, ALARM: 2 };

/** Trim and collapse whitespace for stable area/equipment matching. */
export function normalizeAreaKey(value) {
  if (value == null || value === "") return "";
  return String(value).trim().replace(/\s+/g, " ");
}

/** Trim equipment/tag identifiers for stable matching. */
export function normalizeEquipmentKey(value) {
  if (value == null || value === "") return "";
  return String(value).trim();
}

/**
 * Build dashboard area order from config: plant areas first, then virtual
 * aggregation buckets (e.g. DM Water Electrode Cooling).
 */
export function buildDashboardAreaOrder(config = loadGmdConfigV2()) {
  const order = [];
  const seen = new Set();

  for (const area of getPlantAreas(config)) {
    const canonical = normalizeAreaKey(area.display_name);
    if (!canonical || seen.has(canonical)) continue;
    seen.add(canonical);
    order.push(area.display_name);
  }

  for (const entry of collectActiveEquipmentFromConfig(config)) {
    const bucket = resolveDashboardArea({
      area: entry.area,
      category: entry.category_display_name,
    });
    const normalized = normalizeAreaKey(bucket);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    order.push(bucket);
  }

  return order;
}

/** Map a raw area label to the canonical dashboard area key. */
export function resolveCanonicalDashboardArea(rawArea, lookups) {
  const normalized = normalizeAreaKey(rawArea);
  if (!normalized) return "";
  if (lookups?.canonicalAreaByNormalized?.has(normalized)) {
    return lookups.canonicalAreaByNormalized.get(normalized);
  }
  const lower = normalized.toLowerCase();
  if (lookups?.canonicalAreaByNormalized?.has(lower)) {
    return lookups.canonicalAreaByNormalized.get(lower);
  }
  for (const area of lookups?.dashboardAreaOrder || []) {
    if (normalizeAreaKey(area).toLowerCase() === lower) return area;
  }
  return String(rawArea).trim();
}

export function normalizeStatus(status) {
  const value = String(status || "NORMAL").trim().toUpperCase();
  if (value === "CRITICAL") return "ALARM";
  if (STATUS_RANK[value] !== undefined) return value;
  return "NORMAL";
}

/** Plant timezone for all sheet timestamps (matches backend GMD_PLANT_TIMEZONE). */
export const PLANT_TIMEZONE = "Asia/Kolkata";
const PLANT_UTC_OFFSET = "+05:30";

function plantCalendarDay(date) {
  return date.toLocaleDateString("en-CA", { timeZone: PLANT_TIMEZONE });
}

function parsePlantWallClock(y, m, d, h, min, s = "0") {
  const sec = String(s).padStart(2, "0");
  const iso = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}T${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}:${sec}${PLANT_UTC_OFFSET}`;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function parseTimestamp(value) {
  if (!value) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }

  const text = String(value).trim();
  if (!text) return null;

  const isoMatch = text.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (isoMatch) {
    const [, y, m, d, h, min, s = "0"] = isoMatch;
    return parsePlantWallClock(y, m, d, h, min, s);
  }

  const dmyMatch = text.match(/^(\d{2})\/(\d{2})\/(\d{4})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (dmyMatch) {
    const [, d, m, y, h, min, s = "0"] = dmyMatch;
    return parsePlantWallClock(y, m, d, h, min, s);
  }

  const dmyDashMatch = text.match(/^(\d{2})-(\d{2})-(\d{4})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (dmyDashMatch) {
    const [, d, m, y, h, min, s = "0"] = dmyDashMatch;
    return parsePlantWallClock(y, m, d, h, min, s);
  }

  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function isToday(date) {
  if (!date) return false;
  return plantCalendarDay(date) === plantCalendarDay(new Date());
}

export function formatTime(value) {
  const date = parseTimestamp(value);
  if (!date) return "—";
  return date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function formatDateTime(value) {
  const date = parseTimestamp(value);
  if (!date) return "—";
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Standard status tokens for consistent dashboard presentation. */
export const DASHBOARD_STATUS = {
  NORMAL: { emoji: "🟢", label: "Normal", tone: "normal" },
  WARNING: { emoji: "🟡", label: "Warning", tone: "warning" },
  ALARM: { emoji: "🔴", label: "Alarm", tone: "alarm" },
  PENDING: { emoji: "⚪", label: "Awaiting Today's Round", tone: "pending" },
  INFO: { emoji: "🔵", label: "Information", tone: "info" },
};

function isYesterday(date, now = new Date()) {
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  return plantCalendarDay(date) === plantCalendarDay(yesterday);
}

/**
 * Human-friendly relative timestamp for dashboard cards.
 * Returns { label, title } where title is the full timestamp for tooltips.
 */
export function formatRelativeTime(value, now = new Date()) {
  const date = parseTimestamp(value);
  if (!date) return { label: "—", title: "" };

  const title = formatDateTime(value);
  const timeStr = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMs >= 0 && diffMins < 1) {
    return { label: "Just now", title };
  }
  if (diffMs >= 0 && diffMins < 60) {
    return { label: `${diffMins} minute${diffMins === 1 ? "" : "s"} ago`, title };
  }
  if (isToday(date)) {
    if (diffHours < 12) {
      return { label: `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`, title };
    }
    return { label: `Today • ${timeStr}`, title };
  }
  if (isYesterday(date, now)) {
    return { label: `Yesterday • ${timeStr}`, title };
  }
  if (diffDays > 0 && diffDays < 7) {
    return { label: `${diffDays} day${diffDays === 1 ? "" : "s"} ago`, title };
  }
  return { label: title, title };
}

/** Convenience wrapper — label only. */
export function formatRelativeTimeLabel(value, now = new Date()) {
  return formatRelativeTime(value, now).label;
}

/** Build lookup maps from V2 config for area/category/tag resolution. */
export function buildConfigLookups(config = loadGmdConfigV2()) {
  const dashboardAreaOrder = buildDashboardAreaOrder(config);
  const canonicalAreaByNormalized = new Map();
  for (const area of dashboardAreaOrder) {
    canonicalAreaByNormalized.set(normalizeAreaKey(area), area);
    canonicalAreaByNormalized.set(normalizeAreaKey(area).toLowerCase(), area);
  }

  const byEquipmentName = new Map();
  const equipmentByName = new Map();
  const byTagNo = new Map();
  const areaEquipment = new Map();
  let totalParameters = 0;

  for (const entry of collectActiveEquipmentFromConfig(config)) {
    const name = entry.display_name;
    const equipNorm = normalizeEquipmentKey(name);
    const equipLookupKey = equipNorm.toLowerCase();
    const area = entry.area || "";
    const meta = {
      area,
      category: entry.category_display_name,
      tag_no: entry.tag_no || "",
      equipment: entry,
      display_name: name,
    };

    byEquipmentName.set(name, meta);
    if (!equipmentByName.has(equipLookupKey)) equipmentByName.set(equipLookupKey, []);
    equipmentByName.get(equipLookupKey).push(meta);

    if (entry.tag_no) {
      byTagNo.set(normalizeEquipmentKey(entry.tag_no).toLowerCase(), meta);
    }

    const bucket = resolveDashboardArea(meta);
    appendUniqueEquipmentMeta(areaEquipment, bucket, meta);
    if (DM_WATER_CATEGORIES.has(meta.category) && meta.area) {
      const physicalArea = resolveCanonicalDashboardArea(meta.area, {
        canonicalAreaByNormalized,
        dashboardAreaOrder,
      });
      if (physicalArea && physicalArea !== bucket) {
        appendUniqueEquipmentMeta(areaEquipment, physicalArea, meta);
      }
    }

    const sections = entry.sections || [];
    for (const section of sections) {
      for (const group of section.groups || []) {
        for (const param of group.parameters || []) {
          if (param.is_visible !== false && param.active !== false) totalParameters += 1;
        }
      }
    }
  }

  return {
    config,
    byEquipmentName,
    equipmentByName,
    byTagNo,
    areaEquipment,
    dashboardAreaOrder,
    canonicalAreaByNormalized,
    totalParameters,
    totalEquipment: getTotalEquipmentCount(config),
    equipmentByArea: getEquipmentCountByArea(config),
  };
}

/** Resolve which dashboard area card an equipment entry belongs to. */
export function resolveDashboardArea(meta) {
  if (DM_WATER_CATEGORIES.has(meta.category)) {
    return "DM Water Electrode Cooling";
  }
  return meta.area || meta.category || "Unknown";
}

export function resolveReadingArea(reading, lookups) {
  if (!reading || !lookups) return "Unknown";

  const areaTank = normalizeAreaKey(reading.area_tank);
  const equipKey = normalizeEquipmentKey(reading.equipment).toLowerCase();
  const tagKey = normalizeEquipmentKey(reading.tag_no).toLowerCase();

  if (reading.category && DM_WATER_CATEGORIES.has(reading.category)) {
    return resolveCanonicalDashboardArea("DM Water Electrode Cooling", lookups);
  }

  if (tagKey && lookups.byTagNo?.has(tagKey)) {
    return resolveDashboardArea(lookups.byTagNo.get(tagKey));
  }

  if (equipKey) {
    const metas = lookups.equipmentByName?.get(equipKey) || [];
    if (areaTank && metas.length > 0) {
      const tankMatch = metas.find(
        (meta) => normalizeAreaKey(meta.area).toLowerCase() === areaTank.toLowerCase()
      );
      if (tankMatch) return resolveDashboardArea(tankMatch);
    }

    for (const dashboardArea of lookups.dashboardAreaOrder || []) {
      const meta = matchConfiguredEquipmentInArea(reading, dashboardArea, lookups);
      if (!meta) continue;
      if (
        !areaTank ||
        normalizeAreaKey(meta.area).toLowerCase() === areaTank.toLowerCase()
      ) {
        return dashboardArea;
      }
    }

    if (metas.length === 1) return resolveDashboardArea(metas[0]);
  }

  if (areaTank) return resolveCanonicalDashboardArea(areaTank, lookups);

  const byName = equipKey ? lookups.byEquipmentName?.get(reading.equipment) : null;
  if (byName) return resolveDashboardArea(byName);

  return normalizeAreaKey(reading.category) || "Unknown";
}

/** Match a sheet reading row to configured equipment within a dashboard area. */
export function matchConfiguredEquipmentInArea(row, dashboardArea, lookups) {
  const equipmentList = lookups.areaEquipment?.get(dashboardArea) || [];
  const equipNorm = normalizeEquipmentKey(row.equipment).toLowerCase();
  const tagNorm = normalizeEquipmentKey(row.tag_no).toLowerCase();
  if (!equipNorm && !tagNorm) return null;

  for (const meta of equipmentList) {
    const aliases = [meta.display_name, meta.tag_no]
      .filter(Boolean)
      .map((value) => normalizeEquipmentKey(value).toLowerCase());
    if (equipNorm && aliases.includes(equipNorm)) return meta;
    if (tagNorm && aliases.includes(tagNorm)) return meta;
  }
  return null;
}

function equipmentMetaKey(meta) {
  return `${meta.display_name}::${meta.tag_no || ""}`;
}

function appendUniqueEquipmentMeta(areaEquipment, areaName, meta) {
  if (!areaName || !meta) return;
  if (!areaEquipment.has(areaName)) areaEquipment.set(areaName, []);
  const list = areaEquipment.get(areaName);
  const key = equipmentMetaKey(meta);
  if (!list.some((item) => equipmentMetaKey(item) === key)) {
    list.push(meta);
  }
}

/**
 * Physical tank area for DM Water category readings (A/E/G/K Tank).
 * Returns empty string when not applicable.
 */
export function getPhysicalTankAreaForReading(row, lookups) {
  if (!row?.category || !DM_WATER_CATEGORIES.has(row.category)) return "";
  const areaTank = normalizeAreaKey(row.area_tank);
  if (!areaTank) return "";
  return resolveCanonicalDashboardArea(areaTank, lookups);
}

/**
 * Dashboard areas where a reading must appear.
 * DM Water readings are visible in both the virtual DM bucket and their physical tank.
 */
export function getDashboardAreasForReading(row, lookups) {
  const areas = [];
  const seen = new Set();
  const add = (area) => {
    if (!area || seen.has(area)) return;
    seen.add(area);
    areas.push(area);
  };

  add(resolveReadingArea(row, lookups));
  add(getPhysicalTankAreaForReading(row, lookups));
  return areas;
}

/** True when a reading belongs to a dashboard area (including shared DM Water equipment). */
export function readingVisibleInDashboardArea(row, dashboardArea, lookups) {
  if (!row || !dashboardArea || !lookups) return false;
  return getDashboardAreasForReading(row, lookups).includes(dashboardArea);
}

export function deriveAreaStatus({ alarm, warning, hasTodayReadings }) {
  if (!hasTodayReadings) return "PENDING";
  if (alarm > 0) return "ALARM";
  if (warning > 0) return "WARNING";
  return "NORMAL";
}

/** Equipment touched today per dashboard area (canonical equipment display names). */
export function getTodayTouchedByArea(recentReadings, lookups) {
  const areaOrder = lookups.dashboardAreaOrder || buildDashboardAreaOrder(lookups.config);
  const touched = new Map();
  for (const area of areaOrder) {
    touched.set(area, new Set());
  }

  for (const row of recentReadings || []) {
    if (!isToday(parseTimestamp(row.timestamp))) continue;

    for (const area of getDashboardAreasForReading(row, lookups)) {
      const bucket = touched.get(area);
      if (!bucket) continue;

      const meta = matchConfiguredEquipmentInArea(row, area, lookups);
      if (meta) bucket.add(normalizeEquipmentKey(meta.display_name).toLowerCase());
    }
  }

  return touched;
}

/** Aggregate equipment-health rows into area-first summaries. */
export function computeAreaSummaries(equipmentHealth, recentReadings, lookups) {
  const todayTouched = getTodayTouchedByArea(recentReadings, lookups);
  const healthByName = new Map(
    (equipmentHealth || []).map((row) => [row.equipment, row])
  );

  return (lookups.dashboardAreaOrder || buildDashboardAreaOrder(lookups.config)).map((area) => {
    const equipmentList = lookups.areaEquipment.get(area) || [];
    const configuredCount = equipmentList.length;
    const touchedNames = todayTouched.get(area) || new Set();
    const touchedToday = new Set();
    for (const meta of equipmentList) {
      if (touchedNames.has(normalizeEquipmentKey(meta.display_name).toLowerCase())) {
        touchedToday.add(meta.display_name);
      }
    }

    const hasTodayReadings = touchedToday.size > 0;

    let normal = 0;
    let warning = 0;
    let alarm = 0;
    let lastUpdated = null;

    if (hasTodayReadings) {
      for (const meta of equipmentList) {
        if (!touchedNames.has(normalizeEquipmentKey(meta.display_name).toLowerCase())) continue;

        const names = [meta.display_name, meta.tag_no].filter(Boolean);
        let healthRow = null;
        for (const name of names) {
          if (healthByName.has(name)) {
            healthRow = healthByName.get(name);
            break;
          }
        }

        const status = normalizeStatus(healthRow?.latest_status);
        if (status === "ALARM") alarm += 1;
        else if (status === "WARNING") warning += 1;
        else normal += 1;

        const ts = parseTimestamp(healthRow?.latest_timestamp || healthRow?.last_reading_time);
        if (ts && (!lastUpdated || ts > lastUpdated)) lastUpdated = ts;
      }

      for (const row of recentReadings || []) {
        if (!isToday(parseTimestamp(row.timestamp))) continue;
        if (!readingVisibleInDashboardArea(row, area, lookups)) continue;
        const ts = parseTimestamp(row.timestamp);
        if (ts && (!lastUpdated || ts > lastUpdated)) lastUpdated = ts;
      }
    }

    const trackedCount = normal + warning + alarm;
    const pendingToday = Math.max(0, configuredCount - touchedToday.size);
    const areaStatus = deriveAreaStatus({ alarm, warning, hasTodayReadings });
    const healthPercent =
      hasTodayReadings && trackedCount > 0
        ? Math.round((normal / trackedCount) * 100)
        : null;

    return {
      area,
      configuredCount,
      normal,
      warning,
      alarm,
      pending: pendingToday,
      pendingToday,
      hasTodayReadings,
      areaStatus,
      healthPercent,
      trackedCount,
      lastUpdated,
      lastUpdatedLabel: lastUpdated
        ? formatRelativeTime(lastUpdated).label
        : DASHBOARD_STATUS.PENDING.label,
      lastUpdatedTitle: lastUpdated ? formatDateTime(lastUpdated) : "",
      healthLabel:
        hasTodayReadings && healthPercent != null
          ? `${healthPercent}%`
          : DASHBOARD_STATUS.PENDING.label,
    };
  });
}

export function computeTodayMetrics(recentReadings, lookups) {
  const todayRows = (recentReadings || []).filter((row) => isToday(parseTimestamp(row.timestamp)));
  const equipmentToday = new Set();

  for (const row of todayRows) {
    let meta = null;
    for (const area of getDashboardAreasForReading(row, lookups)) {
      meta = matchConfiguredEquipmentInArea(row, area, lookups);
      if (meta) break;
    }
    if (meta) {
      equipmentToday.add(
        `${normalizeAreaKey(meta.area)}::${normalizeEquipmentKey(meta.display_name)}`
      );
    }
  }

  return {
    todayEntryCount: todayRows.length,
    todayEquipmentTouched: equipmentToday.size,
  };
}

export function computeRoundCompletion(recentReadings, lookups) {
  const areaOrder = lookups.dashboardAreaOrder || buildDashboardAreaOrder(lookups.config);

  return areaOrder.map((area) => {
    const configured = lookups.areaEquipment.get(area) || [];
    const touchedDisplayNames = new Set();

    for (const row of recentReadings || []) {
      if (!isToday(parseTimestamp(row.timestamp))) continue;
      if (!readingVisibleInDashboardArea(row, area, lookups)) continue;
      const meta = matchConfiguredEquipmentInArea(row, area, lookups);
      if (meta) touchedDisplayNames.add(meta.display_name);
    }

    let completed = 0;
    for (const meta of configured) {
      if (touchedDisplayNames.has(meta.display_name)) completed += 1;
    }

    const total = configured.length;
    const remaining = Math.max(0, total - completed);
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
    const hasTodaySubmissions = completed > 0;

    return { area, total, completed, remaining, percent, hasTodaySubmissions };
  });
}

export function computePendingRoundCount(roundCompletion) {
  return roundCompletion.reduce((sum, row) => sum + row.remaining, 0);
}

export function getLastUpdatedTime(recentReadings) {
  let latest = null;
  for (const row of recentReadings || []) {
    const ts = parseTimestamp(row.timestamp);
    if (ts && (!latest || ts > latest)) latest = ts;
  }
  return latest;
}

export function buildPlantBanner(summary, activeAlarms, lastRefresh, todayMetrics = null) {
  const alarmCount = summary?.alarm ?? 0;
  const warningCount = summary?.warning ?? 0;
  const todayEntryCount = todayMetrics?.todayEntryCount ?? 0;

  if (alarmCount > 0) {
    return {
      tone: "alarm",
      title: `${alarmCount} Critical Alarm${alarmCount > 1 ? "s" : ""} Require Immediate Attention`,
      description: "Equipment exceeding alarm thresholds — review active alerts below.",
      icon: "alarm",
    };
  }
  if (warningCount > 0) {
    return {
      tone: "warning",
      title: `${warningCount} Equipment Need Inspection`,
      description: "Warning-level readings detected across monitored assets.",
      icon: "warning",
    };
  }
  if (todayEntryCount === 0) {
    return {
      tone: "pending",
      title: "Awaiting Today's Inspection",
      description: "No readings submitted today. Historical equipment status is shown below.",
      icon: "pending",
    };
  }
  return {
    tone: "normal",
    title: "All Systems Normal",
    description: "No active warnings or alarms on monitored equipment.",
    icon: "normal",
  };
}

/** Compact banner for today's round submission status. */
export function buildTodayRoundBanner(todayMetrics, lastUpdatedTime) {
  const count = todayMetrics?.todayEntryCount ?? 0;
  const lastRelative = lastUpdatedTime ? formatRelativeTime(lastUpdatedTime) : null;

  if (count === 0) {
    return {
      tone: "pending",
      title: "Today's Round Pending",
      description: "No readings have been submitted today.",
      metaLabel: lastRelative ? "Last submission" : null,
      metaValue: lastRelative?.label ?? null,
      metaTitle: lastRelative?.title ?? "",
    };
  }

  return {
    tone: "in_progress",
    title: "Today's Round In Progress",
    description: `${count} reading${count === 1 ? "" : "s"} submitted`,
    metaLabel: "Last update",
    metaValue: lastRelative?.label ?? "—",
    metaTitle: lastRelative?.title ?? "",
  };
}

export function dedupeRecentReadings(readings, limit = 10) {
  const seen = new Set();
  const result = [];

  for (const row of readings || []) {
    const key = [
      row.timestamp,
      row.area_tank,
      row.equipment,
      row.tag_no,
      row.parameter,
      row.value,
    ].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(row);
    if (result.length >= limit) break;
  }

  return result;
}

export function groupLatestParameters(equipmentHealth, equipmentName) {
  const row = (equipmentHealth || []).find((item) => item.equipment === equipmentName);
  if (!row) return [];
  return [
    {
      parameter: row.latest_parameter,
      value: row.latest_value,
      status: normalizeStatus(row.latest_status),
    },
  ].filter((item) => item.parameter);
}

export function filterDashboardData({
  recentReadings,
  activeAlarms,
  equipmentHealth,
  lookups,
  filters,
  searchQuery,
}) {
  const query = String(searchQuery || "").trim().toLowerCase();

  const matchesQuery = (row) => {
    if (!query) return true;
    const area = resolveReadingArea(row, lookups);
    const haystack = [
      area,
      row.category,
      row.equipment,
      row.tag_no,
      row.parameter,
      row.parameter_display_name,
      row.location,
      row.verified_by,
      row.area_tank,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  };

  const matchesFilters = (row) => {
    if (
      filters.area &&
      filters.area !== "all" &&
      !readingVisibleInDashboardArea(row, filters.area, lookups)
    ) {
      return false;
    }
    if (filters.category && filters.category !== "all" && row.category !== filters.category) return false;
    if (filters.equipment && filters.equipment !== "all" && row.equipment !== filters.equipment) return false;
    if (filters.tagNo && filters.tagNo !== "all" && row.tag_no !== filters.tagNo) return false;
    if (filters.status && filters.status !== "all" && normalizeStatus(row.status) !== filters.status) return false;
    if (filters.verifiedBy && filters.verifiedBy !== "all" && row.verified_by !== filters.verifiedBy) return false;
    return true;
  };

  const filteredReadings = (recentReadings || []).filter(
    (row) => matchesQuery(row) && matchesFilters(row)
  );
  const filteredAlarms = (activeAlarms || []).filter(
    (row) => matchesQuery(row) && matchesFilters(row)
  );
  const filteredHealth = (equipmentHealth || []).filter((row) => {
    if (!matchesQuery(row)) return false;
    const pseudo = { ...row, area_tank: "", tag_no: "" };
    return matchesFilters(pseudo);
  });

  return { filteredReadings, filteredAlarms, filteredHealth };
}

export function computeTodayCompletedRounds(roundCompletion) {
  return roundCompletion.reduce((sum, row) => sum + row.completed, 0);
}

/** Unique configured equipment instances inspected today across all dashboard areas. */
export function computeTodayCompletedEquipment(recentReadings, lookups) {
  return computeTodayMetrics(recentReadings, lookups).todayEquipmentTouched;
}

export function getProgressBarClass(percent, { pending = false } = {}) {
  if (pending) return "h-2.5 bg-zinc-100 [&>div]:bg-zinc-300";
  if (percent >= 100) return "h-2.5 bg-zinc-100 [&>div]:bg-[#16A34A]";
  if (percent >= 70) return "h-2.5 bg-zinc-100 [&>div]:bg-[#002FA7]";
  if (percent >= 40) return "h-2.5 bg-zinc-100 [&>div]:bg-yellow-500";
  return "h-2.5 bg-zinc-100 [&>div]:bg-[#002FA7]";
}

export function getParameterDisplay(reading) {
  return reading.parameter_display_name || reading.location || reading.parameter || "—";
}

/** Build searchable index from config + recent readings. */
export function buildSearchIndex(lookups, recentReadings = []) {
  const items = [];
  const seen = new Set();

  const push = (entry) => {
    const key = `${entry.type}:${entry.value}:${entry.area}`;
    if (seen.has(key)) return;
    seen.add(key);
    items.push(entry);
  };

  for (const area of lookups.dashboardAreaOrder || buildDashboardAreaOrder(lookups.config)) {
    push({
      type: "area",
      value: area,
      label: area,
      area,
      category: "",
      equipment: "",
      tagNo: "",
      searchText: area.toLowerCase(),
    });

    const equipmentList = lookups.areaEquipment.get(area) || [];
    for (const meta of equipmentList) {
      push({
        type: "equipment",
        value: meta.display_name,
        label: meta.display_name,
        area,
        category: meta.category || "",
        equipment: meta.display_name,
        tagNo: meta.tag_no || "",
        searchText: [area, meta.category, meta.display_name, meta.tag_no]
          .filter(Boolean)
          .join(" ")
          .toLowerCase(),
      });

      if (meta.tag_no) {
        push({
          type: "tag",
          value: meta.tag_no,
          label: meta.tag_no,
          area,
          category: meta.category || "",
          equipment: meta.display_name,
          tagNo: meta.tag_no,
          searchText: [area, meta.category, meta.display_name, meta.tag_no]
            .filter(Boolean)
            .join(" ")
            .toLowerCase(),
        });
      }
    }
  }

  for (const row of recentReadings || []) {
    const area = resolveReadingArea(row, lookups);
    if (row.category) {
      push({
        type: "category",
        value: row.category,
        label: row.category,
        area,
        category: row.category,
        equipment: row.equipment || "",
        tagNo: row.tag_no || "",
        searchText: [area, row.category, row.equipment, row.tag_no].filter(Boolean).join(" ").toLowerCase(),
      });
    }
    if (row.parameter) {
      push({
        type: "parameter",
        value: row.parameter,
        label: getParameterDisplay(row),
        area,
        category: row.category || "",
        equipment: row.equipment || "",
        tagNo: row.tag_no || "",
        searchText: [area, row.category, row.equipment, row.tag_no, row.parameter, getParameterDisplay(row)]
          .filter(Boolean)
          .join(" ")
          .toLowerCase(),
      });
    }
    if (row.verified_by) {
      push({
        type: "verified_by",
        value: row.verified_by,
        label: row.verified_by,
        area,
        category: row.category || "",
        equipment: row.equipment || "",
        tagNo: row.tag_no || "",
        searchText: row.verified_by.toLowerCase(),
      });
    }
  }

  return items;
}

export function searchSuggestions(index, query, limit = 8) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return [];

  return index
    .filter((item) => item.searchText.includes(q) || item.value.toLowerCase().includes(q))
    .sort((a, b) => {
      const aStarts = a.value.toLowerCase().startsWith(q) ? 0 : 1;
      const bStarts = b.value.toLowerCase().startsWith(q) ? 0 : 1;
      if (aStarts !== bStarts) return aStarts - bStarts;
      return a.label.localeCompare(b.label);
    })
    .slice(0, limit);
}

export function findMostRecentResolvedAlert(recentReadings, activeAlarms, lookups) {
  const activeKeys = new Set(
    (activeAlarms || []).map((alert) =>
      [alert.equipment, alert.parameter, alert.timestamp].join("|")
    )
  );

  for (const row of recentReadings || []) {
    const status = normalizeStatus(row.status);
    if (status !== "WARNING" && status !== "ALARM") continue;

    const key = [row.equipment, row.parameter, row.timestamp].join("|");
    if (activeKeys.has(key)) continue;

    return {
      ...row,
      area: resolveReadingArea(row, lookups),
      resolvedLabel: status === "ALARM" ? "Historical alarm" : "Historical warning",
    };
  }

  return null;
}

function rowMatchesFilters(row, filters, lookups, omitKey = null) {
  if (
    omitKey !== "area" &&
    filters.area &&
    filters.area !== "all" &&
    !readingVisibleInDashboardArea(row, filters.area, lookups)
  ) {
    return false;
  }
  if (omitKey !== "category" && filters.category && filters.category !== "all" && row.category !== filters.category)
    return false;
  if (omitKey !== "equipment" && filters.equipment && filters.equipment !== "all" && row.equipment !== filters.equipment)
    return false;
  if (omitKey !== "tagNo" && filters.tagNo && filters.tagNo !== "all" && row.tag_no !== filters.tagNo) return false;
  if (omitKey !== "status" && filters.status && filters.status !== "all" && normalizeStatus(row.status) !== filters.status)
    return false;
  if (
    omitKey !== "verifiedBy" &&
    filters.verifiedBy &&
    filters.verifiedBy !== "all" &&
    row.verified_by !== filters.verifiedBy
  )
    return false;
  return true;
}

export function buildCascadingFilterOptions(recentReadings, lookups, filters) {
  const rows = recentReadings || [];
  const statuses = ["NORMAL", "WARNING", "ALARM"];

  const areas = new Set(lookups.dashboardAreaOrder || buildDashboardAreaOrder(lookups.config));
  const categories = new Set();
  const equipment = new Set();
  const tagNos = new Set();
  const verifiedBy = new Set();

  for (const row of rows) {
    if (!rowMatchesFilters(row, filters, lookups, "area")) continue;
    areas.add(resolveReadingArea(row, lookups));
  }

  for (const row of rows) {
    if (!rowMatchesFilters(row, filters, lookups, "category")) continue;
    if (row.category) categories.add(row.category);
  }

  for (const row of rows) {
    if (!rowMatchesFilters(row, filters, lookups, "equipment")) continue;
    if (row.equipment) equipment.add(row.equipment);
  }

  for (const row of rows) {
    if (!rowMatchesFilters(row, filters, lookups, "tagNo")) continue;
    if (row.tag_no) tagNos.add(row.tag_no);
  }

  for (const row of rows) {
    if (!rowMatchesFilters(row, filters, lookups, "verifiedBy")) continue;
    if (row.verified_by) verifiedBy.add(row.verified_by);
  }

  if (filters.area && filters.area !== "all") {
    const configured = lookups.areaEquipment.get(filters.area) || [];
    for (const meta of configured) {
      if (meta.category) categories.add(meta.category);
      equipment.add(meta.display_name);
      if (meta.tag_no) tagNos.add(meta.tag_no);
    }
  }

  return {
    areas: [...areas],
    categories: [...categories].sort(),
    equipment: [...equipment].sort(),
    tagNos: [...tagNos].sort(),
    verifiedBy: [...verifiedBy].sort(),
    statuses,
  };
}

export function sanitizeFilters(filters, filterOptions) {
  const next = { ...filters };
  if (next.area !== "all" && !filterOptions.areas.includes(next.area)) next.area = "all";
  if (next.category !== "all" && !filterOptions.categories.includes(next.category)) next.category = "all";
  if (next.equipment !== "all" && !filterOptions.equipment.includes(next.equipment)) next.equipment = "all";
  if (next.tagNo !== "all" && !filterOptions.tagNos.includes(next.tagNo)) next.tagNo = "all";
  if (next.verifiedBy !== "all" && !filterOptions.verifiedBy.includes(next.verifiedBy)) next.verifiedBy = "all";
  return next;
}

/** Group configured equipment by category for area drill-down. */
export function groupAreaEquipmentByCategory(areaName, lookups) {
  const equipmentList = lookups.areaEquipment.get(areaName) || [];
  const groups = new Map();

  for (const meta of equipmentList) {
    const category = meta.category || "Other";
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(meta);
  }

  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, items]) => ({
      category,
      equipment: items.sort((a, b) => a.display_name.localeCompare(b.display_name)),
    }));
}

/** @deprecated Prefer lookups.dashboardAreaOrder from buildConfigLookups(). */
export const DASHBOARD_AREA_ORDER = buildDashboardAreaOrder();

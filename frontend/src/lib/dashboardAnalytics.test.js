import {
  buildConfigLookups,
  buildDashboardAreaOrder,
  computeAreaSummaries,
  computeRoundCompletion,
  computeTodayCompletedEquipment,
  computeTodayMetrics,
  getDashboardAreasForReading,
  isToday,
  formatRelativeTime,
  matchConfiguredEquipmentInArea,
  normalizeAreaKey,
  parseTimestamp,
  readingVisibleInDashboardArea,
  resolveReadingArea,
} from "./dashboardAnalytics";

function todayTimestamp(hours = 10, minutes = 0) {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const h = String(hours).padStart(2, "0");
  const min = String(minutes).padStart(2, "0");
  return `${y}-${m}-${d} ${h}:${min}:00`;
}

describe("dashboardAnalytics aggregation", () => {
  const lookups = buildConfigLookups();

  test("builds dashboard areas dynamically from config", () => {
    const areas = buildDashboardAreaOrder();
    expect(areas).toContain("A Tank");
    expect(areas).toContain("E Tank");
    expect(areas).toContain("G Tank");
    expect(areas).toContain("K Tank");
    expect(areas).toContain("Utility Area");
    expect(areas).toContain("DM Water Electrode Cooling");
    expect(areas.length).toBe(6);
  });

  test("normalizes area keys consistently", () => {
    expect(normalizeAreaKey("  E   Tank ")).toBe("E Tank");
    expect(normalizeAreaKey("e tank")).toBe("e tank");
  });

  test("parses sheet timestamps as plant-local IST wall clock", () => {
    const parsed = parseTimestamp("2026-06-16 15:00:00");
    expect(parsed).not.toBeNull();
    expect(parsed.toISOString()).toBe("2026-06-16T09:30:00.000Z");
  });

  test("formatRelativeTime uses IST-parsed instants", () => {
    const reading = "2026-06-16 14:00:00";
    const now = parseTimestamp("2026-06-16 15:00:00");
    expect(formatRelativeTime(reading, now).label).toBe("1 hour ago");
  });

  test("parses sheet timestamps as local today", () => {
    const ts = todayTimestamp(14, 30);
    const parsed = parseTimestamp(ts);
    expect(parsed).not.toBeNull();
    expect(isToday(parsed)).toBe(true);
  });

  test("disambiguates duplicate Gas Blower-1 by area_tank", () => {
    const reading = {
      area_tank: "E Tank",
      category: "Blowers",
      equipment: "Gas Blower-1",
      tag_no: "",
      timestamp: todayTimestamp(),
    };
    expect(resolveReadingArea(reading, lookups)).toBe("E Tank");
    expect(matchConfiguredEquipmentInArea(reading, "E Tank", lookups)?.display_name).toBe(
      "Gas Blower-1"
    );
  });

  test("routes DM water electrode cooling to dedicated dashboard area", () => {
    const reading = {
      area_tank: "E Tank",
      category: "DM Water Electrode Cooling",
      equipment: "E Tank Electrode Cooling",
      tag_no: "",
      timestamp: todayTimestamp(),
    };
    expect(resolveReadingArea(reading, lookups)).toBe("DM Water Electrode Cooling");
    expect(
      matchConfiguredEquipmentInArea(reading, "DM Water Electrode Cooling", lookups)?.display_name
    ).toBe("E Tank Electrode Cooling");
    expect(matchConfiguredEquipmentInArea(reading, "E Tank", lookups)?.display_name).toBe(
      "E Tank Electrode Cooling"
    );
  });

  test("DM water readings are visible in physical tank and virtual DM area", () => {
    const tanks = [
      ["A Tank", "A Tank Electrode Cooling"],
      ["E Tank", "E Tank Electrode Cooling"],
      ["G Tank", "G Tank Electrode Cooling"],
      ["K Tank", "K Tank Electrode Cooling"],
    ];

    for (const [tank, equipment] of tanks) {
      const reading = {
        area_tank: tank,
        category: "DM Water Electrode Cooling",
        equipment,
        timestamp: todayTimestamp(10, 0),
        status: "NORMAL",
      };

      expect(getDashboardAreasForReading(reading, lookups)).toEqual(
        expect.arrayContaining([tank, "DM Water Electrode Cooling"])
      );
      expect(readingVisibleInDashboardArea(reading, tank, lookups)).toBe(true);
      expect(readingVisibleInDashboardArea(reading, "DM Water Electrode Cooling", lookups)).toBe(
        true
      );

      const summaries = computeAreaSummaries([], [reading], lookups);
      const tankSummary = summaries.find((row) => row.area === tank);
      const dmSummary = summaries.find((row) => row.area === "DM Water Electrode Cooling");

      expect(tankSummary?.hasTodayReadings).toBe(true);
      expect(dmSummary?.hasTodayReadings).toBe(true);
    }
  });

  test("DM water round completion counts toward physical tank and DM virtual area", () => {
    const reading = {
      area_tank: "A Tank",
      category: "DM Water Electrode Cooling",
      equipment: "A Tank Electrode Cooling",
      timestamp: todayTimestamp(9, 0),
      status: "NORMAL",
    };

    const round = computeRoundCompletion([reading], lookups);
    const aTank = round.find((row) => row.area === "A Tank");
    const dmArea = round.find((row) => row.area === "DM Water Electrode Cooling");

    expect(aTank?.completed).toBe(1);
    expect(aTank?.hasTodaySubmissions).toBe(true);
    expect(dmArea?.completed).toBe(1);
    expect(dmArea?.hasTodaySubmissions).toBe(true);
  });

  test("E Tank blower submission updates area health and round completion", () => {
    const readings = [
      {
        area_tank: "E Tank",
        category: "Blowers",
        equipment: "MCB-5",
        parameter: "blower_drive_end_vertical",
        value: "1.2",
        status: "NORMAL",
        timestamp: todayTimestamp(9, 15),
        verified_by: "Tech",
      },
    ];

    const round = computeRoundCompletion(readings, lookups);
    const eTank = round.find((row) => row.area === "E Tank");
    const eTankTotal = (lookups.areaEquipment.get("E Tank") || []).length;
    expect(eTank.completed).toBe(1);
    expect(eTank.total).toBe(eTankTotal);
    expect(eTank.percent).toBe(Math.round((1 / eTankTotal) * 100));
    expect(eTank.remaining).toBe(eTankTotal - 1);
    expect(eTank.hasTodaySubmissions).toBe(true);

    const summaries = computeAreaSummaries([], readings, lookups);
    const eSummary = summaries.find((row) => row.area === "E Tank");
    expect(eSummary.hasTodayReadings).toBe(true);
    expect(eSummary.normal).toBe(1);
    expect(eSummary.pendingToday).toBe(eTankTotal - 1);
    expect(eSummary.healthPercent).toBe(100);
    expect(eSummary.areaStatus).toBe("NORMAL");
  });

  test("counts unique completed equipment across multiple areas", () => {
    const readings = [
      {
        area_tank: "A Tank",
        category: "Blowers",
        equipment: "MCB-1",
        timestamp: todayTimestamp(8, 0),
        status: "NORMAL",
      },
      {
        area_tank: "E Tank",
        category: "DM Water Electrode Cooling",
        equipment: "E Tank Electrode Cooling",
        timestamp: todayTimestamp(8, 5),
        status: "NORMAL",
      },
    ];

    expect(computeTodayCompletedEquipment(readings, lookups)).toBe(2);
    expect(computeTodayMetrics(readings, lookups).todayEntryCount).toBe(2);
  });

  test("Utility Area tag equipment resolves correctly", () => {
    const utilityList = lookups.areaEquipment.get("Utility Area") || [];
    const sample = utilityList.find((meta) => meta.tag_no);
    expect(sample).toBeTruthy();

    const reading = {
      area_tank: "Utility Area",
      category: sample.category,
      equipment: sample.display_name,
      tag_no: sample.tag_no,
      timestamp: todayTimestamp(11, 0),
      status: "NORMAL",
    };

    expect(resolveReadingArea(reading, lookups)).toBe("Utility Area");
    expect(matchConfiguredEquipmentInArea(reading, "Utility Area", lookups)?.display_name).toBe(
      sample.display_name
    );
  });
});

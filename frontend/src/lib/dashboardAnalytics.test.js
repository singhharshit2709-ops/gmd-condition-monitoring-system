import {
  buildConfigLookups,
  buildDashboardAreaOrder,
  computeAreaSummaries,
  computeRoundCompletion,
  computeTodayCompletedEquipment,
  computeTodayMetrics,
  isToday,
  matchConfiguredEquipmentInArea,
  normalizeAreaKey,
  parseTimestamp,
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
    expect(eTank.completed).toBe(1);
    expect(eTank.total).toBe(12);
    expect(eTank.percent).toBe(8);
    expect(eTank.remaining).toBe(11);
    expect(eTank.hasTodaySubmissions).toBe(true);

    const summaries = computeAreaSummaries([], readings, lookups);
    const eSummary = summaries.find((row) => row.area === "E Tank");
    expect(eSummary.hasTodayReadings).toBe(true);
    expect(eSummary.normal).toBe(1);
    expect(eSummary.pendingToday).toBe(11);
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

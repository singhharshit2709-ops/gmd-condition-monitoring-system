import axios from "axios";

/** Single plant for G Tank ECM — must match backend machine_config.json plants.GT */
export const PLANT_ID = "GMD";

export const PLANT_LABEL =
  "Neutral Glass — General Maintenance Department Condition Monitoring";

/** Build /config/{plant}/{machine} URL with encoded path segments (spaces in area names). */
export function configMachineUrl(apiBase, plantId, machineId) {
  const base = apiBase.replace(/\/$/, "");
  return `${base}/config/${encodeURIComponent(plantId)}/${encodeURIComponent(machineId)}`;
}

/** Load area (machine) ids from backend — single source of truth with machine_config.json */
export async function fetchGtAreas(apiBase) {
  const base = apiBase.replace(/\/$/, "");
  const res = await axios.get(`${base}/config/plants`);
  const machines = res.data?.[PLANT_ID]?.machines;
  if (!machines || typeof machines !== "object") {
    return [];
  }
  return Object.keys(machines);
}

/** Fallback if API unavailable — mirrors machine_config.json GT machines (v3.0.0) */
export const GT_AREAS_FALLBACK = [
  "MCB-1",
  "MCB-2",
  "MCB-3",
  "Gas Blower-1",
  "Gas Blower-2",
  "Chimney Blower",
  "Tank Cooling Blower",
  "Cooling Blower",
  "Throat Cooling Blower",

  "G Tank Electrode Cooling",
  "K Tank Electrode Cooling",
  "E Tank Electrode Cooling",
  "K & E Tank Batch Charger",

  "Compressor House CT",
  "G Tank CT",
  "A Tank CT",
];

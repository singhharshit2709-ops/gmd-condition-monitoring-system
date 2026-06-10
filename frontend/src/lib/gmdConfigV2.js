import gmdMachineConfigV2 from "@gmd-config/v2";

/**
 * Resolve equipment by display_name from the V2 configuration document.
 * Returns { plant, category, equipment } or null.
 */
export function findEquipmentByDisplayName(displayName) {
  for (const plant of gmdMachineConfigV2.plants || []) {
    for (const category of plant.categories || []) {
      for (const equipment of category.equipment || []) {
        if (equipment.display_name === displayName && equipment.active !== false) {
          return { plant, category, equipment };
        }
      }
    }
  }
  return null;
}

/** @returns {typeof gmdMachineConfigV2} */
export function loadGmdConfigV2() {
  return gmdMachineConfigV2;
}

export function sortByDisplayOrder(items) {
  return [...items].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
}

/**
 * Walk section → group → parameter tree; return flat list of renderable rows.
 * Respects active flags and is_visible on parameters.
 */
export function collectRenderableParameters(equipment) {
  const rows = [];

  for (const section of sortByDisplayOrder(equipment.sections || [])) {
    if (section.active === false) continue;

    for (const group of sortByDisplayOrder(section.groups || [])) {
      if (group.active === false) continue;

      for (const param of sortByDisplayOrder(group.parameters || [])) {
        if (param.is_visible === false) continue;
        rows.push({ section, group, param });
      }
    }
  }

  return rows;
}

export function isReadingComplete(value) {
  if (value === "" || value === null || value === undefined) return false;
  const trimmed = String(value).trim();
  if (trimmed === "") return false;
  return !Number.isNaN(Number(trimmed));
}

export function countCompletedReadings(readings, renderableRows) {
  return renderableRows.filter(({ param }) => isReadingComplete(readings[param.key])).length;
}

export function getExpectedReadingCount(equipment, renderableRows) {
  if (typeof equipment.expected_reading_count === "number") {
    return equipment.expected_reading_count;
  }
  return renderableRows.filter(({ param }) => param.required).length;
}

export function buildInitialReadings(renderableRows) {
  const initial = {};
  for (const { param } of renderableRows) {
    initial[param.key] = "";
  }
  return initial;
}

export function getInputStep(param) {
  const step = param.validation?.step;
  if (typeof step === "number" && step > 0) return step;
  if (param.decimal_precision === 0) return 1;
  return 0.01;
}

/** Required visible parameters that have no valid value entered. */
export function getMissingRequiredReadings(readings, renderableRows) {
  return renderableRows.filter(
    ({ param }) => param.required && !isReadingComplete(readings[param.key])
  );
}

/**
 * Build a preview submission payload (not sent to any API).
 * Includes normalized numeric readings for completed fields only.
 */
export function buildV2PreviewPayload({
  category,
  equipment,
  readings,
  renderableRows,
  configVersion,
  schemaVersion,
}) {
  const normalizedReadings = {};
  const readingDetails = [];

  for (const { section, group, param } of renderableRows) {
    const raw = readings[param.key];
    if (!isReadingComplete(raw)) continue;

    const numericValue = Number(String(raw).trim());
    normalizedReadings[param.key] = numericValue;
    readingDetails.push({
      key: param.key,
      display_full_label: param.display_full_label,
      location: param.display_full_label,
      unit: param.unit,
      value: numericValue,
      section: section.label,
      group: group.label,
    });
  }

  return {
    category: category.display_name,
    equipment: equipment.display_name,
    readings: normalizedReadings,
    verified_by: "",
    remarks: "",
    entry_source: "Web",
    config_version: configVersion,
    schema_version: schemaVersion,
    equipment_version: equipment.version,
    reading_details: readingDetails,
  };
}

export function validateRequiredReadings(readings, renderableRows) {
  const missing = getMissingRequiredReadings(readings, renderableRows);
  return {
    valid: missing.length === 0,
    missing,
  };
}

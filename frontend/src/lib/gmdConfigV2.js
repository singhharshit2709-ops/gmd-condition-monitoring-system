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

/**
 * Return active tank/area options from the first active plant in config.
 */
export function getPlantAreas(config = gmdMachineConfigV2) {
  for (const plant of config.plants || []) {
    if (plant.active === false) continue;
    return sortByDisplayOrder(
      (plant.areas || []).filter((area) => area.active !== false)
    );
  }
  return [];
}

export function getAreaNavigationMode(areaDisplayName, config = gmdMachineConfigV2) {
  if (!areaDisplayName) return "tank_equipment";
  for (const plant of config.plants || []) {
    if (plant.active === false) continue;
    for (const area of plant.areas || []) {
      if (area.display_name === areaDisplayName) {
        return area.navigation_mode || "tank_equipment";
      }
    }
  }
  return "tank_equipment";
}

export function isUtilityTagArea(areaDisplayName, config = gmdMachineConfigV2) {
  return getAreaNavigationMode(areaDisplayName, config) === "utility_tag";
}

/**
 * Collect equipment entries whose area matches the selected tank display_name.
 * Returns [{ plant, category, equipment }, ...] sorted for UI display.
 */
export function collectEquipmentByArea(areaDisplayName, config = gmdMachineConfigV2) {
  if (!areaDisplayName) return [];

  const matches = [];

  for (const plant of config.plants || []) {
    if (plant.active === false) continue;

    for (const category of plant.categories || []) {
      if (category.active === false) continue;

      for (const equipment of category.equipment || []) {
        if (equipment.active === false) continue;
        if (equipment.area !== areaDisplayName) continue;
        matches.push({ plant, category, equipment });
      }
    }
  }

  return matches.sort((a, b) => {
    const orderDiff = (a.equipment.display_order ?? 0) - (b.equipment.display_order ?? 0);
    if (orderDiff !== 0) return orderDiff;
    return String(a.equipment.display_name).localeCompare(String(b.equipment.display_name));
  });
}

/**
 * Resolve a configured equipment id within an area to { plant, category, equipment }.
 */
export function findEquipmentInArea(areaDisplayName, equipmentId, config = gmdMachineConfigV2) {
  return (
    collectEquipmentByArea(areaDisplayName, config).find(
      ({ equipment }) => equipment.id === equipmentId
    ) || null
  );
}

/**
 * Utility Area: distinct equipment type labels for an area (e.g. Screw Compressor).
 */
export function collectEquipmentKindsByArea(areaDisplayName, config = gmdMachineConfigV2) {
  const entries = collectEquipmentByArea(areaDisplayName, config);
  const kindOrder = [];
  const seen = new Set();

  for (const entry of entries) {
    const kind = entry.equipment.equipment_kind;
    if (!kind || seen.has(kind)) continue;
    seen.add(kind);
    kindOrder.push(kind);
  }

  return kindOrder;
}

/**
 * Utility Area: tag entries for a selected equipment kind.
 */
export function collectTagsByAreaAndKind(
  areaDisplayName,
  equipmentKind,
  config = gmdMachineConfigV2
) {
  if (!areaDisplayName || !equipmentKind) return [];

  return collectEquipmentByArea(areaDisplayName, config).filter(
    ({ equipment }) => equipment.equipment_kind === equipmentKind
  );
}

export function findUtilityTagEquipment(
  areaDisplayName,
  equipmentKind,
  equipmentId,
  config = gmdMachineConfigV2
) {
  return (
    collectTagsByAreaAndKind(areaDisplayName, equipmentKind, config).find(
      ({ equipment }) => equipment.id === equipmentId
    ) || null
  );
}

export function sortByDisplayOrder(items) {
  return [...items].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
}

/** Total active equipment instances from config metadata or live count. */
export function getTotalEquipmentCount(config = gmdMachineConfigV2) {
  const registry = config?.metadata?.custom?.equipment_registry;
  if (registry && typeof registry.total_equipment === "number") {
    return registry.total_equipment;
  }
  let total = 0;
  for (const plant of config.plants || []) {
    for (const category of plant.categories || []) {
      for (const equipment of category.equipment || []) {
        if (equipment.active !== false) total += 1;
      }
    }
  }
  return total;
}

/** Equipment counts per tank/area from metadata or computed from config. */
export function getEquipmentCountByArea(config = gmdMachineConfigV2) {
  const registry = config?.metadata?.custom?.equipment_registry;
  if (registry?.by_area && typeof registry.by_area === "object") {
    return registry.by_area;
  }
  const counts = {};
  for (const plant of config.plants || []) {
    for (const category of plant.categories || []) {
      for (const equipment of category.equipment || []) {
        if (equipment.active === false) continue;
        const area = equipment.area || "";
        counts[area] = (counts[area] || 0) + 1;
      }
    }
  }
  return counts;
}

export function getAreaEquipmentCount(areaDisplayName, config = gmdMachineConfigV2) {
  if (!areaDisplayName) return 0;
  const byArea = getEquipmentCountByArea(config);
  if (typeof byArea[areaDisplayName] === "number") return byArea[areaDisplayName];
  return collectEquipmentByArea(areaDisplayName, config).length;
}

/** Flat list of active equipment with category/plant context for dashboard analytics. */
export function collectActiveEquipmentFromConfig(config = gmdMachineConfigV2) {
  const entries = [];
  for (const plant of config.plants || []) {
    if (plant.active === false) continue;
    for (const category of plant.categories || []) {
      if (category.active === false) continue;
      for (const equipment of category.equipment || []) {
        if (equipment.active === false) continue;
        entries.push({
          ...equipment,
          category_id: category.id,
          category_display_name: category.display_name,
          plant_id: plant.id,
        });
      }
    }
  }
  return entries;
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
  verifiedBy = "",
  remarks = "",
  media = null,
  areaTank = "",
  tagNo = "",
  submissionId = "",
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
    verified_by: String(verifiedBy ?? "").trim(),
    remarks: String(remarks ?? "").trim(),
    entry_source: "Web",
    config_version: configVersion,
    schema_version: schemaVersion,
    equipment_version: equipment.version,
    reading_details: readingDetails,
    media_name: media?.name ? String(media.name).trim() : "",
    media_type: media?.type ? String(media.type).trim() : "",
    media_data: media?.data ? String(media.data) : "",
    area_tank: String(areaTank ?? "").trim(),
    tag_no: String(tagNo ?? "").trim(),
    submission_id: String(submissionId ?? "").trim(),
  };
}

export function validateRequiredReadings(readings, renderableRows) {
  const missing = getMissingRequiredReadings(readings, renderableRows);
  return {
    valid: missing.length === 0,
    missing,
  };
}

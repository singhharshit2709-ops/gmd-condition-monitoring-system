import { useMemo, useState } from "react";
import RoundSheetForm from "@/components/v2/RoundSheetForm";
import NavigationSelect from "@/components/v2/NavigationSelect";
import {
  collectEquipmentByArea,
  collectEquipmentKindsByArea,
  collectTagsByAreaAndKind,
  findEquipmentInArea,
  findUtilityTagEquipment,
  getAreaEquipmentCount,
  getEquipmentCountByArea,
  getPlantAreas,
  getTotalEquipmentCount,
  isUtilityTagArea,
  loadGmdConfigV2,
} from "@/lib/gmdConfigV2";

/**
 * Production Add Reading flow:
 * - Tank areas: Tank → Equipment → Readings → Preview → Submit
 * - Utility Area: Tank/Area → Equipment Type → Tag No → Readings → Preview → Submit
 */
export default function AddReadingPage() {
  const config = loadGmdConfigV2();
  const [selectedTank, setSelectedTank] = useState("");
  const [selectedEquipmentKind, setSelectedEquipmentKind] = useState("");
  const [selectedEquipmentId, setSelectedEquipmentId] = useState("");

  const areas = useMemo(() => getPlantAreas(config), [config]);
  const totalEquipment = useMemo(() => getTotalEquipmentCount(config), [config]);
  const equipmentByArea = useMemo(() => getEquipmentCountByArea(config), [config]);
  const utilityNavigation = isUtilityTagArea(selectedTank, config);
  const selectedAreaCount = useMemo(
    () => getAreaEquipmentCount(selectedTank, config),
    [selectedTank, config]
  );

  const tankOptions = useMemo(
    () =>
      areas.map((area) => ({
        value: area.display_name,
        label: `${area.display_name} (${equipmentByArea[area.display_name] ?? 0} equipment)`,
      })),
    [areas, equipmentByArea]
  );

  const equipmentKindOptions = useMemo(
    () =>
      collectEquipmentKindsByArea(selectedTank, config).map((kind) => ({
        value: kind,
        label: kind,
      })),
    [selectedTank, config]
  );

  const tankEquipmentEntries = useMemo(
    () => collectEquipmentByArea(selectedTank, config),
    [selectedTank, config]
  );

  const tankEquipmentOptions = useMemo(
    () =>
      tankEquipmentEntries.map(({ equipment }) => ({
        value: equipment.id,
        label: equipment.display_name,
      })),
    [tankEquipmentEntries]
  );

  const tagEntries = useMemo(
    () => collectTagsByAreaAndKind(selectedTank, selectedEquipmentKind, config),
    [selectedTank, selectedEquipmentKind, config]
  );

  const tagOptions = useMemo(
    () =>
      tagEntries.map(({ equipment }) => ({
        value: equipment.id,
        label: equipment.tag_no || equipment.display_name,
      })),
    [tagEntries]
  );

  const resolved = useMemo(() => {
    if (!selectedTank || !selectedEquipmentId) return null;
    if (utilityNavigation) {
      if (!selectedEquipmentKind) return null;
      return findUtilityTagEquipment(
        selectedTank,
        selectedEquipmentKind,
        selectedEquipmentId,
        config
      );
    }
    return findEquipmentInArea(selectedTank, selectedEquipmentId, config);
  }, [
    selectedTank,
    selectedEquipmentKind,
    selectedEquipmentId,
    utilityNavigation,
    config,
  ]);

  const handleTankChange = (value) => {
    setSelectedTank(value);
    setSelectedEquipmentKind("");
    setSelectedEquipmentId("");
  };

  const handleEquipmentKindChange = (value) => {
    setSelectedEquipmentKind(value);
    setSelectedEquipmentId("");
  };

  const activeEquipmentOptions = utilityNavigation ? tagOptions : tankEquipmentOptions;
  const equipmentSelectDisabled = utilityNavigation
    ? !selectedEquipmentKind
    : !selectedTank;
  const equipmentPlaceholder = utilityNavigation
    ? selectedEquipmentKind
      ? "Select Tag No"
      : "Select equipment type first"
    : selectedTank
      ? "Select equipment"
      : "Select a tank first";

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-light tracking-tight text-zinc-950">Add Reading</h1>
        <p className="text-sm font-medium text-zinc-800 mt-1">Neutral Glass</p>
        <p className="text-sm text-zinc-600 mt-0.5">
          GMD Condition Monitoring · Config v{config.config_version}
        </p>
        <p className="text-sm text-zinc-700 mt-2">
          Select tank/area and equipment, enter readings, then preview and submit the round sheet.
          {" "}
          <span className="text-zinc-600">
            {totalEquipment} equipment instances configured across all tanks.
          </span>
        </p>
      </div>

      <div
        className={`grid grid-cols-1 ${
          utilityNavigation ? "md:grid-cols-3" : "md:grid-cols-2"
        } gap-4 mb-6 border border-zinc-200 bg-white p-6`}
      >
        <NavigationSelect
          id="add-reading-tank-select"
          label="Tank / Area"
          value={selectedTank}
          onChange={handleTankChange}
          placeholder="Select tank / area"
          options={tankOptions}
          testId="add-reading-tank-select"
        />
        {utilityNavigation && (
          <NavigationSelect
            id="add-reading-equipment-kind-select"
            label="Equipment"
            value={selectedEquipmentKind}
            onChange={handleEquipmentKindChange}
            disabled={!selectedTank}
            placeholder={selectedTank ? "Select equipment type" : "Select Utility Area first"}
            options={equipmentKindOptions}
            testId="add-reading-equipment-kind-select"
          />
        )}
        <NavigationSelect
          id="add-reading-equipment-select"
          label={utilityNavigation ? "Tag No" : "Equipment"}
          value={selectedEquipmentId}
          onChange={setSelectedEquipmentId}
          disabled={equipmentSelectDisabled}
          placeholder={equipmentPlaceholder}
          options={activeEquipmentOptions}
          testId="add-reading-equipment-select"
        />
      </div>

      {selectedTank && !selectedEquipmentId && selectedAreaCount > 0 && (
        <div className="mb-4 text-sm text-zinc-600">
          {selectedTank}: {selectedAreaCount} equipment
          {utilityNavigation ? " types / tags" : ""} available
        </div>
      )}

      {!selectedTank && (
        <div className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
          Choose a tank / area to see available equipment.
        </div>
      )}

      {selectedTank && (utilityNavigation ? !selectedEquipmentKind : activeEquipmentOptions.length === 0) && (
        <div className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
          {utilityNavigation
            ? `Select an equipment type for ${selectedTank}.`
            : `No equipment is configured for ${selectedTank} in gmd_machine_config_v2.json.`}
        </div>
      )}

      {selectedTank &&
        (utilityNavigation ? selectedEquipmentKind : true) &&
        activeEquipmentOptions.length > 0 &&
        !selectedEquipmentId && (
          <div className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
            {utilityNavigation
              ? `Select a Tag No to open the round sheet for ${selectedEquipmentKind}.`
              : `Select equipment to open the round sheet for ${selectedTank}.`}
          </div>
        )}

      {resolved && (
        <RoundSheetForm
          key={`${selectedTank}-${selectedEquipmentKind}-${selectedEquipmentId}`}
          equipment={resolved.equipment}
          category={resolved.category}
          areaTank={selectedTank}
          tagNo={utilityNavigation ? resolved.equipment.tag_no || "" : ""}
          configVersion={config.config_version}
          schemaVersion={config.schema_version}
        />
      )}
    </div>
  );
}

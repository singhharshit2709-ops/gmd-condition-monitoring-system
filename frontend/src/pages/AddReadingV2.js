import { useMemo } from "react";
import RoundSheetForm from "@/components/v2/RoundSheetForm";
import { findEquipmentByDisplayName, loadGmdConfigV2 } from "@/lib/gmdConfigV2";

const PILOT_EQUIPMENT = "MCB-1";

export default function AddReadingV2() {
  const config = loadGmdConfigV2();

  const resolved = useMemo(
    () => findEquipmentByDisplayName(PILOT_EQUIPMENT),
    []
  );

  if (!resolved) {
    return (
      <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
        <div className="border-2 border-[#E11D48] bg-red-50 p-6 text-red-800">
          Equipment &quot;{PILOT_EQUIPMENT}&quot; was not found in gmd_machine_config_v2.json.
        </div>
      </div>
    );
  }

  const { category, equipment } = resolved;

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-light tracking-tight text-zinc-950">
          Maintenance Round Entry
        </h1>
        <p className="text-sm font-medium text-zinc-800 mt-1">Neutral Glass — V2 Pilot</p>
        <p className="text-sm text-zinc-600 mt-0.5">
          Config v{config.config_version} · Schema v{config.schema_version}
        </p>
        <p className="text-sm text-zinc-700 mt-2">
          Dynamic round sheet rendered from gmd_machine_config_v2.json — no hardcoded parameters.
        </p>
      </div>

      <RoundSheetForm
        equipment={equipment}
        category={category}
        configVersion={config.config_version}
        schemaVersion={config.schema_version}
      />
    </div>
  );
}

import { useMemo, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import AreaStatusBadge from "@/components/dashboard/AreaStatusBadge";
import StatusBadge from "@/components/dashboard/StatusBadge";
import {
  formatDateTime,
  getParameterDisplay,
  groupAreaEquipmentByCategory,
  readingVisibleInDashboardArea,
  resolveReadingArea,
} from "@/lib/dashboardAnalytics";

function EquipmentDrillDownItem({ meta, equipmentHealth, recentReadings, onSelectEquipment }) {
  const healthRow = (equipmentHealth || []).find(
    (row) => row.equipment === meta.display_name || row.equipment === meta.tag_no
  );
  const latest = (recentReadings || []).find(
    (row) => row.equipment === meta.display_name || row.tag_no === meta.tag_no
  );

  return (
    <button
      type="button"
      onClick={() => latest && onSelectEquipment?.(latest)}
      className="w-full text-left border border-zinc-100 rounded p-3 hover:border-[#002FA7]/30 hover:bg-zinc-50 transition-colors"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-zinc-900">{meta.display_name}</span>
        <StatusBadge status={healthRow?.latest_status || latest?.status || "NORMAL"} />
      </div>
      {meta.tag_no && <p className="text-xs font-mono text-zinc-500 mt-1">Tag: {meta.tag_no}</p>}
      {latest && (
        <p className="text-xs text-zinc-600 mt-2">
          {getParameterDisplay(latest)} · {latest.value ?? "—"}
          {latest.unit ? ` ${latest.unit}` : ""}
        </p>
      )}
    </button>
  );
}

export default function EquipmentSummaryDrawer({
  open,
  onOpenChange,
  selection,
  lookups,
  equipmentHealth,
  recentReadings,
  onSelectEquipment,
}) {
  const [expandedCategory, setExpandedCategory] = useState(null);

  const drillDown = useMemo(() => {
    if (!selection || selection.type !== "area") return [];
    return groupAreaEquipmentByCategory(selection.data.area, lookups);
  }, [selection, lookups]);

  if (!selection) return null;

  const isArea = selection.type === "area";
  const areaName = isArea ? selection.data.area : resolveReadingArea(selection.data, lookups);
  const equipmentName = isArea ? null : selection.data.equipment;
  const tagNo = isArea ? null : selection.data.tag_no || "";

  const healthRow = equipmentName
    ? (equipmentHealth || []).find((row) => row.equipment === equipmentName)
    : null;

  const latestReadings = (recentReadings || [])
    .filter((row) => {
      if (isArea) return readingVisibleInDashboardArea(row, areaName, lookups);
      return row.equipment === equipmentName || row.tag_no === tagNo;
    })
    .slice(0, 8);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isArea ? areaName : equipmentName}</SheetTitle>
          <SheetDescription>
            {isArea
              ? "Area drill-down — categories, equipment, latest snapshot"
              : "Equipment snapshot — latest submission"}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {!isArea && (
            <dl className="grid grid-cols-1 gap-3 text-sm">
              <div>
                <dt className="text-zinc-500">Area</dt>
                <dd className="font-medium text-zinc-950">{areaName}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Category</dt>
                <dd className="text-zinc-900">{selection.data.category || healthRow?.category || "—"}</dd>
              </div>
              {tagNo && (
                <div>
                  <dt className="text-zinc-500">Tag No</dt>
                  <dd className="font-mono text-zinc-900">{tagNo}</dd>
                </div>
              )}
              <div>
                <dt className="text-zinc-500">Verified By</dt>
                <dd className="text-zinc-900">{selection.data.verified_by || healthRow?.latest_verified_by || "—"}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Submission Time</dt>
                <dd className="font-mono text-zinc-900">
                  {formatDateTime(selection.data.timestamp || healthRow?.latest_timestamp)}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Overall Status</dt>
                <dd className="mt-1">
                  <StatusBadge status={selection.data.status || healthRow?.latest_status} />
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Media Available</dt>
                <dd className="text-zinc-900">
                  {selection.data.media_url || selection.data.media_name ? "Yes" : "No"}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Remarks</dt>
                <dd className="text-zinc-900">{selection.data.remarks || healthRow?.latest_remarks || "—"}</dd>
              </div>
            </dl>
          )}

          {isArea && (
            <>
              <AreaStatusBadge status={selection.data.areaStatus} />
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-zinc-500">Equipment</dt>
                  <dd className="font-mono font-medium">{selection.data.configuredCount}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Health</dt>
                  <dd className="font-mono font-medium">
                    {selection.data.healthPercent != null ? `${selection.data.healthPercent}%` : "No data yet"}
                  </dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Normal</dt>
                  <dd className="font-mono text-[#16A34A]">{selection.data.normal}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Warning</dt>
                  <dd className="font-mono text-yellow-700">{selection.data.warning}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Alarm</dt>
                  <dd className="font-mono text-[#E11D48]">{selection.data.alarm}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Pending Today</dt>
                  <dd className="font-mono text-zinc-900">{selection.data.pendingToday}</dd>
                </div>
              </dl>

              <div>
                <h4 className="text-sm uppercase tracking-[0.15em] text-zinc-500 mb-3">Categories → Equipment</h4>
                <div className="space-y-2">
                  {drillDown.map(({ category, equipment }) => (
                    <div key={category} className="border border-zinc-100 rounded-lg overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setExpandedCategory(expandedCategory === category ? null : category)}
                        className="w-full flex items-center justify-between px-3 py-2 bg-zinc-50 text-sm font-medium text-zinc-900 hover:bg-zinc-100"
                      >
                        {category}
                        <span className="text-xs text-zinc-500">{equipment.length} assets</span>
                      </button>
                      {expandedCategory === category && (
                        <div className="p-2 space-y-2">
                          {equipment.map((meta) => (
                            <EquipmentDrillDownItem
                              key={meta.display_name}
                              meta={meta}
                              equipmentHealth={equipmentHealth}
                              recentReadings={recentReadings}
                              onSelectEquipment={onSelectEquipment}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <div>
            <h4 className="text-sm uppercase tracking-[0.15em] text-zinc-500 mb-3">
              {isArea ? "Recent Area Readings" : "Latest Parameters"}
            </h4>
            {latestReadings.length === 0 ? (
              <p className="text-sm text-zinc-500">No recent readings available.</p>
            ) : (
              <ul className="space-y-2">
                {latestReadings.map((row, idx) => (
                  <li key={idx} className="border border-zinc-100 p-3 text-sm rounded">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-zinc-900">
                        {row.equipment}
                        {row.parameter ? ` · ${getParameterDisplay(row)}` : ""}
                      </span>
                      <StatusBadge status={row.status} />
                    </div>
                    <p className="font-mono text-zinc-700 mt-1">
                      {row.value ?? "—"}
                      {row.unit ? ` ${row.unit}` : ""}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{formatDateTime(row.timestamp)}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

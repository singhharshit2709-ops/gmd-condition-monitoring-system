import { useMemo, useState } from "react";
import {
  buildInitialReadings,
  buildV2PreviewPayload,
  collectRenderableParameters,
  countCompletedReadings,
  getExpectedReadingCount,
  getInputStep,
  getMissingRequiredReadings,
  isReadingComplete,
  sortByDisplayOrder,
} from "@/lib/gmdConfigV2";
import { formatV2PreviewError, validateV2Preview } from "@/lib/v2PreviewApi";

function ParameterInput({ param, value, onChange, showRequiredHighlight }) {
  const isEmptyRequired = param.required && !isReadingComplete(value);
  const highlight = showRequiredHighlight && isEmptyRequired;
  const editable = param.editable !== false;

  return (
    <div className="flex flex-col gap-1">
      <label
        className="text-sm font-medium text-zinc-950"
        title={param.display_full_label}
      >
        {param.display_short_label}
        {param.required && <span className="text-[#E11D48] ml-0.5">*</span>}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="number"
          step={getInputStep(param)}
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          disabled={!editable}
          aria-label={param.display_full_label}
          aria-required={param.required}
          className={`w-full max-w-[140px] border px-3 py-1.5 text-sm font-mono text-center rounded-none focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-1 ${
            highlight
              ? "border-2 border-[#E11D48] bg-red-50"
              : "border-zinc-200 bg-white"
          } ${!editable ? "bg-zinc-100 text-zinc-500 cursor-not-allowed" : ""}`}
          placeholder="—"
        />
        <span className="text-xs font-mono text-zinc-500 whitespace-nowrap">{param.unit}</span>
      </div>
      {!editable && (
        <span className="text-[10px] uppercase tracking-wider text-zinc-400">
          Read-only ({param.source || "system"})
        </span>
      )}
    </div>
  );
}

function ParameterTableRow({ param, value, onChange, showRequiredHighlight }) {
  const isEmptyRequired = param.required && !isReadingComplete(value);
  const highlight = showRequiredHighlight && isEmptyRequired;
  const editable = param.editable !== false;

  return (
    <tr className={`border-b border-zinc-100 ${highlight ? "bg-red-50/80" : ""}`}>
      <td className="px-4 py-3 text-sm font-medium text-zinc-950" title={param.display_full_label}>
        {param.display_short_label}
        {param.required && <span className="text-[#E11D48] ml-0.5">*</span>}
      </td>
      <td className="px-4 py-2">
        <input
          type="number"
          step={getInputStep(param)}
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          disabled={!editable}
          aria-label={param.display_full_label}
          aria-required={param.required}
          className={`w-32 border px-3 py-1.5 text-sm font-mono text-center rounded-none focus:outline-none focus:ring-1 focus:ring-[#002FA7] mx-auto block ${
            highlight ? "border-2 border-[#E11D48] bg-red-50" : "border-zinc-200 bg-white"
          } ${!editable ? "bg-zinc-100 text-zinc-500 cursor-not-allowed" : ""}`}
          placeholder="—"
        />
      </td>
      <td className="px-4 py-2 text-center text-xs font-mono text-zinc-500">{param.unit}</td>
    </tr>
  );
}

function GroupBlock({ group, readings, onChange, showRequiredHighlight }) {
  const parameters = sortByDisplayOrder(group.parameters || []).filter(
    (p) => p.is_visible !== false
  );

  if (parameters.length === 0) return null;

  const isTriplet = group.layout === "vibration_triplet" && parameters.length === 3;
  const isSingleTemperature =
    parameters.length === 1 &&
    parameters[0].display_short_label === group.label;

  if (isTriplet) {
    return (
      <div className="mb-6 last:mb-0">
        <h4 className="text-sm font-medium tracking-tight text-zinc-800 mb-3 border-b border-zinc-200 pb-2">
          {group.label}
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {parameters.map((param) => (
            <ParameterInput
              key={param.key}
              param={param}
              value={readings[param.key] ?? ""}
              onChange={onChange}
              showRequiredHighlight={showRequiredHighlight}
            />
          ))}
        </div>
      </div>
    );
  }

  if (isSingleTemperature) {
    const param = parameters[0];
    return (
      <div className="mb-4 last:mb-0">
        <ParameterInput
          param={{ ...param, display_short_label: group.label }}
          value={readings[param.key] ?? ""}
          onChange={onChange}
          showRequiredHighlight={showRequiredHighlight}
        />
      </div>
    );
  }

  return (
    <div className="mb-6 last:mb-0">
      <h4 className="text-sm font-medium tracking-tight text-zinc-800 mb-3 border-b border-zinc-200 pb-2">
        {group.label}
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-zinc-50">
            <tr className="border-b border-zinc-200">
              <th className="text-left px-4 py-2 text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500">
                Parameter
              </th>
              <th className="text-center px-4 py-2 text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500">
                Value
              </th>
              <th className="text-center px-4 py-2 text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-400">
                Unit
              </th>
            </tr>
          </thead>
          <tbody>
            {parameters.map((param) => (
              <ParameterTableRow
                key={param.key}
                param={param}
                value={readings[param.key] ?? ""}
                onChange={onChange}
                showRequiredHighlight={showRequiredHighlight}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SectionBlock({ section, readings, onChange, showRequiredHighlight }) {
  const groups = sortByDisplayOrder(section.groups || []).filter((g) => g.active !== false);

  return (
    <div className="border border-zinc-200 bg-white p-6 mb-6">
      <h3 className="text-lg font-medium tracking-tight text-zinc-900 mb-1">
        {section.label}
      </h3>
      {section.description && (
        <p className="text-sm text-zinc-600 mb-4">{section.description}</p>
      )}
      {groups.map((group) => (
        <GroupBlock
          key={`${section.id}-${group.id}`}
          group={group}
          readings={readings}
          onChange={onChange}
          showRequiredHighlight={showRequiredHighlight}
        />
      ))}
    </div>
  );
}

function SummaryStat({ label, value }) {
  return (
    <div className="border border-zinc-200 bg-zinc-50 p-3">
      <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500 mb-1">
        {label}
      </p>
      <p className="text-sm font-mono font-medium text-zinc-950">{value}</p>
    </div>
  );
}

function PreviewModal({
  open,
  onClose,
  payload,
  loading,
  networkError,
  apiResult,
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="v2-preview-title"
    >
      <div className="w-full max-w-2xl max-h-[85vh] overflow-hidden border border-zinc-200 bg-white flex flex-col">
        <div className="flex items-center justify-between border-b border-zinc-200 px-6 py-4">
          <h3 id="v2-preview-title" className="text-lg font-medium text-zinc-950">
            Submission Preview
          </h3>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="text-sm uppercase tracking-[0.15em] text-zinc-600 hover:text-zinc-950 disabled:opacity-50"
          >
            Close
          </button>
        </div>
        <div className="overflow-y-auto p-6 space-y-4">
          {loading && (
            <div
              className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-700 flex items-center gap-3"
              data-testid="v2-preview-loading"
            >
              <span className="inline-block h-4 w-4 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin" />
              Validating submission with server…
            </div>
          )}

          {!loading && networkError && (
            <div
              className="border-2 border-[#E11D48] bg-red-50 p-4 text-sm text-red-800"
              data-testid="v2-preview-network-error"
            >
              <p className="font-medium">{networkError}</p>
            </div>
          )}

          {!loading && !networkError && apiResult?.success && (
            <div
              className="border-2 border-[#16A34A] bg-green-50 p-4 text-sm text-green-800 space-y-2"
              data-testid="v2-preview-success"
            >
              <p className="font-medium">{apiResult.validation_message}</p>
              <p className="font-mono text-xs">
                Received {apiResult.received_readings} of {apiResult.expected_readings} expected
                readings.
              </p>
            </div>
          )}

          {!loading && !networkError && apiResult && !apiResult.success && (
            <div
              className="border-2 border-[#E11D48] bg-red-50 p-4 text-sm text-red-800 space-y-3"
              data-testid="v2-preview-validation-error"
            >
              <p className="font-medium">{apiResult.validation_message}</p>
              {apiResult.missing_parameters?.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-[0.15em] font-bold mb-1">
                    Missing parameters
                  </p>
                  <ul className="list-disc list-inside space-y-1">
                    {apiResult.missing_parameters.map((item) => (
                      <li key={item.key}>
                        {item.display_full_label || item.key}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {apiResult.invalid_parameters?.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-[0.15em] font-bold mb-1">
                    Invalid parameters
                  </p>
                  <ul className="list-disc list-inside space-y-1">
                    {apiResult.invalid_parameters.map((item) => (
                      <li key={item.key}>
                        <span className="font-mono">{item.key}</span>
                        {" — "}
                        {item.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="font-mono text-xs text-red-700">
                Received {apiResult.received_readings} of {apiResult.expected_readings} expected
                readings.
              </p>
            </div>
          )}

          {payload && (
            <details className="text-xs">
              <summary className="cursor-pointer text-zinc-600 uppercase tracking-[0.15em] font-bold mb-2">
                Debug payload (local)
              </summary>
              <pre className="font-mono bg-zinc-50 border border-zinc-200 p-4 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(payload, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Config-driven round sheet form — render only, no persistence.
 */
export default function RoundSheetForm({
  equipment,
  category,
  configVersion,
  schemaVersion,
}) {
  const renderableRows = useMemo(
    () => collectRenderableParameters(equipment),
    [equipment]
  );

  const [readings, setReadings] = useState(() => buildInitialReadings(renderableRows));
  const [showRequiredHighlight, setShowRequiredHighlight] = useState(true);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewPayload, setPreviewPayload] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewNetworkError, setPreviewNetworkError] = useState(null);
  const [previewApiResult, setPreviewApiResult] = useState(null);

  const expectedCount = getExpectedReadingCount(equipment, renderableRows);
  const completedCount = countCompletedReadings(readings, renderableRows);
  const remainingCount = Math.max(0, expectedCount - completedCount);
  const missingRows = useMemo(
    () => getMissingRequiredReadings(readings, renderableRows),
    [readings, renderableRows]
  );

  const sections = sortByDisplayOrder(equipment.sections || []).filter(
    (s) => s.active !== false
  );

  const handleChange = (key, value) => {
    setReadings((prev) => ({ ...prev, [key]: value }));
  };

  const handleReset = () => {
    setReadings(buildInitialReadings(renderableRows));
    setPreviewOpen(false);
    setPreviewPayload(null);
    setPreviewLoading(false);
    setPreviewNetworkError(null);
    setPreviewApiResult(null);
  };

  const handlePreview = async () => {
    const payload = buildV2PreviewPayload({
      category,
      equipment,
      readings,
      renderableRows,
      configVersion,
      schemaVersion,
    });

    console.log("[V2 Preview] Payload:", payload);

    setPreviewOpen(true);
    setPreviewPayload(payload);
    setPreviewLoading(true);
    setPreviewNetworkError(null);
    setPreviewApiResult(null);

    try {
      const result = await validateV2Preview({
        category: payload.category,
        equipment: payload.equipment,
        readings: payload.readings,
      });
      setPreviewApiResult(result);
    } catch (error) {
      setPreviewNetworkError(formatV2PreviewError(error));
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 mb-6">
        <div className="lg:col-span-8 border border-zinc-200 bg-white p-6">
          <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500 mb-3">
            Round Summary
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <SummaryStat label="Equipment" value={equipment.display_name} />
            <SummaryStat label="Expected Readings" value={String(expectedCount)} />
            <SummaryStat label="Completed" value={String(completedCount)} />
            <SummaryStat label="Remaining" value={String(remainingCount)} />
            <SummaryStat label="Config Version" value={configVersion} />
            <SummaryStat label="Schema Version" value={schemaVersion} />
          </div>
          <div className="mt-4">
            <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500 mb-1">
              Round Progress
            </p>
            <p className="text-2xl font-light font-mono text-zinc-950" data-testid="v2-progress">
              {completedCount} / {expectedCount} completed
            </p>
            <div className="mt-2 h-2 bg-zinc-100 border border-zinc-200">
              <div
                className="h-full bg-[#002FA7] transition-all duration-300"
                style={{
                  width: expectedCount > 0 ? `${(completedCount / expectedCount) * 100}%` : "0%",
                }}
              />
            </div>
          </div>
          <p className="text-sm text-zinc-600 mt-3">{category.display_name}</p>
          {equipment.description && (
            <p className="text-sm text-zinc-500 mt-1">{equipment.description}</p>
          )}
        </div>

        <div className="lg:col-span-4 border border-zinc-200 bg-white p-6">
          <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500 mb-3">
            Missing Readings
          </p>
          {missingRows.length === 0 ? (
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 p-3">
              All required readings entered.
            </p>
          ) : (
            <ul className="space-y-2 max-h-64 overflow-y-auto" data-testid="v2-missing-list">
              {missingRows.map(({ param }) => (
                <li
                  key={param.key}
                  className="text-sm text-zinc-800 border-l-2 border-[#E11D48] pl-3 py-1"
                >
                  {param.display_full_label}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <button
          type="button"
          onClick={handlePreview}
          disabled={previewLoading}
          className="px-5 py-2 bg-[#002FA7] text-white text-sm font-medium uppercase tracking-[0.1em] hover:bg-[#002FA7]/90 disabled:opacity-60 disabled:cursor-not-allowed"
          data-testid="v2-preview-button"
        >
          {previewLoading ? "Validating…" : "Preview"}
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="px-5 py-2 border border-zinc-300 bg-white text-zinc-800 text-sm font-medium uppercase tracking-[0.1em] hover:border-zinc-500"
          data-testid="v2-reset-button"
        >
          Reset
        </button>
      </div>

      {sections.map((section) => (
        <SectionBlock
          key={section.id}
          section={section}
          readings={readings}
          onChange={handleChange}
          showRequiredHighlight={showRequiredHighlight}
        />
      ))}

      <div className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
        <p>
          V2 pilot — configuration-driven preview. Data is not saved. Preview validates against
          POST /api/v2/preview (no persistence).
        </p>
        <label className="flex items-center gap-2 mt-3 text-xs text-zinc-700 cursor-pointer">
          <input
            type="checkbox"
            checked={showRequiredHighlight}
            onChange={(e) => setShowRequiredHighlight(e.target.checked)}
            className="rounded-none"
          />
          Highlight required empty fields
        </label>
      </div>

      <PreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        payload={previewPayload}
        loading={previewLoading}
        networkError={previewNetworkError}
        apiResult={previewApiResult}
      />
    </div>
  );
}

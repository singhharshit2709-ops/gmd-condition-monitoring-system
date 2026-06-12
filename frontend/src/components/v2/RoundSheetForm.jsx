import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { buildRoundSheetFocusChain, FOCUS_STEP, focusStepId } from "@/lib/roundSheetFocusOrder";
import { useRoundSheetKeyboardNavigation } from "@/hooks/useRoundSheetKeyboardNavigation";
import { formatV2PreviewError, validateV2Preview } from "@/lib/v2PreviewApi";
import { formatV2SubmitError, submitV2Round } from "@/lib/v2SubmitApi";

function ParameterInput({
  param,
  value,
  onChange,
  showRequiredHighlight,
  inputRef,
  onInputKeyDown,
}) {
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
          ref={inputRef}
          type="number"
          step={getInputStep(param)}
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          onKeyDown={onInputKeyDown}
          disabled={!editable}
          aria-label={param.display_full_label}
          aria-required={param.required}
          data-focus-step={`param:${param.key}`}
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

function ParameterTableRow({
  param,
  value,
  onChange,
  showRequiredHighlight,
  inputRef,
  onInputKeyDown,
}) {
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
          ref={inputRef}
          type="number"
          step={getInputStep(param)}
          value={value}
          onChange={(e) => onChange(param.key, e.target.value)}
          onKeyDown={onInputKeyDown}
          disabled={!editable}
          aria-label={param.display_full_label}
          aria-required={param.required}
          data-focus-step={`param:${param.key}`}
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

function GroupBlock({ group, readings, onChange, showRequiredHighlight, bindParameterInput }) {
  const parameters = sortByDisplayOrder(group.parameters || []).filter(
    (p) => p.is_visible !== false
  );

  if (parameters.length === 0) return null;

  const isTriplet = group.layout === "vibration_triplet" && parameters.length === 3;
  const isSingleTemperature =
    parameters.length === 1 &&
    parameters[0].display_short_label === group.label;

  const renderInput = (param, labelOverride) => {
    const bindings = bindParameterInput(param.key);
    return (
      <ParameterInput
        key={param.key}
        param={labelOverride ? { ...param, display_short_label: labelOverride } : param}
        value={readings[param.key] ?? ""}
        onChange={onChange}
        showRequiredHighlight={showRequiredHighlight}
        inputRef={bindings.ref}
        onInputKeyDown={bindings.onKeyDown}
      />
    );
  };

  const renderTableRow = (param) => {
    const bindings = bindParameterInput(param.key);
    return (
      <ParameterTableRow
        key={param.key}
        param={param}
        value={readings[param.key] ?? ""}
        onChange={onChange}
        showRequiredHighlight={showRequiredHighlight}
        inputRef={bindings.ref}
        onInputKeyDown={bindings.onKeyDown}
      />
    );
  };

  if (isTriplet) {
    return (
      <div className="mb-6 last:mb-0">
        <h4 className="text-sm font-medium tracking-tight text-zinc-800 mb-3 border-b border-zinc-200 pb-2">
          {group.label}
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {parameters.map((param) => renderInput(param))}
        </div>
      </div>
    );
  }

  if (isSingleTemperature) {
    const param = parameters[0];
    return (
      <div className="mb-4 last:mb-0">
        {renderInput(param, group.label)}
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
            {parameters.map((param) => renderTableRow(param))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SectionBlock({ section, readings, onChange, showRequiredHighlight, bindParameterInput }) {
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
          bindParameterInput={bindParameterInput}
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

function RoundSheetMetadataSection({
  verifiedBy,
  onVerifiedByChange,
  remarks,
  onRemarksChange,
  photoPreview,
  photoFilename,
  onPhotoSelect,
  onPhotoClear,
  bindMetadataInput,
  uploadButtonRef,
  onUploadKeyDown,
}) {
  return (
    <div className="border border-zinc-200 bg-white p-6 mb-6">
      <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500 mb-4">
        Round Completion
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label
              htmlFor="round-sheet-verified-by"
              className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-2 block"
            >
              Verified By
            </label>
            <input
              id="round-sheet-verified-by"
              type="text"
              value={verifiedBy}
              onChange={(e) => onVerifiedByChange(e.target.value)}
              placeholder="Enter your name"
              ref={bindMetadataInput(FOCUS_STEP.VERIFIED_BY).ref}
              onKeyDown={bindMetadataInput(FOCUS_STEP.VERIFIED_BY).onKeyDown}
              data-focus-step={FOCUS_STEP.VERIFIED_BY}
              className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2 rounded-none"
            />
          </div>
          <div>
            <label
              htmlFor="round-sheet-remarks"
              className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-2 block"
            >
              Remarks
            </label>
            <input
              id="round-sheet-remarks"
              type="text"
              value={remarks}
              onChange={(e) => onRemarksChange(e.target.value)}
              placeholder="Enter any observational notes"
              ref={bindMetadataInput(FOCUS_STEP.REMARKS).ref}
              onKeyDown={bindMetadataInput(FOCUS_STEP.REMARKS).onKeyDown}
              data-focus-step={FOCUS_STEP.REMARKS}
              className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2 rounded-none"
            />
          </div>
        </div>
        <div>
          <p className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-3">
            Upload Media
          </p>
          {!photoPreview ? (
            <button
              type="button"
              ref={uploadButtonRef}
              onClick={onPhotoSelect}
              onKeyDown={onUploadKeyDown}
              data-focus-step={FOCUS_STEP.UPLOAD}
              className="flex items-center gap-2 px-4 py-3 border-2 border-dashed border-zinc-300 hover:border-[#002FA7] bg-white text-sm text-zinc-700 transition-all duration-150 rounded-none w-full md:w-auto focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2"
            >
              Capture / Upload Photo
            </button>
          ) : (
            <div className="space-y-2">
              <img
                src={photoPreview}
                alt="Upload preview"
                className="w-48 h-36 object-cover border-2 border-[#002FA7]"
              />
              <p className="text-xs font-mono text-zinc-500 truncate">{photoFilename}</p>
              <button
                type="button"
                onClick={onPhotoClear}
                className="text-xs uppercase tracking-[0.15em] text-[#E11D48] hover:underline"
              >
                Remove photo
              </button>
            </div>
          )}
        </div>
      </div>
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
  onSubmit,
  submitLoading,
  submitError,
  submitResult,
  submitDisabled,
  submitButtonRef,
}) {
  if (!open) return null;

  const canSubmit =
    !loading &&
    !networkError &&
    apiResult?.success &&
    !submitResult &&
    !submitDisabled;

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
            disabled={loading || submitLoading}
            className="text-sm uppercase tracking-[0.15em] text-zinc-600 hover:text-zinc-950 disabled:opacity-50"
          >
            Close
          </button>
        </div>
        <div className="overflow-y-auto p-6 space-y-4 flex-1">
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

          {!loading && !networkError && apiResult?.success && !submitResult && (
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

          {submitLoading && (
            <div
              className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-700 flex items-center gap-3"
              data-testid="v2-submit-loading"
            >
              <span className="inline-block h-4 w-4 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin" />
              Submitting…
            </div>
          )}

          {!submitLoading && submitError && (
            <div
              className="border-2 border-[#E11D48] bg-red-50 p-4 text-sm text-red-800 space-y-3"
              data-testid="v2-submit-error"
            >
              <p className="font-medium">{submitError.message}</p>
              {submitError.missing_parameters?.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-[0.15em] font-bold mb-1">
                    Missing parameters
                  </p>
                  <ul className="list-disc list-inside space-y-1">
                    {submitError.missing_parameters.map((item) => (
                      <li key={item.key}>
                        {item.display_full_label || item.key}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {submitError.invalid_parameters?.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-[0.15em] font-bold mb-1">
                    Invalid parameters
                  </p>
                  <ul className="list-disc list-inside space-y-1">
                    {submitError.invalid_parameters.map((item) => (
                      <li key={item.key}>
                        <span className="font-mono">{item.key}</span>
                        {" — "}
                        {item.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {submitResult && (
            <div
              className="border-2 border-[#16A34A] bg-green-50 p-4 text-sm text-green-800 space-y-2"
              data-testid="v2-submit-success"
            >
              <p className="font-medium">{submitResult.message}</p>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono mt-2">
                <div>
                  <dt className="uppercase tracking-[0.1em] text-green-700">Equipment</dt>
                  <dd>{submitResult.equipment}</dd>
                </div>
                <div>
                  <dt className="uppercase tracking-[0.1em] text-green-700">Category</dt>
                  <dd>{submitResult.category}</dd>
                </div>
                <div>
                  <dt className="uppercase tracking-[0.1em] text-green-700">Reading count</dt>
                  <dd>{submitResult.reading_count}</dd>
                </div>
                <div>
                  <dt className="uppercase tracking-[0.1em] text-green-700">Submitted at</dt>
                  <dd>{submitResult.submitted_at}</dd>
                </div>
              </dl>
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

        {canSubmit && (
          <div className="border-t border-zinc-200 px-6 py-4 bg-zinc-50">
            <button
              type="button"
              ref={submitButtonRef}
              onClick={onSubmit}
              disabled={submitLoading || submitDisabled}
              className="w-full sm:w-auto px-5 py-2 bg-[#16A34A] text-white text-sm font-medium uppercase tracking-[0.1em] hover:bg-[#16A34A]/90 disabled:opacity-60 disabled:cursor-not-allowed"
              data-testid="v2-submit-button-modal"
            >
              Submit Round
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Config-driven round sheet form with keyboard navigation and preview/submit workflow.
 */
export default function RoundSheetForm({
  equipment,
  category,
  areaTank = "",
  tagNo = "",
  configVersion,
  schemaVersion,
}) {
  const renderableRows = useMemo(
    () => collectRenderableParameters(equipment),
    [equipment]
  );

  const focusChain = useMemo(
    () => buildRoundSheetFocusChain(renderableRows),
    [renderableRows]
  );

  const { getRef, focusFirst, focusByStepId, handleNavigationKeyDown } =
    useRoundSheetKeyboardNavigation(focusChain);

  const fileInputRef = useRef(null);
  const submissionIdRef = useRef(
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `submission-${Date.now()}`
  );

  const [readings, setReadings] = useState(() => buildInitialReadings(renderableRows));
  const [verifiedBy, setVerifiedBy] = useState("");
  const [remarks, setRemarks] = useState("");
  const [photoPreview, setPhotoPreview] = useState(null);
  const [photoFilename, setPhotoFilename] = useState("");
  const [photoMimeType, setPhotoMimeType] = useState("");
  const [showRequiredHighlight, setShowRequiredHighlight] = useState(true);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewPayload, setPreviewPayload] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewNetworkError, setPreviewNetworkError] = useState(null);
  const [previewApiResult, setPreviewApiResult] = useState(null);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);
  const [submitCompleted, setSubmitCompleted] = useState(false);

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

  const canSubmitFromToolbar =
    previewApiResult?.success && !previewLoading && !submitLoading && !submitCompleted;

  const clearSubmitState = useCallback(() => {
    setSubmitLoading(false);
    setSubmitError(null);
    setSubmitResult(null);
    setSubmitCompleted(false);
  }, []);

  const clearPreviewState = useCallback(() => {
    setPreviewLoading(false);
    setPreviewNetworkError(null);
    setPreviewApiResult(null);
  }, []);

  const invalidateWorkflow = useCallback(() => {
    clearPreviewState();
    clearSubmitState();
    setPreviewPayload(null);
  }, [clearPreviewState, clearSubmitState]);

  const buildPayload = useCallback(
    () =>
      buildV2PreviewPayload({
        category,
        equipment,
        readings,
        renderableRows,
        configVersion,
        schemaVersion,
        verifiedBy,
        remarks,
        media: photoPreview
          ? {
              name: photoFilename,
              type: photoMimeType,
              data: photoPreview,
            }
          : null,
        areaTank,
        tagNo,
        submissionId: submissionIdRef.current,
      }),
    [
      category,
      equipment,
      readings,
      renderableRows,
      configVersion,
      schemaVersion,
      verifiedBy,
      remarks,
      photoPreview,
      photoFilename,
      photoMimeType,
      areaTank,
      tagNo,
    ]
  );

  const bindParameterInput = useCallback(
    (paramKey) => {
      const stepId = focusStepId({ type: FOCUS_STEP.PARAMETER, key: paramKey });
      return {
        ref: getRef(stepId),
        onKeyDown: (event) => handleNavigationKeyDown(event, stepId),
      };
    },
    [getRef, handleNavigationKeyDown]
  );

  const bindMetadataInput = useCallback(
    (stepType) => ({
      ref: getRef(stepType),
      onKeyDown: (event) => handleNavigationKeyDown(event, stepType),
    }),
    [getRef, handleNavigationKeyDown]
  );

  const bindActionButton = useCallback(
    (stepType) => ({
      ref: getRef(stepType),
      onKeyDown: (event) => {
        if (
          event.key === "ArrowUp" ||
          event.key === "ArrowDown" ||
          event.key === "ArrowLeft" ||
          event.key === "ArrowRight"
        ) {
          handleNavigationKeyDown(event, stepType);
        }
      },
    }),
    [getRef, handleNavigationKeyDown]
  );

  const handleUploadKeyDown = useCallback(
    (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fileInputRef.current?.click();
        return;
      }
      handleNavigationKeyDown(event, FOCUS_STEP.UPLOAD);
    },
    [handleNavigationKeyDown]
  );

  const handleChange = (key, value) => {
    setReadings((prev) => ({ ...prev, [key]: value }));
    invalidateWorkflow();
  };

  const handleVerifiedByChange = (value) => {
    setVerifiedBy(value);
    invalidateWorkflow();
  };

  const handleRemarksChange = (value) => {
    setRemarks(value);
    invalidateWorkflow();
  };

  const handlePhotoSelect = () => {
    fileInputRef.current?.click();
  };

  const handlePhotoCapture = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      setPhotoPreview(reader.result);
      setPhotoFilename(file.name);
      setPhotoMimeType(file.type || "");
      invalidateWorkflow();
    };
    reader.readAsDataURL(file);
    event.target.value = "";
  };

  const handlePhotoClear = () => {
    setPhotoPreview(null);
    setPhotoFilename("");
    setPhotoMimeType("");
    invalidateWorkflow();
  };

  const handleReset = () => {
    setReadings(buildInitialReadings(renderableRows));
    setVerifiedBy("");
    setRemarks("");
    setPhotoPreview(null);
    setPhotoFilename("");
    setPhotoMimeType("");
    submissionIdRef.current =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `submission-${Date.now()}`;
    setPreviewOpen(false);
    setPreviewPayload(null);
    clearPreviewState();
    clearSubmitState();
    window.setTimeout(() => focusFirst(), 0);
  };

  const handlePreview = async () => {
    const payload = buildPayload();

    console.log("[V2 Preview] Payload:", payload);

    setPreviewOpen(true);
    setPreviewPayload(payload);
    setPreviewLoading(true);
    setPreviewNetworkError(null);
    setPreviewApiResult(null);
    clearSubmitState();

    try {
      const result = await validateV2Preview({
        category: payload.category,
        equipment: payload.equipment,
        readings: payload.readings,
      });
      console.log("[V2 Preview] Response", {
        timestamp: new Date().toISOString(),
        result,
      });
      setPreviewApiResult(result);
    } catch (error) {
      setPreviewNetworkError(formatV2PreviewError(error));
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!previewPayload || submitCompleted || submitLoading) return;

    setSubmitLoading(true);
    setSubmitError(null);
    setSubmitResult(null);

    try {
      const result = await submitV2Round(previewPayload);
      setSubmitResult(result);
      setSubmitCompleted(true);
      console.log("[V2 Submit] Recorded successfully:", result);
    } catch (error) {
      const responseData = error.response?.data;
      if (error.isValidationFailure || (responseData?.success === false && responseData?.validation_message)) {
        setSubmitError({
          message: responseData?.validation_message || error.message,
          missing_parameters: responseData?.missing_parameters || [],
          invalid_parameters: responseData?.invalid_parameters || [],
        });
      } else {
        setSubmitError({ message: formatV2SubmitError(error) });
      }
    } finally {
      setSubmitLoading(false);
    }
  };

  const previewButtonBindings = bindActionButton(FOCUS_STEP.PREVIEW);
  const submitButtonBindings = bindActionButton(FOCUS_STEP.SUBMIT);

  useEffect(() => {
    if (previewApiResult?.success && !previewLoading) {
      const target = previewOpen ? "submit_modal" : FOCUS_STEP.SUBMIT;
      const timer = window.setTimeout(() => focusByStepId(target), 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [previewApiResult, previewLoading, previewOpen, focusByStepId]);

  useEffect(() => {
    const timer = window.setTimeout(() => focusFirst(), 0);
    return () => window.clearTimeout(timer);
  }, [equipment.id, focusFirst]);

  return (
    <div>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handlePhotoCapture}
        className="hidden"
        tabIndex={-1}
        aria-hidden="true"
      />

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

      {sections.map((section) => (
        <SectionBlock
          key={section.id}
          section={section}
          readings={readings}
          onChange={handleChange}
          showRequiredHighlight={showRequiredHighlight}
          bindParameterInput={bindParameterInput}
        />
      ))}

      <RoundSheetMetadataSection
        verifiedBy={verifiedBy}
        onVerifiedByChange={handleVerifiedByChange}
        remarks={remarks}
        onRemarksChange={handleRemarksChange}
        photoPreview={photoPreview}
        photoFilename={photoFilename}
        onPhotoSelect={handlePhotoSelect}
        onPhotoClear={handlePhotoClear}
        bindMetadataInput={bindMetadataInput}
        uploadButtonRef={getRef(FOCUS_STEP.UPLOAD)}
        onUploadKeyDown={handleUploadKeyDown}
      />

      <div className="flex flex-wrap gap-3 mb-6">
        <button
          type="button"
          ref={previewButtonBindings.ref}
          onKeyDown={previewButtonBindings.onKeyDown}
          onClick={handlePreview}
          disabled={previewLoading || submitLoading || submitCompleted}
          data-focus-step={FOCUS_STEP.PREVIEW}
          data-testid="v2-preview-button"
          className="px-5 py-2 bg-[#002FA7] text-white text-sm font-medium uppercase tracking-[0.1em] hover:bg-[#002FA7]/90 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2"
        >
          {previewLoading ? "Validating…" : "Preview"}
        </button>
        <button
          type="button"
          ref={submitButtonBindings.ref}
          onKeyDown={submitButtonBindings.onKeyDown}
          onClick={handleSubmit}
          disabled={!canSubmitFromToolbar}
          data-focus-step={FOCUS_STEP.SUBMIT}
          data-testid="v2-submit-button"
          className="px-5 py-2 bg-[#16A34A] text-white text-sm font-medium uppercase tracking-[0.1em] hover:bg-[#16A34A]/90 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#16A34A] focus:ring-offset-2"
        >
          {submitLoading ? "Submitting…" : "Submit"}
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

      <div className="border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
        <p>
          Preview validates against POST /api/v2/preview; submit persists via POST /api/v2/submit
          after successful validation. Use Enter to move forward, Shift+Enter to move back, and
          arrow keys to navigate fields in display order.
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
        onSubmit={handleSubmit}
        submitLoading={submitLoading}
        submitError={submitError}
        submitResult={submitResult}
        submitDisabled={submitCompleted}
        submitButtonRef={getRef("submit_modal")}
      />
    </div>
  );
}

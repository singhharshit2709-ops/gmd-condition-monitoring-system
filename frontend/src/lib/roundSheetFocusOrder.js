/** Focus step types for Add Reading round sheet keyboard navigation. */
export const FOCUS_STEP = {
  PARAMETER: "parameter",
  VERIFIED_BY: "verified_by",
  REMARKS: "remarks",
  UPLOAD: "upload_media",
  PREVIEW: "preview",
  SUBMIT: "submit",
};

export function focusStepId(step) {
  if (step.type === FOCUS_STEP.PARAMETER) {
    return `param:${step.key}`;
  }
  return step.type;
}

/**
 * Build ordered focus chain matching maintenance round sheet display order.
 * Skips read-only parameters (editable === false).
 */
export function buildRoundSheetFocusChain(renderableRows) {
  const chain = renderableRows
    .filter(({ param }) => param.editable !== false)
    .map(({ param }) => ({
      type: FOCUS_STEP.PARAMETER,
      key: param.key,
    }));

  chain.push(
    { type: FOCUS_STEP.VERIFIED_BY },
    { type: FOCUS_STEP.REMARKS },
    { type: FOCUS_STEP.UPLOAD },
    { type: FOCUS_STEP.PREVIEW },
    { type: FOCUS_STEP.SUBMIT }
  );

  return chain;
}

export function findFocusStepIndex(chain, stepId) {
  return chain.findIndex((step) => focusStepId(step) === stepId);
}

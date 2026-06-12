import axios from "axios";
import { getApiBase } from "./api";

function redactPayload(body) {
  if (!body?.media_data) return body;
  return { ...body, media_data: "(redacted)" };
}

/**
 * Submit a validated V2 round sheet to POST /api/v2/submit.
 * Expects the same payload shape produced by buildV2PreviewPayload.
 * Throws if validation fails (HTTP 200) or persistence fails.
 */
export async function submitV2Round(payload) {
  const apiBase = getApiBase();
  const body = {
    category: payload.category,
    equipment: payload.equipment,
    readings: payload.readings,
    verified_by: payload.verified_by ?? "",
    remarks: payload.remarks ?? "",
    entry_source: payload.entry_source ?? "Web",
    area_tank: payload.area_tank ?? "",
    tag_no: payload.tag_no ?? "",
    submission_id: payload.submission_id ?? "",
  };

  if (payload.media_data) {
    body.media_name = payload.media_name ?? "";
    body.media_type = payload.media_type ?? "";
    body.media_data = payload.media_data;
  }

  console.log("[V2 Submit] Request", {
    timestamp: new Date().toISOString(),
    apiBase,
    payload: redactPayload(body),
  });

  const response = await axios.post(`${apiBase}/api/v2/submit`, body);

  console.log("[V2 Submit] Response", {
    timestamp: new Date().toISOString(),
    status: response.status,
    data: response.data,
  });

  if (response.status === 200) {
    const data = response.data || {};
    const error = new Error(data.validation_message || "Validation failed before submit.");
    error.response = { data, status: 200 };
    error.isValidationFailure = true;
    throw error;
  }

  if (response.status !== 201) {
    throw new Error(`Unexpected submit response status ${response.status}.`);
  }

  const data = response.data || {};
  if (!data.success || !data.submitted_at || !(data.reading_count > 0)) {
    throw new Error(data.message || "Submit did not persist readings to Google Sheets.");
  }

  if (typeof window !== "undefined") {
    window.localStorage.removeItem("dashboardSummary");
    window.dispatchEvent(
      new CustomEvent("gmd-readings-updated", {
        detail: data,
      })
    );
  }

  return data;
}

export function formatV2SubmitError(error) {
  if (!error.response) {
    return "Unable to reach the validation server. Check that the backend is running.";
  }

  const { data, status } = error.response;

  if (data?.validation_message) {
    return data.validation_message;
  }

  if (data?.message) {
    return data.message;
  }

  const detail = data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  if (detail && typeof detail === "object" && detail.message) {
    return detail.message;
  }

  return error.message || `Submit request failed (${status}).`;
}

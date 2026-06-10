import axios from "axios";
import { getApiBase } from "./api";

/**
 * Validate a V2 round sheet submission against POST /api/v2/preview.
 * Does not persist data.
 */
export async function validateV2Preview({ category, equipment, readings }) {
  const apiBase = getApiBase();
  const response = await axios.post(`${apiBase}/api/v2/preview`, {
    category,
    equipment,
    readings,
  });
  return response.data;
}

export function formatV2PreviewError(error) {
  if (!error.response) {
    return "Unable to reach the validation server. Check that the backend is running.";
  }

  const { data, status } = error.response;

  if (data?.validation_message) {
    return data.validation_message;
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

  return error.message || `Validation request failed (${status}).`;
}

/**
 * API base URL: env override, else same origin (production static+API on Render), else local backend.
 */
export function getApiBase() {
  const fromEnv = process.env.REACT_APP_BACKEND_URL;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, "");
  }
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
}

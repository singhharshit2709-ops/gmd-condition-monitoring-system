export function getApiBase() {
  const fromEnv = process.env.REACT_APP_BACKEND_URL;

  if (fromEnv !== undefined && fromEnv !== null && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, "");
  }

  if (typeof window !== "undefined" && window.location?.origin) {
    const port = window.location.port;
    // CRA / Vite dev servers proxy to backend on 8000
    if (port === "3000" || port === "5173") {
      return "http://127.0.0.1:8000";
    }
    return window.location.origin;
  }

  return "http://127.0.0.1:8000";
}

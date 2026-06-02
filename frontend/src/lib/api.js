export function getApiBase() {
  const fromEnv = process.env.REACT_APP_BACKEND_URL;

  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, "");
  }

  return "http://127.0.0.1:8000";
}

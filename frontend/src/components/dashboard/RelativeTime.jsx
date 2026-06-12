import { formatRelativeTime } from "@/lib/dashboardAnalytics";

function toTimestampValue(value) {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString();
  return String(value);
}

/** Inline relative timestamp with full value in tooltip. */
export default function RelativeTime({ value, className = "" }) {
  const timestamp = toTimestampValue(value);
  const { label, title } = formatRelativeTime(timestamp);
  if (label === "—") {
    return <span className={className}>—</span>;
  }
  return (
    <time dateTime={timestamp || undefined} title={title || undefined} className={className}>
      {label}
    </time>
  );
}

import { normalizeStatus, DASHBOARD_STATUS } from "@/lib/dashboardAnalytics";

const STYLES = {
  NORMAL: "bg-[#16A34A] text-white",
  WARNING: "bg-yellow-500 text-white",
  ALARM: "bg-[#E11D48] text-white",
  PENDING: "bg-zinc-200 text-zinc-700",
};

const LABELS = {
  NORMAL: `${DASHBOARD_STATUS.NORMAL.emoji} NORMAL`,
  WARNING: `${DASHBOARD_STATUS.WARNING.emoji} WARNING`,
  ALARM: `${DASHBOARD_STATUS.ALARM.emoji} ALARM`,
  PENDING: `${DASHBOARD_STATUS.PENDING.emoji} PENDING`,
};

export default function StatusBadge({ status, className = "" }) {
  const normalized = normalizeStatus(status);
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 text-xs font-bold uppercase tracking-wider rounded-sm ${STYLES[normalized] || STYLES.NORMAL} ${className}`}
    >
      {LABELS[normalized] || LABELS.NORMAL}
    </span>
  );
}

import { DASHBOARD_STATUS } from "@/lib/dashboardAnalytics";

const STYLES = {
  NORMAL: {
    dot: "bg-[#16A34A]",
    text: "text-[#16A34A]",
    label: `${DASHBOARD_STATUS.NORMAL.emoji} ${DASHBOARD_STATUS.NORMAL.label}`,
  },
  WARNING: {
    dot: "bg-yellow-500",
    text: "text-yellow-700",
    label: `${DASHBOARD_STATUS.WARNING.emoji} ${DASHBOARD_STATUS.WARNING.label}`,
  },
  ALARM: {
    dot: "bg-[#E11D48]",
    text: "text-[#E11D48]",
    label: `${DASHBOARD_STATUS.ALARM.emoji} ${DASHBOARD_STATUS.ALARM.label}`,
  },
  PENDING: {
    dot: "bg-zinc-300",
    text: "text-zinc-600",
    label: `${DASHBOARD_STATUS.PENDING.emoji} ${DASHBOARD_STATUS.PENDING.label}`,
  },
};

export default function AreaStatusBadge({ status, className = "" }) {
  const tone = STYLES[status] || STYLES.PENDING;
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-medium ${tone.text} ${className}`}>
      <span className={`h-2.5 w-2.5 rounded-full ${tone.dot}`} aria-hidden />
      {tone.label}
    </span>
  );
}

import { CheckCircle, HourglassHigh, Warning } from "@phosphor-icons/react";

const TONE_STYLES = {
  normal: {
    border: "border-[#16A34A]",
    bg: "bg-green-50",
    text: "text-[#16A34A]",
    sub: "text-green-700",
    icon: CheckCircle,
    emoji: "🟢",
  },
  warning: {
    border: "border-yellow-500",
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    sub: "text-yellow-800",
    icon: Warning,
    emoji: "🟡",
  },
  alarm: {
    border: "border-[#E11D48]",
    bg: "bg-red-50",
    text: "text-[#E11D48]",
    sub: "text-red-700",
    icon: Warning,
    emoji: "🔴",
  },
  pending: {
    border: "border-zinc-300",
    bg: "bg-zinc-50",
    text: "text-zinc-700",
    sub: "text-zinc-600",
    icon: HourglassHigh,
    emoji: "⚪",
  },
};

export default function PlantHealthBanner({ banner, lastRefreshLabel }) {
  const tone = TONE_STYLES[banner.tone] || TONE_STYLES.normal;
  const Icon = tone.icon;

  return (
    <div className={`border-2 ${tone.border} ${tone.bg} p-5 md:p-6 rounded-lg`}>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start gap-3">
          <Icon size={28} weight="fill" className={tone.text} />
          <div>
            <h2 className={`text-xl font-medium tracking-tight ${tone.text}`}>
              {tone.emoji} {banner.title}
            </h2>
            <p className={`text-sm mt-1 ${tone.sub}`}>{banner.description}</p>
          </div>
        </div>
        {lastRefreshLabel && (
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500 shrink-0">
            Dashboard refresh: {lastRefreshLabel}
          </p>
        )}
      </div>
    </div>
  );
}

import { CheckCircle, Clock, HourglassHigh } from "@phosphor-icons/react";

const TONE_STYLES = {
  pending: {
    border: "border-yellow-400",
    bg: "bg-yellow-50/80",
    text: "text-yellow-800",
    sub: "text-yellow-700",
    icon: HourglassHigh,
    emoji: "🟡",
  },
  in_progress: {
    border: "border-[#16A34A]",
    bg: "bg-green-50/80",
    text: "text-[#16A34A]",
    sub: "text-green-700",
    icon: CheckCircle,
    emoji: "🟢",
  },
};

export default function TodayRoundBanner({ banner }) {
  if (!banner) return null;

  const tone = TONE_STYLES[banner.tone] || TONE_STYLES.pending;
  const Icon = tone.icon;

  return (
    <div className={`border ${tone.border} ${tone.bg} px-5 py-4 rounded-lg`}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <Icon size={22} weight="duotone" className={`${tone.text} shrink-0 mt-0.5`} />
          <div className="min-w-0">
            <h2 className={`text-base font-medium tracking-tight ${tone.text}`}>
              {tone.emoji} {banner.title}
            </h2>
            <p className={`text-sm mt-0.5 ${tone.sub}`}>{banner.description}</p>
          </div>
        </div>
        {banner.metaLabel && banner.metaValue && (
          <div className="flex items-center gap-2 text-sm text-zinc-600 shrink-0 sm:text-right">
            <Clock size={16} className="text-zinc-400 shrink-0" />
            <span>
              {banner.metaLabel}:{" "}
              <time dateTime={banner.metaTitle || undefined} title={banner.metaTitle || undefined}>
                {banner.metaValue}
              </time>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

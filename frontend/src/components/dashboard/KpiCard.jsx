export default function KpiCard({ icon: Icon, title, value, description, accent = "border-zinc-200", valueTitle = "" }) {
  return (
    <div className={`bg-white border ${accent} p-5 rounded-lg shadow-sm`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">{title}</p>
          <p
            className="text-2xl md:text-3xl font-light text-zinc-950 mt-2 leading-tight"
            title={valueTitle || undefined}
          >
            {value}
          </p>
          <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{description}</p>
        </div>
        {Icon && <Icon size={24} weight="duotone" className="text-[#002FA7] shrink-0" />}
      </div>
    </div>
  );
}

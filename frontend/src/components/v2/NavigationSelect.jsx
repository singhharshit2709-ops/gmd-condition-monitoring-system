export default function NavigationSelect({
  id,
  label,
  value,
  onChange,
  disabled,
  placeholder,
  options,
  testId,
}) {
  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={id}
        className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        data-testid={testId}
        className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 rounded-none focus:outline-none focus:ring-2 focus:ring-[#002FA7] disabled:bg-zinc-100 disabled:text-zinc-500"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

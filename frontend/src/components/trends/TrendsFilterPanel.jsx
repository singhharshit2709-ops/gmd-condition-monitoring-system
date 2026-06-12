import { Progress } from "@/components/ui/progress";

function FilterSelect({ label, value, onChange, options, placeholder = "Select…", disabled = false }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-[0.15em] text-zinc-500">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="mt-1 w-full border border-zinc-200 bg-white px-3 py-2.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-[#002FA7] rounded disabled:opacity-50"
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function TrendsFilterPanel({
  areas,
  categories,
  equipmentOptions,
  parameters,
  selectedArea,
  selectedCategory,
  selectedEquipmentId,
  selectedParameter,
  compareParameters,
  windowOption,
  startDate,
  endDate,
  onAreaChange,
  onCategoryChange,
  onEquipmentChange,
  onParameterChange,
  onCompareChange,
  onWindowChange,
  onStartDateChange,
  onEndDateChange,
}) {
  const toggleCompare = (key) => {
    if (compareParameters.includes(key)) {
      onCompareChange(compareParameters.filter((k) => k !== key));
    } else if (compareParameters.length < 3) {
      onCompareChange([...compareParameters, key]);
    }
  };

  return (
    <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg space-y-5">
      <div>
        <h3 className="text-lg font-medium text-zinc-900">Trend Explorer</h3>
        <p className="text-sm text-zinc-500 mt-1">Select area → equipment → parameter to plot historical readings</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FilterSelect
          label="Area / Tank"
          value={selectedArea}
          onChange={onAreaChange}
          options={areas.map((a) => ({ value: a, label: a }))}
          placeholder="Select area…"
        />
        <FilterSelect
          label="Category"
          value={selectedCategory}
          onChange={onCategoryChange}
          options={categories.map((c) => ({ value: c, label: c }))}
          placeholder="All categories"
          disabled={!selectedArea}
        />
        <FilterSelect
          label="Equipment"
          value={selectedEquipmentId}
          onChange={onEquipmentChange}
          options={equipmentOptions.map((eq) => ({
            value: eq.id,
            label: eq.tag_no ? `${eq.display_name} (${eq.tag_no})` : eq.display_name,
          }))}
          placeholder="Select equipment…"
          disabled={!selectedArea}
        />
        <FilterSelect
          label="Parameter"
          value={selectedParameter}
          onChange={onParameterChange}
          options={parameters.map((p) => ({
            value: p.key,
            label: p.unit ? `${p.label} (${p.unit})` : p.label,
          }))}
          placeholder="Select parameter…"
          disabled={!selectedEquipmentId}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FilterSelect
          label="Time Range"
          value={windowOption}
          onChange={onWindowChange}
          options={[
            { value: "all", label: "All history" },
            { value: "7", label: "Last 7 days" },
            { value: "30", label: "Last 30 days" },
            { value: "90", label: "Last 90 days" },
            { value: "custom", label: "Custom range" },
          ]}
          placeholder="Time range"
        />
        {windowOption === "custom" && (
          <>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.15em] text-zinc-500">Start Date</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => onStartDateChange(e.target.value)}
                className="mt-1 w-full border border-zinc-200 bg-white px-3 py-2.5 text-sm rounded focus:outline-none focus:ring-2 focus:ring-[#002FA7]"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.15em] text-zinc-500">End Date</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => onEndDateChange(e.target.value)}
                className="mt-1 w-full border border-zinc-200 bg-white px-3 py-2.5 text-sm rounded focus:outline-none focus:ring-2 focus:ring-[#002FA7]"
              />
            </label>
          </>
        )}
      </div>

      {parameters.length > 1 && selectedParameter && (
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-zinc-500 mb-2">
            Compare on chart (up to 3)
          </p>
          <div className="flex flex-wrap gap-2">
            {parameters.map((p) => {
              const active = compareParameters.includes(p.key) || p.key === selectedParameter;
              const isPrimary = p.key === selectedParameter;
              return (
                <button
                  key={p.key}
                  type="button"
                  disabled={isPrimary}
                  onClick={() => toggleCompare(p.key)}
                  className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                    isPrimary
                      ? "border-[#002FA7] bg-[#002FA7] text-white cursor-default"
                      : active
                        ? "border-[#002FA7] text-[#002FA7] bg-blue-50"
                        : "border-zinc-200 text-zinc-600 hover:border-zinc-300"
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

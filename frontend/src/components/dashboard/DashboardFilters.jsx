function FilterSelect({ label, value, onChange, options, allLabel = "All" }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-[0.15em] text-zinc-500">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-[#002FA7] rounded"
      >
        <option value="all">{allLabel}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

const CASCADE_RESET = {
  area: ["category", "equipment", "tagNo"],
  category: ["equipment", "tagNo"],
  equipment: ["tagNo"],
};

export default function DashboardFilters({ filters, filterOptions, onChange }) {
  const set = (key) => (value) => {
    const next = { ...filters, [key]: value };
    for (const resetKey of CASCADE_RESET[key] || []) {
      next[resetKey] = "all";
    }
    onChange(next);
  };

  return (
    <section className="bg-white border border-zinc-200 p-5 md:p-6 rounded-lg">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-lg font-medium text-zinc-900">Filters</h3>
          <p className="text-sm text-zinc-500 mt-1">Cascade by area → category → equipment → tag</p>
        </div>
        <button
          type="button"
          onClick={() =>
            onChange({
              area: "all",
              category: "all",
              equipment: "all",
              tagNo: "all",
              status: "all",
              verifiedBy: "all",
            })
          }
          className="text-xs uppercase tracking-[0.12em] text-[#002FA7] hover:underline"
        >
          Clear all
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <FilterSelect label="Area" value={filters.area} onChange={set("area")} options={filterOptions.areas} />
        <FilterSelect
          label="Category"
          value={filters.category}
          onChange={set("category")}
          options={filterOptions.categories}
        />
        <FilterSelect
          label="Equipment"
          value={filters.equipment}
          onChange={set("equipment")}
          options={filterOptions.equipment}
        />
        <FilterSelect label="Tag No" value={filters.tagNo} onChange={set("tagNo")} options={filterOptions.tagNos} />
        <FilterSelect label="Status" value={filters.status} onChange={set("status")} options={filterOptions.statuses} />
        <FilterSelect
          label="Verified By"
          value={filters.verifiedBy}
          onChange={set("verifiedBy")}
          options={filterOptions.verifiedBy}
        />
      </div>
    </section>
  );
}

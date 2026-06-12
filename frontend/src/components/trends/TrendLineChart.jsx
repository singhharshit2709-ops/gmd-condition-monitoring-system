import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import { formatTrendTimestamp } from "@/lib/trendsAnalytics";

export default function TrendLineChart({ rows, series, thresholdLines = [], yAxisLabel = "" }) {
  if (!rows.length || !series.length) {
    return (
      <div className="border border-dashed border-zinc-200 rounded-lg p-12 text-center text-sm text-zinc-500">
        No trend data for the selected filters. Try a broader time range or different equipment/parameter.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart data={rows} margin={{ top: 12, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "#71717a" }}
          interval="preserveStartEnd"
          minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#71717a" }}
          label={
            yAxisLabel
              ? { value: yAxisLabel, angle: -90, position: "insideLeft", style: { fill: "#71717a", fontSize: 12 } }
              : undefined
          }
        />
        <Tooltip
          labelFormatter={(_, payload) => {
            const ts = payload?.[0]?.payload?.timestamp;
            return ts ? formatTrendTimestamp(ts) : "";
          }}
          formatter={(value, name) => [typeof value === "number" ? value.toFixed(2) : value, name]}
        />
        <Legend verticalAlign="top" height={36} />

        {thresholdLines.map((line) => (
          <ReferenceLine
            key={line.label}
            y={line.value}
            stroke={line.color}
            strokeDasharray="6 4"
            label={{ value: line.label, position: "insideTopRight", fill: line.color, fontSize: 11 }}
          />
        ))}

        {series.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.unit ? `${s.name} (${s.unit})` : s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={{ r: 2 }}
            activeDot={{ r: 4 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

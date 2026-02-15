"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { DailySeriesItem } from "@/types/api";
import { useT } from "@/i18n";
import { formatDateShort } from "@/lib/format-date";

interface TooltipPayloadEntry {
  color: string;
  name: string;
  value: number;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((sum, p) => sum + Number(p.value), 0);
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="mb-2 text-sm font-semibold text-foreground">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center justify-between gap-4 text-sm">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            {entry.name}
          </span>
          <span className="font-medium">{Number(entry.value).toFixed(1)} kWh</span>
        </div>
      ))}
      <div className="mt-2 border-t pt-2 text-sm font-semibold text-foreground">
        Total: {total.toFixed(1)} kWh
      </div>
    </div>
  );
}

export function DailyConsumptionChart({ data }: { data: DailySeriesItem[] }) {
  const t = useT();
  const formatted = data.map((d) => ({
    ...d,
    date: formatDateShort(d.date),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={formatted} barCategoryGap="20%">
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
        <XAxis
          dataKey="date"
          fontSize={12}
          tick={{ fill: "#9ca3af" }}
          axisLine={{ stroke: "#d1d5db" }}
          tickLine={false}
        />
        <YAxis
          fontSize={12}
          tick={{ fill: "#9ca3af" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${Number(v)}`}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
        <Legend
          iconType="square"
          iconSize={10}
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
        />
        <Bar
          dataKey="off_peak_kwh"
          name={t.common.offPeak}
          stackId="a"
          fill="#22c55e"
        />
        <Bar
          dataKey="partial_peak_kwh"
          name={t.common.partialPeak}
          stackId="a"
          fill="#f59e0b"
        />
        <Bar
          dataKey="peak_kwh"
          name={t.common.peak}
          stackId="a"
          fill="#ef4444"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

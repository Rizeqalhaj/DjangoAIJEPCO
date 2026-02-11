"use client";

import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SpikeEvent } from "@/types/api";
import { useT } from "@/i18n";

interface ChartEntry {
  time: string;
  power_kw: number;
  baseline_kw: number;
  factor: number;
  extra: number;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; color: string; name: string; payload?: ChartEntry }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const entry = payload[0]?.payload;
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md min-w-[160px]">
      <p className="mb-1.5 text-sm font-semibold text-foreground">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center justify-between gap-4 text-sm">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: p.color }}
            />
            {p.name}
          </span>
          <span className="font-medium">{Number(p.value).toFixed(2)} kW</span>
        </div>
      ))}
      {entry && (
        <div className="mt-2 border-t pt-2 text-xs text-muted-foreground">
          Spike factor: <span className="font-semibold text-red-500">{entry.factor.toFixed(1)}x</span>
        </div>
      )}
    </div>
  );
}

export function SpikeTimeline({ spikes }: { spikes: SpikeEvent[] }) {
  const t = useT();

  const data: ChartEntry[] = spikes.map((s) => ({
    time: new Date(s.timestamp).toLocaleDateString("en", {
      month: "short",
      day: "numeric",
      hour: "numeric",
    }),
    power_kw: s.power_kw,
    baseline_kw: s.baseline_kw,
    factor: s.spike_factor,
    extra: s.estimated_extra_cost_fils,
  }));

  const avgBaseline =
    data.length > 0
      ? data.reduce((sum, d) => sum + d.baseline_kw, 0) / data.length
      : 0;

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} barGap={-20}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
        <XAxis
          dataKey="time"
          fontSize={11}
          tick={{ fill: "#9ca3af" }}
          axisLine={{ stroke: "#d1d5db" }}
          tickLine={false}
          angle={-20}
          textAnchor="end"
          height={60}
        />
        <YAxis
          fontSize={12}
          tick={{ fill: "#9ca3af" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${Number(v)} kW`}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
        <Legend iconType="square" iconSize={10} wrapperStyle={{ fontSize: 12 }} />
        {avgBaseline > 0 && (
          <ReferenceLine
            y={avgBaseline}
            stroke="#94a3b8"
            strokeDasharray="6 3"
            label={{
              value: `Avg ${avgBaseline.toFixed(1)} kW`,
              position: "insideTopRight",
              fill: "#94a3b8",
              fontSize: 11,
            }}
          />
        )}
        <Bar
          dataKey="baseline_kw"
          name={t.spikes.baseline}
          fill="#cbd5e1"
          radius={[3, 3, 0, 0]}
          barSize={28}
        />
        <Bar
          dataKey="power_kw"
          name={t.spikes.power}
          fill="#ef4444"
          fillOpacity={0.85}
          radius={[3, 3, 0, 0]}
          barSize={16}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

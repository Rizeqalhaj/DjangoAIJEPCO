"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import type { ConsumptionSummary } from "@/types/api";
import { useT } from "@/i18n";

const COLORS = ["#ef4444", "#f59e0b", "#22c55e"];

function renderLabel(props: PieLabelRenderProps) {
  const cx = Number(props.cx ?? 0);
  const cy = Number(props.cy ?? 0);
  const midAngle = Number(props.midAngle ?? 0);
  const innerRadius = Number(props.innerRadius ?? 0);
  const outerRadius = Number(props.outerRadius ?? 0);
  const percent = Number(props.percent ?? 0);
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={13}
      fontWeight={600}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: { fill: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <div className="flex items-center gap-2 text-sm">
        <span
          className="inline-block h-3 w-3 rounded-sm"
          style={{ backgroundColor: entry.payload.fill }}
        />
        <span className="font-medium">{entry.name}</span>
      </div>
      <p className="mt-1 text-lg font-bold">{Number(entry.value).toFixed(1)}%</p>
    </div>
  );
}

export function TouBreakdownPie({ data }: { data: ConsumptionSummary }) {
  const t = useT();
  const pieData = [
    { name: t.common.peak, value: data.peak_share_percent, fill: COLORS[0] },
    { name: t.common.partialPeak, value: data.partial_peak_share_percent, fill: COLORS[1] },
    { name: t.common.offPeak, value: data.off_peak_share_percent, fill: COLORS[2] },
  ];

  return (
    <div className="h-56 sm:h-64 md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
        <Pie
          data={pieData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="45%"
          innerRadius="32%"
          outerRadius="65%"
          paddingAngle={2}
          label={renderLabel}
          labelLine={false}
          strokeWidth={2}
          stroke="var(--background, #fff)"
        >
          {pieData.map((entry, idx) => (
            <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
          ))}
        </Pie>
        <text
          x="50%"
          y="45%"
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-muted-foreground text-xs"
        >
          TOU Split
        </text>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, paddingTop: 4 }}
        />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

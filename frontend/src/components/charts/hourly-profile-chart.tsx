"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import type { HourlyProfile } from "@/types/api";
import { useT } from "@/i18n";

function getZoneColor(hour: number) {
  if (hour >= 16 && hour < 20) return "#ef4444";
  if ((hour >= 12 && hour < 16) || (hour >= 20 && hour < 23)) return "#f59e0b";
  return "#22c55e";
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const hour = label ?? "";
  const kw = Number(payload[0].value).toFixed(2);
  const hourNum = parseInt(hour);
  const color = isNaN(hourNum) ? "#3b82f6" : getZoneColor(hourNum);
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="text-sm font-semibold text-foreground">{hour}:00</p>
      <p className="text-sm">
        <span className="inline-block h-2 w-2 rounded-full me-1.5" style={{ backgroundColor: color }} />
        <span className="font-medium">{kw} kW</span>
      </p>
    </div>
  );
}

export function HourlyProfileChart({ data }: { data: HourlyProfile }) {
  const t = useT();
  const hourly = data.hourly_avg_kw.map((kw, hour) => ({
    hour: hour,
    kw: Math.round(kw * 100) / 100,
    label: `${hour}`,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={hourly}>
        <defs>
          <linearGradient id="kwGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <ReferenceArea x1={0} x2={12} fill="#22c55e" fillOpacity={0.06} />
        <ReferenceArea x1={12} x2={16} fill="#f59e0b" fillOpacity={0.06} />
        <ReferenceArea x1={16} x2={20} fill="#ef4444" fillOpacity={0.08} />
        <ReferenceArea x1={20} x2={23} fill="#f59e0b" fillOpacity={0.06} />
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
        <XAxis
          dataKey="hour"
          fontSize={11}
          tick={{ fill: "#9ca3af" }}
          axisLine={{ stroke: "#d1d5db" }}
          tickLine={false}
          tickFormatter={(v) => `${Number(v)}:00`}
        />
        <YAxis
          fontSize={12}
          tick={{ fill: "#9ca3af" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${Number(v)} kW`}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          x={data.peak_hour}
          stroke="#ef4444"
          strokeDasharray="4 4"
          label={{
            value: `${t.common.peak} ${data.peak_avg_kw.toFixed(1)} kW`,
            position: "top",
            fill: "#ef4444",
            fontSize: 11,
          }}
        />
        <ReferenceLine
          x={data.lowest_hour}
          stroke="#22c55e"
          strokeDasharray="4 4"
          label={{
            value: `${data.lowest_avg_kw.toFixed(1)} kW`,
            position: "top",
            fill: "#22c55e",
            fontSize: 11,
          }}
        />
        <Area
          type="monotone"
          dataKey="kw"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="url(#kwGradient)"
          name="kW"
          dot={false}
          activeDot={{ r: 4, fill: "#3b82f6", stroke: "#fff", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

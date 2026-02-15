"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ConsumptionSummary } from "@/types/api";
import { formatDateShort } from "@/lib/format-date";
import { useT } from "@/i18n";

function StatSkeleton() {
  return (
    <Card>
      <CardContent className="pt-6">
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-7 w-32 mb-1" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}

function StatCard({
  borderColor,
  icon,
  label,
  value,
  detail,
  detailColor,
}: {
  borderColor: string;
  icon: string;
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  detailColor?: string;
}) {
  return (
    <Card className={`border-s-4 ${borderColor}`}>
      <CardContent className="pt-6">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-lg">
            {icon}
          </div>
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold leading-tight">{value}</p>
            {detail && (
              <p className={`mt-0.5 text-xs ${detailColor ?? "text-muted-foreground"}`}>
                {detail}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function StatsCards({ summary }: { summary?: ConsumptionSummary }) {
  const t = useT();

  if (!summary) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatSkeleton />
        <StatSkeleton />
        <StatSkeleton />
        <StatSkeleton />
      </div>
    );
  }

  const trendIcon =
    summary.trend === "increasing"
      ? "↑"
      : summary.trend === "decreasing"
        ? "↓"
        : "→";

  const trendColor =
    summary.trend === "increasing"
      ? "text-red-500"
      : summary.trend === "decreasing"
        ? "text-green-500"
        : "text-gray-500";

  const trendLabel =
    summary.trend === "increasing"
      ? t.common.increasing
      : summary.trend === "decreasing"
        ? t.common.decreasing
        : t.common.stable;

  const highLowDetail = summary.highest_day
    ? `${t.dashboard.high}: ${summary.highest_day.kwh.toFixed(0)} ${t.common.kwh} (${formatDateShort(summary.highest_day.date)})`
    : undefined;

  const lowDetail = summary.lowest_day
    ? `${t.dashboard.low}: ${summary.lowest_day.kwh.toFixed(0)} ${t.common.kwh} (${formatDateShort(summary.lowest_day.date)})`
    : undefined;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        borderColor="border-s-blue-500"
        icon="⚡"
        label={t.dashboard.totalKwh}
        value={`${summary.total_kwh.toFixed(1)} ${t.common.kwh}`}
        detail={highLowDetail ?? t.dashboard.last30Days}
      />
      <StatCard
        borderColor="border-s-green-500"
        icon="📊"
        label={t.dashboard.avgDailyKwh}
        value={`${summary.avg_daily_kwh.toFixed(1)} ${t.common.kwh}/${t.common.day}`}
        detail={lowDetail}
      />
      <StatCard
        borderColor="border-s-amber-500"
        icon="📈"
        label={t.dashboard.trend}
        value={
          <span className={trendColor}>
            {trendIcon} {Math.abs(summary.trend_percent_per_week).toFixed(1)}%
          </span>
        }
        detail={trendLabel}
        detailColor={trendColor}
      />
      <StatCard
        borderColor="border-s-purple-500"
        icon="🔋"
        label={t.dashboard.peakShare}
        value={`${summary.peak_share_percent.toFixed(1)}%`}
        detail={`${t.common.offPeak}: ${summary.off_peak_share_percent.toFixed(1)}%`}
      />
    </div>
  );
}

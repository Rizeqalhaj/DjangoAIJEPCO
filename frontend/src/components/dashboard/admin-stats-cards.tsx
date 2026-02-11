"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AdminStats } from "@/types/api";
import { useT } from "@/i18n";

function AdminStatSkeleton() {
  return (
    <Card>
      <CardContent className="pt-6">
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-7 w-20 mb-1" />
        <Skeleton className="h-3 w-16" />
      </CardContent>
    </Card>
  );
}

function AdminStatCard({
  borderColor,
  icon,
  label,
  value,
  detail,
}: {
  borderColor: string;
  icon: string;
  label: string;
  value: React.ReactNode;
  detail?: string;
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
              <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function AdminStatsCards({ stats }: { stats?: AdminStats }) {
  const t = useT();

  if (!stats) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <AdminStatSkeleton />
        <AdminStatSkeleton />
        <AdminStatSkeleton />
        <AdminStatSkeleton />
      </div>
    );
  }

  const verifiedPct =
    stats.total_subscribers > 0
      ? Math.round((stats.verified_subscribers / stats.total_subscribers) * 100)
      : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <AdminStatCard
        borderColor="border-s-blue-500"
        icon="👥"
        label={t.dashboard.subscribers}
        value={stats.total_subscribers}
        detail={`${stats.verified_subscribers} ${t.admin.verified} (${verifiedPct}%)`}
      />
      <AdminStatCard
        borderColor="border-s-green-500"
        icon="📋"
        label={t.dashboard.activePlans}
        value={stats.active_plans}
        detail={`${stats.total_plans} total`}
      />
      <AdminStatCard
        borderColor="border-s-amber-500"
        icon="📊"
        label={t.dashboard.readings30d}
        value={stats.total_readings_30d.toLocaleString()}
      />
      <AdminStatCard
        borderColor="border-s-purple-500"
        icon="✅"
        label={t.admin.verified}
        value={`${verifiedPct}%`}
        detail={`${stats.verified_subscribers} / ${stats.total_subscribers}`}
      />
    </div>
  );
}

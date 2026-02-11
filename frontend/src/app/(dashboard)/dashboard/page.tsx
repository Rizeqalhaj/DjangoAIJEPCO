"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth-store";
import { useConsumptionSummary, useDailySeries, useSpikes } from "@/hooks/use-meter";
import { useAdminStats, useAdminSubscribers } from "@/hooks/use-admin";
import { useT } from "@/i18n";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { AdminStatsCards } from "@/components/dashboard/admin-stats-cards";
import { SubscriberTable } from "@/components/dashboard/subscriber-table";
import { DailyConsumptionChart } from "@/components/charts/daily-consumption-chart";
import { TouBreakdownPie } from "@/components/charts/tou-breakdown-pie";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const RANGE_OPTIONS = [7, 14, 30, 60, 90] as const;

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="lg:col-span-2 h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
    </div>
  );
}

function AdminView() {
  const t = useT();
  const { data: stats, isLoading: sl } = useAdminStats();
  const { data: subs, isLoading: bl } = useAdminSubscribers();
  if (sl || bl) return <PageSkeleton />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t.admin.title}</h1>
      <AdminStatsCards stats={stats} />
      <Card>
        <CardHeader><CardTitle>{t.admin.subscriberList}</CardTitle></CardHeader>
        <CardContent>
          {subs ? <SubscriberTable subscribers={subs} /> : <p className="text-muted-foreground">{t.common.noData}</p>}
        </CardContent>
      </Card>
    </div>
  );
}

function SubscriberView() {
  const [days, setDays] = useState(30);
  const t = useT();
  const { user } = useAuthStore();
  const sub = user?.subscriber?.subscription_number ?? "";
  const { data: summary, isLoading: sl } = useConsumptionSummary(sub, days);
  const { data: daily, isLoading: dl } = useDailySeries(sub, days);
  const { data: spikesData } = useSpikes(sub, days);

  if (sl || dl) return <PageSkeleton />;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t.common.welcome}, {user?.subscriber?.name ?? user?.username}</h1>
        <div className="flex gap-2">
          {RANGE_OPTIONS.map((d) => (
            <Button
              key={d}
              variant={days === d ? "default" : "outline"}
              size="sm"
              onClick={() => setDays(d)}
            >
              {d} {t.common.days}
            </Button>
          ))}
        </div>
      </div>
      <StatsCards summary={summary} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>{t.nav.consumption} — {days} {t.common.days}</CardTitle></CardHeader>
          <CardContent>{daily ? <DailyConsumptionChart data={daily} /> : <Skeleton className="h-56" />}</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>{t.dashboard.touBreakdown}</CardTitle></CardHeader>
          <CardContent>{summary ? <TouBreakdownPie data={summary} /> : <Skeleton className="h-56" />}</CardContent>
        </Card>
      </div>
      {spikesData && spikesData.count > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              {t.dashboard.recentSpikes} <Badge variant="destructive">{spikesData.count}</Badge>
            </CardTitle>
            <Link href="/spikes"><Button variant="ghost" size="sm">{t.dashboard.viewAll}</Button></Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {spikesData.spikes.slice(0, 3).map((s, i) => (
                <div key={i} className="flex justify-between text-sm border-b pb-2 last:border-0">
                  <span className="text-muted-foreground">{new Date(s.timestamp).toLocaleString()}</span>
                  <span className="font-medium text-[#ef4444]">{s.power_kw} {t.common.kw} ({s.spike_factor.toFixed(1)}x)</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { isAdmin } = useAuthStore();
  return isAdmin ? <AdminView /> : <SubscriberView />;
}

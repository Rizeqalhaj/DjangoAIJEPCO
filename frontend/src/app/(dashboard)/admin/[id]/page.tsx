"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useAdminSubscriberDetail } from "@/hooks/use-admin";
import { useConsumptionSummary, useDailySeries, useSpikes } from "@/hooks/use-meter";
import { useT } from "@/i18n";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { DailyConsumptionChart } from "@/components/charts/daily-consumption-chart";
import { TouBreakdownPie } from "@/components/charts/tou-breakdown-pie";
import { SpikeTimeline } from "@/components/charts/spike-timeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const RANGE_OPTIONS = [7, 14, 30, 60, 90] as const;

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-20 rounded-xl" />
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

export default function AdminSubscriberPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [days, setDays] = useState(30);
  const t = useT();
  const { data: d, isLoading } = useAdminSubscriberDetail(Number(id));
  const subNum = d?.subscription_number ?? "";
  const { data: summary } = useConsumptionSummary(subNum, days);
  const { data: daily } = useDailySeries(subNum, days);
  const { data: spikes } = useSpikes(subNum, days);

  if (isLoading || !d) return <DetailSkeleton />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Link href="/admin"><Button variant="ghost" size="sm">{t.common.back}</Button></Link>
          <h1 className="text-2xl font-bold">{d.name}</h1>
          <Badge>{d.tariff_category}</Badge>
          {d.has_ev && <Badge variant="secondary">EV</Badge>}
          {d.has_solar && <Badge variant="secondary">Solar</Badge>}
        </div>
        <div className="flex gap-2">
          {RANGE_OPTIONS.map((r) => (
            <Button
              key={r}
              variant={days === r ? "default" : "outline"}
              size="sm"
              onClick={() => setDays(r)}
            >
              {r} {t.common.days}
            </Button>
          ))}
        </div>
      </div>
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">{t.admin.subscription}</p>
              <p className="font-mono font-medium">{d.subscription_number}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t.admin.phone}</p>
              <p className="font-mono font-medium">{d.phone_number}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t.admin.area}</p>
              <p className="font-medium">{d.area}, {d.governorate}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t.admin.household}</p>
              <p className="font-medium">{d.household_size ?? "N/A"}</p>
            </div>
          </div>
        </CardContent>
      </Card>
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
      {spikes && spikes.count > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">{t.nav.spikes} <Badge variant="destructive">{spikes.count}</Badge></CardTitle>
          </CardHeader>
          <CardContent><SpikeTimeline spikes={spikes.spikes} /></CardContent>
        </Card>
      )}
    </div>
  );
}

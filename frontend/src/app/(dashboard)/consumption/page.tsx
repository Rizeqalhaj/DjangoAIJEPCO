"use client";

import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useDailySeries, useHourlyProfile } from "@/hooks/use-meter";
import { useT } from "@/i18n";
import { DailyConsumptionChart } from "@/components/charts/daily-consumption-chart";
import { HourlyProfileChart } from "@/components/charts/hourly-profile-chart";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const RANGE_OPTIONS = [7, 14, 30, 60, 90] as const;

export default function ConsumptionPage() {
  const [days, setDays] = useState(14);
  const t = useT();
  const sub = useAuthStore((s) => s.user?.subscriber?.subscription_number ?? "");

  const { data: daily, isLoading: dailyLoading } = useDailySeries(sub, days);
  const { data: hourly, isLoading: hourlyLoading } = useHourlyProfile(sub, days);

  const totalKwh = daily?.reduce((sum, d) => sum + d.total_kwh, 0) ?? 0;
  const avgDaily = daily && daily.length > 0 ? totalKwh / daily.length : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t.nav.consumption}</h1>
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

      <Card>
        <CardHeader>
          <CardTitle>
            {t.nav.consumption} — {days} {t.common.days}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {dailyLoading ? (
            <Skeleton className="h-64" />
          ) : daily ? (
            <DailyConsumptionChart data={daily} />
          ) : (
            <p className="text-muted-foreground">{t.common.noData}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {t.common.hour}ly {t.nav.consumption}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {hourlyLoading ? (
            <Skeleton className="h-64" />
          ) : hourly ? (
            <HourlyProfileChart data={hourly} />
          ) : (
            <p className="text-muted-foreground">{t.common.noData}</p>
          )}
        </CardContent>
      </Card>

      {daily && daily.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                {t.common.total} ({days} {t.common.days})
              </p>
              <p className="text-2xl font-bold">
                {totalKwh.toFixed(1)} {t.common.kwh}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                {t.common.avgDaily}
              </p>
              <p className="text-2xl font-bold">
                {avgDaily.toFixed(1)} {t.common.kwh}/{t.common.day}
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

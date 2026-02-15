"use client";

import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useDailySeries, useHourlyProfile, type DateRange } from "@/hooks/use-meter";
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
  const [customRange, setCustomRange] = useState<DateRange | undefined>();
  const [showCustom, setShowCustom] = useState(false);
  const [startInput, setStartInput] = useState("");
  const [endInput, setEndInput] = useState("");
  const t = useT();
  const sub = useAuthStore((s) => s.user?.subscriber?.subscription_number ?? "");

  const { data: daily, isLoading: dailyLoading } = useDailySeries(sub, days, customRange);
  const { data: hourly, isLoading: hourlyLoading } = useHourlyProfile(sub, days);

  const totalKwh = daily?.reduce((sum, d) => sum + d.total_kwh, 0) ?? 0;
  const avgDaily = daily && daily.length > 0 ? totalKwh / daily.length : 0;

  const selectPreset = (d: number) => {
    setDays(d);
    setCustomRange(undefined);
    setShowCustom(false);
  };

  const applyCustomRange = () => {
    if (startInput && endInput) {
      setCustomRange({ startDate: startInput, endDate: endInput });
      setDays(0);
    }
  };

  const periodLabel = customRange
    ? `${customRange.startDate} → ${customRange.endDate}`
    : `${days} ${t.common.days}`;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t.nav.consumption}</h1>
        <div className="flex flex-wrap items-center gap-2">
          {RANGE_OPTIONS.map((d) => (
            <Button
              key={d}
              variant={!customRange && days === d ? "default" : "outline"}
              size="sm"
              onClick={() => selectPreset(d)}
            >
              {d} {t.common.days}
            </Button>
          ))}
          <Button
            variant={showCustom || customRange ? "default" : "outline"}
            size="sm"
            onClick={() => setShowCustom(!showCustom)}
          >
            {t.dashboard.customRange}
          </Button>
        </div>
      </div>

      {showCustom && (
        <div className="flex flex-wrap items-end gap-3 p-3 rounded-lg border bg-muted/30">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">{t.dashboard.from}</label>
            <input
              type="date"
              value={startInput}
              onChange={(e) => setStartInput(e.target.value)}
              className="rounded-md border px-3 py-1.5 text-sm bg-background"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">{t.dashboard.to}</label>
            <input
              type="date"
              value={endInput}
              onChange={(e) => setEndInput(e.target.value)}
              className="rounded-md border px-3 py-1.5 text-sm bg-background"
            />
          </div>
          <Button
            size="sm"
            onClick={applyCustomRange}
            disabled={!startInput || !endInput || startInput > endInput}
          >
            {t.dashboard.apply}
          </Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>
            {t.nav.consumption} — {periodLabel}
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
                {t.common.total} ({periodLabel})
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

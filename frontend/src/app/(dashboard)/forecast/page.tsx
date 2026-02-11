"use client";

import { useAuthStore } from "@/stores/auth-store";
import { useBillForecast } from "@/hooks/use-meter";
import { useT } from "@/i18n";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ForecastPage() {
  const t = useT();
  const sub = useAuthStore((s) => s.user?.subscriber?.subscription_number ?? "");
  const { data: fc, isLoading } = useBillForecast(sub);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
        <Skeleton className="h-24 rounded-xl" />
      </div>
    );
  }

  const total = fc ? fc.days_elapsed + fc.days_remaining : 30;
  const pct = fc ? Math.round((fc.days_elapsed / total) * 100) : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t.forecast.title}</h1>
      {fc && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-s-4 border-s-blue-500">
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">{t.forecast.projected}</p>
                <p className="text-3xl font-bold">{fc.projected_monthly_kwh.toFixed(0)} {t.common.kwh}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t.forecast.soFar}: {fc.actual_kwh_so_far.toFixed(0)} {t.common.kwh}
                </p>
              </CardContent>
            </Card>
            <Card className="border-s-4 border-s-green-500">
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">{t.forecast.lastMonth}</p>
                <p className="text-2xl font-bold">{fc.last_month_kwh.toFixed(0)} {t.common.kwh}</p>
              </CardContent>
            </Card>
            <Card className="border-s-4 border-s-amber-500">
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">{t.forecast.change}</p>
                <p className={`text-2xl font-bold ${fc.change_vs_last_month_percent > 0 ? "text-[#ef4444]" : "text-[#22c55e]"}`}>
                  {fc.change_vs_last_month_percent > 0 ? "+" : ""}{fc.change_vs_last_month_percent.toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">{fc.days_remaining} {t.forecast.daysLeft}</p>
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader><CardTitle>{t.forecast.billingProgress}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{fc.days_elapsed} {t.forecast.daysElapsed}</span>
                <span>{fc.days_remaining} {t.forecast.daysLeft}</span>
              </div>
              <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
              </div>
              <p className="text-xs text-muted-foreground text-center">
                {pct}% — {fc.actual_kwh_so_far.toFixed(0)} {t.common.kwh} / ~{fc.projected_monthly_kwh.toFixed(0)} {t.common.kwh}
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

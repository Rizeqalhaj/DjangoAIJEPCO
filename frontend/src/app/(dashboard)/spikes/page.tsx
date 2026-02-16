"use client";

import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useSpikes, type DateRange } from "@/hooks/use-meter";
import { useT } from "@/i18n";
import { formatDateTime } from "@/lib/format-date";
import { SpikeTimeline } from "@/components/charts/spike-timeline";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function severityClass(factor: number): string {
  if (factor >= 3) return "bg-[#ef4444]/10 border-[#ef4444]/30";
  if (factor >= 2) return "bg-[#f59e0b]/10 border-[#f59e0b]/30";
  return "";
}

const RANGE_OPTIONS = [7, 14, 30, 60, 90] as const;

export default function SpikesPage() {
  const [days, setDays] = useState(7);
  const [customRange, setCustomRange] = useState<DateRange | undefined>();
  const [showCustom, setShowCustom] = useState(false);
  const [startInput, setStartInput] = useState("");
  const [endInput, setEndInput] = useState("");
  const t = useT();
  const sub = useAuthStore(
    (s) => s.user?.subscriber?.subscription_number ?? ""
  );
  const { data, isLoading } = useSpikes(sub, days, customRange);

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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{t.spikes.title}</h1>
          {data && (
            <Badge variant={data.count > 0 ? "destructive" : "secondary"}>
              {data.count} {t.spikes.detected}
            </Badge>
          )}
        </div>
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

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      ) : data && data.count > 0 ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{t.spikes.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <SpikeTimeline spikes={data.spikes} />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-start p-2">{t.spikes.time}</th>
                      <th className="text-start p-2">{t.spikes.power}</th>
                      <th className="text-start p-2">{t.spikes.baseline}</th>
                      <th className="text-start p-2">{t.spikes.factor}</th>
                      <th className="text-start p-2">{t.spikes.duration}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.spikes.map((s, i) => (
                      <tr
                        key={i}
                        className={`border ${severityClass(s.spike_factor)}`}
                      >
                        <td className="p-2">
                          {formatDateTime(s.timestamp)}
                        </td>
                        <td className="p-2 font-medium text-[#ef4444]">
                          {s.power_kw} {t.common.kw}
                        </td>
                        <td className="p-2">
                          {s.baseline_kw} {t.common.kw}
                        </td>
                        <td className="p-2 font-semibold">
                          {s.spike_factor.toFixed(1)}x
                        </td>
                        <td className="p-2">
                          {s.duration_minutes} {t.spikes.minutes}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="h-16 w-16 rounded-full bg-[#22c55e]/10 flex items-center justify-center">
              <svg
                className="h-8 w-8 text-[#22c55e]"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <p className="text-lg font-medium">{t.spikes.noSpikes}</p>
            <p className="text-sm text-muted-foreground">
              {t.spikes.noSpikesDesc}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

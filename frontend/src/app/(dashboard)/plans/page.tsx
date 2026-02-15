"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth-store";
import { usePlans } from "@/hooks/use-plans";
import { useT } from "@/i18n";
import { formatDate } from "@/lib/format-date";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const BADGE_STYLE: Record<string, string> = {
  active: "bg-blue-500 hover:bg-blue-600",
  monitoring: "bg-[#f59e0b] hover:bg-[#f59e0b]/80",
  verified: "bg-[#22c55e] hover:bg-[#22c55e]/80",
  completed: "bg-gray-500 hover:bg-gray-600",
  abandoned: "bg-[#ef4444] hover:bg-[#ef4444]/80",
};

export default function PlansPage() {
  const t = useT();
  const sub = useAuthStore((s) => s.user?.subscriber?.subscription_number ?? "");
  const { data: plans, isLoading } = usePlans(sub);
  const queryClient = useQueryClient();
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  async function handleCancel(planId: number) {
    if (!confirm(t.plans.confirmCancel)) return;
    setCancellingId(planId);
    try {
      await api.delete(`/plans/detail/${planId}/`);
      queryClient.invalidateQueries({ queryKey: ["plans", sub] });
    } finally {
      setCancellingId(null);
    }
  }

  const label: Record<string, string> = {
    active: t.plans.active, monitoring: t.plans.monitoring,
    verified: t.plans.verified, completed: t.plans.completed, abandoned: t.plans.abandoned,
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
      </div>
    );
  }

  if (!plans || plans.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">{t.plans.title}</h1>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
              <svg className="h-8 w-8 text-primary" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <p className="text-lg font-medium">{t.plans.noPlans}</p>
            <p className="text-sm text-muted-foreground">{t.plans.noPlansDesc}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t.plans.title}</h1>
      {plans.map((p) => {
        const vr = p.verification_result as Record<string, number> | null;
        const cur = vr?.current_daily_kwh ?? null;
        const saved = cur !== null && p.baseline_daily_kwh > 0
          ? ((p.baseline_daily_kwh - cur) / p.baseline_daily_kwh * 100).toFixed(1) : null;
        return (
          <Card key={p.id}>
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <CardTitle className="text-lg">{p.plan_summary}</CardTitle>
                <Badge className={BADGE_STYLE[p.status] ?? ""}>{label[p.status] ?? p.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div><p className="text-sm text-muted-foreground">{t.plans.pattern}</p><p className="text-sm">{p.detected_pattern}</p></div>
              {p.user_hypothesis && <div><p className="text-sm text-muted-foreground">{t.plans.hypothesis}</p><p className="text-sm">{p.user_hypothesis}</p></div>}
              <div className="flex flex-wrap gap-6 text-sm">
                <div><span className="text-muted-foreground">{t.plans.baseline}: </span><span className="font-medium">{p.baseline_daily_kwh} {t.common.kwh}/{t.common.day}</span></div>
                {cur !== null && (
                  <div>
                    <span className="text-muted-foreground">{t.plans.current}: </span>
                    <span className="font-medium">{cur} {t.common.kwh}/{t.common.day}</span>
                    {saved && <span className={`ms-2 font-semibold ${Number(saved) > 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>{Number(saved) > 0 ? "-" : "+"}{Math.abs(Number(saved))}%</span>}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground border-t pt-3">
                <span>{t.plans.created}: {formatDate(p.created_at)}</span>
                {p.verify_after_date && <span>{t.plans.verifyBy}: {formatDate(p.verify_after_date)}</span>}
                {(p.status === "active" || p.status === "monitoring") && (
                  <Button
                    variant="destructive"
                    size="sm"
                    className="ms-auto h-7 text-xs"
                    disabled={cancellingId === p.id}
                    onClick={() => handleCancel(p.id)}
                  >
                    {cancellingId === p.id ? "..." : t.plans.cancel}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

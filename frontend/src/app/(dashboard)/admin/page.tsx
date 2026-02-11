"use client";

import { useState, useMemo } from "react";
import { useAdminStats, useAdminSubscribers } from "@/hooks/use-admin";
import { useT } from "@/i18n";
import { AdminStatsCards } from "@/components/dashboard/admin-stats-cards";
import { SubscriberTable } from "@/components/dashboard/subscriber-table";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export default function AdminPage() {
  const t = useT();
  const { data: stats, isLoading: statsLoading } = useAdminStats();
  const { data: subscribers, isLoading: subsLoading } =
    useAdminSubscribers();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!subscribers) return [];
    if (!search.trim()) return subscribers;
    const q = search.toLowerCase();
    return subscribers.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.area.toLowerCase().includes(q) ||
        s.phone_number.includes(q) ||
        s.subscription_number.includes(q)
    );
  }, [subscribers, search]);

  if (statsLoading || subsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t.admin.title}</h1>
      <AdminStatsCards stats={stats} />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <CardTitle>{t.admin.subscriberList}</CardTitle>
          <div className="w-full max-w-xs">
            <Input
              placeholder={t.common.search}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="text-sm"
            />
          </div>
        </CardHeader>
        <CardContent>
          {filtered.length > 0 ? (
            <SubscriberTable subscribers={filtered} />
          ) : (
            <p className="text-center text-muted-foreground py-8">
              {t.common.noData}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

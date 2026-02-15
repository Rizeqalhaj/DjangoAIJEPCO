"use client";

import Link from "next/link";
import type { AdminSubscriber } from "@/types/api";
import { useT } from "@/i18n";
import { formatDate } from "@/lib/format-date";
import { Badge } from "@/components/ui/badge";

function StatusBadge({ verified }: { verified: boolean }) {
  return verified ? (
    <Badge className="bg-green-100 text-green-700 border-green-200 hover:bg-green-100">
      Verified
    </Badge>
  ) : (
    <Badge variant="secondary" className="bg-gray-100 text-gray-500 border-gray-200">
      Unverified
    </Badge>
  );
}

function FeatureBadge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${color}`}
    >
      {label}
    </span>
  );
}

export function SubscriberTable({
  subscribers,
}: {
  subscribers: AdminSubscriber[];
}) {
  const t = useT();

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/40">
            <th className="text-start p-3 font-medium text-muted-foreground">
              {t.admin.name}
            </th>
            <th className="text-start p-3 font-medium text-muted-foreground">
              {t.admin.subscription}
            </th>
            <th className="text-start p-3 font-medium text-muted-foreground">
              {t.admin.area}
            </th>
            <th className="text-start p-3 font-medium text-muted-foreground">
              {t.admin.phone}
            </th>
            <th className="text-start p-3 font-medium text-muted-foreground">
              {t.admin.lastReading}
            </th>
            <th className="text-start p-3 font-medium text-muted-foreground">
              {t.admin.verified}
            </th>
          </tr>
        </thead>
        <tbody>
          {subscribers.map((sub, idx) => (
            <tr
              key={sub.id}
              className={`
                border-b transition-all duration-150 hover:bg-primary/5 hover:scale-[1.002]
                ${idx % 2 === 0 ? "bg-background" : "bg-muted/20"}
              `}
            >
              <td className="p-3">
                <div className="flex items-center gap-2">
                  <Link
                    href={`/admin/${sub.id}`}
                    className="text-primary hover:underline font-medium"
                  >
                    {sub.name}
                  </Link>
                  {sub.has_ev && (
                    <FeatureBadge label="EV" color="bg-blue-100 text-blue-700" />
                  )}
                  {sub.has_solar && (
                    <FeatureBadge label="Solar" color="bg-amber-100 text-amber-700" />
                  )}
                </div>
              </td>
              <td className="p-3 font-mono text-xs text-muted-foreground">
                {sub.subscription_number}
              </td>
              <td className="p-3">{sub.area}</td>
              <td className="p-3 font-mono text-xs text-muted-foreground">
                {sub.phone_number}
              </td>
              <td className="p-3 text-xs text-muted-foreground">
                {sub.last_reading_at
                  ? formatDate(sub.last_reading_at)
                  : "---"}
              </td>
              <td className="p-3">
                <StatusBadge verified={sub.is_verified} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

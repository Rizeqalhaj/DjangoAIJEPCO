"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { useT } from "@/i18n";
import { useCurrentTou } from "@/hooks/use-tariff";
import { useLanguageStore } from "@/stores/language-store";
import { LanguageToggle } from "./language-toggle";
import { Button } from "@/components/ui/button";

const TOU_COLORS: Record<string, string> = {
  peak: "#ef4444",
  partial_peak: "#f59e0b",
  off_peak: "#22c55e",
};

function formatMinutesLeft(minutes: number, locale: string): string {
  if (minutes >= 60) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return locale === "ar"
      ? `${h} \u0633${m > 0 ? ` ${m} \u062F` : ""}`
      : `${h}h${m > 0 ? ` ${m}m` : ""}`;
  }
  return locale === "ar" ? `${minutes} \u062F` : `${minutes}m`;
}

function TouIndicator() {
  const { data: tou } = useCurrentTou();
  const locale = useLanguageStore((s) => s.locale);
  const t = useT();

  if (!tou) return null;

  const color = TOU_COLORS[tou.period] ?? "#6b7280";
  const label = locale === "ar" ? tou.period_name_ar : tou.period_name_en;
  const timeLeft = formatMinutesLeft(tou.minutes_remaining, locale);

  return (
    <div className="flex items-center gap-2 rounded-full bg-muted px-3 py-1.5">
      <span
        className="inline-block h-2.5 w-2.5 rounded-full animate-pulse"
        style={{ backgroundColor: color }}
      />
      <span className="text-sm font-medium">{label}</span>
      <span className="text-xs text-muted-foreground">
        {"\u2014"} {timeLeft} {t.common.days === "days" ? "left" : "\u0645\u062A\u0628\u0642\u064A"}
      </span>
    </div>
  );
}

function UserAvatar({ name }: { name: string }) {
  const initial = name.charAt(0).toUpperCase();

  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
      {initial}
    </div>
  );
}

export function Topbar() {
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clear);
  const router = useRouter();
  const t = useT();

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  const displayName = user?.subscriber?.name || user?.username || "";

  return (
    <header className="h-14 bg-white flex items-center justify-between px-4 shadow-sm">
      <div className="flex items-center gap-3">
        <TouIndicator />
      </div>

      <div className="flex items-center gap-3">
        <LanguageToggle />

        <div className="flex items-center gap-2">
          <UserAvatar name={displayName} />
          <span className="text-sm font-medium text-foreground">
            {displayName}
          </span>
        </div>

        <Button variant="ghost" size="sm" onClick={handleLogout}>
          {t.nav.logout}
        </Button>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { useT } from "@/i18n";
import { cn } from "@/lib/utils";

const NAV_ICONS: Record<string, string> = {
  dashboard: "\uD83D\uDCCA",
  consumption: "\uD83D\uDD0B",
  spikes: "\uD83D\uDCC8",
  forecast: "\uD83D\uDCB0",
  plans: "\uD83D\uDCCB",
  chat: "\uD83E\uDD16",
  admin: "\u2699\uFE0F",
};

const subscriberLinks = [
  { href: "/dashboard", key: "dashboard" as const },
  { href: "/consumption", key: "consumption" as const },
  { href: "/spikes", key: "spikes" as const },
  { href: "/forecast", key: "forecast" as const },
  { href: "/plans", key: "plans" as const },
  { href: "/chat", key: "chat" as const },
];

function NavLink({
  href,
  icon,
  label,
  active,
}: {
  href: string;
  icon: string;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 ps-3 pe-3 py-2.5 rounded-md text-sm font-medium",
        "transition-all duration-200 group",
        active
          ? "bg-primary/10 text-primary border-s-[3px] border-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground border-s-[3px] border-transparent"
      )}
    >
      <span className="text-base transition-transform duration-200 group-hover:scale-110">
        {icon}
      </span>
      {label}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const isAdmin = useAuthStore((s) => s.isAdmin);
  const t = useT();

  return (
    <aside className="w-64 border-e bg-white h-screen sticky top-0 flex flex-col">
      <div className="p-4 border-b">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{"\u26A1"}</span>
          <h1 className="text-xl font-bold tracking-tight">KahrabaAI</h1>
        </div>
      </div>

      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {subscriberLinks.map((link) => (
          <NavLink
            key={link.href}
            href={link.href}
            icon={NAV_ICONS[link.key]}
            label={t.nav[link.key]}
            active={pathname === link.href}
          />
        ))}

        {isAdmin && (
          <>
            <div className="my-2 border-t" />
            <NavLink
              href="/admin"
              icon={NAV_ICONS.admin}
              label={t.nav.admin}
              active={pathname.startsWith("/admin")}
            />
          </>
        )}
      </nav>

      <div className="border-t px-4 py-3">
        <p className="text-xs text-muted-foreground text-center">
          KahrabaAI v1.0
        </p>
      </div>
    </aside>
  );
}

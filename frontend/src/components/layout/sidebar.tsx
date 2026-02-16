"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { useLanguageStore } from "@/stores/language-store";
import { useT } from "@/i18n";
import { cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

const NAV_ICONS: Record<string, string> = {
  dashboard: "\uD83D\uDCCA",
  spikes: "\uD83D\uDCC8",
  forecast: "\uD83D\uDCB0",
  plans: "\uD83D\uDCCB",
  chat: "\uD83E\uDD16",
  admin: "\u2699\uFE0F",
};

const subscriberLinks = [
  { href: "/dashboard", key: "dashboard" as const },
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
  onClick,
}: {
  href: string;
  icon: string;
  label: string;
  active: boolean;
  onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
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

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const isAdmin = useAuthStore((s) => s.isAdmin);
  const t = useT();

  return (
    <>
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {subscriberLinks.map((link) => (
          <NavLink
            key={link.href}
            href={link.href}
            icon={NAV_ICONS[link.key]}
            label={t.nav[link.key]}
            active={pathname === link.href}
            onClick={onNavigate}
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
              onClick={onNavigate}
            />
          </>
        )}
      </nav>

      <div className="border-t px-4 py-3">
        <p className="text-xs text-muted-foreground text-center">
          KahrabaAI v1.0
        </p>
      </div>
    </>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-64 border-e bg-white h-screen sticky top-0 flex-col">
      <div className="p-4 border-b">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{"\u26A1"}</span>
          <h1 className="text-xl font-bold tracking-tight">KahrabaAI</h1>
        </div>
      </div>
      <SidebarContent />
    </aside>
  );
}

export function MobileSidebar() {
  const [open, setOpen] = useState(false);
  const dir = useLanguageStore((s) => s.dir);
  const side = dir === "rtl" ? "right" : "left";

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(true)}
        className="p-2 rounded-md hover:bg-muted transition-colors"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side={side} className="w-64 p-0" showCloseButton={false}>
          <SheetHeader className="p-4 border-b">
            <SheetTitle className="flex items-center gap-2">
              <span className="text-2xl">{"\u26A1"}</span>
              KahrabaAI
            </SheetTitle>
          </SheetHeader>
          <SidebarContent onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </div>
  );
}

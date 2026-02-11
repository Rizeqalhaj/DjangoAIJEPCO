"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { RtlProvider } from "@/components/layout/rtl-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Skeleton } from "@/components/ui/skeleton";
import api from "@/lib/api";
import type { User } from "@/types/api";

function DashboardSkeleton() {
  return (
    <div className="flex min-h-screen animate-in fade-in duration-300">
      {/* Sidebar skeleton */}
      <div className="w-64 border-e bg-white h-screen flex flex-col">
        <div className="p-4 border-b">
          <Skeleton className="h-7 w-32" />
        </div>
        <div className="p-2 space-y-2 flex-1">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full rounded-md" />
          ))}
        </div>
        <div className="border-t p-3">
          <Skeleton className="h-4 w-24 mx-auto" />
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col">
        <div className="h-14 bg-white shadow-sm flex items-center justify-between px-4">
          <Skeleton className="h-8 w-48 rounded-full" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
        <div className="flex-1 p-6 bg-gray-50 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, setUser } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("kahrabaai_access");
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!isAuthenticated) {
      api
        .get<User>("/auth/me/")
        .then((res) => {
          setUser(res.data);
          setReady(true);
        })
        .catch(() => {
          router.replace("/login");
        });
    } else {
      setReady(true);
    }
  }, [isAuthenticated, router, setUser]);

  if (!ready) return <DashboardSkeleton />;

  return (
    <RtlProvider>
      <div className="flex min-h-screen animate-in fade-in duration-300">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Topbar />
          <main className="flex-1 p-6 bg-gray-50">{children}</main>
        </div>
      </div>
    </RtlProvider>
  );
}

"use client";

import { useEffect } from "react";
import { useLanguageStore } from "@/stores/language-store";

export function RtlProvider({ children }: { children: React.ReactNode }) {
  const { dir, locale } = useLanguageStore();

  useEffect(() => {
    document.documentElement.dir = dir;
    document.documentElement.lang = locale;
  }, [dir, locale]);

  return <>{children}</>;
}

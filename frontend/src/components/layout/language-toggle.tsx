"use client";

import { useLanguageStore } from "@/stores/language-store";
import { Button } from "@/components/ui/button";

export function LanguageToggle() {
  const { locale, setLocale } = useLanguageStore();

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => setLocale(locale === "ar" ? "en" : "ar")}
      className="text-sm font-medium"
    >
      {locale === "ar" ? "EN" : "\u0639\u0631\u0628\u064A"}
    </Button>
  );
}

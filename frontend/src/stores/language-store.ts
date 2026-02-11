import { create } from "zustand";
import { persist } from "zustand/middleware";

type Locale = "ar" | "en";

interface LanguageState {
  locale: Locale;
  dir: "rtl" | "ltr";
  setLocale: (locale: Locale) => void;
}

export const useLanguageStore = create<LanguageState>()(
  persist(
    (set) => ({
      locale: "ar",
      dir: "rtl",
      setLocale: (locale) =>
        set({ locale, dir: locale === "ar" ? "rtl" : "ltr" }),
    }),
    { name: "kahrabaai-lang" }
  )
);

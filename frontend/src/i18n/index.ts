import { useLanguageStore } from "@/stores/language-store";
import { ar } from "./ar";
import { en } from "./en";

const translations = { ar, en } as const;

export function useT() {
  const { locale } = useLanguageStore();
  return translations[locale];
}

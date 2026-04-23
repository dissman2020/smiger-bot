"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import en, { type Locale } from "./en";
import zh from "./zh";

type Lang = "en" | "zh";

interface I18nContextValue {
  t: Locale;
  lang: Lang;
  toggleLang: () => void;
}

const I18nContext = createContext<I18nContextValue>({
  t: en,
  lang: "en",
  toggleLang: () => {},
});

const STORAGE_KEY = "smiger_lang";
const locales: Record<Lang, Locale> = { en, zh };

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Lang | null;
    if (stored && locales[stored]) {
      setLang(stored);
    }
  }, []);

  const toggleLang = useCallback(() => {
    setLang((prev) => {
      const next = prev === "en" ? "zh" : "en";
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  return (
    <I18nContext.Provider value={{ t: locales[lang], lang, toggleLang }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useLocale() {
  return useContext(I18nContext);
}

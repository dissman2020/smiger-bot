"use client";

import { useLocale } from "@/lib/i18n";
import { Globe } from "lucide-react";

export default function LangToggle({ className }: { className?: string }) {
  const { t, toggleLang } = useLocale();

  return (
    <button
      onClick={toggleLang}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${className ?? "bg-white/5 border-white/10 text-white/70 hover:bg-white/10"}`}
    >
      <Globe size={14} />
      {t.langSwitch}
    </button>
  );
}

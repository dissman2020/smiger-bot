"use client";

import "./globals.css";
import { I18nProvider, useLocale } from "@/lib/i18n";
import { useEffect } from "react";

function DynamicHead() {
  const { t, lang } = useLocale();

  useEffect(() => {
    document.title = t.landing.title;
    document.documentElement.lang = lang;
  }, [t, lang]);

  return null;
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>Smiger Guitar Expert</title>
        <meta name="description" content="AI-powered pre-sales assistant for Smiger guitars" />
      </head>
      <body className="bg-gray-50 min-h-screen">
        <I18nProvider>
          <DynamicHead />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}

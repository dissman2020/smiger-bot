"use client";

import { useEffect, useState } from "react";
import { BookOpen, MessageSquare, Users, FileText } from "lucide-react";
import { getDashboardStats } from "@/lib/api";
import { DashboardStats } from "@/lib/types";
import { useLocale } from "@/lib/i18n";

function StatCard({ label, value, today, todayLabel, icon: Icon }: { label: string; value: number; today?: number; todayLabel: string; icon: any }) {
  return (
    <div className="bg-dark-900 rounded-xl border border-white/5 p-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-dark-400">{label}</span>
        <div className="w-9 h-9 bg-brand-500/10 rounded-lg flex items-center justify-center">
          <Icon size={18} className="text-brand-400" />
        </div>
      </div>
      <p className="text-3xl font-bold text-white">{value.toLocaleString()}</p>
      {today !== undefined && <p className="text-xs text-dark-500 mt-1">+{today} {todayLabel}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useLocale();
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => { getDashboardStats().then(setStats).catch(console.error); }, []);

  if (!stats) return <div className="text-dark-500 text-sm">{t.dashboardPage.loading}</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">{t.dashboardPage.title}</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard label={t.dashboardPage.conversations} value={stats.total_conversations} today={stats.conversations_today} todayLabel={t.dashboardPage.today} icon={MessageSquare} />
        <StatCard label={t.dashboardPage.messages} value={stats.total_messages} todayLabel={t.dashboardPage.today} icon={FileText} />
        <StatCard label={t.dashboardPage.leadsCaptured} value={stats.total_leads} today={stats.leads_today} todayLabel={t.dashboardPage.today} icon={Users} />
        <StatCard label={t.dashboardPage.knowledgeDocs} value={stats.total_documents} todayLabel={t.dashboardPage.today} icon={BookOpen} />
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { getApiBase, getLeads } from "@/lib/api";
import { LeadItem } from "@/lib/types";
import { useLocale } from "@/lib/i18n";

export default function LeadsPage() {
  const { t } = useLocale();
  const [leads, setLeads] = useState<LeadItem[]>([]);
  useEffect(() => { getLeads().then(setLeads).catch(console.error); }, []);

  const handleExport = () => {
    const token = localStorage.getItem("admin_token");
    const base = getApiBase();
    window.open(`${base}/api/leads/export?token=${token}`, "_blank");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t.leadsPage.title}</h1>
        <button onClick={handleExport} className="inline-flex items-center gap-2 px-4 py-2.5 bg-dark-800 border border-white/10 text-sm text-dark-300 font-medium rounded-lg hover:bg-dark-700 transition-colors">
          <Download size={16} />{t.leadsPage.export}
        </button>
      </div>
      <div className="bg-dark-900 rounded-xl border border-white/5 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-dark-800 text-dark-400 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-5 py-3">{t.leadsPage.thName}</th>
              <th className="text-left px-5 py-3">{t.leadsPage.thCompany}</th>
              <th className="text-left px-5 py-3">{t.leadsPage.thEmail}</th>
              <th className="text-left px-5 py-3">{t.leadsPage.thPhone}</th>
              <th className="text-left px-5 py-3">{t.leadsPage.thCountry}</th>
              <th className="text-left px-5 py-3">{t.leadsPage.thRequirement}</th>
              <th className="text-left px-5 py-3">{t.leadsPage.thDate}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {leads.length === 0 && <tr><td colSpan={7} className="text-center py-12 text-dark-500">{t.leadsPage.empty}</td></tr>}
            {leads.map((lead) => (
              <tr key={lead.id} className="hover:bg-white/[0.02]">
                <td className="px-5 py-3 text-dark-200">{lead.name || "—"}</td>
                <td className="px-5 py-3 text-dark-200">{lead.company || "—"}</td>
                <td className="px-5 py-3 text-brand-400 font-medium">{lead.email}</td>
                <td className="px-5 py-3 text-dark-400">{lead.phone || "—"}</td>
                <td className="px-5 py-3 text-dark-400">{lead.country || "—"}</td>
                <td className="px-5 py-3 text-dark-400 max-w-[200px] truncate">{lead.requirement || "—"}</td>
                <td className="px-5 py-3 text-dark-400">{new Date(lead.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

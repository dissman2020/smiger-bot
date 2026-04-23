"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, Plus, BarChart3 } from "lucide-react";
import { getCsRecords, getCsStats, importCsRecords, createCsRecord } from "@/lib/api";
import { useLocale } from "@/lib/i18n";

export default function CsDataPage() {
  const { t } = useLocale();
  const [records, setRecords] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [importing, setImporting] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [newRecord, setNewRecord] = useState({ customer_name: "", customer_email: "", channel: "email", subject: "", content: "", agent_name: "", status: "open" });

  const load = useCallback(() => {
    getCsRecords({ limit: 100 }).then(setRecords).catch(console.error);
    getCsStats().then(setStats).catch(console.error);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setImporting(true);
    try {
      const result = await importCsRecords(files[0]);
      alert(`Imported: ${result.imported}, Skipped: ${result.skipped}`);
      load();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleAdd = async () => {
    if (!newRecord.content) return;
    try {
      await createCsRecord(newRecord);
      setShowAdd(false);
      setNewRecord({ customer_name: "", customer_email: "", channel: "email", subject: "", content: "", agent_name: "", status: "open" });
      load();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const inputCls = "bg-dark-800 text-white placeholder:text-dark-500 rounded-lg border border-white/10 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50";
  const statusColor = (s: string) => s === "resolved" ? "text-green-400 bg-green-500/10" : s === "open" ? "text-yellow-400 bg-yellow-500/10" : "text-dark-400 bg-dark-700";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t.csPage.title}</h1>
        <div className="flex gap-3">
          <button onClick={() => setShowAdd(!showAdd)} className="inline-flex items-center gap-2 px-4 py-2.5 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 transition-colors">
            <Plus size={16} />{t.csPage.addRecord}
          </button>
          <label className={`inline-flex items-center gap-2 px-4 py-2.5 bg-dark-800 border border-white/10 text-dark-300 text-sm font-medium rounded-lg hover:bg-dark-700 cursor-pointer transition-colors ${importing ? "opacity-50" : ""}`}>
            <Upload size={16} />{importing ? t.csPage.importing : t.csPage.import}
            <input ref={fileRef} type="file" className="hidden" onChange={handleImport} accept=".json" />
          </label>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: t.csPage.total, value: stats.total, icon: BarChart3 },
            { label: t.csPage.open, value: stats.open, icon: BarChart3 },
            { label: t.csPage.resolved, value: stats.resolved, icon: BarChart3 },
            { label: t.csPage.channels, value: Object.keys(stats.channels || {}).length, icon: BarChart3 },
          ].map(({ label, value, icon: Icon }, i) => (
            <div key={i} className="bg-dark-900 border border-white/5 rounded-xl p-4">
              <div className="text-xs text-dark-400 mb-1">{label}</div>
              <div className="text-2xl font-bold text-white">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <div className="bg-dark-900 border border-white/5 rounded-xl p-5 mb-6 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="Customer Name" value={newRecord.customer_name} onChange={(e) => setNewRecord({ ...newRecord, customer_name: e.target.value })} className={inputCls} />
            <input placeholder="Email" value={newRecord.customer_email} onChange={(e) => setNewRecord({ ...newRecord, customer_email: e.target.value })} className={inputCls} />
            <select value={newRecord.channel} onChange={(e) => setNewRecord({ ...newRecord, channel: e.target.value })} className={inputCls}>
              <option value="email">Email</option>
              <option value="phone">Phone</option>
              <option value="chat">Chat</option>
              <option value="social">Social</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <input placeholder="Subject" value={newRecord.subject} onChange={(e) => setNewRecord({ ...newRecord, subject: e.target.value })} className={`w-full ${inputCls}`} />
          <textarea placeholder="Content *" value={newRecord.content} onChange={(e) => setNewRecord({ ...newRecord, content: e.target.value })} rows={3} className={`w-full resize-none ${inputCls}`} />
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Agent Name" value={newRecord.agent_name} onChange={(e) => setNewRecord({ ...newRecord, agent_name: e.target.value })} className={inputCls} />
            <button onClick={handleAdd} disabled={!newRecord.content} className="bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 disabled:opacity-50 transition-colors">
              {t.csPage.addRecord}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-dark-900 rounded-xl border border-white/5 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-dark-800 text-dark-400 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-5 py-3">{t.csPage.thCustomer}</th>
              <th className="text-left px-5 py-3">{t.csPage.thEmail}</th>
              <th className="text-left px-5 py-3">{t.csPage.thChannel}</th>
              <th className="text-left px-5 py-3">{t.csPage.thSubject}</th>
              <th className="text-left px-5 py-3">{t.csPage.thAgent}</th>
              <th className="text-left px-5 py-3">{t.csPage.thStatus}</th>
              <th className="text-left px-5 py-3">{t.csPage.thDate}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {records.length === 0 && <tr><td colSpan={7} className="text-center py-12 text-dark-500">{t.csPage.empty}</td></tr>}
            {records.map((r) => (
              <tr key={r.id} className="hover:bg-white/[0.02]">
                <td className="px-5 py-3 text-dark-200">{r.customer_name || "—"}</td>
                <td className="px-5 py-3 text-brand-400">{r.customer_email || "—"}</td>
                <td className="px-5 py-3 text-dark-400 capitalize">{r.channel}</td>
                <td className="px-5 py-3 text-dark-300 max-w-[200px] truncate">{r.subject || "—"}</td>
                <td className="px-5 py-3 text-dark-400">{r.agent_name || "—"}</td>
                <td className="px-5 py-3"><span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(r.status)}`}>{r.status}</span></td>
                <td className="px-5 py-3 text-dark-400">{new Date(r.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

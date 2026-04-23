"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, Upload, RefreshCw, Search, Pencil, Trash2, X } from "lucide-react";
import {
  getFaqEntries,
  createFaqEntry,
  updateFaqEntry,
  deleteFaqEntry,
  syncFaqToKnowledge,
  importFaqFile,
} from "@/lib/api";
import { useLocale } from "@/lib/i18n";

const CATEGORIES = [
  "general",
  "pricing",
  "moq",
  "delivery",
  "customization",
  "logistics",
  "country_preferences",
];

interface FaqEntry {
  id: number;
  category: string;
  question_cn: string;
  question_en: string;
  answer_cn: string;
  answer_en: string;
  tags: string[] | null;
  extra_metadata: any;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

function CategoryBadge({ category, labels }: { category: string; labels: Record<string, string> }) {
  const colors: Record<string, string> = {
    pricing: "text-emerald-400 bg-emerald-500/10",
    moq: "text-blue-400 bg-blue-500/10",
    delivery: "text-amber-400 bg-amber-500/10",
    customization: "text-purple-400 bg-purple-500/10",
    logistics: "text-cyan-400 bg-cyan-500/10",
    country_preferences: "text-pink-400 bg-pink-500/10",
    general: "text-gray-400 bg-gray-500/10",
  };
  return (
    <span className={`text-xs rounded-full px-2 py-0.5 ${colors[category] || colors.general}`}>
      {labels[category] || category}
    </span>
  );
}

export default function FaqPage() {
  const { t } = useLocale();
  const ft = (t as any).faqPage || {};
  const catLabels = ft.categories || {};

  const [entries, setEntries] = useState<FaqEntry[]>([]);
  const [filterCat, setFilterCat] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [editing, setEditing] = useState<FaqEntry | null>(null);
  const [creating, setCreating] = useState(false);
  const importRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    getFaqEntries({ category: filterCat || undefined, q: searchQ || undefined })
      .then(setEntries)
      .catch(console.error);
  }, [filterCat, searchQ]);

  useEffect(() => { load(); }, [load]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncFaqToKnowledge();
      const msg = (ft.syncSuccess || "Synced {entries} entries ({chunks} chunks)")
        .replace("{entries}", result.total_entries)
        .replace("{chunks}", result.total_chunks);
      alert(msg);
    } catch (err: any) {
      alert(err.message || err);
    } finally {
      setSyncing(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importFaqFile(file);
      alert(`Imported ${result.imported} entries`);
      load();
    } catch (err: any) {
      alert(err.message || err);
    } finally {
      setImporting(false);
      if (importRef.current) importRef.current.value = "";
    }
  };

  const handleDelete = async (entry: FaqEntry) => {
    const msg = ft.deleteConfirm
      ? ft.deleteConfirm(entry.question_cn || entry.question_en)
      : `Delete "${entry.question_en}"?`;
    if (!confirm(msg)) return;
    try {
      await deleteFaqEntry(entry.id);
      load();
    } catch (err: any) {
      alert(err.message || err);
    }
  };

  const handleSave = async (data: any) => {
    try {
      if (editing) {
        await updateFaqEntry(editing.id, data);
      } else {
        await createFaqEntry(data);
      }
      setEditing(null);
      setCreating(false);
      load();
    } catch (err: any) {
      alert(err.message || err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">{ft.title || "FAQ Management"}</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setEditing(null); setCreating(true); }}
            className="flex items-center gap-2 bg-brand-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-600 transition-colors"
          >
            <Plus size={16} /> {ft.addEntry || "Add FAQ"}
          </button>
          <label className="flex items-center gap-2 bg-white/5 text-dark-300 px-4 py-2 rounded-lg text-sm hover:bg-white/10 cursor-pointer transition-colors">
            <Upload size={16} /> {importing ? ft.importing || "Importing..." : ft.import || "Import File"}
            <input ref={importRef} type="file" className="hidden" accept=".json,.doc,.docx,.txt" onChange={handleImport} />
          </label>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 bg-white/5 text-dark-300 px-4 py-2 rounded-lg text-sm hover:bg-white/10 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={16} className={syncing ? "animate-spin" : ""} />
            {syncing ? ft.syncing || "Syncing..." : ft.syncKnowledge || "Sync to KB"}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-500" />
          <input
            type="text"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder={ft.search || "Search..."}
            className="w-full pl-9 pr-3 py-2 bg-dark-800 border border-white/10 rounded-lg text-sm text-white placeholder-dark-500 focus:outline-none focus:border-brand-500/50"
          />
        </div>
        <select
          value={filterCat}
          onChange={(e) => setFilterCat(e.target.value)}
          className="bg-dark-800 border border-white/10 rounded-lg text-sm text-dark-300 px-3 py-2 focus:outline-none focus:border-brand-500/50"
        >
          <option value="">{ft.allCategories || "All Categories"}</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{catLabels[c] || c}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-dark-800/50 border border-white/5 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/5 text-dark-400 text-left">
              <th className="px-4 py-3 font-medium w-8">#</th>
              <th className="px-4 py-3 font-medium">{ft.thQuestion || "Question"}</th>
              <th className="px-4 py-3 font-medium max-w-[200px]">{ft.thAnswer || "Answer"}</th>
              <th className="px-4 py-3 font-medium">{ft.thCategory || "Category"}</th>
              <th className="px-4 py-3 font-medium">{ft.thTags || "Tags"}</th>
              <th className="px-4 py-3 font-medium w-24">{ft.thAction || "Action"}</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-dark-500">
                  {ft.empty || "No FAQ entries yet."}
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr key={entry.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 text-dark-500">{entry.id}</td>
                  <td className="px-4 py-3">
                    <div className="text-white text-sm leading-snug">{entry.question_cn}</div>
                    <div className="text-dark-400 text-xs mt-0.5">{entry.question_en}</div>
                  </td>
                  <td className="px-4 py-3 max-w-[200px]">
                    <div className="text-dark-300 text-xs truncate">{entry.answer_cn}</div>
                  </td>
                  <td className="px-4 py-3">
                    <CategoryBadge category={entry.category} labels={catLabels} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(entry.tags || []).map((tag) => (
                        <span key={tag} className="text-[10px] text-dark-400 bg-white/5 rounded px-1.5 py-0.5">{tag}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => { setEditing(entry); setCreating(false); }}
                        className="p-1.5 text-dark-400 hover:text-brand-400 transition-colors"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(entry)}
                        className="p-1.5 text-dark-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Edit/Create Modal */}
      {(editing || creating) && (
        <FaqFormModal
          entry={editing}
          labels={ft}
          catLabels={catLabels}
          onSave={handleSave}
          onClose={() => { setEditing(null); setCreating(false); }}
        />
      )}
    </div>
  );
}

function FaqFormModal({
  entry,
  labels,
  catLabels,
  onSave,
  onClose,
}: {
  entry: FaqEntry | null;
  labels: any;
  catLabels: Record<string, string>;
  onSave: (data: any) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    category: entry?.category || "general",
    question_cn: entry?.question_cn || "",
    question_en: entry?.question_en || "",
    answer_cn: entry?.answer_cn || "",
    answer_en: entry?.answer_en || "",
    tags: (entry?.tags || []).join(", "),
    sort_order: entry?.sort_order || 0,
    is_active: entry?.is_active ?? true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...form,
      tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
    });
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-800 border border-white/10 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white">{labels.formTitle || "FAQ Entry"}</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-dark-400 mb-1">{labels.category || "Category"}</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full bg-dark-900 border border-white/10 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/50"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{catLabels[c] || c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-dark-400 mb-1">{labels.tags || "Tags"}</label>
              <input
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                className="w-full bg-dark-900 border border-white/10 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/50"
                placeholder="EQ, LOGO, OEM"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-dark-400 mb-1">{labels.questionCn || "Question (CN)"}</label>
            <input
              value={form.question_cn}
              onChange={(e) => setForm({ ...form, question_cn: e.target.value })}
              required
              className="w-full bg-dark-900 border border-white/10 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/50"
            />
          </div>
          <div>
            <label className="block text-xs text-dark-400 mb-1">{labels.questionEn || "Question (EN)"}</label>
            <input
              value={form.question_en}
              onChange={(e) => setForm({ ...form, question_en: e.target.value })}
              required
              className="w-full bg-dark-900 border border-white/10 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/50"
            />
          </div>
          <div>
            <label className="block text-xs text-dark-400 mb-1">{labels.answerCn || "Answer (CN)"}</label>
            <textarea
              value={form.answer_cn}
              onChange={(e) => setForm({ ...form, answer_cn: e.target.value })}
              rows={3}
              required
              className="w-full bg-dark-900 border border-white/10 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/50 resize-y"
            />
          </div>
          <div>
            <label className="block text-xs text-dark-400 mb-1">{labels.answerEn || "Answer (EN)"}</label>
            <textarea
              value={form.answer_en}
              onChange={(e) => setForm({ ...form, answer_en: e.target.value })}
              rows={3}
              required
              className="w-full bg-dark-900 border border-white/10 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/50 resize-y"
            />
          </div>
          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-dark-400 hover:text-white transition-colors">
              {labels.cancel || "Cancel"}
            </button>
            <button type="submit" className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors">
              {labels.save || "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

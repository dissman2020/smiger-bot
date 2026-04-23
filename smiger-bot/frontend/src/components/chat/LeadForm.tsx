"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { LeadFormData } from "@/lib/types";
import { useLocale } from "@/lib/i18n";

interface Props {
  conversationId: string;
  onSubmit: (data: LeadFormData) => void;
  onClose: () => void;
}

export default function LeadForm({ conversationId, onSubmit, onClose }: Props) {
  const { t } = useLocale();
  const [form, setForm] = useState<LeadFormData>({ name: "", company: "", email: "", phone: "", country: "", requirement: "" });
  const [submitting, setSubmitting] = useState(false);

  const update = (field: keyof LeadFormData, value: string) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email) return;
    setSubmitting(true);
    onSubmit(form);
  };

  const inputCls = "bg-dark-800 text-dark-100 placeholder:text-dark-500 rounded-lg border border-white/10 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50";

  return (
    <div className="animate-fade-in-up bg-dark-800 border border-white/10 rounded-2xl p-5 mx-2 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-white text-sm">{t.lead.title}</h3>
        <button onClick={onClose} className="text-dark-400 hover:text-white transition-colors"><X size={18} /></button>
      </div>
      <p className="text-xs text-dark-400 mb-4">{t.lead.subtitle}</p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <input type="text" placeholder={t.lead.name} value={form.name} onChange={(e) => update("name", e.target.value)} className={inputCls} />
          <input type="text" placeholder={t.lead.company} value={form.company} onChange={(e) => update("company", e.target.value)} className={inputCls} />
        </div>
        <input type="email" placeholder={t.lead.email} required value={form.email} onChange={(e) => update("email", e.target.value)} className={`w-full ${inputCls}`} />
        <div className="grid grid-cols-2 gap-3">
          <input type="text" placeholder={t.lead.phone} value={form.phone} onChange={(e) => update("phone", e.target.value)} className={inputCls} />
          <input type="text" placeholder={t.lead.country} value={form.country} onChange={(e) => update("country", e.target.value)} className={inputCls} />
        </div>
        <textarea placeholder={t.lead.requirement} value={form.requirement} onChange={(e) => update("requirement", e.target.value)} rows={2} className={`w-full resize-none ${inputCls}`} />
        <button type="submit" disabled={submitting || !form.email} className="w-full py-2.5 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 disabled:opacity-50 transition-colors">
          {submitting ? t.lead.submitting : t.lead.submit}
        </button>
      </form>
    </div>
  );
}

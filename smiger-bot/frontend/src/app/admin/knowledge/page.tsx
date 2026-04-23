"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileUp, Trash2, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { getDocuments, uploadDocument, deleteDocument } from "@/lib/api";
import { DocumentItem } from "@/lib/types";
import { useLocale } from "@/lib/i18n";
import clsx from "clsx";

function StatusBadge({ status, labels }: { status: string; labels: { ready: string; error: string; processing: string } }) {
  if (status === "ready") return <span className="inline-flex items-center gap-1 text-xs text-green-400 bg-green-500/10 rounded-full px-2 py-0.5"><CheckCircle size={12} /> {labels.ready}</span>;
  if (status === "error") return <span className="inline-flex items-center gap-1 text-xs text-red-400 bg-red-500/10 rounded-full px-2 py-0.5"><AlertCircle size={12} /> {labels.error}</span>;
  return <span className="inline-flex items-center gap-1 text-xs text-yellow-400 bg-yellow-500/10 rounded-full px-2 py-0.5"><Loader2 size={12} className="animate-spin" /> {labels.processing}</span>;
}

export default function KnowledgePage() {
  const { t } = useLocale();
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => { getDocuments().then(setDocs).catch(console.error); }, []);
  useEffect(() => { load(); }, [load]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setUploading(true);
    try { for (const file of Array.from(files)) await uploadDocument(file); load(); }
    catch (err: any) { alert(err.message || err); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(t.knowledgePage.deleteConfirm(name))) return;
    try { await deleteDocument(id); load(); } catch (err: any) { alert(err.message || err); }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  };

  const statusLabels = { ready: t.knowledgePage.statusReady, error: t.knowledgePage.statusError, processing: t.knowledgePage.statusProcessing };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t.knowledgePage.title}</h1>
        <label className={clsx("inline-flex items-center gap-2 px-4 py-2.5 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 cursor-pointer transition-colors", uploading && "opacity-50 pointer-events-none")}>
          <FileUp size={16} />{uploading ? t.knowledgePage.uploading : t.knowledgePage.upload}
          <input ref={fileRef} type="file" className="hidden" onChange={handleUpload} multiple accept=".pdf,.docx,.xlsx,.txt,.md,.csv,.json" />
        </label>
      </div>
      <p className="text-sm text-dark-400 mb-4">{t.knowledgePage.description}</p>
      <div className="bg-dark-900 rounded-xl border border-white/5 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-dark-800 text-dark-400 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-5 py-3">{t.knowledgePage.thFile}</th>
              <th className="text-left px-5 py-3">{t.knowledgePage.thType}</th>
              <th className="text-left px-5 py-3">{t.knowledgePage.thSize}</th>
              <th className="text-left px-5 py-3">{t.knowledgePage.thChunks}</th>
              <th className="text-left px-5 py-3">{t.knowledgePage.thStatus}</th>
              <th className="text-left px-5 py-3">{t.knowledgePage.thUploaded}</th>
              <th className="text-right px-5 py-3">{t.knowledgePage.thAction}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {docs.length === 0 && <tr><td colSpan={7} className="text-center py-12 text-dark-500">{t.knowledgePage.empty}</td></tr>}
            {docs.map((doc) => (
              <tr key={doc.id} className="hover:bg-white/[0.02]">
                <td className="px-5 py-3 font-medium text-dark-200 max-w-[200px] truncate">{doc.filename}</td>
                <td className="px-5 py-3 text-dark-400 uppercase">{doc.file_type}</td>
                <td className="px-5 py-3 text-dark-400">{formatSize(doc.file_size)}</td>
                <td className="px-5 py-3 text-dark-400">{doc.chunk_count}</td>
                <td className="px-5 py-3"><StatusBadge status={doc.status} labels={statusLabels} /></td>
                <td className="px-5 py-3 text-dark-400">{new Date(doc.created_at).toLocaleDateString()}</td>
                <td className="px-5 py-3 text-right">
                  <button onClick={() => handleDelete(doc.id, doc.filename)} className="text-dark-500 hover:text-red-400 transition-colors"><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

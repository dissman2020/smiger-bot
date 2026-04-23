"use client";

import { useEffect, useState } from "react";
import { MessageSquare, ChevronRight } from "lucide-react";
import { clearConversationHistory, getConversations, getConversation } from "@/lib/api";
import { ConversationItem } from "@/lib/types";
import { useLocale } from "@/lib/i18n";

interface MessageItem { id: string; role: string; content: string; created_at: string; }

export default function ConversationsPage() {
  const { t } = useLocale();
  const [convs, setConvs] = useState<ConversationItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [clearing, setClearing] = useState(false);

  useEffect(() => { getConversations().then(setConvs).catch(console.error); }, []);

  const viewConversation = async (id: string) => {
    setSelected(id);
    setLoadingMsgs(true);
    try { const data = await getConversation(id); setMessages(data.messages || []); }
    catch { setMessages([]); }
    finally { setLoadingMsgs(false); }
  };

  const handleClearHistory = async () => {
    const confirmed = window.confirm("确认清除所有历史聊天记录？该操作不可恢复。");
    if (!confirmed) return;

    setClearing(true);
    try {
      await clearConversationHistory();
      setConvs([]);
      setSelected(null);
      setMessages([]);
      window.alert("历史聊天记录已清除。");
    } catch (e: any) {
      window.alert(`清除失败：${e.message || "未知错误"}`);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t.conversationsPage.title}</h1>
        <button
          onClick={handleClearHistory}
          disabled={clearing}
          className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors"
        >
          {clearing ? "清除中..." : "清除历史聊天记录"}
        </button>
      </div>
      <div className="flex gap-6 h-[calc(100vh-12rem)]">
        <div className="w-80 bg-dark-900 rounded-xl border border-white/5 overflow-y-auto shrink-0">
          {convs.length === 0 && <div className="p-8 text-center text-dark-500 text-sm">{t.conversationsPage.empty}</div>}
          {convs.map((c) => (
            <button key={c.id} onClick={() => viewConversation(c.id)} className={`w-full text-left px-4 py-3 border-b border-white/5 hover:bg-white/[0.03] transition-colors ${selected === c.id ? "bg-brand-500/10" : ""}`}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-dark-200 truncate">{c.visitor_id}</span>
                <ChevronRight size={14} className="text-dark-600" />
              </div>
              <p className="text-xs text-dark-500 mt-1 truncate">{c.message_preview || t.conversationsPage.noMessages}</p>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-dark-500">
                <span>{c.turn_count} {t.conversationsPage.turns}</span>
                <span>{c.language.toUpperCase()}</span>
                {c.lead_captured && <span className="text-brand-400 font-medium">Lead</span>}
                <span className="ml-auto">{new Date(c.created_at).toLocaleDateString()}</span>
              </div>
            </button>
          ))}
        </div>
        <div className="flex-1 bg-dark-900 rounded-xl border border-white/5 overflow-y-auto p-5">
          {!selected && (
            <div className="flex flex-col items-center justify-center h-full text-dark-500">
              <MessageSquare size={40} className="mb-3 opacity-30" />
              <p className="text-sm">{t.conversationsPage.selectHint}</p>
            </div>
          )}
          {selected && loadingMsgs && <div className="text-sm text-dark-500">{t.conversationsPage.loading}</div>}
          {selected && !loadingMsgs && (
            <div className="space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-start" : "justify-end"}`}>
                  <div className="max-w-[70%]">
                    <div className={`mb-1 text-[10px] px-1 ${msg.role === "user" ? "text-dark-400 text-left" : "text-sky-300 text-right"}`}>
                      {msg.role === "user" ? "客户" : "客服/AI"}
                    </div>
                    <div className={`rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${msg.role === "user" ? "bg-dark-800 text-dark-200 border border-white/5 rounded-tl-sm" : "bg-sky-600 text-white rounded-tr-sm"}`}>
                      {msg.content}
                      <div className={`text-[10px] mt-1 ${msg.role === "user" ? "text-dark-500" : "text-white/60"}`}>{new Date(msg.created_at).toLocaleTimeString()}</div>
                    </div>
                  </div>
                </div>
              ))}
              {messages.length === 0 && <p className="text-sm text-dark-500">{t.conversationsPage.noMessages}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock,
  List,
  MessageSquare,
  Phone,
  Send,
  UserCheck,
} from "lucide-react";
import clsx from "clsx";
import {
  acceptHandoff,
  getApiSettings,
  getHandoffList,
  getHandoffMessages,
  replyHandoff,
  resolveHandoff,
  updateHandoffChannel,
} from "@/lib/api";
import { useLocale } from "@/lib/i18n";

interface HandoffConv {
  id: string;
  visitor_id: string;
  customer_region?: string | null;
  customer_country_code?: string | null;
  customer_phone?: string | null;
  language: string;
  turn_count: number;
  lead_captured: boolean;
  handoff_status: string;
  handoff_at: string | null;
  whatsapp_tag: string | null;
  telegram_account_name?: string | null;
  created_at: string;
  updated_at: string;
  message_preview: string | null;
}

interface Msg {
  id: string;
  role: string;
  content: string;
  created_at: string;
  confidence: number | null;
}

interface TelegramAccountOption {
  name: string;
  enabled: boolean;
  bot_token: string;
  admin_chat_id: string;
  webhook_secret: string;
}

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  none: { bg: "bg-dark-600/30", text: "text-dark-400", label: "AI" },
  pending: { bg: "bg-amber-500/15", text: "text-amber-400", label: "待接入" },
  active: { bg: "bg-emerald-500/15", text: "text-emerald-400", label: "人工中" },
  resolved: { bg: "bg-blue-500/15", text: "text-blue-400", label: "已完成" },
};

export default function HandoffPage() {
  const { t } = useLocale();
  const [convs, setConvs] = useState<HandoffConv[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [regionFilter, setRegionFilter] = useState("all");
  const [telegramAccounts, setTelegramAccounts] = useState<TelegramAccountOption[]>([]);
  const [selectedTelegramAccount, setSelectedTelegramAccount] = useState("");
  const [channelSaving, setChannelSaving] = useState(false);
  const msgEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const selectedConv = convs.find((c) => c.id === selected);
  const enabledTelegramAccounts = useMemo(
    () => telegramAccounts.filter((a) => a.enabled),
    [telegramAccounts]
  );

  const fetchConvs = useCallback(async () => {
    try {
      const data = await getHandoffList(undefined, showAll);
      setConvs(data);
    } catch {
      // ignore
    }
  }, [showAll]);

  const fetchMessages = useCallback(async (convId: string) => {
    try {
      const data = await getHandoffMessages(convId);
      setMessages(data);
    } catch {
      // ignore
    }
  }, []);

  const fetchTelegramAccounts = useCallback(async () => {
    try {
      const settings = await getApiSettings();
      setTelegramAccounts((settings.telegram_accounts || []) as TelegramAccountOption[]);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchConvs();
    fetchTelegramAccounts();
    const iv = setInterval(fetchConvs, 5000);
    return () => clearInterval(iv);
  }, [fetchConvs, fetchTelegramAccounts]);

  useEffect(() => {
    if (!selected) return;
    fetchMessages(selected);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => fetchMessages(selected), 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [selected, fetchMessages]);

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!selectedConv) return;
    const account = selectedConv.telegram_account_name || enabledTelegramAccounts[0]?.name || "";
    setSelectedTelegramAccount(account);
  }, [selectedConv, enabledTelegramAccounts]);

  const regions = useMemo(() => {
    const set = new Set<string>();
    convs.forEach((c) => {
      if (c.customer_region) set.add(c.customer_region);
    });
    return ["all", ...Array.from(set).sort()];
  }, [convs]);

  const filteredConvs = useMemo(() => {
    if (regionFilter === "all") return convs;
    return convs.filter((c) => (c.customer_region || "") === regionFilter);
  }, [convs, regionFilter]);

  const handleSelect = (id: string) => {
    setSelected(id);
    setReplyText("");
  };

  const handleAccept = async () => {
    if (!selected) return;
    setAccepting(true);
    try {
      await acceptHandoff(selected, selectedTelegramAccount || undefined);
      await fetchConvs();
      await fetchMessages(selected);
    } catch (e) {
      console.error(e);
    } finally {
      setAccepting(false);
    }
  };

  const handleSaveChannel = async () => {
    if (!selected) return;
    setChannelSaving(true);
    try {
      await updateHandoffChannel(selected, selectedTelegramAccount || undefined);
      await fetchConvs();
    } catch (e) {
      console.error(e);
    } finally {
      setChannelSaving(false);
    }
  };

  const handleReply = async () => {
    if (!selected || !replyText.trim()) return;
    setSending(true);
    try {
      await replyHandoff(selected, replyText.trim());
      setReplyText("");
      await fetchMessages(selected);
      await fetchConvs();
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  const handleResolve = async () => {
    if (!selected) return;
    try {
      await resolveHandoff(selected);
      await fetchConvs();
    } catch (e) {
      console.error(e);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleReply();
    }
  };

  const pendingCount = convs.filter((c) => c.handoff_status === "pending").length;
  const activeCount = convs.filter((c) => c.handoff_status === "active").length;

  const canAccept = selectedConv && selectedConv.handoff_status !== "active";
  const isActive = selectedConv?.handoff_status === "active";

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-white">
          {(t as any).handoffPage?.title ?? "人工接管"}
        </h1>
        <div className="flex gap-2">
          {pendingCount > 0 && (
            <span className="flex items-center gap-1.5 bg-amber-500/15 text-amber-400 text-xs font-medium px-2.5 py-1 rounded-full">
              <AlertTriangle size={12} />
              {pendingCount} 待接入
            </span>
          )}
          {activeCount > 0 && (
            <span className="flex items-center gap-1.5 bg-emerald-500/15 text-emerald-400 text-xs font-medium px-2.5 py-1 rounded-full">
              <UserCheck size={12} />
              {activeCount} 服务中
            </span>
          )}
        </div>

        <select
          value={regionFilter}
          onChange={(e) => setRegionFilter(e.target.value)}
          className="ml-auto bg-dark-800 text-dark-200 border border-white/10 rounded-lg px-2 py-1.5 text-xs"
        >
          {regions.map((r) => (
            <option key={r} value={r}>
              {r === "all" ? "全部地区" : r}
            </option>
          ))}
        </select>

        <button
          onClick={() => setShowAll((v) => !v)}
          className={clsx(
            "flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors border",
            showAll
              ? "bg-brand-500/15 text-brand-400 border-brand-500/30"
              : "bg-dark-800 text-dark-400 border-white/10 hover:bg-white/5"
          )}
        >
          <List size={14} />
          {showAll ? "显示全部对话" : "仅显示接管相关"}
        </button>
      </div>

      <div className="flex gap-6 h-[calc(100vh-12rem)]">
        <div className="w-96 bg-dark-900 rounded-xl border border-white/5 overflow-y-auto shrink-0">
          {filteredConvs.length === 0 && (
            <div className="p-8 text-center text-dark-500 text-sm">
              <Phone size={32} className="mx-auto mb-3 opacity-30" />
              暂无会话记录
            </div>
          )}
          {filteredConvs.map((c) => {
            const badge = STATUS_BADGE[c.handoff_status] || STATUS_BADGE.none;
            return (
              <button
                key={c.id}
                onClick={() => handleSelect(c.id)}
                className={clsx(
                  "w-full text-left px-4 py-3 border-b border-white/5 hover:bg-white/[0.03] transition-colors",
                  selected === c.id ? "bg-brand-500/10" : ""
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-dark-200 truncate">
                    {c.customer_phone || c.visitor_id}
                  </span>
                  <ChevronRight size={14} className="text-dark-600 shrink-0" />
                </div>
                <p className="text-xs text-dark-500 truncate">{c.message_preview || "..."}</p>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className={clsx("text-[10px] font-medium px-1.5 py-0.5 rounded", badge.bg, badge.text)}>
                    {badge.label}
                  </span>
                  {c.customer_region && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300">
                      {c.customer_region}
                    </span>
                  )}
                  {c.whatsapp_tag && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">
                      WA #{c.whatsapp_tag}
                    </span>
                  )}
                  {c.telegram_account_name && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300">
                      TG {c.telegram_account_name}
                    </span>
                  )}
                  <span className="text-[10px] text-dark-500 flex items-center gap-1">
                    <Clock size={10} />
                    {new Date(c.updated_at || c.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex-1 bg-dark-900 rounded-xl border border-white/5 flex flex-col overflow-hidden">
          {!selected ? (
            <div className="flex-1 flex flex-col items-center justify-center text-dark-500">
              <MessageSquare size={40} className="mb-3 opacity-30" />
              <p className="text-sm">选择一个会话查看详情并接入人工服务</p>
            </div>
          ) : (
            <>
              <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between bg-dark-900/80">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-dark-300 font-medium">
                    {selectedConv?.customer_phone || selectedConv?.visitor_id}
                  </span>
                  {selectedConv && (
                    <span className={clsx(
                      "text-[10px] font-medium px-1.5 py-0.5 rounded",
                      STATUS_BADGE[selectedConv.handoff_status]?.bg,
                      STATUS_BADGE[selectedConv.handoff_status]?.text
                    )}>
                      {STATUS_BADGE[selectedConv.handoff_status]?.label}
                    </span>
                  )}
                  {selectedConv?.customer_region && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300">
                      区域 {selectedConv.customer_region}
                    </span>
                  )}
                </div>
                <div className="flex gap-2 items-center">
                  {canAccept && (
                    <button
                      onClick={handleAccept}
                      disabled={accepting}
                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                    >
                      <UserCheck size={14} />
                      {accepting ? "接入中..." : "接入对话"}
                    </button>
                  )}
                  {isActive && (
                    <button
                      onClick={handleResolve}
                      className="flex items-center gap-1.5 bg-dark-700 hover:bg-dark-600 text-dark-300 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                    >
                      <CheckCircle2 size={14} />
                      结束服务
                    </button>
                  )}
                </div>
              </div>

              <div className="px-5 py-3 border-b border-white/5 bg-dark-900/70 flex items-center gap-2">
                <label className="text-xs text-dark-400">对接 Telegram:</label>
                <select
                  value={selectedTelegramAccount}
                  onChange={(e) => setSelectedTelegramAccount(e.target.value)}
                  className="bg-dark-800 text-dark-100 border border-white/10 rounded px-2 py-1 text-xs"
                >
                  <option value="">默认</option>
                  {enabledTelegramAccounts.map((a) => (
                    <option key={a.name} value={a.name}>
                      {a.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleSaveChannel}
                  disabled={channelSaving}
                  className="bg-sky-600 hover:bg-sky-500 text-white text-xs px-2.5 py-1 rounded transition-colors disabled:opacity-50"
                >
                  {channelSaving ? "保存中..." : "保存"}
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {messages.map((msg) => (
                  <div key={msg.id} className={clsx("flex", msg.role === "user" ? "justify-start" : "justify-end")}>
                    <div className="max-w-[72%]">
                      <div className={clsx(
                        "mb-1 text-[10px] px-1",
                        msg.role === "user" ? "text-dark-400 text-left" : "text-sky-300 text-right"
                      )}>
                        {msg.role === "user" ? "客户" : "客服"}
                      </div>
                      <div className={clsx(
                        "rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap",
                        msg.role === "user"
                          ? "bg-dark-800 text-dark-200 border border-white/5 rounded-tl-sm"
                          : "bg-sky-600 text-white rounded-tr-sm"
                      )}>
                        {msg.content}
                        <div className={clsx("text-[10px] mt-1", msg.role === "user" ? "text-dark-500" : "text-white/60")}>
                          {new Date(msg.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={msgEndRef} />
              </div>

              {isActive && (
                <div className="px-4 py-3 border-t border-white/5 bg-dark-900/80">
                  <div className="flex gap-2">
                    <textarea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="输入回复内容（Enter 发送）"
                      rows={1}
                      className="flex-1 bg-dark-800 text-dark-100 placeholder:text-dark-500 rounded-lg border border-white/10 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                    />
                    <button
                      onClick={handleReply}
                      disabled={sending || !replyText.trim()}
                      className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <Send size={16} />
                    </button>
                  </div>
                </div>
              )}

              {!isActive && (
                <div className="px-4 py-3 border-t border-white/5 bg-dark-800/50">
                  <p className="text-xs text-dark-400 text-center">
                    先选择 Telegram 对接账号，再点击“接入对话”开始人工服务。
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

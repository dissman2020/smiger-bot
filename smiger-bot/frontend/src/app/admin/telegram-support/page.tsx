"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bot, CheckCircle2, ChevronRight, MessageSquare, RefreshCw, Send, User, Zap } from "lucide-react";
import clsx from "clsx";
import {
  getTelegramSupportChat,
  getTelegramSupportChats,
  getTelegramSupportSettings,
  replyTelegramSupportChat,
  updateTelegramSupportChatAi,
  updateTelegramSupportSettings,
} from "@/lib/api";

interface TelegramSupportSettings {
  ai_enabled: boolean;
  max_history: number;
  system_prompt: string;
  telegram_enabled: boolean;
  active_account: string;
}

interface TelegramSupportChat {
  chat_id: string;
  account_name: string | null;
  display_name: string | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  ai_enabled: boolean;
  ai_enabled_override: boolean | null;
  unread_count: number;
  message_count: number;
  last_message_preview: string | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

interface TelegramSupportMessage {
  id: string;
  chat_id: string;
  role: string;
  content: string;
  source: string;
  telegram_message_id: string | null;
  created_at: string;
}

const defaultSettings: TelegramSupportSettings = {
  ai_enabled: true,
  max_history: 12,
  system_prompt: "",
  telegram_enabled: false,
  active_account: "",
};

function customerName(chat: TelegramSupportChat) {
  if (chat.display_name) return chat.display_name;
  if (chat.username) return `@${chat.username}`;
  return chat.chat_id;
}

function formatTime(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export default function TelegramSupportPage() {
  const [settings, setSettings] = useState<TelegramSupportSettings>(defaultSettings);
  const [chats, setChats] = useState<TelegramSupportChat[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedChat, setSelectedChat] = useState<TelegramSupportChat | null>(null);
  const [messages, setMessages] = useState<TelegramSupportMessage[]>([]);
  const [replyText, setReplyText] = useState("");
  const [savingSettings, setSavingSettings] = useState(false);
  const [sending, setSending] = useState(false);
  const [loadingChats, setLoadingChats] = useState(false);
  const [notice, setNotice] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const selectedFromList = useMemo(
    () => chats.find((chat) => chat.chat_id === selected) || selectedChat,
    [chats, selected, selectedChat]
  );

  const loadSettings = useCallback(async () => {
    const data = await getTelegramSupportSettings();
    setSettings(data);
  }, []);

  const loadChats = useCallback(async () => {
    setLoadingChats(true);
    try {
      const data = await getTelegramSupportChats();
      setChats(data);
    } finally {
      setLoadingChats(false);
    }
  }, []);

  const loadChat = useCallback(async (chatId: string, markRead = true) => {
    const data = await getTelegramSupportChat(chatId, markRead);
    setSelectedChat(data.chat);
    setMessages(data.messages || []);
  }, []);

  useEffect(() => {
    loadSettings().catch(console.error);
    loadChats().catch(console.error);
    const timer = setInterval(() => {
      loadChats().catch(() => undefined);
      if (selected) loadChat(selected, false).catch(() => undefined);
    }, 5000);
    return () => clearInterval(timer);
  }, [loadSettings, loadChats, loadChat, selected]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelect = async (chatId: string) => {
    setSelected(chatId);
    setReplyText("");
    await loadChat(chatId, true);
    await loadChats();
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    setNotice("");
    try {
      const data = await updateTelegramSupportSettings({
        ai_enabled: settings.ai_enabled,
        max_history: settings.max_history,
        system_prompt: settings.system_prompt,
      });
      setSettings(data);
      setNotice("Settings saved.");
    } catch (error: any) {
      setNotice(error.message || "Failed to save settings.");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleToggleGlobalAi = async () => {
    const data = await updateTelegramSupportSettings({ ai_enabled: !settings.ai_enabled });
    setSettings(data);
  };

  const handleSetChatAi = async (aiEnabled: boolean | undefined, clearOverride = false) => {
    if (!selected) return;
    await updateTelegramSupportChatAi(selected, aiEnabled, clearOverride);
    await loadChat(selected, false);
    await loadChats();
  };

  const handleReply = async () => {
    if (!selected || !replyText.trim()) return;
    setSending(true);
    try {
      await replyTelegramSupportChat(selected, replyText.trim());
      setReplyText("");
      await loadChat(selected, true);
      await loadChats();
    } catch (error: any) {
      setNotice(error.message || "Failed to send message.");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleReply();
    }
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Telegram Support</h1>
          <p className="mt-1 text-sm text-dark-400">
            Direct Telegram customer inbox from project3plus, now running inside the project3 admin platform.
          </p>
        </div>
        <button
          onClick={() => {
            loadSettings().catch(console.error);
            loadChats().catch(console.error);
            if (selected) loadChat(selected, false).catch(console.error);
          }}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-dark-800 px-3 py-2 text-sm text-dark-200 transition-colors hover:bg-dark-700"
        >
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <div className="rounded-xl border border-white/5 bg-dark-900 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
                <Bot size={16} className="text-sky-400" />
                Module Settings
              </h2>
              <p className="mt-1 text-xs text-dark-500">
                Telegram channel: {settings.telegram_enabled ? "enabled" : "disabled"} / account: {settings.active_account || "-"}
              </p>
            </div>
            <button
              onClick={handleToggleGlobalAi}
              className={clsx(
                "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                settings.ai_enabled ? "bg-emerald-500/15 text-emerald-300" : "bg-dark-700 text-dark-300"
              )}
            >
              Global AI {settings.ai_enabled ? "ON" : "OFF"}
            </button>
          </div>

          <label className="mb-1 block text-xs text-dark-400">Max history turns</label>
          <input
            type="number"
            min={1}
            max={50}
            value={settings.max_history}
            onChange={(event) => setSettings({ ...settings, max_history: Number(event.target.value) || 12 })}
            className="mb-4 w-full rounded-lg border border-white/10 bg-dark-800 px-3 py-2 text-sm text-white outline-none focus:ring-2 focus:ring-brand-500/50"
          />

          <label className="mb-1 block text-xs text-dark-400">System prompt</label>
          <textarea
            value={settings.system_prompt}
            onChange={(event) => setSettings({ ...settings, system_prompt: event.target.value })}
            rows={4}
            className="w-full resize-none rounded-lg border border-white/10 bg-dark-800 px-3 py-2 text-sm text-white outline-none focus:ring-2 focus:ring-brand-500/50"
          />

          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleSaveSettings}
              disabled={savingSettings}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
            >
              <CheckCircle2 size={15} />
              {savingSettings ? "Saving..." : "Save Settings"}
            </button>
            {notice && <span className="text-xs text-brand-400">{notice}</span>}
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-dark-900 p-5">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <Zap size={16} className="text-amber-400" />
            How this module works
          </h2>
          <div className="grid gap-3 text-sm text-dark-300 md:grid-cols-3">
            <div className="rounded-lg border border-white/5 bg-dark-800/60 p-3">
              Customers message the configured Telegram bot in a private chat.
            </div>
            <div className="rounded-lg border border-white/5 bg-dark-800/60 p-3">
              AI replies automatically when global AI and per-chat AI are enabled.
            </div>
            <div className="rounded-lg border border-white/5 bg-dark-800/60 p-3">
              Staff can pause AI for a chat and send manual replies from this page.
            </div>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-23rem)] min-h-[520px] gap-6">
        <div className="w-96 shrink-0 overflow-hidden rounded-xl border border-white/5 bg-dark-900">
          <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
            <h2 className="text-sm font-semibold text-white">Inbox</h2>
            <span className="text-xs text-dark-500">{loadingChats ? "Loading..." : `${chats.length} chats`}</span>
          </div>
          <div className="h-full overflow-y-auto pb-12">
            {chats.length === 0 && (
              <div className="p-8 text-center text-sm text-dark-500">
                <MessageSquare size={34} className="mx-auto mb-3 opacity-30" />
                No Telegram customer chats yet.
              </div>
            )}
            {chats.map((chat) => (
              <button
                key={chat.chat_id}
                onClick={() => handleSelect(chat.chat_id).catch(console.error)}
                className={clsx(
                  "w-full border-b border-white/5 px-4 py-3 text-left transition-colors hover:bg-white/[0.03]",
                  selected === chat.chat_id ? "bg-brand-500/10" : ""
                )}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-dark-100">{customerName(chat)}</span>
                  <ChevronRight size={14} className="shrink-0 text-dark-600" />
                </div>
                <p className="truncate text-xs text-dark-500">{chat.last_message_preview || "No messages"}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {chat.unread_count > 0 && (
                    <span className="rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white">
                      {chat.unread_count}
                    </span>
                  )}
                  <span className={clsx(
                    "rounded px-1.5 py-0.5 text-[10px] font-medium",
                    chat.ai_enabled ? "bg-emerald-500/15 text-emerald-300" : "bg-dark-700 text-dark-300"
                  )}>
                    AI {chat.ai_enabled ? "ON" : "OFF"}
                  </span>
                  {chat.account_name && (
                    <span className="rounded bg-sky-500/15 px-1.5 py-0.5 text-[10px] font-medium text-sky-300">
                      {chat.account_name}
                    </span>
                  )}
                  <span className="ml-auto text-[10px] text-dark-500">{formatTime(chat.last_message_at)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-white/5 bg-dark-900">
          {!selectedFromList && (
            <div className="flex flex-1 flex-col items-center justify-center text-dark-500">
              <User size={40} className="mb-3 opacity-30" />
              <p className="text-sm">Select a Telegram chat to view messages.</p>
            </div>
          )}

          {selectedFromList && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 bg-dark-900/80 px-5 py-3">
                <div>
                  <h2 className="text-sm font-semibold text-white">{customerName(selectedFromList)}</h2>
                  <p className="mt-1 text-xs text-dark-500">
                    Chat ID {selectedFromList.chat_id}
                    {selectedFromList.username ? ` / @${selectedFromList.username}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => handleSetChatAi(true).catch(console.error)}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-500"
                  >
                    AI ON
                  </button>
                  <button
                    onClick={() => handleSetChatAi(false).catch(console.error)}
                    className="rounded-lg bg-dark-700 px-3 py-1.5 text-xs font-medium text-dark-200 transition-colors hover:bg-dark-600"
                  >
                    AI OFF
                  </button>
                  <button
                    onClick={() => handleSetChatAi(undefined, true).catch(console.error)}
                    className="rounded-lg border border-white/10 bg-dark-800 px-3 py-1.5 text-xs font-medium text-dark-300 transition-colors hover:bg-dark-700"
                  >
                    Use Global
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-5">
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div key={message.id} className={clsx("flex", message.role === "user" ? "justify-start" : "justify-end")}>
                      <div className="max-w-[72%]">
                        <div className={clsx(
                          "mb-1 px-1 text-[10px]",
                          message.role === "user" ? "text-left text-dark-400" : "text-right text-sky-300"
                        )}>
                          {message.role === "user" ? "Customer" : message.source === "ai" ? "AI" : "Staff"}
                        </div>
                        <div className={clsx(
                          "rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap",
                          message.role === "user"
                            ? "rounded-tl-sm border border-white/5 bg-dark-800 text-dark-200"
                            : "rounded-tr-sm bg-sky-600 text-white"
                        )}>
                          {message.content}
                          <div className={clsx("mt-1 text-[10px]", message.role === "user" ? "text-dark-500" : "text-white/60")}>
                            {formatTime(message.created_at)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={bottomRef} />
                </div>
              </div>

              <div className="border-t border-white/5 bg-dark-900/80 px-4 py-3">
                <div className="flex gap-2">
                  <textarea
                    value={replyText}
                    onChange={(event) => setReplyText(event.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                    placeholder="Type a manual reply. Enter sends, Shift+Enter adds a newline."
                    className="flex-1 resize-none rounded-lg border border-white/10 bg-dark-800 px-3 py-2 text-sm text-dark-100 outline-none placeholder:text-dark-500 focus:ring-2 focus:ring-brand-500/50"
                  />
                  <button
                    onClick={handleReply}
                    disabled={sending || !replyText.trim()}
                    className="inline-flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
                  >
                    <Send size={16} />
                    {sending ? "Sending..." : "Send"}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, X, Guitar, UserCheck } from "lucide-react";
import clsx from "clsx";
import { ChatMessage, LeadFormData, ProductCard } from "@/lib/types";
import { canUseChatWebSocket, getConversation, sendMessage, submitLead, wsUrl } from "@/lib/api";
import { ChatWebSocket } from "@/lib/websocket";
import { useLocale } from "@/lib/i18n";
import ChatBubble from "./ChatBubble";
import ChatInput from "./ChatInput";
import LeadForm from "./LeadForm";
import TypingIndicator from "./TypingIndicator";
import ProductCards from "./ProductCards";

const VISITOR_KEY = "smiger_visitor_id";
const CONV_KEY = "smiger_conv_id";
const CUSTOMER_PROFILE_KEY = "smiger_customer_profile_v1";
const CHAT_HISTORY_KEY_PREFIX = "smiger_chat_history_v1:";

type CustomerProfile = {
  region: string;
  countryCode: string;
  phone: string;
  phoneE164: string;
};

const COUNTRY_OPTIONS = [
  { region: "CN", name: "China", code: "+86" },
  { region: "US", name: "United States", code: "+1" },
  { region: "GB", name: "United Kingdom", code: "+44" },
  { region: "DE", name: "Germany", code: "+49" },
  { region: "FR", name: "France", code: "+33" },
  { region: "IN", name: "India", code: "+91" },
  { region: "JP", name: "Japan", code: "+81" },
  { region: "KR", name: "South Korea", code: "+82" },
  { region: "BR", name: "Brazil", code: "+55" },
  { region: "AE", name: "UAE", code: "+971" },
];

function normalizePhoneNumber(countryCode: string, localPhone: string): string {
  const digits = localPhone.replace(/\D/g, "");
  const cc = countryCode.replace(/[^\d+]/g, "");
  if (!digits || !cc) return "";
  return `${cc}${digits}`;
}

function phoneBasedIds(phoneE164: string): { visitorId: string; conversationId: string } {
  const digits = phoneE164.replace(/\D/g, "");
  return {
    visitorId: `phone_${digits}`,
    conversationId: `conv_phone_${digits}`,
  };
}

type ConversationMessage = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

type ConversationPayload = {
  handoff_status?: string;
  lead_captured?: boolean;
  messages?: ConversationMessage[];
};

type PersistedMessage = Omit<ChatMessage, "timestamp"> & { timestamp: string };

function greetingMessage(content: string): ChatMessage {
  return { id: "greeting", role: "assistant", content, timestamp: new Date() };
}

function historyStorageKey(conversationId: string): string {
  return `${CHAT_HISTORY_KEY_PREFIX}${conversationId}`;
}

function parseHistory(raw: string | null): ChatMessage[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as PersistedMessage[];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((m) => m && typeof m.content === "string")
      .map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      }));
  } catch {
    return [];
  }
}

function toPersistedHistory(messages: ChatMessage[]): PersistedMessage[] {
  return messages
    .filter((m) => !m.isStreaming)
    .map((m) => ({
      ...m,
      timestamp: m.timestamp.toISOString(),
    }));
}

function normalizeRole(role: string): ChatMessage["role"] {
  if (role === "user" || role === "assistant" || role === "system") return role;
  return "assistant";
}

function mapConversationMessages(messages: ConversationMessage[] | undefined): ChatMessage[] {
  if (!Array.isArray(messages)) return [];
  return messages.map((msg) => ({
    id: msg.id,
    role: normalizeRole(msg.role),
    content: msg.content,
    timestamp: new Date(msg.created_at),
  }));
}

export default function ChatWidget() {
  const { t } = useLocale();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showLeadForm, setShowLeadForm] = useState(false);
  const [leadSubmitted, setLeadSubmitted] = useState(false);
  const [handoffActive, setHandoffActive] = useState(false);
  const [customerProfile, setCustomerProfile] = useState<CustomerProfile | null>(null);
  const [visitorId, setVisitorId] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [profileRegion, setProfileRegion] = useState("CN");
  const [profileCode, setProfileCode] = useState("+86");
  const [profilePhone, setProfilePhone] = useState("");
  const [profileError, setProfileError] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<ChatWebSocket | null>(null);
  const streamingRef = useRef("");
  const fallbackTimerRef = useRef<number | null>(null);
  const fallbackActiveRef = useRef(false);

  const profilePayload = useMemo(() => ({
    customer_region: customerProfile?.region || "",
    customer_country_code: customerProfile?.countryCode || "",
    customer_phone: customerProfile?.phoneE164 || "",
  }), [customerProfile]);

  const clearFallbackTimer = useCallback(() => {
    if (fallbackTimerRef.current !== null) {
      window.clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem(CUSTOMER_PROFILE_KEY);
    if (!raw) return;
    try {
      const saved = JSON.parse(raw) as CustomerProfile;
      if (!saved.phoneE164 || !saved.region || !saved.countryCode) return;
      setCustomerProfile(saved);
      const ids = phoneBasedIds(saved.phoneE164);
      setVisitorId(ids.visitorId);
      setConversationId(ids.conversationId);
      localStorage.setItem(VISITOR_KEY, ids.visitorId);
      localStorage.setItem(CONV_KEY, ids.conversationId);
    } catch {
      // ignore broken cache
    }
  }, []);

  useEffect(() => {
    if (!customerProfile || !conversationId || typeof window === "undefined") return;

    const key = historyStorageKey(conversationId);
    const cached = parseHistory(localStorage.getItem(key));
    if (cached.length > 0) {
      setMessages(cached);
    }

    let cancelled = false;
    const loadFromServer = async () => {
      try {
        const conversation = (await getConversation(conversationId)) as ConversationPayload;
        if (cancelled) return;

        const restored = mapConversationMessages(conversation.messages);
        if (restored.length > 0) {
          setMessages(restored);
        } else if (cached.length === 0) {
          setMessages([greetingMessage(t.chat.greeting)]);
        }

        setHandoffActive(conversation.handoff_status === "active");
        setLeadSubmitted(Boolean(conversation.lead_captured));
      } catch {
        if (cancelled) return;
        if (cached.length === 0) {
          setMessages([greetingMessage(t.chat.greeting)]);
        }
      }
    };

    loadFromServer();

    return () => {
      cancelled = true;
    };
  }, [conversationId, customerProfile, t.chat.greeting]);

  useEffect(() => {
    if (typeof window === "undefined" || !customerProfile || !conversationId) return;
    const key = historyStorageKey(conversationId);
    localStorage.setItem(key, JSON.stringify(toPersistedHistory(messages)));
  }, [conversationId, customerProfile, messages]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 50);
  }, []);

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [isOpen, messages.length, scrollToBottom]);

  const finishStreaming = useCallback(() => {
    clearFallbackTimer();
    fallbackActiveRef.current = false;
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.isStreaming) {
        const content = last.content || "";
        if (!content.trim()) return prev.slice(0, -1);
        return [...prev.slice(0, -1), { ...last, content, isStreaming: false }];
      }
      return prev;
    });
    setIsLoading(false);
  }, [clearFallbackTimer]);

  const addSystemMessage = useCallback((content: string) => {
    const msg: ChatMessage = {
      id: "sys_" + Date.now(),
      role: "system",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, msg]);
    scrollToBottom();
  }, [scrollToBottom]);

  const sendViaRest = useCallback(async (text: string) => {
    fallbackActiveRef.current = true;
    try {
      const resp = await sendMessage(text, conversationId, visitorId, profilePayload);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        const reply = resp.message || "";
        const products = resp.products || [];
        if (last?.isStreaming) {
          if (!reply.trim()) return prev.slice(0, -1);
          return [...prev.slice(0, -1), { ...last, content: reply, products, isStreaming: false }];
        }
        if (!reply.trim()) return prev;
        return [...prev, {
          id: "a_" + Date.now(),
          role: "assistant",
          content: reply,
          products,
          timestamp: new Date(),
        }];
      });
      setIsLoading(false);
      scrollToBottom();
      if (resp.lead_prompt && !leadSubmitted) {
        setTimeout(() => setShowLeadForm(true), 1500);
      }
    } catch {
      finishStreaming();
    } finally {
      clearFallbackTimer();
      fallbackActiveRef.current = false;
    }
  }, [clearFallbackTimer, conversationId, finishStreaming, leadSubmitted, profilePayload, scrollToBottom, visitorId]);

  const connectWs = useCallback(() => {
    if (!canUseChatWebSocket()) return;
    if (wsRef.current?.isConnected || !conversationId) return;
    const ws = new ChatWebSocket(
      wsUrl(conversationId),
      (token) => {
        if (fallbackActiveRef.current) return;
        clearFallbackTimer();
        streamingRef.current += token;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.isStreaming) return [...prev.slice(0, -1), { ...last, content: streamingRef.current }];
          return prev;
        });
        scrollToBottom();
      },
      (data) => {
        if (fallbackActiveRef.current) {
          fallbackActiveRef.current = false;
          return;
        }
        clearFallbackTimer();
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.isStreaming) {
            if (!(last.content || "").trim()) {
              return prev.slice(0, -1);
            }
            return [...prev.slice(0, -1), { ...last, isStreaming: false }];
          }
          return prev;
        });
        setIsLoading(false);
        if (data.handoff_active) setHandoffActive(true);
        if (data.lead_prompt && !leadSubmitted) setTimeout(() => setShowLeadForm(true), 1500);
      },
      () => {
        wsRef.current = null;
        if (fallbackTimerRef.current === null) finishStreaming();
      },
      () => {
        wsRef.current = null;
        if (fallbackTimerRef.current === null) finishStreaming();
      },
      (items: ProductCard[]) => {
        setMessages((prev) => {
          const lastAssistantIdx = prev.map((m, i) => ({ m, i })).filter((x) => x.m.role === "assistant").pop();
          if (lastAssistantIdx) {
            const updated = [...prev];
            updated[lastAssistantIdx.i] = { ...updated[lastAssistantIdx.i], products: items };
            return updated;
          }
          return prev;
        });
        scrollToBottom();
      },
      () => {
        setHandoffActive(true);
        addSystemMessage(t.chat.handoffNotice ?? "感谢您的咨询，人工客服将尽快联系您。");
        setTimeout(() => setShowLeadForm(true), 800);
      },
      (content: string) => {
        const agentMsg: ChatMessage = {
          id: "agent_" + Date.now(),
          role: "assistant",
          content,
          timestamp: new Date(),
          isAgent: true,
        };
        setMessages((prev) => [...prev, agentMsg]);
        scrollToBottom();
      },
      (content: string) => {
        if (content === "sales_connected") {
          addSystemMessage(t.chat.salesConnected ?? "销售代表已接入对话。");
        } else if (content === "handoff_resolved") {
          setHandoffActive(false);
          addSystemMessage(t.chat.handoffResolved ?? "人工服务结束，AI 助手继续为您服务。");
        }
      },
    );
    ws.connect().catch(() => {
      wsRef.current = null;
      if (fallbackTimerRef.current === null) finishStreaming();
    });
    wsRef.current = ws;
  }, [conversationId, leadSubmitted, scrollToBottom, finishStreaming, addSystemMessage, t, clearFallbackTimer]);

  useEffect(() => {
    if (!isOpen || !customerProfile || !conversationId) return;
    connectWs();
  }, [connectWs, conversationId, customerProfile, isOpen]);

  const handleProfileSubmit = useCallback(() => {
    const phoneE164 = normalizePhoneNumber(profileCode, profilePhone);
    if (!phoneE164) {
      setProfileError("请输入有效手机号");
      return;
    }
    const profile: CustomerProfile = {
      region: profileRegion,
      countryCode: profileCode,
      phone: profilePhone.trim(),
      phoneE164,
    };
    const ids = phoneBasedIds(phoneE164);

    setCustomerProfile(profile);
    setVisitorId(ids.visitorId);
    setConversationId(ids.conversationId);
    setProfileError("");
    setMessages([]);
    clearFallbackTimer();
    fallbackActiveRef.current = false;
    streamingRef.current = "";
    wsRef.current?.close();
    wsRef.current = null;
    setIsLoading(false);
    setHandoffActive(false);
    setLeadSubmitted(false);
    setShowLeadForm(false);

    if (typeof window !== "undefined") {
      localStorage.setItem(CUSTOMER_PROFILE_KEY, JSON.stringify(profile));
      localStorage.setItem(VISITOR_KEY, ids.visitorId);
      localStorage.setItem(CONV_KEY, ids.conversationId);
    }
  }, [clearFallbackTimer, profileCode, profilePhone, profileRegion]);

  const handleSend = useCallback(
    (text: string) => {
      if (!customerProfile || !conversationId || !visitorId) return;

      clearFallbackTimer();
      fallbackActiveRef.current = false;

      const userMsg: ChatMessage = {
        id: "u_" + Date.now(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      scrollToBottom();
      streamingRef.current = "";

      const humanMode = handoffActive;
      if (!humanMode) {
        setIsLoading(true);
        const assistantMsg: ChatMessage = {
          id: "a_" + Date.now(),
          role: "assistant",
          content: "",
          timestamp: new Date(),
          isStreaming: true,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        setIsLoading(false);
      }

      if (!canUseChatWebSocket()) {
        void sendViaRest(text);
        return;
      }

      if (!wsRef.current?.isConnected) {
        connectWs();
      }
      wsRef.current?.send(text, visitorId, "en", profilePayload);

      if (humanMode) {
        return;
      }

      fallbackTimerRef.current = window.setTimeout(async () => {
        await sendViaRest(text);
        wsRef.current?.close();
        wsRef.current = null;
      }, 12000);
    },
    [clearFallbackTimer, connectWs, conversationId, customerProfile, handoffActive, profilePayload, scrollToBottom, sendViaRest, visitorId]
  );

  const handleLeadSubmit = async (data: LeadFormData) => {
    try {
      await submitLead({ ...data, conversation_id: conversationId });
      setLeadSubmitted(true);
      setShowLeadForm(false);
      setMessages((prev) => [...prev, {
        id: "lead_thanks",
        role: "assistant",
        content: t.chat.leadThanks,
        timestamp: new Date(),
      }]);
    } catch {
      alert(t.chat.submitError);
    }
  };

  useEffect(() => () => {
    clearFallbackTimer();
    wsRef.current?.close();
    wsRef.current = null;
  }, [clearFallbackTimer]);

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          "fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-xl flex items-center justify-center transition-all duration-300 hover:scale-105",
          isOpen ? "bg-dark-700 hover:bg-dark-600" : "bg-brand-500 hover:bg-brand-600"
        )}
      >
        {isOpen ? <X size={24} className="text-white" /> : <MessageCircle size={24} className="text-white" />}
        {!isOpen && <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-brand-400 rounded-full animate-pulse-ring" />}
      </button>

      <div
        className={clsx(
          "fixed bottom-24 right-6 z-50 w-[640px] max-w-[calc(100vw-1.5rem)] bg-dark-900 rounded-2xl shadow-2xl border border-white/10 flex flex-col overflow-hidden transition-all duration-300",
          isOpen ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 translate-y-4 pointer-events-none"
        )}
        style={{ height: "min(820px, calc(100vh - 5rem))" }}
      >
        <div className="bg-gradient-to-r from-brand-700 to-brand-600 px-5 py-4 text-white flex items-center gap-3">
          <div className="w-10 h-10 bg-white/15 rounded-full flex items-center justify-center">
            {handoffActive ? <UserCheck size={20} /> : <Guitar size={20} />}
          </div>
          <div>
            <h3 className="font-semibold text-sm">{t.chat.headerTitle}</h3>
            <p className="text-xs text-white/70">
              {handoffActive ? (t.chat.humanMode ?? "人工客服已接入") : t.chat.headerStatus}
            </p>
          </div>
        </div>

        {!customerProfile ? (
          <div className="flex-1 bg-dark-950 p-5 space-y-4">
            <div className="text-sm text-dark-200 font-medium">开始对话前，请先填写手机号</div>
            <p className="text-xs text-dark-400">用于客服按国家/地区分流，并建立手机号唯一会话记录。</p>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={`${profileRegion}|${profileCode}`}
                onChange={(e) => {
                  const [region, code] = e.target.value.split("|");
                  setProfileRegion(region);
                  setProfileCode(code);
                }}
                className="bg-dark-800 text-dark-100 rounded-lg border border-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
              >
                {COUNTRY_OPTIONS.map((c) => (
                  <option key={`${c.region}|${c.code}`} value={`${c.region}|${c.code}`}>
                    {c.region} ({c.code}) {c.name}
                  </option>
                ))}
              </select>
              <input
                value={profilePhone}
                onChange={(e) => setProfilePhone(e.target.value)}
                placeholder="Phone number"
                className="bg-dark-800 text-dark-100 rounded-lg border border-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
              />
            </div>
            {profileError && <p className="text-xs text-red-400">{profileError}</p>}
            <button
              type="button"
              onClick={handleProfileSubmit}
              className="w-full py-2.5 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 transition-colors"
            >
              开始聊天
            </button>
          </div>
        ) : (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3 bg-dark-950">
              {messages.map((msg) => (
                <div key={msg.id} className="space-y-2">
                  {msg.role === "system" ? (
                    <div className="flex justify-center">
                      <span className="bg-brand-500/10 text-brand-400 text-xs px-3 py-1.5 rounded-full border border-brand-500/20">
                        {msg.content}
                      </span>
                    </div>
                  ) : (
                    <>
                      <ChatBubble message={msg} />
                      {msg.products && msg.products.length > 0 && (
                        <ProductCards items={msg.products} />
                      )}
                    </>
                  )}
                </div>
              ))}
              {isLoading && messages[messages.length - 1]?.role === "user" && <TypingIndicator />}
              {showLeadForm && !leadSubmitted && (
                <LeadForm conversationId={conversationId} onSubmit={handleLeadSubmit} onClose={() => setShowLeadForm(false)} />
              )}
            </div>

            <ChatInput onSend={handleSend} disabled={isLoading || !customerProfile} />
          </>
        )}
      </div>
    </>
  );
}

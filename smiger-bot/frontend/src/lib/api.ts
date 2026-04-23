import type { ProductCard } from "./types";

const STATIC_API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export function getApiBase(): string {
  if (STATIC_API_BASE) return STATIC_API_BASE;
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:8000";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("admin_token") : null;
  const headers: Record<string, string> = { ...(options?.headers as Record<string, string>) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options?.body instanceof FormData)) headers["Content-Type"] = "application/json";

  const res = await fetch(`${getApiBase()}${path}`, { ...options, headers });
  if (!res.ok) {
    if ((res.status === 401 || res.status === 403) && typeof window !== "undefined") {
      localStorage.removeItem("admin_token");
      if (!window.location.pathname.includes("/admin/login")) {
        window.location.href = "/admin/login";
      }
    }
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail);
  }
  return res.json();
}

// Auth
export const login = (username: string, password: string) =>
  request<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

// Chat (REST fallback)
export const sendMessage = (
  message: string,
  conversationId?: string,
  visitorId?: string,
  extras?: {
    customer_region?: string;
    customer_country_code?: string;
    customer_phone?: string;
  }
) =>
  request<{
    conversation_id: string;
    message: string;
    confidence: number;
    lead_prompt: boolean;
    products?: ProductCard[];
  }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId, visitor_id: visitorId, ...extras }),
  });

// Leads
export const submitLead = (data: {
  conversation_id?: string;
  name?: string;
  company?: string;
  email: string;
  phone?: string;
  country?: string;
  requirement?: string;
}) => request("/api/leads", { method: "POST", body: JSON.stringify(data) });

export const getLeads = (skip = 0, limit = 50) => request<any[]>(`/api/leads?skip=${skip}&limit=${limit}`);

// Knowledge
export const getDocuments = () => request<any[]>("/api/knowledge/documents");
export const deleteDocument = (id: string) => request(`/api/knowledge/documents/${id}`, { method: "DELETE" });
export const getKnowledgeStats = () => request<any>("/api/knowledge/stats");

export const uploadDocument = async (file: File) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("admin_token") : null;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiBase()}/api/knowledge/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

// Conversations
export const getConversations = (skip = 0, limit = 50) =>
  request<any[]>(`/api/chat/conversations?skip=${skip}&limit=${limit}`);

export const getConversation = (id: string) => request<any>(`/api/chat/conversations/${id}`);
export const clearConversationHistory = () =>
  request<any>("/api/chat/conversations", { method: "DELETE" });

// Dashboard
export const getDashboardStats = () => request<any>("/api/dashboard/stats");

// API Settings
export const getApiSettings = () => request<any>("/api/admin/settings");
export const updateApiSettings = (data: any) =>
  request<any>("/api/admin/settings", { method: "PUT", body: JSON.stringify(data) });
export const testApiConnections = () => request<any>("/api/admin/settings/test", { method: "POST" });

// Customer Service Data
export const getCsRecords = (params?: { status?: string; channel?: string; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.channel) q.set("channel", params.channel);
  if (params?.limit) q.set("limit", String(params.limit));
  return request<any[]>(`/api/admin/cs/records?${q.toString()}`);
};
export const createCsRecord = (data: any) =>
  request<any>("/api/admin/cs/records", { method: "POST", body: JSON.stringify(data) });
export const getCsStats = () => request<any>("/api/admin/cs/stats");
export const importCsRecords = async (file: File) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("admin_token") : null;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiBase()}/api/admin/cs/records/import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

// FAQ
export const getFaqEntries = (params?: { category?: string; q?: string }) => {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.q) query.set("q", params.q);
  return request<any[]>(`/api/faq/entries?${query.toString()}`);
};
export const createFaqEntry = (data: any) =>
  request<any>("/api/faq/entries", { method: "POST", body: JSON.stringify(data) });
export const updateFaqEntry = (id: number, data: any) =>
  request<any>(`/api/faq/entries/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteFaqEntry = (id: number) =>
  request<any>(`/api/faq/entries/${id}`, { method: "DELETE" });
export const getFaqCategories = () => request<any[]>("/api/faq/categories");
export const syncFaqToKnowledge = () => request<any>("/api/faq/sync", { method: "POST" });
export const importFaqFile = async (file: File) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("admin_token") : null;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiBase()}/api/faq/import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

// Handoff
export const getHandoffCount = () => request<{ pending: number; active: number }>("/api/admin/handoff/count");
export const getHandoffList = (status?: string, all?: boolean) => {
  const q = new URLSearchParams();
  if (status) q.set("status", status);
  if (all) q.set("all", "true");
  const qs = q.toString();
  return request<any[]>(`/api/admin/handoff/list${qs ? `?${qs}` : ""}`);
};
export const getHandoffMessages = (convId: string) =>
  request<any[]>(`/api/admin/handoff/${convId}/messages`);
export const acceptHandoff = (convId: string, telegramAccountName?: string) =>
  request<any>(`/api/admin/handoff/${convId}/accept`, {
    method: "POST",
    body: JSON.stringify({ telegram_account_name: telegramAccountName || null }),
  });
export const updateHandoffChannel = (convId: string, telegramAccountName?: string) =>
  request<any>(`/api/admin/handoff/${convId}/channel`, {
    method: "POST",
    body: JSON.stringify({ telegram_account_name: telegramAccountName || null }),
  });
export const replyHandoff = (convId: string, message: string) =>
  request<any>(`/api/admin/handoff/${convId}/reply`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
export const resolveHandoff = (convId: string) =>
  request<any>(`/api/admin/handoff/${convId}/resolve`, { method: "POST" });

// Telegram Support
export const getTelegramSupportSettings = () =>
  request<any>("/api/admin/telegram-support/settings");
export const updateTelegramSupportSettings = (data: any) =>
  request<any>("/api/admin/telegram-support/settings", { method: "PUT", body: JSON.stringify(data) });
export const getTelegramSupportChats = () =>
  request<any[]>("/api/admin/telegram-support/chats");
export const getTelegramSupportChat = (chatId: string, markRead = true) =>
  request<any>(`/api/admin/telegram-support/chats/${encodeURIComponent(chatId)}?mark_read=${markRead ? "true" : "false"}`);
export const markTelegramSupportChatRead = (chatId: string) =>
  request<any>(`/api/admin/telegram-support/chats/${encodeURIComponent(chatId)}/read`, { method: "POST" });
export const updateTelegramSupportChatAi = (
  chatId: string,
  aiEnabled?: boolean,
  clearOverride = false
) =>
  request<any>(`/api/admin/telegram-support/chats/${encodeURIComponent(chatId)}/ai`, {
    method: "POST",
    body: JSON.stringify({ ai_enabled: aiEnabled, clear_override: clearOverride }),
  });
export const replyTelegramSupportChat = (chatId: string, text: string) =>
  request<any>(`/api/admin/telegram-support/chats/${encodeURIComponent(chatId)}/messages`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });

// WebSocket URL helper
export function wsUrl(conversationId: string): string {
  const base = getApiBase().replace(/^http/, "ws");
  return `${base}/api/chat/ws/${conversationId}`;
}

export function canUseChatWebSocket(): boolean {
  if (typeof window === "undefined") return true;

  try {
    const apiUrl = new URL(getApiBase(), window.location.href);
    const pageUrl = new URL(window.location.href);

    if (apiUrl.origin === pageUrl.origin) return true;

    // Cloudflare quick tunnels create separate public hosts for frontend/backend.
    // In that cross-origin tunnel setup, REST is much more reliable than WSS.
    const apiIsTunnel = apiUrl.hostname.endsWith(".trycloudflare.com");
    const pageIsTunnel = pageUrl.hostname.endsWith(".trycloudflare.com");
    return !(apiIsTunnel || pageIsTunnel);
  } catch {
    return true;
  }
}

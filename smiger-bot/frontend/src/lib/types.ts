export interface ProductCard {
  model: string;
  name: string;
  name_cn?: string;
  brand: string;
  category: string;
  price: number | null;
  colors: string[];
  url: string;
  thumbnail: string;
  specs?: Record<string, string>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  products?: ProductCard[];
  isAgent?: boolean;
}

export interface LeadFormData {
  name: string;
  company: string;
  email: string;
  phone: string;
  country: string;
  requirement: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface ConversationItem {
  id: string;
  visitor_id: string;
  language: string;
  turn_count: number;
  lead_captured: boolean;
  handoff_status?: string;
  created_at: string;
  message_preview: string | null;
}

export interface HandoffConversation {
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
  telegram_account_name?: string | null;
  created_at: string;
  updated_at: string;
  message_preview: string | null;
}

export interface HandoffCount {
  pending: number;
  active: number;
}

export interface LeadItem {
  id: string;
  conversation_id: string | null;
  name: string | null;
  company: string | null;
  email: string;
  phone: string | null;
  country: string | null;
  requirement: string | null;
  source: string;
  created_at: string;
}

export interface DashboardStats {
  total_conversations: number;
  total_messages: number;
  total_leads: number;
  total_documents: number;
  conversations_today: number;
  leads_today: number;
}

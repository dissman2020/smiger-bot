from datetime import datetime

from pydantic import BaseModel, Field


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    visitor_id: str | None = None
    language: str = "en"
    customer_region: str | None = None
    customer_country_code: str | None = None
    customer_phone: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    confidence: float | None = None
    lead_prompt: bool = False
    products: list[dict] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    confidence: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    visitor_id: str
    customer_region: str | None = None
    customer_country_code: str | None = None
    customer_phone: str | None = None
    language: str
    turn_count: int
    lead_captured: bool
    handoff_status: str = "none"
    handoff_at: datetime | None = None
    telegram_account_name: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    id: str
    visitor_id: str
    customer_region: str | None = None
    customer_country_code: str | None = None
    customer_phone: str | None = None
    language: str
    turn_count: int
    lead_captured: bool
    handoff_status: str = "none"
    created_at: datetime
    message_preview: str | None = None

    model_config = {"from_attributes": True}


# ---------- Knowledge ----------
class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeStats(BaseModel):
    total_documents: int
    total_chunks: int
    ready_documents: int


# ---------- Leads ----------
class LeadCreate(BaseModel):
    conversation_id: str | None = None
    name: str | None = None
    company: str | None = None
    email: str
    phone: str | None = None
    country: str | None = None
    requirement: str | None = None


class LeadOut(BaseModel):
    id: str
    conversation_id: str | None
    name: str | None
    company: str | None
    email: str
    phone: str | None
    country: str | None
    requirement: str | None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Auth ----------
class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Dashboard ----------
class DashboardStats(BaseModel):
    total_conversations: int
    total_messages: int
    total_leads: int
    total_documents: int
    conversations_today: int
    leads_today: int


# ---------- Customer Service Records ----------
class CsRecordCreate(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    channel: str = "manual"
    subject: str | None = None
    content: str
    agent_name: str | None = None
    status: str = "open"
    tags: str | None = None
    external_id: str | None = None


class CsRecordOut(BaseModel):
    id: str
    customer_name: str | None
    customer_email: str | None
    customer_phone: str | None
    channel: str
    subject: str | None
    content: str
    agent_name: str | None
    status: str
    tags: str | None
    external_id: str | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class CsStats(BaseModel):
    total: int
    open: int
    resolved: int
    channels: dict[str, int]


# ---------- FAQ ----------
class FaqEntryCreate(BaseModel):
    category: str = "general"
    question_cn: str
    question_en: str
    answer_cn: str
    answer_en: str
    tags: list[str] | None = None
    extra_metadata: dict | None = None
    sort_order: int = 0
    is_active: bool = True


class FaqEntryUpdate(BaseModel):
    category: str | None = None
    question_cn: str | None = None
    question_en: str | None = None
    answer_cn: str | None = None
    answer_en: str | None = None
    tags: list[str] | None = None
    extra_metadata: dict | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class FaqEntryOut(BaseModel):
    id: int
    category: str
    question_cn: str
    question_en: str
    answer_cn: str
    answer_en: str
    tags: list[str] | None
    extra_metadata: dict | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class FaqSyncResult(BaseModel):
    total_entries: int
    total_chunks: int


# ---------- Handoff ----------
class HandoffCount(BaseModel):
    pending: int
    active: int


class HandoffReply(BaseModel):
    message: str


class HandoffAcceptRequest(BaseModel):
    telegram_account_name: str | None = None


class HandoffConversationItem(BaseModel):
    id: str
    visitor_id: str
    customer_region: str | None = None
    customer_country_code: str | None = None
    customer_phone: str | None = None
    language: str
    turn_count: int
    lead_captured: bool
    handoff_status: str
    handoff_at: datetime | None
    whatsapp_tag: str | None = None
    telegram_account_name: str | None = None
    created_at: datetime
    updated_at: datetime
    message_preview: str | None = None

    model_config = {"from_attributes": True}

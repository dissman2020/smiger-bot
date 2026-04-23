import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="processing")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    visitor_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    customer_region: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    customer_country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String, default="en")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)  # 乐观锁版本号
    lead_captured: Mapped[bool] = mapped_column(Boolean, default=False)
    handoff_status: Mapped[str] = mapped_column(String, default="none")
    handoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whatsapp_tag: Mapped[str | None] = mapped_column(String(8), nullable=True)
    telegram_account_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handoff_notice_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")
    lead: Mapped["Lead | None"] = relationship(back_populates="conversation", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str | None] = mapped_column(String, ForeignKey("conversations.id"), nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, default="chatbot")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped["Conversation | None"] = relationship(back_populates="lead")


class CsRecord(Base):
    """Customer-service interaction records imported from external CS systems."""
    __tablename__ = "cs_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    customer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String, nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    channel: Mapped[str] = mapped_column(String, default="manual")
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")
    tags: Mapped[str | None] = mapped_column(String, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FaqEntry(Base):
    """Structured bilingual FAQ knowledge entries."""
    __tablename__ = "faq_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), index=True, default="general")
    question_cn: Mapped[str] = mapped_column(Text, nullable=False)
    question_en: Mapped[str] = mapped_column(Text, nullable=False)
    answer_cn: Mapped[str] = mapped_column(Text, nullable=False)
    answer_en: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=_utcnow)


class TelegramSupportSetting(Base):
    """Runtime settings for direct Telegram customer support."""
    __tablename__ = "telegram_support_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_history: Mapped[int] = mapped_column(Integer, default=12)
    system_prompt: Mapped[str] = mapped_column(
        Text,
        default=(
            "You are a professional, polite, concise Telegram support assistant. "
            "Reply in Chinese by default unless the user clearly uses another language. "
            "If you are unsure, say so instead of making things up."
        ),
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TelegramSupportChat(Base):
    """A private Telegram chat with a customer."""
    __tablename__ = "telegram_support_chats"

    chat_id: Mapped[str] = mapped_column(String, primary_key=True)
    account_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_enabled_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    messages: Mapped[list["TelegramSupportMessage"]] = relationship(
        back_populates="chat",
        order_by="TelegramSupportMessage.created_at",
    )


class TelegramSupportMessage(Base):
    """Message history for direct Telegram customer support."""
    __tablename__ = "telegram_support_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    chat_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("telegram_support_chats.chat_id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, default="telegram")
    telegram_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chat: Mapped["TelegramSupportChat"] = relationship(back_populates="messages")


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in [
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS handoff_status VARCHAR DEFAULT 'none'",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS handoff_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS whatsapp_tag VARCHAR(8)",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS customer_region VARCHAR(16)",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS customer_country_code VARCHAR(8)",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(32)",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS telegram_account_name VARCHAR(64)",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS handoff_notice_sent BOOLEAN DEFAULT FALSE",
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 0",
            "CREATE INDEX IF NOT EXISTS idx_conversations_customer_region ON conversations (customer_region)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_customer_phone ON conversations (customer_phone)",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

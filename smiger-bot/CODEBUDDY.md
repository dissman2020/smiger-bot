# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

Smiger AI Pre-sales Bot - A 7x24 AI-powered pre-sales chatbot for Smiger Guitars (维音乐器), built with RAG (Retrieval-Augmented Generation) technology.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, WebSocket |
| Frontend | Next.js 14, Tailwind CSS, TypeScript |
| LLM | DeepSeek-V3.2 via SophNet API (configurable) |
| Vector DB | ChromaDB |
| Database | PostgreSQL (SQLAlchemy async) |
| Cache | Redis |
| Deploy | Docker Compose |

## Common Commands

### Docker Compose (Recommended)

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop all services
docker compose down

# Load seed data
docker compose exec backend python -m app.seed

# Database migrations (handled automatically via init_db)
docker compose exec backend python -c "from app.models.database import init_db; import asyncio; asyncio.run(init_db())"
```

### Local Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Load seed data
python -m app.seed
```

### Local Frontend Development

```bash
cd frontend
npm install
npm run dev        # Development server on http://localhost:3000
npm run build      # Production build
```

### Testing

No test suite is currently configured. To add tests, use pytest:

```bash
cd backend
pip install pytest pytest-asyncio
pytest
```

## Architecture Overview

### Backend Structure (`backend/app/`)

```
backend/app/
├── main.py              # FastAPI entry point, router registration
├── config.py            # Pydantic Settings, all env vars
├── seed.py              # Seed data loader (products, FAQs)
├── api/                 # REST + WebSocket endpoints
│   ├── chat.py          # Chat endpoints (REST + WebSocket /api/chat/ws/{id})
│   ├── auth.py          # JWT authentication
│   ├── knowledge.py     # Document upload/management
│   ├── leads.py         # Lead capture API
│   ├── dashboard.py     # Stats endpoints
│   ├── faq.py           # FAQ management
│   ├── handoff.py       # Human handoff system
│   └── *_webhook.py     # Telegram, WhatsApp, Google Chat webhooks
├── core/                # Business logic
│   ├── rag_engine.py    # ChromaDB vector search, document chunking
│   ├── llm_gateway.py   # LLM API client (SophNet/OpenAI compatible)
│   ├── conversation.py  # ConversationManager, chat flow orchestration
│   ├── prompts.py       # System prompts, fallback responses
│   ├── mcp_tools.py     # Tool definitions for LLM function calling
│   ├── business_rules.py# Lead capture logic, conversation policies
│   ├── product_index.py # Product catalog search
│   └── telegram_*.py    # Telegram bot runtime (polling/webhook)
├── models/              # Database models
│   ├── database.py      # SQLAlchemy models, async engine, init_db()
│   └── schemas.py       # Pydantic request/response models
└── services/            # Supporting services
    ├── document.py      # PDF, DOCX, XLSX parsing
    ├── embedding.py     # Text embedding interface
    ├── faq_parser.py    # FAQ JSON import/export
    └── lead_service.py  # Lead management utilities
```

### Frontend Structure (`frontend/src/`)

```
frontend/src/
├── app/                 # Next.js App Router
│   ├── page.tsx         # Chat widget page
│   ├── layout.tsx       # Root layout
│   └── admin/           # Admin dashboard pages
├── components/          # React components
└── lib/                 # Utilities, API clients, types
```

### Key Architectural Patterns

1. **RAG Pipeline** (`core/rag_engine.py`, `core/conversation.py`):
   - Documents chunked and stored in ChromaDB with embeddings
   - User queries embedded and matched against knowledge base
   - Top-K results injected into LLM prompt as context
   - Similarity threshold configurable via `SIMILARITY_THRESHOLD`

2. **Conversation Flow** (`core/conversation.py`):
   - `ConversationManager` orchestrates multi-turn chat
   - History stored in Redis (24h TTL)
   - Lead capture triggered after `LEAD_TRIGGER_TURN` turns
   - Supports tool calling via `mcp_tools.py`

3. **Multi-Channel Support**:
   - Web chat (WebSocket at `/api/chat/ws/{id}`)
   - Telegram Bot (polling or webhook mode)
   - WhatsApp Business API
   - Google Chat webhook
   - All channels share the same conversation/lead backend

4. **Database Models** (`models/database.py`):
   - `Conversation`: Chat sessions with handoff status
   - `Message`: Individual chat messages
   - `Lead`: Captured lead information
   - `Document`: Uploaded knowledge base files
   - `FaqEntry`: Structured bilingual Q&A
   - `CsRecord`: External customer service imports
   - `TelegramSupportChat`: Direct Telegram support conversations

5. **Configuration** (`config.py`):
   - All settings via environment variables
   - `.env` file loaded automatically
   - Key vars: `LLM_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Admin login (returns JWT) |
| POST | `/api/chat` | Non-streaming chat |
| WS | `/api/chat/ws/{id}` | Streaming WebSocket chat |
| GET | `/api/chat/conversations` | List conversations (admin) |
| GET | `/api/chat/conversations/{id}` | Get conversation detail |
| POST | `/api/knowledge/upload` | Upload document |
| GET | `/api/knowledge/documents` | List documents |
| DELETE | `/api/knowledge/documents/{id}` | Delete document + chunks |
| POST | `/api/leads` | Submit lead form |
| GET | `/api/leads` | List leads (admin) |
| GET | `/api/leads/export` | Export CSV |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/health` | Health check |

## Environment Variables

See `.env.example` for all options. Key variables:

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | SophNet/OpenAI API key |
| `LLM_BASE_URL` | Default: SophNet API |
| `LLM_MODEL` | Default: DeepSeek-V3.2 |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin panel credentials |
| `TELEGRAM_ENABLED` / `TELEGRAM_BOT_TOKEN` | Telegram bot config |
| `WHATSAPP_ENABLED` / `WHATSAPP_*` | WhatsApp Business API |

## Development Notes

- Backend uses SQLAlchemy 2.0 with async PostgreSQL (`asyncpg`)
- ChromaDB runs in-process with persistence to `CHROMA_PERSIST_DIR`
- Redis used for conversation history cache (24h expiration)
- Document parsing supports: PDF, DOCX, XLSX, TXT
- Frontend is a static Next.js export (no SSR)
- Admin panel at `/admin` with JWT authentication

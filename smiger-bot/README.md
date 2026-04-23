# Smiger AI Pre-sales Bot

A 7x24 AI-powered pre-sales chatbot for Smiger Guitars (维音乐器), built with RAG (Retrieval-Augmented Generation) technology.

## Features

- **RAG Knowledge Engine** — Upload product docs, FAQs, and sales materials; the AI answers based on your knowledge base
- **Proactive Sales Strategy** — Not just Q&A; the bot guides conversations toward lead capture
- **Streaming Chat** — Real-time token-by-token response via WebSocket
- **Lead Capture** — Embedded contact forms triggered naturally during conversation
- **Admin Dashboard** — Manage knowledge base, view conversations, track leads, export data
- **Seed Data Included** — Pre-loaded with Smiger guitar product catalog and FAQs

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, WebSocket |
| Frontend | Next.js 14, Tailwind CSS |
| LLM | OpenAI GPT-4o (configurable) |
| Vector DB | ChromaDB |
| Database | PostgreSQL |
| Cache | Redis |
| Deploy | Docker Compose |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### 1. Clone and configure

```bash
cd smiger-bot
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Launch with Docker Compose

```bash
docker compose up -d --build
```

This starts all services:
- **Frontend**: http://localhost:3000 (chat interface)
- **Backend API**: http://localhost:8000 (API + WebSocket)
- **API Docs**: http://localhost:8000/docs (Swagger UI)

### 3. Load seed data

```bash
docker compose exec backend python -m app.seed
```

### 4. Access the admin panel

Navigate to http://localhost:3000/admin and log in:
- Username: `admin`
- Password: `smiger2026`

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
cp ../.env.example ../.env
# Edit .env: set DATABASE_URL to your local PostgreSQL, REDIS_URL to local Redis

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Load seed data

```bash
cd backend
python -m app.seed
```

## Project Structure

```
smiger-bot/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Environment configuration
│   │   ├── seed.py           # Seed data loader
│   │   ├── api/              # REST + WebSocket endpoints
│   │   ├── core/             # RAG engine, LLM gateway, prompts, conversation manager
│   │   ├── models/           # Database models + Pydantic schemas
│   │   └── services/         # Document parsing, embedding, lead management
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages (chat + admin)
│   │   ├── components/       # React components (chat widget, admin UI)
│   │   └── lib/              # API client, WebSocket, types
│   ├── package.json
│   └── Dockerfile
├── seed_data/                # Pre-loaded guitar knowledge
│   ├── products.json         # Product catalog
│   └── faq.json              # Frequently asked questions
├── docker-compose.yml        # One-command deployment
└── .env.example              # Environment template
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Admin login |
| POST | `/api/chat` | Send chat message (REST) |
| WS | `/api/chat/ws/{id}` | Streaming chat (WebSocket) |
| GET | `/api/chat/conversations` | List conversations |
| GET | `/api/chat/conversations/{id}` | Get conversation detail |
| POST | `/api/knowledge/upload` | Upload document |
| GET | `/api/knowledge/documents` | List documents |
| DELETE | `/api/knowledge/documents/{id}` | Delete document |
| GET | `/api/knowledge/stats` | Knowledge base stats |
| POST | `/api/leads` | Submit lead |
| GET | `/api/leads` | List leads |
| GET | `/api/leads/export` | Export leads as CSV |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/health` | Health check |

## Configuration

All settings are configured via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Your OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-4o` | LLM model for chat |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `ADMIN_USERNAME` | `admin` | Admin panel username |
| `ADMIN_PASSWORD` | `smiger2026` | Admin panel password |
| `SIMILARITY_THRESHOLD` | `0.3` | RAG confidence threshold |
| `LEAD_TRIGGER_TURN` | `3` | Turns before prompting lead capture |

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_settings, auth, chat, cs_data, dashboard, faq, gchat_webhook, handoff, knowledge, leads, telegram_support, telegram_webhook, whatsapp_webhook
from app.core.telegram_runtime import configure_telegram_runtime, shutdown_telegram_runtime
from app.models.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Smiger AI Pre-sales Bot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(leads.router)
app.include_router(dashboard.router)
app.include_router(api_settings.router)
app.include_router(cs_data.router)
app.include_router(faq.router)
app.include_router(handoff.router)
app.include_router(telegram_support.router)
app.include_router(whatsapp_webhook.router)
app.include_router(telegram_webhook.router)
app.include_router(gchat_webhook.router)


@app.on_event("startup")
async def startup():
    await init_db()
    await configure_telegram_runtime()


@app.on_event("shutdown")
async def shutdown():
    shutdown_telegram_runtime()


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "smiger-bot"}

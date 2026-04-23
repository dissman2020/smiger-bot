"""API configuration management."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import verify_token
from app.config import settings
from app.core import gchat_client, llm_gateway, telegram_client, whatsapp_client
from app.core.telegram_accounts import (
    get_active_telegram_account,
    get_active_account_name,
    list_telegram_accounts,
    set_telegram_accounts,
    sync_legacy_telegram_fields_from_active,
    upsert_active_telegram_account,
)
from app.core.telegram_runtime import get_telegram_webhook_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/settings", tags=["settings"])


class TelegramAccountConfig(BaseModel):
    name: str
    enabled: bool = True
    bot_token: str = ""
    admin_chat_id: str = ""
    webhook_secret: str = ""


class ApiSettingsOut(BaseModel):
    llm_base_url: str
    llm_model: str
    embedding_url: str
    embedding_easyllm_id: str
    embedding_dimensions: int
    llm_api_key_set: bool

    whatsapp_enabled: bool = False
    whatsapp_phone_number_id: str = ""
    whatsapp_admin_phone: str = ""
    whatsapp_template_name: str = ""
    whatsapp_access_token_set: bool = False
    whatsapp_verify_token: str = ""

    telegram_enabled: bool = False
    telegram_active_account: str = ""
    telegram_accounts: list[TelegramAccountConfig] = []
    telegram_account_count: int = 0
    telegram_admin_chat_id: str = ""
    telegram_bot_token_set: bool = False
    telegram_webhook_secret: str = ""

    gchat_enabled: bool = False
    gchat_webhook_url: str = ""
    gchat_verify_token: str = ""


class ApiSettingsUpdate(BaseModel):
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    embedding_url: str | None = None
    embedding_easyllm_id: str | None = None
    embedding_dimensions: int | None = None

    whatsapp_enabled: bool | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_verify_token: str | None = None
    whatsapp_admin_phone: str | None = None
    whatsapp_template_name: str | None = None

    telegram_enabled: bool | None = None
    telegram_active_account: str | None = None
    telegram_accounts: list[TelegramAccountConfig] | None = None
    # Legacy single-account fields kept for backward compatibility.
    telegram_bot_token: str | None = None
    telegram_admin_chat_id: str | None = None
    telegram_webhook_secret: str | None = None

    gchat_enabled: bool | None = None
    gchat_webhook_url: str | None = None
    gchat_verify_token: str | None = None


class TestResult(BaseModel):
    llm_ok: bool
    llm_message: str
    embedding_ok: bool
    embedding_message: str
    whatsapp_ok: bool = False
    whatsapp_message: str = ""
    telegram_ok: bool = False
    telegram_message: str = ""
    gchat_ok: bool = False
    gchat_message: str = ""


def _current() -> ApiSettingsOut:
    sync_legacy_telegram_fields_from_active()
    active = get_active_telegram_account(require_ready=False)
    accounts = list_telegram_accounts()
    active_name = active["name"] if active else get_active_account_name()

    return ApiSettingsOut(
        llm_base_url=settings.LLM_BASE_URL,
        llm_model=settings.LLM_MODEL,
        embedding_url=settings.EMBEDDING_URL,
        embedding_easyllm_id=settings.EMBEDDING_EASYLLM_ID,
        embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        llm_api_key_set=bool(settings.LLM_API_KEY),

        whatsapp_enabled=settings.WHATSAPP_ENABLED,
        whatsapp_phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        whatsapp_admin_phone=settings.WHATSAPP_ADMIN_PHONE,
        whatsapp_template_name=settings.WHATSAPP_TEMPLATE_NAME,
        whatsapp_access_token_set=bool(settings.WHATSAPP_ACCESS_TOKEN),
        whatsapp_verify_token=settings.WHATSAPP_VERIFY_TOKEN,

        telegram_enabled=settings.TELEGRAM_ENABLED,
        telegram_active_account=active_name,
        telegram_accounts=[TelegramAccountConfig(**item) for item in accounts],
        telegram_account_count=len(accounts),
        telegram_admin_chat_id=(active["admin_chat_id"] if active else ""),
        telegram_bot_token_set=bool(active and active["bot_token"]),
        telegram_webhook_secret=(active["webhook_secret"] if active else ""),

        gchat_enabled=settings.GCHAT_ENABLED,
        gchat_webhook_url=settings.GCHAT_WEBHOOK_URL,
        gchat_verify_token=settings.GCHAT_VERIFY_TOKEN,
    )


@router.get("", response_model=ApiSettingsOut)
async def get_settings(_: str = Depends(verify_token)):
    return _current()


@router.put("", response_model=ApiSettingsOut)
async def update_settings(body: ApiSettingsUpdate, _: str = Depends(verify_token)):
    telegram_changed = False

    if body.llm_api_key is not None:
        settings.LLM_API_KEY = body.llm_api_key
    if body.llm_base_url is not None:
        settings.LLM_BASE_URL = body.llm_base_url
    if body.llm_model is not None:
        settings.LLM_MODEL = body.llm_model
    if body.embedding_url is not None:
        settings.EMBEDDING_URL = body.embedding_url
    if body.embedding_easyllm_id is not None:
        settings.EMBEDDING_EASYLLM_ID = body.embedding_easyllm_id
    if body.embedding_dimensions is not None:
        settings.EMBEDDING_DIMENSIONS = body.embedding_dimensions

    if body.whatsapp_enabled is not None:
        settings.WHATSAPP_ENABLED = body.whatsapp_enabled
    if body.whatsapp_phone_number_id is not None:
        settings.WHATSAPP_PHONE_NUMBER_ID = body.whatsapp_phone_number_id
    if body.whatsapp_access_token is not None:
        settings.WHATSAPP_ACCESS_TOKEN = body.whatsapp_access_token
    if body.whatsapp_verify_token is not None:
        settings.WHATSAPP_VERIFY_TOKEN = body.whatsapp_verify_token
    if body.whatsapp_admin_phone is not None:
        settings.WHATSAPP_ADMIN_PHONE = body.whatsapp_admin_phone
    if body.whatsapp_template_name is not None:
        settings.WHATSAPP_TEMPLATE_NAME = body.whatsapp_template_name

    if body.telegram_enabled is not None:
        settings.TELEGRAM_ENABLED = body.telegram_enabled
        telegram_changed = True

    if body.telegram_active_account is not None:
        settings.TELEGRAM_ACTIVE_ACCOUNT = body.telegram_active_account.strip()
        telegram_changed = True

    if body.telegram_accounts is not None:
        set_telegram_accounts(
            [item.model_dump() for item in body.telegram_accounts],
            active_account=body.telegram_active_account,
        )
        telegram_changed = True

    legacy_telegram_payload = any([
        body.telegram_bot_token is not None,
        body.telegram_admin_chat_id is not None,
        body.telegram_webhook_secret is not None,
    ])
    if legacy_telegram_payload:
        upsert_active_telegram_account(
            bot_token=body.telegram_bot_token,
            admin_chat_id=body.telegram_admin_chat_id,
            webhook_secret=body.telegram_webhook_secret,
        )
        telegram_changed = True
    else:
        sync_legacy_telegram_fields_from_active()

    if body.gchat_enabled is not None:
        settings.GCHAT_ENABLED = body.gchat_enabled
    if body.gchat_webhook_url is not None:
        settings.GCHAT_WEBHOOK_URL = body.gchat_webhook_url
    if body.gchat_verify_token is not None:
        settings.GCHAT_VERIFY_TOKEN = body.gchat_verify_token

    llm_gateway._llm_client = None
    llm_gateway._http_client = None

    if telegram_changed and settings.TELEGRAM_ENABLED:
        mode = (settings.TELEGRAM_MODE or "polling").strip().lower()
        if mode == "webhook":
            webhook_url = get_telegram_webhook_url()
            if webhook_url:
                results = await telegram_client.set_webhook_for_enabled_accounts(webhook_url)
                if not results:
                    logger.warning("No enabled Telegram account found for webhook reconfiguration")
                for item in results:
                    if item["ok"]:
                        logger.info(
                            "Telegram webhook reconfigured for %s: %s",
                            item["name"],
                            webhook_url,
                        )
                    else:
                        logger.warning(
                            "Telegram webhook reconfiguration failed for %s: %s",
                            item["name"],
                            item["description"],
                        )

    logger.info("API settings updated via admin panel")
    return _current()


@router.post("/test", response_model=TestResult)
async def test_connections(_: str = Depends(verify_token)):
    llm_ok, llm_msg = False, ""
    emb_ok, emb_msg = False, ""

    try:
        client = httpx.AsyncClient(timeout=15.0)
        r = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            json={"model": settings.LLM_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
        )
        if r.status_code == 200:
            llm_ok, llm_msg = True, "Connected"
        else:
            llm_msg = f"HTTP {r.status_code}: {r.text[:200]}"
        await client.aclose()
    except Exception as e:
        llm_msg = str(e)[:200]

    try:
        client = httpx.AsyncClient(timeout=15.0)
        r = await client.post(
            settings.EMBEDDING_URL,
            json={"easyllm_id": settings.EMBEDDING_EASYLLM_ID, "input_texts": ["test"], "dimensions": settings.EMBEDDING_DIMENSIONS},
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
        )
        if r.status_code == 200:
            emb_ok, emb_msg = True, "Connected"
        else:
            emb_msg = f"HTTP {r.status_code}: {r.text[:200]}"
        await client.aclose()
    except Exception as e:
        emb_msg = str(e)[:200]

    wa_ok, wa_msg = False, "Not configured"
    if settings.WHATSAPP_ENABLED:
        try:
            wa_ok, wa_msg = await whatsapp_client.test_connection()
        except Exception as e:
            wa_msg = str(e)[:200]

    tg_ok, tg_msg = False, "Not configured"
    if settings.TELEGRAM_ENABLED:
        try:
            tg_ok, tg_msg = await telegram_client.test_connection()
        except Exception as e:
            tg_msg = str(e)[:200]

    gc_ok, gc_msg = False, "Not configured"
    if settings.GCHAT_ENABLED:
        try:
            gc_ok, gc_msg = await gchat_client.test_connection()
        except Exception as e:
            gc_msg = str(e)[:200]

    return TestResult(
        llm_ok=llm_ok,
        llm_message=llm_msg,
        embedding_ok=emb_ok,
        embedding_message=emb_msg,
        whatsapp_ok=wa_ok,
        whatsapp_message=wa_msg,
        telegram_ok=tg_ok,
        telegram_message=tg_msg,
        gchat_ok=gc_ok,
        gchat_message=gc_msg,
    )

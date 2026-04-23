"""Telegram runtime selection for polling vs webhook deployments."""
from __future__ import annotations

import asyncio
import logging
import os

from app.config import settings
from app.core import telegram_client
from app.core.telegram_poller import start_polling, stop_polling

logger = logging.getLogger(__name__)

_WEBHOOK_PATH = "/api/webhook/telegram"


def _telegram_mode() -> str:
    mode = (settings.TELEGRAM_MODE or "polling").strip().lower()
    return mode or "polling"


def _public_base_url() -> str:
    base_url = settings.TELEGRAM_WEBHOOK_BASE_URL.strip()
    if base_url:
        return base_url.rstrip("/")

    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if render_url:
        return render_url.rstrip("/")

    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_domain:
        if railway_domain.startswith("http://") or railway_domain.startswith("https://"):
            return railway_domain.rstrip("/")
        return f"https://{railway_domain.rstrip('/')}"

    return ""


def get_telegram_webhook_url() -> str:
    base_url = _public_base_url()
    if not base_url:
        return ""
    return f"{base_url}{_WEBHOOK_PATH}"


async def configure_telegram_runtime() -> None:
    """Start polling locally or register a webhook on public deployments."""
    if not telegram_client.is_enabled():
        logger.info("Telegram runtime skipped: not enabled")
        return

    mode = _telegram_mode()
    if mode == "webhook":
        webhook_url = get_telegram_webhook_url()
        if not webhook_url:
            logger.warning(
                "Telegram webhook mode enabled but no public URL found. "
                "Set TELEGRAM_WEBHOOK_BASE_URL or use a platform-provided public domain."
            )
            return

        results = await telegram_client.set_webhook_for_enabled_accounts(webhook_url)
        if not results:
            logger.warning("No enabled Telegram account available for webhook registration")
            return

        for item in results:
            if item["ok"]:
                logger.info("Telegram webhook configured for %s: %s", item["name"], webhook_url)
            else:
                logger.warning(
                    "Telegram webhook registration failed for %s: %s",
                    item["name"],
                    item["description"],
                )
        return

    if mode != "polling":
        logger.warning("Unknown TELEGRAM_MODE=%s, defaulting to polling", settings.TELEGRAM_MODE)

    asyncio.create_task(start_polling())


def shutdown_telegram_runtime() -> None:
    if _telegram_mode() == "polling":
        stop_polling()

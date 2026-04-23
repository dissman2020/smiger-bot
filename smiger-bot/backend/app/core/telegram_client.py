"""Telegram Bot API client for admin notifications and message forwarding."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.core.telegram_accounts import (
    get_account_by_name,
    get_active_telegram_account,
    list_enabled_telegram_accounts,
)

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"


def _resolve_account(
    account_name: str | None = None,
    require_ready: bool = True,
) -> dict[str, Any] | None:
    if account_name:
        return get_account_by_name(
            account_name,
            require_ready=require_ready,
            enabled_only=True,
        )
    return get_active_telegram_account(require_ready=require_ready)


def _bot_url(account: dict[str, Any], method: str) -> str:
    return f"{_API_BASE}/bot{account['bot_token']}/{method}"


def is_enabled(account_name: str | None = None) -> bool:
    if not settings.TELEGRAM_ENABLED:
        return False
    return bool(_resolve_account(account_name=account_name, require_ready=True))


async def _post_for_account(
    account: dict[str, Any],
    method: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(_bot_url(account, method), json=payload)
        data = resp.json()
        if not data.get("ok"):
            logger.warning("Telegram API error(%s): %s", account["name"], data)
        return data


async def _post(
    method: str,
    payload: dict[str, Any],
    account_name: str | None = None,
) -> dict[str, Any]:
    if not settings.TELEGRAM_ENABLED:
        return {"ok": False, "description": "Telegram disabled"}

    account = _resolve_account(account_name=account_name, require_ready=True)
    if not account:
        return {"ok": False, "description": "Telegram account not configured"}
    return await _post_for_account(account, method, payload)


async def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    account_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return await _post("sendMessage", payload, account_name=account_name)


async def notify_new_lead(
    lead_name: str | None,
    email: str,
    phone: str | None,
    company: str | None,
    country: str | None,
    requirement: str | None,
    account_name: str | None = None,
) -> bool:
    """Send new lead notification to a Telegram admin account."""
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not settings.TELEGRAM_ENABLED or not account:
        return False

    lines = [
        "New lead",
        f"Name: {lead_name or '-'}",
        f"Email: {email}",
        f"Phone: {phone or '-'}",
        f"Company: {company or '-'}",
        f"Country/Region: {country or '-'}",
    ]
    if requirement:
        lines.append(f"Requirement: {requirement[:300]}")

    try:
        result = await send_message(
            account["admin_chat_id"],
            "\n".join(lines),
            account_name=account["name"],
        )
        if result.get("ok"):
            logger.info("Telegram new-lead notification sent (%s)", account["name"])
            return True
        return False
    except Exception:
        logger.exception("Telegram new-lead notification failed (%s)", account["name"])
        return False


async def notify_handoff(
    conv_tag: str,
    visitor_id: str,
    message_preview: str,
    account_name: str | None = None,
    customer_phone: str | None = None,
    customer_region: str | None = None,
) -> bool:
    """Notify admin about a new handoff request via Telegram."""
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not settings.TELEGRAM_ENABLED or not account:
        return False

    parts = [
        f"New handoff request [#{conv_tag}]",
        f"Visitor: {visitor_id}",
    ]
    if customer_region:
        parts.append(f"Region: {customer_region}")
    if customer_phone:
        parts.append(f"Phone: {customer_phone}")
    parts.extend([
        f"Message: {message_preview[:200]}",
        "---",
        f"Reply with tag: #{conv_tag}",
    ])
    text = "\n".join(parts)

    try:
        result = await send_message(
            account["admin_chat_id"],
            text,
            account_name=account["name"],
        )
        if result.get("ok"):
            logger.info("Telegram handoff notification sent [#%s] via %s", conv_tag, account["name"])
            return True
        return False
    except Exception:
        logger.exception("Telegram handoff notification failed [#%s] via %s", conv_tag, account["name"])
        return False


async def forward_user_message(
    conv_tag: str,
    content: str,
    account_name: str | None = None,
) -> bool:
    """Forward a user's web chat message to Telegram admin."""
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not settings.TELEGRAM_ENABLED or not account:
        return False

    text = f"[#{conv_tag}] User: {content}"
    try:
        result = await send_message(
            account["admin_chat_id"],
            text,
            parse_mode="",
            account_name=account["name"],
        )
        return bool(result.get("ok"))
    except Exception:
        logger.exception("Telegram forward failed [#%s] via %s", conv_tag, account["name"])
        return False


async def set_webhook(url: str, account_name: str | None = None) -> tuple[bool, str]:
    """Register a webhook URL with Telegram."""
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not account:
        return False, "Telegram account is not configured"

    payload: dict[str, Any] = {"url": url}
    if account.get("webhook_secret"):
        payload["secret_token"] = account["webhook_secret"]
    try:
        result = await _post_for_account(account, "setWebhook", payload)
        ok = bool(result.get("ok", False))
        desc = str(result.get("description", ""))
        return ok, desc
    except Exception as e:
        return False, str(e)[:200]


async def set_webhook_for_enabled_accounts(url: str) -> list[dict[str, Any]]:
    """Register webhook for all enabled Telegram accounts."""
    results: list[dict[str, Any]] = []
    for account in list_enabled_telegram_accounts(require_ready=True):
        ok, description = await set_webhook(url, account_name=account["name"])
        results.append({
            "name": account["name"],
            "ok": ok,
            "description": description,
        })
    return results


async def delete_webhook(
    drop_pending: bool = False,
    account_name: str | None = None,
) -> tuple[bool, str]:
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not account:
        return False, "Telegram account is not configured"
    try:
        result = await _post_for_account(
            account,
            "deleteWebhook",
            {"drop_pending_updates": drop_pending},
        )
        return bool(result.get("ok", False)), str(result.get("description", ""))
    except Exception as e:
        return False, str(e)[:200]


async def get_updates(
    offset: int | None = None,
    timeout: int = 30,
    account_name: str | None = None,
) -> list[dict[str, Any]]:
    """Long-poll for updates (used by polling mode)."""
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not settings.TELEGRAM_ENABLED or not account:
        return []

    params: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        async with httpx.AsyncClient(timeout=float(timeout + 10)) as client:
            resp = await client.post(_bot_url(account, "getUpdates"), json=params)
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
            logger.warning("Telegram getUpdates error(%s): %s", account["name"], data)
            return []
    except Exception:
        logger.exception("Telegram getUpdates request failed (%s)", account["name"])
        return []


async def test_connection(account_name: str | None = None) -> tuple[bool, str]:
    """Quick connectivity test via getMe."""
    account = _resolve_account(account_name=account_name, require_ready=True)
    if not settings.TELEGRAM_ENABLED:
        return False, "Telegram disabled"
    if not account:
        return False, "Telegram account is not configured"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_bot_url(account, "getMe"))
            data = resp.json()
            if data.get("ok"):
                bot = data["result"]
                return True, f"Connected as @{bot.get('username', 'unknown')} ({account['name']})"
            return False, str(data.get("description", "Unknown error"))
    except Exception as e:
        return False, str(e)[:200]

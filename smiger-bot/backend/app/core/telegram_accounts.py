"""Helpers for multi-account Telegram Bot configuration."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

TelegramAccount = dict[str, Any]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _to_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    text = _clean(value).lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _dedupe_names(accounts: list[TelegramAccount]) -> list[TelegramAccount]:
    used: set[str] = set()
    normalized: list[TelegramAccount] = []

    for i, account in enumerate(accounts):
        base = _clean(account.get("name")) or f"account-{i + 1}"
        name = base
        suffix = 2
        while name in used:
            name = f"{base}-{suffix}"
            suffix += 1
        used.add(name)

        normalized.append({
            "name": name,
            "enabled": _to_bool(account.get("enabled"), True),
            "bot_token": _clean(account.get("bot_token")),
            "admin_chat_id": _clean(account.get("admin_chat_id")),
            "webhook_secret": _clean(account.get("webhook_secret")),
        })

    return normalized


def list_telegram_accounts(include_disabled: bool = True) -> list[TelegramAccount]:
    """Return configured Telegram accounts, with legacy single-account fallback."""
    raw = _clean(settings.TELEGRAM_BOT_ACCOUNTS)
    parsed: list[TelegramAccount] = []

    if raw:
        try:
            payload = json.loads(raw)
            if isinstance(payload, list):
                candidates = [item for item in payload if isinstance(item, dict)]
                parsed = _dedupe_names(candidates)  # type: ignore[arg-type]
            else:
                logger.warning("TELEGRAM_BOT_ACCOUNTS must be a JSON array")
        except Exception:
            logger.warning("Invalid TELEGRAM_BOT_ACCOUNTS JSON, using legacy fields")

    if parsed:
        accounts = parsed
    else:
        token = _clean(settings.TELEGRAM_BOT_TOKEN)
        chat_id = _clean(settings.TELEGRAM_ADMIN_CHAT_ID)
        secret = _clean(settings.TELEGRAM_WEBHOOK_SECRET)
        accounts = [{
            "name": "default",
            "enabled": True,
            "bot_token": token,
            "admin_chat_id": chat_id,
            "webhook_secret": secret,
        }] if (token or chat_id or secret) else []

    if include_disabled:
        return accounts
    return [a for a in accounts if a.get("enabled", True)]


def list_enabled_telegram_accounts(require_ready: bool = True) -> list[TelegramAccount]:
    accounts = list_telegram_accounts(include_disabled=False)
    if not require_ready:
        return accounts
    return [a for a in accounts if a["bot_token"] and a["admin_chat_id"]]


def get_active_account_name() -> str:
    return _clean(settings.TELEGRAM_ACTIVE_ACCOUNT)


def get_account_by_name(
    name: str | None,
    require_ready: bool = True,
    enabled_only: bool = True,
) -> TelegramAccount | None:
    target = _clean(name)
    if not target:
        return None

    accounts = list_telegram_accounts(include_disabled=not enabled_only)
    account = next((a for a in accounts if a["name"] == target), None)
    if not account:
        return None
    if enabled_only and not account.get("enabled", True):
        return None
    if require_ready and (not account["bot_token"] or not account["admin_chat_id"]):
        return None
    return account


def get_account_by_admin_chat_id(
    admin_chat_id: str | None,
    require_ready: bool = True,
    enabled_only: bool = True,
) -> TelegramAccount | None:
    target = _clean(admin_chat_id)
    if not target:
        return None

    accounts = list_telegram_accounts(include_disabled=not enabled_only)
    for account in accounts:
        if _clean(account.get("admin_chat_id")) != target:
            continue
        if enabled_only and not account.get("enabled", True):
            continue
        if require_ready and (not account["bot_token"] or not account["admin_chat_id"]):
            continue
        return account
    return None


def get_account_by_webhook_secret(
    webhook_secret: str | None,
    require_ready: bool = True,
    enabled_only: bool = True,
) -> TelegramAccount | None:
    target = _clean(webhook_secret)
    if not target:
        return None

    accounts = list_telegram_accounts(include_disabled=not enabled_only)
    for account in accounts:
        if _clean(account.get("webhook_secret")) != target:
            continue
        if enabled_only and not account.get("enabled", True):
            continue
        if require_ready and (not account["bot_token"] or not account["admin_chat_id"]):
            continue
        return account
    return None


def get_active_telegram_account(require_ready: bool = True) -> TelegramAccount | None:
    accounts = list_telegram_accounts()
    if not accounts:
        return None

    active_name = get_active_account_name()
    account = next((a for a in accounts if a["name"] == active_name), None)
    if account is None or not account.get("enabled", True):
        account = next((a for a in accounts if a.get("enabled", True)), None)
    if account is None:
        account = accounts[0]

    if not require_ready:
        return account

    if account.get("enabled", True) and account["bot_token"] and account["admin_chat_id"]:
        return account

    return next(
        (
            a for a in accounts
            if a.get("enabled", True) and a["bot_token"] and a["admin_chat_id"]
        ),
        None,
    )


def set_telegram_accounts(
    accounts: list[dict[str, Any]],
    active_account: str | None = None,
) -> None:
    normalized = _dedupe_names(accounts)
    settings.TELEGRAM_BOT_ACCOUNTS = json.dumps(normalized, ensure_ascii=False)

    preferred = _clean(active_account) or get_active_account_name()
    if preferred and any(a["name"] == preferred for a in normalized):
        settings.TELEGRAM_ACTIVE_ACCOUNT = preferred
    else:
        enabled = next((a["name"] for a in normalized if a.get("enabled", True)), None)
        settings.TELEGRAM_ACTIVE_ACCOUNT = enabled or (normalized[0]["name"] if normalized else "")

    sync_legacy_telegram_fields_from_active()


def upsert_active_telegram_account(
    bot_token: str | None = None,
    admin_chat_id: str | None = None,
    webhook_secret: str | None = None,
) -> None:
    accounts = list_telegram_accounts()
    active_name = get_active_account_name()
    if not active_name:
        active_name = accounts[0]["name"] if accounts else "default"

    index = next((i for i, a in enumerate(accounts) if a["name"] == active_name), -1)
    if index < 0:
        accounts.append({
            "name": active_name,
            "enabled": True,
            "bot_token": "",
            "admin_chat_id": "",
            "webhook_secret": "",
        })
        index = len(accounts) - 1

    if bot_token is not None:
        accounts[index]["bot_token"] = _clean(bot_token)
    if admin_chat_id is not None:
        accounts[index]["admin_chat_id"] = _clean(admin_chat_id)
    if webhook_secret is not None:
        accounts[index]["webhook_secret"] = _clean(webhook_secret)

    set_telegram_accounts(accounts, active_account=active_name)


def sync_legacy_telegram_fields_from_active() -> None:
    """Keep legacy single-account fields aligned for backward compatibility."""
    account = get_active_telegram_account(require_ready=False)
    if account is None:
        settings.TELEGRAM_BOT_TOKEN = ""
        settings.TELEGRAM_ADMIN_CHAT_ID = ""
        settings.TELEGRAM_WEBHOOK_SECRET = ""
        return

    settings.TELEGRAM_BOT_TOKEN = _clean(account.get("bot_token"))
    settings.TELEGRAM_ADMIN_CHAT_ID = _clean(account.get("admin_chat_id"))
    settings.TELEGRAM_WEBHOOK_SECRET = _clean(account.get("webhook_secret"))

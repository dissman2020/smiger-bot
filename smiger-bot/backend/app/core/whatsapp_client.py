"""WhatsApp Business Cloud API client for admin notifications and message forwarding."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_API_VERSION = "v20.0"


def _base_url() -> str:
    return f"https://graph.facebook.com/{_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def is_enabled() -> bool:
    return bool(
        settings.WHATSAPP_ENABLED
        and settings.WHATSAPP_PHONE_NUMBER_ID
        and settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_ADMIN_PHONE
    )


async def _post(payload: dict[str, Any]) -> dict[str, Any]:
    """Fire a request to the WhatsApp Cloud API. Returns the JSON response."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(_base_url(), json=payload, headers=_headers())
        data = resp.json()
        if resp.status_code != 200:
            logger.warning("WhatsApp API error %s: %s", resp.status_code, data)
        return data


async def send_text(to: str, body: str) -> dict[str, Any]:
    """Send a plain text message."""
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    })


async def send_template(to: str, template_name: str, params: list[str] | None = None) -> dict[str, Any]:
    """Send a template message (needed to initiate a conversation outside the 24h window)."""
    components: list[dict] = []
    if params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in params],
        })
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": components,
        },
    })


async def notify_handoff(conv_tag: str, visitor_id: str, message_preview: str) -> bool:
    """Notify admin about a new handoff request. Returns True on success."""
    if not is_enabled():
        return False

    to = settings.WHATSAPP_ADMIN_PHONE
    body = (
        f"🔔 新客户咨询 [#{conv_tag}]\n"
        f"访客: {visitor_id}\n"
        f"消息: {message_preview[:200]}\n"
        f"---\n"
        f"回复时请带上标记 #{conv_tag}"
    )

    template_name = settings.WHATSAPP_TEMPLATE_NAME
    if template_name:
        try:
            result = await send_template(to, template_name, [conv_tag, visitor_id, message_preview[:100]])
            if result.get("messages"):
                logger.info("WhatsApp template notification sent for [#%s]", conv_tag)
                return True
        except Exception:
            logger.exception("WhatsApp template send failed, falling back to text")

    try:
        result = await send_text(to, body)
        if result.get("messages"):
            logger.info("WhatsApp text notification sent for [#%s]", conv_tag)
            return True
        logger.warning("WhatsApp notification may have failed: %s", result)
        return False
    except Exception:
        logger.exception("WhatsApp notification failed for [#%s]", conv_tag)
        return False


async def forward_user_message(conv_tag: str, content: str) -> bool:
    """Forward a user's web chat message to admin's WhatsApp."""
    if not is_enabled():
        return False

    to = settings.WHATSAPP_ADMIN_PHONE
    body = f"[#{conv_tag}] 用户: {content}"

    try:
        result = await send_text(to, body)
        return bool(result.get("messages"))
    except Exception:
        logger.exception("WhatsApp forward failed for [#%s]", conv_tag)
        return False


async def test_connection() -> tuple[bool, str]:
    """Quick connectivity test. Returns (ok, message)."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        return False, "Phone Number ID or Access Token not configured"
    try:
        url = f"https://graph.facebook.com/{_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_headers())
            if resp.status_code == 200:
                return True, "Connected"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)[:200]

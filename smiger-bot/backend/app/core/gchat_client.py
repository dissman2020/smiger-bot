"""Google Chat (Workspace) client — sends notifications via Incoming Webhook URL."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(settings.GCHAT_ENABLED and settings.GCHAT_WEBHOOK_URL)


async def _post_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            settings.GCHAT_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        if resp.status_code not in (200, 201):
            logger.warning("Google Chat webhook error %s: %s", resp.status_code, data)
        return data


async def send_text(text: str) -> dict[str, Any]:
    return await _post_webhook({"text": text})


async def send_card(title: str, subtitle: str, fields: list[tuple[str, str]]) -> dict[str, Any]:
    """Send a card message via Google Chat webhook for richer formatting."""
    widgets = [
        {"decoratedText": {"topLabel": label, "text": value}}
        for label, value in fields
    ]
    payload = {
        "cardsV2": [{
            "cardId": "notification",
            "card": {
                "header": {"title": title, "subtitle": subtitle},
                "sections": [{"widgets": widgets}],
            },
        }],
    }
    return await _post_webhook(payload)


async def notify_new_lead(lead_name: str | None, email: str, phone: str | None,
                          company: str | None, country: str | None,
                          requirement: str | None) -> bool:
    if not is_enabled():
        return False

    fields = [
        ("姓名", lead_name or "未填写"),
        ("邮箱", email),
        ("电话", phone or "未填写"),
        ("公司", company or "未填写"),
        ("国家", country or "未填写"),
    ]
    if requirement:
        fields.append(("需求", requirement[:300]))

    try:
        result = await send_card("📋 新客户线索", "来自 Smiger 智能客服", fields)
        if result.get("name"):
            logger.info("Google Chat new-lead notification sent")
            return True
        return False
    except Exception:
        logger.exception("Google Chat new-lead notification failed")
        return False


async def notify_handoff(conv_tag: str, visitor_id: str, message_preview: str) -> bool:
    if not is_enabled():
        return False

    text = (
        f"🔔 *新客户咨询* [#{conv_tag}]\n"
        f"访客: {visitor_id}\n"
        f"消息: {message_preview[:200]}\n"
        f"---\n"
        f"回复时请带上标记 `#{conv_tag}`"
    )

    try:
        result = await send_text(text)
        if result.get("name"):
            logger.info("Google Chat handoff notification sent for [#%s]", conv_tag)
            return True
        return False
    except Exception:
        logger.exception("Google Chat handoff notification failed for [#%s]", conv_tag)
        return False


async def forward_user_message(conv_tag: str, content: str) -> bool:
    if not is_enabled():
        return False

    text = f"[#{conv_tag}] 用户: {content}"

    try:
        result = await send_text(text)
        return bool(result.get("name"))
    except Exception:
        logger.exception("Google Chat forward failed for [#%s]", conv_tag)
        return False


async def test_connection() -> tuple[bool, str]:
    """Quick connectivity test by sending a test message."""
    if not settings.GCHAT_WEBHOOK_URL:
        return False, "Webhook URL not configured"
    try:
        result = await send_text("✅ Smiger Bot 连接测试成功")
        if result.get("name"):
            return True, "Connected"
        return False, f"Unexpected response: {str(result)[:200]}"
    except Exception as e:
        return False, str(e)[:200]

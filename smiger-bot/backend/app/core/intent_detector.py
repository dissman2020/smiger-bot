"""Detect purchase intent from conversation text.

Only triggers on EXPLICIT procurement actions or direct requests for human
support — NOT on general enquiries about price, samples, or shipping.
"""
from __future__ import annotations

import re

# Explicit procurement / order placement
_ORDER_CN = [
    "下单", "签约", "签合同", "确认订单", "正式订购",
    "我要订", "我要下单", "准备下单", "确认采购",
    "发合同", "打款", "付定金", "付全款",
]

_ORDER_EN = [
    "place order", "place an order", "confirm order", "confirm the order",
    "sign contract", "sign the contract",
    "send me invoice", "send invoice", "proforma invoice",
    "ready to order", "proceed with order", "finalize order",
    "i want to order", "we want to order",
    "make the payment", "pay the deposit",
]

# Direct request for human agent
_HUMAN_CN = [
    "转人工", "人工客服", "人工服务", "真人客服", "真人服务",
    "找人工", "接人工", "我要人工", "请转人工",
    "找客服", "联系客服", "联系销售", "找销售",
    "和人聊", "跟人聊", "和真人聊",
]

_HUMAN_EN = [
    "talk to a human", "talk to a person", "talk to someone",
    "speak to a human", "speak to a person", "speak to someone",
    "human agent", "real person", "live agent", "live support",
    "transfer to agent", "connect me to",
    "i need a human", "i want a human",
    "contact sales", "speak to sales",
]

_PATTERN_ORDER_CN = re.compile("|".join(re.escape(k) for k in _ORDER_CN), re.IGNORECASE)
_PATTERN_ORDER_EN = re.compile(r"\b(" + "|".join(re.escape(k) for k in _ORDER_EN) + r")\b", re.IGNORECASE)
_PATTERN_HUMAN_CN = re.compile("|".join(re.escape(k) for k in _HUMAN_CN), re.IGNORECASE)
_PATTERN_HUMAN_EN = re.compile(r"\b(" + "|".join(re.escape(k) for k in _HUMAN_EN) + r")\b", re.IGNORECASE)


def detect_purchase_intent(user_message: str, ai_reply: str = "") -> bool:
    """Return True only when the USER explicitly wants to place an order or
    requests a human agent. AI replies are intentionally ignored to avoid
    false positives from the bot mentioning payment/order terms."""
    text = user_message
    return bool(
        _PATTERN_ORDER_CN.search(text)
        or _PATTERN_ORDER_EN.search(text)
        or _PATTERN_HUMAN_CN.search(text)
        or _PATTERN_HUMAN_EN.search(text)
    )

"""Extract product model references from AI replies and return structured card data."""
from __future__ import annotations

import re
import logging
from typing import Any

from app.core.product_index import load_products, lookup_by_model, get_all_models, get_verified_models

logger = logging.getLogger(__name__)

_MODEL_PATTERN: re.Pattern | None = None


def _get_pattern() -> re.Pattern:
    """Build regex that only matches models with verified website pages."""
    global _MODEL_PATTERN
    if _MODEL_PATTERN is None:
        load_products()
        models = get_verified_models()
        if not models:
            models = get_all_models()
        escaped = sorted((re.escape(m) for m in models), key=len, reverse=True)
        _MODEL_PATTERN = re.compile(
            r"\b(" + "|".join(escaped) + r")\b",
            re.IGNORECASE,
        )
    return _MODEL_PATTERN


def extract_product_cards(text: str, max_cards: int = 4) -> list[dict[str, Any]]:
    """Scan *text* for product model references and return structured card data.

    Returns at most *max_cards* unique products with fields the frontend
    needs to render rich product cards.
    """
    pattern = _get_pattern()
    matches = pattern.findall(text)
    if not matches:
        return []

    seen: set[str] = set()
    cards: list[dict[str, Any]] = []

    for raw_model in matches:
        key = raw_model.upper().strip()
        if key in seen:
            continue
        seen.add(key)

        product = lookup_by_model(raw_model)
        if not product:
            continue

        # Only show cards for products with a verified website page
        page_url = product.get("image_url")
        if not page_url:
            continue

        card: dict[str, Any] = {
            "model": product.get("model", raw_model),
            "name": product.get("name_en", product.get("type", "")),
            "name_cn": product.get("name_cn", ""),
            "brand": product.get("brand", "Smiger"),
            "category": product.get("category", product.get("_category", "")),
            "price": product.get("price_usd"),
            "colors": product.get("colors", []),
            "url": page_url,
            "thumbnail": page_url,
        }

        for spec_key in ("top", "body", "pickups", "frets", "size", "fingerboard",
                         "body_finish", "back_sides", "bridge", "neck"):
            val = product.get(spec_key)
            if val:
                card.setdefault("specs", {})[spec_key] = val

        cards.append(card)
        if len(cards) >= max_cards:
            break

    return cards



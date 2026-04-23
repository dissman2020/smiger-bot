"""In-memory product index built from seed_data/products.json.

Provides fast model lookup, keyword search, and category filtering
without requiring vector DB queries.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_products: list[dict] = []
_model_index: dict[str, dict] = {}
_category_index: dict[str, list[dict]] = {}
_loaded = False

_PRODUCT_FILES = [
    "electric_guitars.json",
    "electric_guitars_luxars.json",
    "acoustic_guitars_1.json",
    "acoustic_guitars_2.json",
    "acoustic_guitars_3.json",
    "classical_guitars.json",
    "ukuleles.json",
    "accessories.json",
    "products.json",
]

_TIER_KEYWORDS = {
    "beginner": ["beginner", "入门", "entry-level", "16-35"],
    "mid_range": ["mid-range", "中档", "mid-range sm", "43-62"],
    "high_end": ["high-end", "高档", "high-grade", "65-215", "premium", "all-solid", "solid top"],
    "electric": ["electric guitar", "电吉他", "st style", "lp style", "tl style", "headless", "modern"],
    "acoustic": ["acoustic guitar", "民谣吉他", "folk guitar"],
    "classical": ["classical guitar", "古典吉他", "flamenco"],
    "bass": ["bass", "贝斯"],
    "ukulele": ["ukulele", "尤克里里", "guitarlele"],
    "accessories": ["accessories", "配件", "strings", "tuning", "effects", "amps", "cases", "picks", "wireless", "speakers", "tuners", "parts"],
    "oem": ["oem", "odm", "定制服务"],
}


def _find_seed_data() -> str:
    """Locate the seed_data directory."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "seed_data"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "seed_data"),
        "/app/seed_data",
    ]
    for c in candidates:
        p = os.path.normpath(c)
        if os.path.isdir(p):
            return p
    return candidates[0]


def _add_product(product: dict) -> None:
    """Add a single product dict to the indices."""
    _products.append(product)

    model_key = product.get("model", "").upper().strip()
    if model_key:
        _model_index[model_key] = product
        normalized = re.sub(r"[^A-Z0-9]", "", model_key)
        if normalized != model_key:
            _model_index[normalized] = product

    cat = product.get("category", "")
    sub = product.get("subcategory", "")
    tier = _classify_tier(f"{cat} {sub}")
    product["_tier"] = tier
    _category_index.setdefault(tier, []).append(product)


def _load_flat_file(path: str) -> None:
    """Load a flat JSON array of product dicts."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for product in data:
        _add_product(product)


def _load_legacy_file(path: str) -> None:
    """Load the old category-grouped products.json format."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for category_block in data:
        cat_name = category_block.get("category", "")
        tier = _classify_tier(cat_name)

        if "info" in category_block:
            info = category_block["info"]
            info["_category"] = cat_name
            info["_tier"] = tier
            info["_is_info"] = True
            _category_index.setdefault(tier, []).append(info)
            continue

        for product in category_block.get("products", []):
            product["_category"] = cat_name
            product["_tier"] = tier
            model_key = product.get("model", "").upper().strip()
            if model_key and model_key not in _model_index:
                _add_product(product)


def load_products() -> None:
    """Load all product JSON files and build indices. Safe to call multiple times."""
    global _products, _model_index, _category_index, _loaded
    if _loaded:
        return

    seed_dir = _find_seed_data()
    _products = []
    _model_index = {}
    _category_index = {}

    for filename in _PRODUCT_FILES:
        path = os.path.join(seed_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            if filename == "products.json":
                _load_legacy_file(path)
            else:
                _load_flat_file(path)
            logger.info("Loaded product file: %s", filename)
        except Exception as e:
            logger.warning("Failed to load %s: %s", filename, e)

    _loaded = True
    logger.info(
        "Product index loaded: %d products, %d model keys, %d categories",
        len(_products), len(_model_index), len(_category_index),
    )


def _classify_tier(category_name: str) -> str:
    lower = category_name.lower()
    for tier, keywords in _TIER_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return tier
    return "other"


def lookup_by_model(model: str) -> dict | None:
    """Exact model lookup (case-insensitive)."""
    load_products()
    key = model.upper().strip()
    result = _model_index.get(key)
    if result:
        return result
    normalized = re.sub(r"[^A-Z0-9]", "", key)
    return _model_index.get(normalized)


def search_by_keywords(keywords: str, limit: int = 5) -> list[dict]:
    """Fuzzy search across all product fields."""
    load_products()
    terms = [t.lower() for t in keywords.split() if t]
    if not terms:
        return []

    scored: list[tuple[int, dict]] = []
    for p in _products:
        text = json.dumps(p, ensure_ascii=False).lower()
        score = sum(1 for t in terms if t in text)
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def list_by_category(tier: str) -> list[dict]:
    """List all products in a tier/category."""
    load_products()
    return _category_index.get(tier, [])


def get_all_models() -> list[str]:
    """Return all known model names."""
    load_products()
    seen: set[str] = set()
    result: list[str] = []
    for p in _products:
        m = p.get("model", "")
        if m and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def get_verified_models() -> list[str]:
    """Return model names that have a verified product page URL (image_url field)."""
    load_products()
    seen: set[str] = set()
    result: list[str] = []
    for p in _products:
        m = p.get("model", "")
        if m and m not in seen and p.get("image_url"):
            seen.add(m)
            result.append(m)
    return result


def get_product_price(model: str) -> dict | None:
    """Return price info for a model."""
    p = lookup_by_model(model)
    if not p:
        return None
    result: dict[str, Any] = {"model": p.get("model")}
    for key in ("price_usd", "price_max_usd", "price_range_usd", "price_with_eq_usd", "_tier", "_category", "category"):
        if key in p:
            result[key] = p[key]
    return result


def format_product_card(product: dict) -> str:
    """Format a product dict into a concise text card for LLM context."""
    skip = {"_category", "_tier", "_is_info", "description_cn", "description_en", "image_url"}
    name = product.get("name_en", product.get("type", ""))
    lines = [f"**{product.get('model', 'N/A')}** — {name}"]
    if product.get("description_cn"):
        lines.append(product["description_cn"])
    if product.get("description_en"):
        lines.append(product["description_en"])
    for k, v in product.items():
        if k in skip or k in ("model", "type", "name_en", "name_cn"):
            continue
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        if v is None:
            continue
        label = k.replace("_", " ").title()
        lines.append(f"- {label}: {v}")
    return "\n".join(lines)

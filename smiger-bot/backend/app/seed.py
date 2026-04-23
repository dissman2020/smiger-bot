"""Load seed data into the knowledge base (v0.1.2)."""
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402
from app.core.rag_engine import (  # noqa: E402
    add_document_chunks,
    add_faq_chunks,
    chunk_faq_entries,
    chunk_text,
    _get_collection,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_DIR = os.path.join(_APP_ROOT, "seed_data")
if not os.path.isdir(SEED_DIR):
    SEED_DIR = os.path.join(os.path.dirname(_APP_ROOT), "seed_data")


PRODUCT_FILES = [
    "electric_guitars.json",
    "electric_guitars_luxars.json",
    "acoustic_guitars_1.json",
    "acoustic_guitars_2.json",
    "acoustic_guitars_3.json",
    "classical_guitars.json",
    "ukuleles.json",
    "accessories.json",
]


def flat_products_to_text(products: list[dict]) -> str:
    """Convert a flat list of product dicts into human-readable text for embedding."""
    skip_keys = {"model", "name_en", "name_cn", "description_cn", "description_en", "image_url"}
    sections: list[str] = []
    for p in products:
        name = p.get("name_en", p.get("name_cn", ""))
        lines = [f"## {p.get('model', '')} — {name}"]
        if p.get("description_cn"):
            lines.append(p["description_cn"])
        if p.get("description_en"):
            lines.append(p["description_en"])
        specs = {k: v for k, v in p.items() if k not in skip_keys and v is not None}
        for k, v in specs.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            lines.append(f"- {k.replace('_', ' ').title()}: {v}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def legacy_products_to_text(data: list) -> str:
    """Convert old category-grouped products.json into text for embedding."""
    skip_keys = {"model", "type", "description", "description_cn", "description_en"}
    sections: list[str] = []
    for category in data:
        cat_name = category.get("category", "")
        sections.append(f"# {cat_name}\n")
        if "info" in category:
            info = category["info"]
            for desc_key in ("description_cn", "description_en", "description"):
                if desc_key in info:
                    sections.append(info[desc_key])
            continue
        for product in category.get("products", []):
            lines = [f"## {product.get('model', '')} — {product.get('type', '')}"]
            if product.get("description_cn"):
                lines.append(product["description_cn"])
            if product.get("description_en"):
                lines.append(product["description_en"])
            specs = {k: v for k, v in product.items() if k not in skip_keys}
            for k, v in specs.items():
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v)
                lines.append(f"- {k.replace('_', ' ').title()}: {v}")
            sections.append("\n".join(lines))
    return "\n\n".join(sections)


def country_prefs_to_text(data: list) -> str:
    """Convert country_preferences.json into embeddable text."""
    sections: list[str] = []
    for entry in data:
        lines = [
            f"## {entry['country']} ({entry.get('country_cn', '')}) 市场偏好 / Market Preferences",
            f"热销型号 Hot models: {', '.join(entry.get('hot_models', []))}",
            f"常见尺寸 Sizes: {', '.join(entry.get('sizes', []))}",
        ]
        if entry.get("features"):
            lines.append(f"特殊要求(CN): {entry['features']}")
        if entry.get("features_en"):
            lines.append(f"Requirements(EN): {entry['features_en']}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def customization_to_text(data: list) -> str:
    """Convert customization_options.json into embeddable text."""
    lines = ["# 定制选项及加价表 / Customization Options & Surcharges\n"]
    for opt in data:
        parts = [f"- {opt['label_cn']} / {opt['label_en']}:"]
        if opt.get("surcharge_rmb") is not None and opt["surcharge_rmb"] > 0:
            parts.append(f"+{opt['surcharge_rmb']}RMB")
        if opt.get("surcharge_usd") is not None and opt["surcharge_usd"] > 0:
            parts.append(f"+${opt['surcharge_usd']}USD")
        if opt.get("surcharge_rmb") == 0 and opt.get("surcharge_usd") == 0:
            parts.append("不加钱/No extra charge")
        if opt.get("note"):
            parts.append(f"({opt['note']})")
        lines.append(" ".join(parts))
    return "\n".join(lines)


async def main():
    collection = _get_collection()
    existing = collection.count()
    if existing > 0:
        logger.info("Knowledge base already has %d chunks, skipping seed.", existing)
        return

    # --- New flat product files ---
    for pf in PRODUCT_FILES:
        pf_path = os.path.join(SEED_DIR, pf)
        if not os.path.exists(pf_path):
            continue
        with open(pf_path, "r", encoding="utf-8") as f:
            pf_data = json.load(f)
        text = flat_products_to_text(pf_data)
        chunks = chunk_text(text, chunk_size=600, chunk_overlap=80)
        count = await add_document_chunks(f"seed_{pf}", chunks, pf,
                                          extra_meta={"category": "products"})
        logger.info("Loaded %d chunks from %s", count, pf)

    # --- Legacy products.json (backward compat) ---
    products_path = os.path.join(SEED_DIR, "products.json")
    if os.path.exists(products_path):
        with open(products_path, "r", encoding="utf-8") as f:
            products = json.load(f)
        text = legacy_products_to_text(products)
        chunks = chunk_text(text, chunk_size=600, chunk_overlap=80)
        count = await add_document_chunks("seed_products", chunks, "products.json")
        logger.info("Loaded %d legacy product chunks", count)

    # --- FAQ (structured bilingual) ---
    faq_path = os.path.join(SEED_DIR, "faq.json")
    if os.path.exists(faq_path):
        with open(faq_path, "r", encoding="utf-8") as f:
            faq_data = json.load(f)

        faq_entries = []
        for i, item in enumerate(faq_data):
            faq_entries.append({
                "id": i + 1,
                "category": item.get("category", "general"),
                "question_cn": item.get("question_cn", item.get("question", "")),
                "question_en": item.get("question_en", item.get("question", "")),
                "answer_cn": item.get("answer_cn", item.get("answer", "")),
                "answer_en": item.get("answer_en", item.get("answer", "")),
                "tags": item.get("tags", []),
            })

        pairs = chunk_faq_entries(faq_entries)
        count = await add_faq_chunks(pairs)
        logger.info("Loaded %d FAQ chunks (structured bilingual)", count)

    # --- Country Preferences ---
    country_path = os.path.join(SEED_DIR, "country_preferences.json")
    if os.path.exists(country_path):
        with open(country_path, "r", encoding="utf-8") as f:
            country_data = json.load(f)
        text = country_prefs_to_text(country_data)
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        count = await add_document_chunks("seed_country_prefs", chunks, "country_preferences.json",
                                          extra_meta={"category": "country_preferences"})
        logger.info("Loaded %d country preference chunks", count)

    # --- Customization Options ---
    custom_path = os.path.join(SEED_DIR, "customization_options.json")
    if os.path.exists(custom_path):
        with open(custom_path, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
        text = customization_to_text(custom_data)
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        count = await add_document_chunks("seed_customization", chunks, "customization_options.json",
                                          extra_meta={"category": "customization"})
        logger.info("Loaded %d customization option chunks", count)

    logger.info("Seed data loaded. Total chunks: %d", collection.count())


if __name__ == "__main__":
    asyncio.run(main())

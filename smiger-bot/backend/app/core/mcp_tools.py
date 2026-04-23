"""MCP Tool definitions and executor for Smiger AI pre-sales bot.

Provides structured tools that the LLM can call via OpenAI function-calling
to retrieve precise business data and perform calculations.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core import business_rules, product_index

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool JSON schemas (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "product_lookup",
            "description": (
                "Look up detailed specifications of a Smiger guitar by model number "
                "or search by keywords/category. Use when the customer asks about a "
                "specific model or wants product recommendations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Exact model number, e.g. 'MAS-41A', 'LG-09', 'SM-401-A'",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["beginner", "mid_range", "high_end", "electric", "bass", "ukulele", "accessories"],
                        "description": "Product tier/category to filter",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "Free-text search keywords, e.g. 'solid top 41 inch mahogany'",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_container",
            "description": (
                "Calculate how many shipping containers are needed for a guitar order. "
                "Use when the customer asks about shipping capacity, container loading, "
                "or how many guitars fit in a 20GP/40GP/40HQ container."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "size": {
                        "type": "string",
                        "enum": ["36", "40", "41", "12string", "bass"],
                        "description": "Guitar size in inches",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Total number of guitars to ship",
                    },
                },
                "required": ["size", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_moq",
            "description": (
                "Validate an order against MOQ (Minimum Order Quantity) rules. "
                "Use when verifying if the customer's order meets minimum requirements."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_type": {
                        "type": "string",
                        "enum": ["stock", "oem"],
                        "description": "stock = our brand, oem = custom brand",
                    },
                    "total_qty": {
                        "type": "integer",
                        "description": "Total order quantity in pieces",
                    },
                    "models": {
                        "type": "object",
                        "description": "Per-model quantities, e.g. {'LG-09': 80, 'SM-401': 40}",
                        "additionalProperties": {"type": "integer"},
                    },
                },
                "required": ["order_type", "total_qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_customization_cost",
            "description": (
                "Calculate extra cost for customization options like left-handed, "
                "pearl logo, EQ installation, color box, etc. Use when the customer "
                "asks about customization pricing or surcharges."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "left_handed", "acrylic_block_dots",
                                "celluloid_binding_upgrade", "pearl_logo",
                                "maple_inlay_logo", "mail_order_packaging",
                                "custom_serial_number", "eq_installation",
                            ],
                        },
                        "description": "List of customization options",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of guitars",
                        "default": 1,
                    },
                    "color_box_size": {
                        "type": "string",
                        "enum": ["34", "36", "38", "39", "40", "41"],
                        "description": "Guitar size for color box surcharge (if needed)",
                    },
                },
                "required": ["options"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_country_recommendations",
            "description": (
                "Get hot-selling guitar models and market preferences for a specific "
                "country. Use when the customer mentions their country or target market."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "Country name, e.g. 'nigeria', 'usa', 'myanmar', 'cambodia', 'canada'",
                    },
                },
                "required": ["country"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_range",
            "description": (
                "Get price range for a product tier or a specific model. "
                "Use when the customer asks 'how much' or about pricing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "string",
                        "enum": ["beginner", "mid_range", "high_end"],
                        "description": "Product tier for general price range",
                    },
                    "model": {
                        "type": "string",
                        "description": "Specific model number for exact price",
                    },
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name with the given arguments. Returns JSON string."""
    try:
        handler = _HANDLERS.get(name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {name}"})
        result = handler(arguments)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("Tool execution error: %s(%s)", name, arguments)
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------

def _handle_product_lookup(args: dict) -> Any:
    model = args.get("model")
    category = args.get("category")
    keywords = args.get("keywords")

    if model:
        p = product_index.lookup_by_model(model)
        if p:
            return {"found": True, "product": _sanitize(p)}
        return {"found": False, "message": f"Model '{model}' not found. Available models: {product_index.get_all_models()[:15]}"}

    if keywords:
        results = product_index.search_by_keywords(keywords, limit=5)
        return {"found": len(results) > 0, "results": [_sanitize(r) for r in results]}

    if category:
        results = product_index.list_by_category(category)
        return {"found": len(results) > 0, "results": [_sanitize(r) for r in results[:8]]}

    return {"error": "Please provide model, keywords, or category"}


def _handle_calculate_container(args: dict) -> Any:
    size = args.get("size", "")
    quantity = args.get("quantity", 0)
    if not size or not quantity:
        return {"error": "Both size and quantity are required"}
    return business_rules.calculate_container(str(size), int(quantity))


def _handle_check_moq(args: dict) -> Any:
    order_type = args.get("order_type", "stock")
    total_qty = args.get("total_qty", 0)
    models = args.get("models")
    return business_rules.check_moq(order_type, int(total_qty), models)


def _handle_customization_cost(args: dict) -> Any:
    options = args.get("options", [])
    quantity = args.get("quantity", 1)
    result = business_rules.calculate_customization_cost(options, int(quantity))

    color_box_size = args.get("color_box_size")
    if color_box_size:
        cost_per = business_rules.COLOR_BOX_SURCHARGE.get(str(color_box_size), 0)
        if cost_per > 0:
            result["color_box"] = {
                "size": color_box_size,
                "cost_per_guitar_usd": cost_per,
                "total_usd": round(cost_per * int(quantity), 2),
                "moq": business_rules.COLOR_BOX_MOQ,
            }

    return result


def _handle_country_recommendations(args: dict) -> Any:
    country = args.get("country", "").lower().strip()
    aliases = {
        "尼日利亚": "nigeria", "美国": "usa", "加拿大": "canada",
        "缅甸": "myanmar", "柬埔寨": "cambodia",
        "us": "usa", "united states": "usa",
    }
    country = aliases.get(country, country)

    prefs = business_rules.COUNTRY_PREFERENCES.get(country)
    if not prefs:
        available = list(business_rules.COUNTRY_PREFERENCES.keys())
        return {"found": False, "message": f"No data for '{country}'. Available: {available}"}

    hot_models_detail = []
    for model_name in prefs.get("hot_models", []):
        p = product_index.lookup_by_model(model_name)
        if p:
            hot_models_detail.append({
                "model": p.get("model"),
                "type": p.get("type"),
                "price_range_usd": p.get("price_range_usd"),
            })
        else:
            hot_models_detail.append({"model": model_name})

    return {
        "found": True,
        "country": country,
        "hot_models": prefs.get("hot_models", []),
        "hot_models_detail": hot_models_detail,
        "sizes": prefs.get("sizes", []),
        "notes": prefs.get("notes", ""),
    }


def _handle_price_range(args: dict) -> Any:
    tier = args.get("tier")
    model = args.get("model")

    result: dict[str, Any] = {}

    if model:
        price_info = product_index.get_product_price(model)
        if price_info:
            result["model_price"] = price_info
        else:
            result["model_price"] = {"error": f"Model '{model}' not found"}

    if tier:
        tier_info = business_rules.PRICE_RANGES.get(tier)
        if tier_info:
            result["tier_range"] = tier_info
        else:
            result["tier_range"] = {"error": f"Unknown tier '{tier}'"}

    if not tier and not model:
        result["all_tiers"] = business_rules.PRICE_RANGES

    return result


def _sanitize(product: dict) -> dict:
    """Remove internal keys and truncate long descriptions for tool output."""
    result = {}
    for k, v in product.items():
        if k.startswith("_"):
            continue
        result[k] = v
    return result


_HANDLERS: dict[str, Any] = {
    "product_lookup": _handle_product_lookup,
    "calculate_container": _handle_calculate_container,
    "check_moq": _handle_check_moq,
    "calculate_customization_cost": _handle_customization_cost,
    "get_country_recommendations": _handle_country_recommendations,
    "get_price_range": _handle_price_range,
}

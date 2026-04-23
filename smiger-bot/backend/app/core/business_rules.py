"""Business rules engine for Smiger guitar manufacturing.

Encodes real pricing, MOQ, container capacity, and customization surcharge
data from the client's historical FAQ documents.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Container capacity data (from 甲方 FAQ)
# Each key = guitar size in inches; values = packing & capacity numbers
# ---------------------------------------------------------------------------
CONTAINER_CAPACITY: dict[str, dict] = {
    "36": {"pcs_per_ctn": 6, "cbm_per_ctn": 0.24, "20gp": 702, "40gp": 1428, "40hq": 1698},
    "40": {"pcs_per_ctn": 6, "cbm_per_ctn": 0.25, "20gp": 672, "40gp": 1368, "40hq": 1632},
    "41": {"pcs_per_ctn": 6, "cbm_per_ctn": 0.35, "20gp": 480, "40gp": 1140, "40hq": 1362},
    "12string": {"pcs_per_ctn": 6, "cbm_per_ctn": 0.35, "20gp": 480, "40gp": 978, "40hq": 1164},
    "bass": {"pcs_per_ctn": 4, "cbm_per_ctn": 0.27, "20gp": 416, "40gp": 844, "40hq": 1128},
}

CONTAINER_CBM = {"20gp": 28, "40gp": 57, "40hq": 68}

# ---------------------------------------------------------------------------
# MOQ rules (from 甲方 FAQ)
# ---------------------------------------------------------------------------
MOQ_RULES = {
    "stock": {
        "min_pcs": 6,
        "mixed_models": True,
        "mixed_colors": True,
        "note_cn": "现货6把起订，可以混色混款",
        "note_en": "Stock MOQ 6PCS, mixed models/colors available",
    },
    "oem": {
        "min_pcs": 120,
        "per_model": 60,
        "per_color": 30,
        "mixed_models": True,
        "note_cn": "贴牌120把起订，可以混款，每个型号起订量60把，每个颜色起订量30把",
        "note_en": "Custom brand MOQ 120pcs, mixed models available. Each model MOQ 60PCS. Each color MOQ 30PCS.",
    },
}

# ---------------------------------------------------------------------------
# Price ranges (from 甲方 FAQ, in USD)
# ---------------------------------------------------------------------------
PRICE_RANGES = {
    "beginner": {"min": 16, "max": 35, "note": "入门级民谣吉他 Beginner guitar series"},
    "mid_range": {"min": 43, "max": 62, "note": "中档民谣吉他 Mid-range acoustic"},
    "high_end": {"min": 43, "max": 215, "note": "高档民谣吉他 High-end acoustic"},
}

# ---------------------------------------------------------------------------
# Customization surcharges (from 甲方 FAQ)
# ---------------------------------------------------------------------------
CUSTOMIZATION_SURCHARGES: dict[str, dict] = {
    "left_handed": {
        "rmb": 3, "usd": 0.5,
        "label_cn": "左手吉他", "label_en": "Left handed guitar",
    },
    "acrylic_block_dots": {
        "rmb": 15,
        "label_cn": "亚克力块状音点", "label_en": "Acrylic block position dots",
    },
    "celluloid_binding_upgrade": {
        "rmb": 10,
        "label_cn": "赛露露包边(差价)", "label_en": "Celluloid binding upgrade (ABS→Celluloid)",
    },
    "pearl_logo": {
        "rmb": 12,
        "label_cn": "白贝LOGO", "label_en": "Pearl shell logo",
    },
    "maple_inlay_logo": {
        "rmb": 5,
        "label_cn": "枫木LOGO镶嵌", "label_en": "Maple inlay logo",
    },
    "mail_order_packaging": {
        "rmb": 15,
        "label_cn": "邮购包装", "label_en": "Mail-order packaging",
    },
    "custom_serial_number": {
        "usd": 0.5,
        "label_cn": "内标不同序号", "label_en": "Custom serial number on label",
    },
    "eq_installation": {
        "rmb": 10, "usd": 1.67,
        "label_cn": "EQ安装费", "label_en": "EQ/Pickup installation fee",
    },
}

COLOR_BOX_SURCHARGE: dict[str, float] = {
    "34": 0.57, "36": 0.73, "38": 0.75,
    "39": 0.80, "40": 0.87, "41": 1.00,
}
COLOR_BOX_MOQ = 1000

# ---------------------------------------------------------------------------
# Delivery time (from 甲方 FAQ)
# ---------------------------------------------------------------------------
DELIVERY_TIMES = {
    "stock": {"min_days": 3, "max_days": 10, "note_cn": "现货单3-10个工作日", "note_en": "Stock order within 3-10 workdays"},
    "oem": {"min_days": 45, "max_days": 60, "note_cn": "OEM订单交期45-60天(支付定金和提供确认设计稿后)", "note_en": "OEM lead time 45-60 days after deposit and confirmed design"},
}

# ---------------------------------------------------------------------------
# Country preferences (from 甲方 FAQ)
# ---------------------------------------------------------------------------
COUNTRY_PREFERENCES: dict[str, dict] = {
    "nigeria": {
        "hot_models": ["LG-09", "LG-07", "SM-412/3", "M-4160"],
        "sizes": ["40", "41"],
        "notes": "装EQ, 配连接线，配包",
    },
    "usa": {
        "hot_models": ["M-215-40", "MAS-41A", "MES-41A", "MDS-41A", "M-F1SS", "SM-361/401"],
        "sizes": ["40", "41"],
        "notes": "高档, 装EQ, 每个内标不同序列号, 配包(高档加厚), 红松面单, 指板不要镶嵌",
    },
    "canada": {
        "hot_models": ["SM-401-A/C", "LG-07-09"],
        "sizes": ["40", "41"],
        "notes": "",
    },
    "myanmar": {
        "hot_models": ["EN/FN-10/20/25/30", "LG-09-EQ"],
        "sizes": ["40"],
        "notes": "擦色",
    },
    "cambodia": {
        "hot_models": ["M-210-41", "M-410-41"],
        "sizes": ["41"],
        "notes": "",
    },
}


def calculate_container(size: str, quantity: int) -> dict:
    """Calculate how many containers are needed for a given guitar size and quantity."""
    spec = CONTAINER_CAPACITY.get(size)
    if not spec:
        return {"error": f"Unknown size: {size}. Available: {list(CONTAINER_CAPACITY.keys())}"}

    cartons = math.ceil(quantity / spec["pcs_per_ctn"])
    total_cbm = cartons * spec["cbm_per_ctn"]

    result = {
        "size": size,
        "quantity": quantity,
        "cartons": cartons,
        "total_cbm": round(total_cbm, 2),
        "fits_in": {},
    }
    for ctype in ("20gp", "40gp", "40hq"):
        max_pcs = spec[ctype]
        containers_needed = math.ceil(quantity / max_pcs) if max_pcs > 0 else 0
        result["fits_in"][ctype] = {
            "max_capacity": max_pcs,
            "containers_needed": containers_needed,
            "fill_rate": round(quantity / (max_pcs * containers_needed) * 100, 1) if containers_needed > 0 else 0,
        }
    return result


def calculate_customization_cost(options: list[str], quantity: int = 1) -> dict:
    """Calculate total surcharge for selected customization options."""
    items = []
    total_rmb = 0.0
    total_usd = 0.0

    for opt in options:
        surcharge = CUSTOMIZATION_SURCHARGES.get(opt)
        if not surcharge:
            continue
        item = {"option": opt, "label_cn": surcharge.get("label_cn", opt), "label_en": surcharge.get("label_en", opt)}
        if "rmb" in surcharge:
            item["per_unit_rmb"] = surcharge["rmb"]
            total_rmb += surcharge["rmb"] * quantity
        if "usd" in surcharge:
            item["per_unit_usd"] = surcharge["usd"]
            total_usd += surcharge["usd"] * quantity
        items.append(item)

    return {
        "items": items,
        "quantity": quantity,
        "total_rmb": round(total_rmb, 2),
        "total_usd": round(total_usd, 2),
    }


def check_moq(order_type: str, total_qty: int, models: dict[str, int] | None = None) -> dict:
    """Validate order against MOQ rules. models = {model_name: qty}."""
    rule = MOQ_RULES.get(order_type)
    if not rule:
        return {"valid": False, "error": f"Unknown order type: {order_type}"}

    issues = []
    if total_qty < rule["min_pcs"]:
        issues.append(f"Total quantity {total_qty} below minimum {rule['min_pcs']}")

    if order_type == "oem" and models:
        for model, qty in models.items():
            if qty < rule["per_model"]:
                issues.append(f"Model {model}: {qty} pcs below per-model minimum {rule['per_model']}")

    return {
        "valid": len(issues) == 0,
        "order_type": order_type,
        "total_qty": total_qty,
        "rule": rule,
        "issues": issues,
    }


def get_business_context() -> str:
    """Generate a business rules summary string for injection into LLM system prompt."""
    lines = [
        "## Smiger Business Rules Reference",
        "",
        "### Pricing (USD FOB)",
        f"- Beginner: ${PRICE_RANGES['beginner']['min']}-${PRICE_RANGES['beginner']['max']}",
        f"- Mid-range acoustic: ${PRICE_RANGES['mid_range']['min']}-${PRICE_RANGES['mid_range']['max']}",
        f"- High-end acoustic: ${PRICE_RANGES['high_end']['min']}-${PRICE_RANGES['high_end']['max']}",
        "",
        "### MOQ",
        f"- Stock: {MOQ_RULES['stock']['note_en']}",
        f"- OEM: {MOQ_RULES['oem']['note_en']}",
        "",
        "### Delivery Time",
        f"- {DELIVERY_TIMES['stock']['note_en']}",
        f"- {DELIVERY_TIMES['oem']['note_en']}",
        "",
        "### Container Capacity (pieces per full container)",
    ]
    for size, spec in CONTAINER_CAPACITY.items():
        lines.append(f"- {size}\": 20GP={spec['20gp']}, 40GP={spec['40gp']}, 40HQ={spec['40hq']}")

    lines += [
        "",
        "### Customization Surcharges",
    ]
    for key, s in CUSTOMIZATION_SURCHARGES.items():
        price_parts = []
        if "rmb" in s:
            price_parts.append(f"+{s['rmb']}RMB")
        if "usd" in s:
            price_parts.append(f"+${s['usd']}")
        lines.append(f"- {s.get('label_en', key)}: {'/'.join(price_parts)} per unit")

    lines += [
        "",
        f"### Color Box: MOQ {COLOR_BOX_MOQ}pcs, extra cost per guitar by size:",
    ]
    for size, cost in COLOR_BOX_SURCHARGE.items():
        lines.append(f'  - {size}": ${cost}')

    return "\n".join(lines)

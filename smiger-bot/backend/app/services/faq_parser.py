"""Parse FAQ documents into structured bilingual Q&A entries."""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "pricing": ["价格", "price", "usd", "rmb", "费用", "cost", "extra cost", "加价", "差价"],
    "moq": ["moq", "起订量", "起订", "minimum order", "最低"],
    "delivery": ["交期", "delivery", "lead time", "工作日", "workday"],
    "customization": ["logo", "定制", "custom", "oem", "odm", "贴牌", "左手", "left hand",
                       "指板", "fingerboard", "包边", "binding", "拾音器", "pickup", "eq",
                       "套装", "bundle", "序号", "serial"],
    "logistics": ["包装", "package", "container", "装柜", "cbm", "shipping", "物流",
                   "20gp", "40gp", "40hq", "彩盒", "color box"],
    "country_preferences": ["国家", "country", "尼日利亚", "美国", "加拿大", "缅甸", "柬埔寨",
                            "nigeria", "usa", "canada", "myanmar", "cambodia"],
}


@dataclass
class ParsedFaqItem:
    question_cn: str = ""
    question_en: str = ""
    answer_cn: str = ""
    answer_en: str = ""
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    extra_metadata: dict = field(default_factory=dict)


def _is_chinese(text: str) -> bool:
    cn_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return cn_chars / max(len(text), 1) > 0.15


def _classify(text: str) -> str:
    combined = text.lower()
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw.lower() in combined)
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=lambda k: scores[k])


def _extract_numbers(text: str) -> dict:
    meta: dict = {}
    usd = re.findall(r"(\d+(?:\.\d+)?)\s*(?:USD|usd|\$)", text)
    if usd:
        meta["prices_usd"] = [float(v) for v in usd]
    rmb = re.findall(r"(\d+(?:\.\d+)?)\s*(?:元|RMB|rmb|CNY)", text)
    if rmb:
        meta["prices_rmb"] = [float(v) for v in rmb]
    moq = re.findall(r"(?:MOQ|起订量?|最低)\s*[:：]?\s*(\d+)", text, re.IGNORECASE)
    if moq:
        meta["moq_values"] = [int(v) for v in moq]
    days = re.findall(r"(\d+)[-~至到](\d+)\s*(?:天|个工作日|days?|workdays?)", text, re.IGNORECASE)
    if days:
        meta["lead_days"] = [{"min": int(a), "max": int(b)} for a, b in days]
    return meta


def _extract_tags(text: str) -> list[str]:
    tag_patterns = [
        (r"\bEQ\b", "EQ"), (r"\bLOGO\b", "LOGO"), (r"\bOEM\b", "OEM"),
        (r"\bODM\b", "ODM"), (r"左手|left.?hand", "left-hand"),
        (r"拾音器|pickup", "pickup"), (r"套装|bundle", "bundle"),
        (r"彩盒|color.?box", "color-box"), (r"指板|fingerboard", "fingerboard"),
        (r"包边|binding", "binding"), (r"内标|label", "label"),
    ]
    tags = []
    lower = text.lower()
    for pattern, tag in tag_patterns:
        if re.search(pattern, lower, re.IGNORECASE):
            tags.append(tag)
    return tags


def _split_bilingual_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """Separate Chinese and English lines."""
    cn, en = [], []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_chinese(stripped):
            cn.append(stripped)
        else:
            en.append(stripped)
    return cn, en


def parse_faq_text(text: str) -> list[ParsedFaqItem]:
    """Parse raw FAQ text into structured bilingual items.

    Detects patterns like:
      - "问：...  答：..."  / "Q: ... A: ..."
      - Question lines followed by answer lines starting with "答："
      - Bilingual pairs (Chinese line followed by English equivalent)
    """
    lines = [l.strip() for l in text.replace("\r\n", "\n").split("\n")]

    blocks: list[dict] = []
    current_q_lines: list[str] = []
    current_a_lines: list[str] = []
    in_answer = False

    q_pattern = re.compile(r"^(?:问\s*[:：]|Q\s*[:：]|^\d+[.、]\s*)", re.IGNORECASE)
    a_pattern = re.compile(r"^(?:答\s*[:：]|A\s*[:：])", re.IGNORECASE)

    def _flush():
        if current_q_lines or current_a_lines:
            blocks.append({"q": list(current_q_lines), "a": list(current_a_lines)})

    for line in lines:
        if not line:
            continue

        if q_pattern.match(line):
            _flush()
            current_q_lines = [q_pattern.sub("", line).strip() or line]
            current_a_lines = []
            in_answer = False
            continue

        if a_pattern.match(line):
            in_answer = True
            cleaned = a_pattern.sub("", line).strip()
            if cleaned:
                current_a_lines = [cleaned]
            else:
                current_a_lines = []
            continue

        # Heuristic: if line ends with '?' or '？' treat as new question
        if (line.endswith("?") or line.endswith("？")) and not in_answer:
            _flush()
            current_q_lines = [line]
            current_a_lines = []
            in_answer = False
            continue

        if in_answer:
            current_a_lines.append(line)
        elif current_q_lines and not current_a_lines:
            current_q_lines.append(line)
        else:
            current_a_lines.append(line)

    _flush()

    items: list[ParsedFaqItem] = []
    for block in blocks:
        q_cn, q_en = _split_bilingual_lines(block["q"])
        a_cn, a_en = _split_bilingual_lines(block["a"])

        if not q_cn and not q_en:
            continue

        combined = "\n".join(block["q"] + block["a"])

        item = ParsedFaqItem(
            question_cn="\n".join(q_cn) if q_cn else "\n".join(q_en),
            question_en="\n".join(q_en) if q_en else "\n".join(q_cn),
            answer_cn="\n".join(a_cn) if a_cn else "\n".join(a_en),
            answer_en="\n".join(a_en) if a_en else "\n".join(a_cn),
            category=_classify(combined),
            tags=_extract_tags(combined),
            extra_metadata=_extract_numbers(combined),
        )
        items.append(item)

    logger.info("Parsed %d FAQ items from text (%d blocks detected)", len(items), len(blocks))
    return items

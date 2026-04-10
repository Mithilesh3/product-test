from __future__ import annotations

import base64
from datetime import datetime
from app.core.time_utils import UTC
from io import BytesIO
import json
import logging
import mimetypes
from pathlib import Path
import re
from typing import Any, Dict, List, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.modules.reports.blueprint import BASIC_SECTION_KEYS
from app.modules.reports.plan_config import ENTERPRISE_SECTIONS

from .svg_diagrams import (
    build_loshu_grid_svg,
    build_numerology_architecture_svg,
    build_planetary_orbit_svg,
    build_structural_deficit_svg,
)

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - import path depends on runtime env
    PlaywrightError = Exception
    sync_playwright = None

try:
    from pypdf import PdfReader, PdfWriter
except Exception:  # pragma: no cover - optional runtime optimization
    PdfReader = None
    PdfWriter = None


logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STRATEGIC_TEMPLATE_NAME = "strategic_life_audit.html"
BASIC_TEMPLATE_NAME = "basic_numerology_report.html"
PREMIUM_TEMPLATE_NAME = "premium_hindi_report.html"
ASSETS_ROOT = Path(__file__).resolve().parents[3] / "assets"

PREMIUM_HI_TITLES: Dict[str, str] = {
    "full_identity_profile": "पूर्ण पहचान प्रोफ़ाइल",
    "core_numbers": "मुख्य अंक",
    "advanced_name_numerology": "उन्नत नाम अंक विश्लेषण",
    "karmic_name_analysis": "कर्मिक नाम विश्लेषण",
    "planetary_name_support_mapping": "ग्रह-आधारित नाम समर्थन मैपिंग",
    "multi_name_correction_options": "बहु-नाम सुधार विकल्प",
    "name_optimization_scoring": "नाम अनुकूलन स्कोर",
    "prefix_suffix_advanced_logic": "उन्नत प्रिफिक्स / सुफिक्स तर्क",
    "mobile_numerology_advanced": "उन्नत मोबाइल अंक विश्लेषण",
    "mobile_digit_micro_analysis": "मोबाइल अंकों का सूक्ष्म विश्लेषण",
    "mobile_energy_forecasting": "मोबाइल ऊर्जा पूर्वानुमान",
    "name_mobile_alignment": "नाम और मोबाइल सामंजस्य",
    "dob_name_alignment": "जन्मतिथि और नाम सामंजस्य",
    "dob_mobile_alignment": "जन्मतिथि और मोबाइल सामंजस्य",
    "full_system_alignment_score": "पूर्ण सिस्टम एलाइनमेंट स्कोर",
    "strength_vs_risk_matrix": "ताकत बनाम जोखिम मैट्रिक्स",
    "life_area_scores": "जीवन-क्षेत्र स्कोर",
    "mulank_deep_analysis": "मूलांक गहन विश्लेषण",
    "bhagyank_destiny_roadmap": "भाग्यांक डेस्टिनी रोडमैप",
    "lo_shu_grid_advanced": "उन्नत लो-शू ग्रिड",
    "planetary_influence_mapping": "ग्रह प्रभाव मैपिंग",
    "current_planetary_phase": "वर्तमान ग्रह चरण",
    "upcoming_transit_highlights": "आगामी गोचर संकेत",
    "personal_year_analysis": "व्यक्तिगत वर्ष विश्लेषण",
    "monthly_cycle_analysis": "मासिक चक्र विश्लेषण",
    "critical_decision_windows": "महत्वपूर्ण निर्णय समय-खिड़कियाँ",
    "wealth_cycle_analysis": "धन चक्र विश्लेषण",
    "career_growth_timeline": "करियर विकास टाइमलाइन",
    "relationship_timing_patterns": "संबंध समय-पैटर्न",
    "dynamic_lucky_numbers": "गतिशील शुभ अंक",
    "situational_caution_numbers": "परिस्थितिजन्य सावधानी अंक",
    "neutral_number_strategy_usage": "तटस्थ अंक उपयोग रणनीति",
    "color_strategy": "रंग रणनीति",
    "energy_objects_recommendation": "ऊर्जा वस्तु सुझाव",
    "advanced_remedies_engine": "उन्नत उपाय इंजन",
    "business_brand_naming": "व्यवसाय / ब्रांड नाम सुझाव",
    "signature_energy_analysis": "हस्ताक्षर ऊर्जा विश्लेषण",
    "mobile_optimization_strategy": "मोबाइल अनुकूलन रणनीति",
    "life_strategy_recommendations": "जीवन रणनीति सुझाव",
    "priority_action_plan": "प्राथमिक कार्य योजना",
    "risk_alerts_and_mitigation": "जोखिम चेतावनी और निवारण",
    "premium_summary_narrative": "प्रीमियम समापन सार",
}

METRIC_CONFIG: Sequence[Dict[str, str]] = (
    {
        "key": "life_stability_index",
        "label": "à¤œà¥€à¤µà¤¨ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ | Life Stability",
        "chart_label": "Life Stability",
    },
    {
        "key": "confidence_score",
        "label": "à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¥à¤ªà¤·à¥à¤Ÿà¤¤à¤¾ | Decision Clarity",
        "chart_label": "Decision Clarity",
    },
    {
        "key": "dharma_alignment_score",
        "label": "à¤§à¤°à¥à¤® à¤¸à¤‚à¤°à¥‡à¤–à¤£ | Dharma Alignment",
        "chart_label": "Dharma Alignment",
    },
    {
        "key": "emotional_regulation_index",
        "label": "à¤­à¤¾à¤µà¤¨à¤¾à¤¤à¥à¤®à¤• à¤¸à¤‚à¤¤à¥à¤²à¤¨ | Emotional Regulation",
        "chart_label": "Emotional Regulation",
    },
    {
        "key": "financial_discipline_index",
        "label": "à¤µà¤¿à¤¤à¥à¤¤ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ | Financial Discipline",
        "chart_label": "Financial Discipline",
    },
    {
        "key": "karma_pressure_index",
        "label": "à¤•à¤°à¥à¤® à¤¦à¤¬à¤¾à¤µ | Karma Pressure",
        "chart_label": "Karma Pressure",
    },
)

LEGACY_LABEL_ALIASES = {
    "à¤¸à¤¾à¤°à¤¾à¤‚à¤¶": "summary",
    "summary": "summary",
    "à¤®à¥à¤–à¥à¤¯ à¤¤à¤¾à¤•à¤¤": "key_strength",
    "key strength": "key_strength",
    "à¤¸à¤‚à¤­à¤¾à¤µà¤¿à¤¤ à¤šà¥à¤¨à¥Œà¤¤à¥€": "key_risk",
    "key risk": "key_risk",
    "à¤µà¥à¤¯à¤¾à¤µà¤¹à¤¾à¤°à¤¿à¤• à¤¸à¥à¤à¤¾à¤µ": "practical_guidance",
    "practical guidance": "practical_guidance",
    "à¤Šà¤°à¥à¤œà¤¾ à¤¸à¤‚à¤•à¥‡à¤¤": "energy_indicators",
    "energy indicators": "energy_indicators",
    "à¤ªà¥à¤°à¤®à¥à¤– à¤¸à¤‚à¤•à¥‡à¤¤à¤•": "key_metrics",
    "key metrics": "key_metrics",
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_text(value: Any, default: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or default


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", [], {})]
    if value in (None, "", [], {}):
        return []
    return [value]


def _sanitize_premium_value(value: Any, default: str = "उपलब्ध नहीं") -> str:
    text = _safe_text(value)
    if not text:
        return default
    for token in ("| |", "@.", "?.", "????", "->"):
        text = text.replace(token, " ")
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;|")
    if not text or re.fullmatch(r"[\s|.@\-]+", text):
        return default
    return text


def _dedupe_phrases(items: List[str]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
    for item in items:
        cleaned = _safe_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def _normalize_focus_text(value: Any) -> str:
    raw = _safe_text(value)
    if not raw:
        return "उपलब्ध नहीं"
    parts = re.split(r"[|,/;]+", raw)
    cleaned = _dedupe_phrases([_safe_text(part) for part in parts if _safe_text(part)])
    return " / ".join(cleaned) if cleaned else "उपलब्ध नहीं"


def _format_number(value: int) -> str:
    return str(value) if isinstance(value, int) and value > 0 else "उपलब्ध नहीं"


def _alignment_state(values: List[int]) -> str:
    usable = [value for value in values if isinstance(value, int) and value > 0]
    if not usable:
        return "निर्धारित नहीं"
    unique = set(usable)
    if len(unique) == 1:
        return "सशक्त मेल"
    if len(unique) == 2:
        return "आंशिक मेल"
    return "मिश्रित"


PLANET_MAP = {
    "Sun": "सूर्य",
    "Moon": "चंद्र",
    "Jupiter": "गुरु",
    "Rahu": "राहु",
    "Mercury": "बुध",
    "Venus": "शुक्र",
    "Ketu": "केतु",
    "Saturn": "शनि",
    "Mars": "मंगल",
}

QUALITY_MAP = {
    "leadership": "नेतृत्व",
    "clarity": "स्पष्टता",
    "authority": "अधिकार",
    "sensitivity": "संवेदनशीलता",
    "intuition": "अंतर्ज्ञान",
    "balance": "संतुलन",
    "wisdom": "बुद्धिमत्ता",
    "expansion": "विस्तार",
    "optimism": "आशावाद",
    "structure": "संरचना",
    "discipline": "अनुशासन",
    "material focus": "भौतिक फोकस",
    "communication": "संवाद",
    "intellect": "बुद्धि",
    "adaptability": "अनुकूलन",
    "harmony": "सामंजस्य",
    "beauty": "सौंदर्य",
    "responsibility": "जिम्मेदारी",
    "insight": "अंतर्दृष्टि",
    "spiritual depth": "आध्यात्मिक गहराई",
    "detachment": "वैराग्य",
    "endurance": "सहनशीलता",
    "action": "क्रिया",
    "courage": "साहस",
    "drive": "प्रेरणा",
}

COLOR_MAP = {
    "Gold": "सुनहरा",
    "Orange": "नारंगी",
    "White": "सफेद",
    "Silver": "चांदी",
    "Yellow": "पीला",
    "Smoky Blue": "धूम्र नीला",
    "Grey": "धूसर",
    "Green": "हरा",
    "Pink": "गुलाबी",
    "Cream": "क्रीम",
    "Smoky White": "धूम्र सफेद",
    "Aqua": "एक्वा",
    "Navy": "नेवी",
    "Indigo": "नील",
    "Black": "काला",
    "Red": "लाल",
    "Maroon": "मैरून",
}

GEM_MAP = {
    "Ruby": "माणिक",
    "Pearl": "मोती",
    "Yellow Sapphire": "पुखराज",
    "Hessonite": "गोमेद",
    "Emerald": "पन्ना",
    "Diamond": "हीरा",
    "Cat's Eye": "लहसुनिया",
    "Blue Sapphire": "नीलम",
    "Red Coral": "मूंगा",
}


def _map_value(value: Any, mapping: Dict[str, str]) -> str:
    text = _safe_text(value)
    if not text:
        return "उपलब्ध नहीं"
    return mapping.get(text, text)


def _map_list(values: Any, mapping: Dict[str, str]) -> str:
    items = _safe_list(values)
    cleaned = [_map_value(item, mapping) for item in items if _safe_text(item)]
    cleaned = [item for item in cleaned if item != "उपलब्ध नहीं"]
    return ", ".join(cleaned) if cleaned else "उपलब्ध नहीं"

def _join_premium_values(values: Any, default: str = "उपलब्ध नहीं") -> str:
    items = _safe_list(values)
    cleaned = [_sanitize_premium_value(item, "") for item in items if _sanitize_premium_value(item, "")]
    return ", ".join(cleaned) if cleaned else default


def _hindi_only_text(value: Any, default: str = "यह भाग उपलब्ध इनपुट के आधार पर तैयार किया गया है।") -> str:
    text = _safe_text(value)
    for token in ("| |", "|", "@.", "?.", "????", "->"):
        text = text.replace(token, " ")
    text = re.sub(r"[A-Za-z]", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;|")
    return text or default


def _split_block_line(value: Any) -> tuple[str, str]:
    line = _safe_text(value)
    if not line:
        return "", ""
    if ":" not in line:
        return "", line
    label, body = line.split(":", 1)
    return _safe_text(label), _safe_text(body)


def _normalize_legacy_label(label: str) -> str:
    normalized = _safe_text(label).lower()
    return LEGACY_LABEL_ALIASES.get(normalized, normalized)


def _legacy_sections_to_payloads(report_sections: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(report_sections, list):
        return {}

    payloads: Dict[str, Dict[str, Any]] = {}
    for section in report_sections:
        if not isinstance(section, dict):
            continue

        key = _safe_text(section.get("key"))
        if not key:
            continue
        title = _safe_text(section.get("title"), key.replace("_", " ").title())
        blocks = section.get("blocks")
        blocks = blocks if isinstance(blocks, list) else []

        # BASIC mobile report sections are already deterministic and ordered.
        # Keep them as waterfall bullets instead of forcing card extraction.
        if key.startswith("basic_"):
            bullets: List[str] = []
            for block in blocks:
                label, value = _split_block_line(block)
                line = f"{label}: {value}" if label and value else (value or label)
                if line:
                    bullets.append(line)
            payloads[key] = {
                "title": title,
                "narrative": _safe_text(section.get("subtitle")),
                "cards": [],
                "bullets": bullets[:24],
            }
            continue

        summary = ""
        key_strength = ""
        key_risk = ""
        practical_guidance = ""
        cards: List[Dict[str, str]] = []

        for block in blocks:
            label, value = _split_block_line(block)
            normalized_label = _normalize_legacy_label(label)

            if normalized_label == "summary":
                summary = value
                continue
            if normalized_label == "key_strength":
                key_strength = value
                cards.append({"label": "à¤®à¥à¤–à¥à¤¯ à¤¤à¤¾à¤•à¤¤", "value": value})
                continue
            if normalized_label == "key_risk":
                key_risk = value
                cards.append({"label": "à¤¸à¤‚à¤­à¤¾à¤µà¤¿à¤¤ à¤šà¥à¤¨à¥Œà¤¤à¥€", "value": value})
                continue
            if normalized_label == "practical_guidance":
                practical_guidance = value
                cards.append({"label": "à¤µà¥à¤¯à¤¾à¤µà¤¹à¤¾à¤°à¤¿à¤• à¤¸à¥à¤à¤¾à¤µ", "value": value})
                continue
            if normalized_label == "energy_indicators":
                cards.append({"label": "à¤Šà¤°à¥à¤œà¤¾ à¤¸à¤‚à¤•à¥‡à¤¤", "value": value})
                continue
            if normalized_label == "key_metrics":
                metric_title = "à¤ªà¥à¤°à¤®à¥à¤– à¤¸à¤‚à¤•à¥‡à¤¤à¤•"
                metric_body = value
                if " - " in value:
                    left, right = value.split(" - ", 1)
                    metric_title = _safe_text(left) or metric_title
                    metric_body = _safe_text(right) or metric_body
                else:
                    metric_label, metric_value = _split_block_line(value)
                    metric_title = metric_label or metric_title
                    metric_body = metric_value or metric_body
                cards.append({"label": metric_title, "value": metric_body})
                continue
            if value:
                cards.append({"label": label or "à¤¬à¤¿à¤‚à¤¦à¥", "value": value})

        narrative_parts = [part for part in [summary, key_strength, key_risk] if _safe_text(part)]
        payloads[key] = {
            "title": title,
            "narrative": " ".join(narrative_parts) if narrative_parts else _safe_text(summary, "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"),
            "cards": cards[:6],
            "bullets": [],
        }
    return payloads


def _clip_text(value: Any, max_chars: int = 180, default: str = "") -> str:
    text = _safe_text(value, default)
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1].rstrip()}â€¦"


def _hindi_major_text(value: Any, default: str = "") -> str:
    text = _safe_text(value, default)
    if not text:
        return default

    text = re.sub(r"\{[^{}]+\}", "", text)
    text = re.sub(r"(,\s*){2,}", ", ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;|")
    if not text:
        return default or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

    replacements = (
        ("Deterministic", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤"),
        ("deterministic", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤"),
        ("Current ", "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ "),
        ("Primary ", "à¤®à¥à¤–à¥à¤¯ "),
        ("Risk band", "à¤°à¤¿à¤¸à¥à¤• à¤¬à¥ˆà¤‚à¤¡"),
        ("Risk Band", "à¤°à¤¿à¤¸à¥à¤• à¤¬à¥ˆà¤‚à¤¡"),
        ("strategic", "à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤•"),
        ("profile", "à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤²"),
        ("analysis", "à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£"),
        ("indicates", "à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ"),
        ("shows", "à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆ"),
        ("supports", "à¤¸à¤ªà¥‹à¤°à¥à¤Ÿ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ"),
        ("improves", "à¤¬à¥‡à¤¹à¤¤à¤° à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ"),
        ("stabilize", "à¤¸à¥à¤¥à¤¿à¤° à¤•à¤°à¥‡à¤‚"),
        ("discipline", "à¤¡à¤¿à¤¸à¤¿à¤ªà¥à¤²à¤¿à¤¨"),
    )
    for source, target in replacements:
        text = text.replace(source, target)

    latin_letters = sum(1 for ch in text if ("a" <= ch.lower() <= "z"))
    latin_ratio = latin_letters / max(len(text), 1)
    if latin_ratio > 0.6 and not re.search(r"[\u0900-\u097F]", text):
        text = f"à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤¸à¤‚à¤•à¥‡à¤¤: {text}. à¤¸à¥à¤§à¤¾à¤° à¤•à¥‡ à¤²à¤¿à¤ disciplined execution protocol à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤"

    return text


def _status_label(status: str) -> str:
    normalized = _safe_text(status).lower()
    if normalized == "strong":
        return "à¤®à¤œà¤¬à¥‚à¤¤ | Strong"
    if normalized == "moderate":
        return "à¤®à¤§à¥à¤¯à¤® | Moderate"
    if normalized == "sensitive":
        return "à¤¸à¤‚à¤µà¥‡à¤¦à¤¨à¤¶à¥€à¤² | Sensitive"
    return _hindi_major_text(status, "à¤®à¤§à¥à¤¯à¤® | Moderate")


def _format_timestamp(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return datetime.now(UTC).strftime("%d %b %Y")

    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%d %b %Y")
    except ValueError:
        return datetime.now(UTC).strftime("%d %b %Y")


def _risk_band(metrics: Dict[str, Any]) -> str:
    explicit = _safe_text(metrics.get("risk_band"))
    if explicit:
        return explicit

    confidence = _safe_int(metrics.get("confidence_score"), 50)
    stability = _safe_int(metrics.get("life_stability_index"), 50)
    emotional = _safe_int(metrics.get("emotional_regulation_index"), 50)
    finance = _safe_int(metrics.get("financial_discipline_index"), 50)
    karma = _safe_int(metrics.get("karma_pressure_index"), 50)
    weakest = min(confidence, stability, emotional, finance)

    if karma >= 75 or weakest <= 34:
        return "à¤‰à¤šà¥à¤š à¤œà¥‹à¤–à¤¿à¤® | High Risk - Structural Intervention Required"
    if karma >= 60 or weakest <= 49:
        return "à¤µà¥‰à¤š à¤œà¤¼à¥‹à¤¨ | Watch Zone - Guided Stabilization Needed"
    if weakest >= 70 and karma <= 45:
        return "à¤¸à¥à¤¥à¤¿à¤° à¤—à¥à¤°à¥‹à¤¥ | Stable Growth - Strategic Scaling Window"
    return "à¤¸à¥à¤§à¤¾à¤° à¤¯à¥‹à¤—à¥à¤¯ | Correctable - Disciplined Execution Needed"


def _status_from_score(score: int) -> str:
    if score >= 75:
        return "Strong"
    if score >= 55:
        return "Moderate"
    return "Sensitive"


def _join_numbers(values: Sequence[Any], default: str = "-") -> str:
    cleaned = [str(_safe_int(item)) for item in values if _safe_int(item, 0) > 0]
    return ", ".join(cleaned) if cleaned else default


def _parse_date(value: Any) -> datetime | None:
    text = _safe_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _reduce_number(value: int) -> int:
    number = abs(int(value))
    while number > 9 and number not in (11, 22):
        number = sum(int(digit) for digit in str(number))
    return number


def _derive_mulank(date_of_birth: Any) -> int:
    parsed = _parse_date(date_of_birth)
    if not parsed:
        return 0
    return _reduce_number(parsed.day)


def _derive_personal_year(date_of_birth: Any, target_year: int | None = None) -> int:
    parsed = _parse_date(date_of_birth)
    if not parsed:
        return 0
    current_year = target_year or datetime.now(UTC).year
    total = sum(int(ch) for ch in f"{parsed.day:02d}{parsed.month:02d}{current_year}")
    return _reduce_number(total)


def _personalize_with_aap(text: Any, full_name: str, *, lead: str = "") -> str:
    cleaned = _hindi_major_text(_safe_text(text), "")
    if not cleaned:
        return ""
    if "à¤†à¤ª" in cleaned:
        return cleaned
    first_name = _safe_text(full_name).split(" ")[0]
    if lead:
        return f"{lead}{cleaned}"
    if first_name:
        return f"{first_name} à¤œà¥€, {cleaned}"
    return f"à¤†à¤ªà¤•à¥‡ à¤²à¤¿à¤ à¤¸à¤‚à¤•à¥‡à¤¤: {cleaned}"


def _extract_focus_text(payload: Dict[str, Any]) -> str:
    normalized_input = payload.get("normalizedInput") if isinstance(payload.get("normalizedInput"), dict) else {}
    legacy_input = payload.get("input_normalized") if isinstance(payload.get("input_normalized"), dict) else {}
    focus = (
        normalized_input.get("currentProblem")
        or normalized_input.get("focusArea")
        or payload.get("current_problem")
        or legacy_input.get("current_problem")
    )
    return _safe_text(focus, "General Alignment")


def _build_profile_snapshot_ui(
    *,
    section: Dict[str, Any],
    full_name: str,
    payload: Dict[str, Any],
    identity: Dict[str, Any],
    birth_details: Dict[str, Any],
    pythagorean: Dict[str, Any],
    chaldean: Dict[str, Any],
) -> Dict[str, Any]:
    cards = [item for item in _safe_list(section.get("cards")) if isinstance(item, dict)]

    summary_text = _safe_text(section.get("narrative"))
    key_traits: List[str] = []
    practical_suggestions: List[str] = []

    for card in cards:
        label = _safe_text(card.get("label")).lower()
        value = _safe_text(card.get("value"))
        if not value:
            continue
        if any(token in label for token in ("summary", "à¤¸à¤¾à¤°à¤¾à¤‚à¤¶")) and not summary_text:
            summary_text = value
            continue
        if any(token in label for token in ("strength", "trait", "risk", "challenge", "à¤¤à¤¾à¤•à¤¤", "à¤šà¥à¤¨à¥Œà¤¤à¥€")):
            key_traits.append(value)
            continue
        if any(token in label for token in ("suggest", "guidance", "action", "advice", "à¤¸à¥à¤à¤¾à¤µ", "à¤®à¤¾à¤°à¥à¤—")):
            practical_suggestions.append(value)
            continue

    if not key_traits:
        key_traits = [_safe_text(card.get("value")) for card in cards[:2] if _safe_text(card.get("value"))]
    if not practical_suggestions:
        practical_suggestions = [_safe_text(card.get("value")) for card in cards[2:4] if _safe_text(card.get("value"))]

    key_traits = [
        _personalize_with_aap(_clip_text(item, max_chars=108), full_name, lead="à¤†à¤ªà¤•à¥€ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² à¤®à¥‡à¤‚ ")
        for item in key_traits[:3]
    ]
    practical_suggestions = [
        _personalize_with_aap(_clip_text(item, max_chars=108), full_name, lead="à¤†à¤ªà¤•à¥‡ à¤²à¤¿à¤ à¤¸à¥à¤à¤¾à¤µ: ")
        for item in practical_suggestions[:3]
    ]

    date_of_birth = birth_details.get("date_of_birth") or identity.get("date_of_birth")
    birthplace_city = _safe_text(birth_details.get("birthplace_city"))
    birthplace_country = _safe_text(
        birth_details.get("birthplace_country") or identity.get("country_of_residence")
    )
    birth_place = ", ".join([part for part in [birthplace_city, birthplace_country] if part])
    focus_text = _extract_focus_text(payload)

    mulank = _derive_mulank(date_of_birth)
    bhagyank = _safe_int(pythagorean.get("life_path_number"), 0)
    destiny = _safe_int(pythagorean.get("destiny_number"), 0)
    name_energy = _safe_int(chaldean.get("name_number"), 0)
    personal_year = _derive_personal_year(date_of_birth)

    summary = _personalize_with_aap(
        _clip_text(summary_text, max_chars=210, default="à¤†à¤ªà¤•à¥€ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² à¤®à¥‡à¤‚ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° à¤ªà¥à¤°à¤—à¤¤à¤¿ à¤¦à¥‹à¤¨à¥‹à¤‚ à¤•à¤¾ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¤¿à¤– à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤"),
        full_name,
    )

    return {
        "title": "Profile Snapshot (à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² à¤¸à¥à¤¨à¥ˆà¤ªà¤¶à¥‰à¤Ÿ)",
        "summary_title": "Summary (à¤¸à¤¾à¤°à¤¾à¤‚à¤¶)",
        "traits_title": "Key Traits (à¤®à¥à¤–à¥à¤¯ à¤µà¤¿à¤¶à¥‡à¤·à¤¤à¤¾à¤à¤)",
        "suggestions_title": "Practical Suggestions (à¤µà¥à¤¯à¤¾à¤µà¤¹à¤¾à¤°à¤¿à¤• à¤¸à¥à¤à¤¾à¤µ)",
        "numbers_title": "Key Numbers (à¤ªà¥à¤°à¤®à¥à¤– à¤¸à¤‚à¤–à¥à¤¯à¤¾à¤à¤)",
        "intro_line": f"{_safe_text(full_name, 'à¤†à¤ª')} à¤œà¥€, à¤¯à¤¹ à¤¸à¥‡à¤•à¥à¤¶à¤¨ à¤¸à¤¿à¤°à¥à¤« à¤†à¤ªà¤•à¥€ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² à¤•à¥‡ à¤²à¤¿à¤ à¤¤à¥ˆà¤¯à¤¾à¤° à¤•à¤¿à¤¯à¤¾ à¤—à¤¯à¤¾ à¤¹à¥ˆà¥¤",
        "summary": summary,
        "profile_facts": [
            {"label": "Name (à¤¨à¤¾à¤®)", "value": _safe_text(full_name, "--")},
            {"label": "Date of Birth (à¤œà¤¨à¥à¤® à¤¤à¤¿à¤¥à¤¿)", "value": _safe_text(date_of_birth, "--")},
            {"label": "Birth Place (à¤œà¤¨à¥à¤® à¤¸à¥à¤¥à¤¾à¤¨)", "value": _safe_text(birth_place, "--")},
            {"label": "Current Focus (à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤«à¥‹à¤•à¤¸)", "value": _safe_text(focus_text, "--")},
        ],
        "key_traits": [item for item in key_traits if item],
        "practical_suggestions": [item for item in practical_suggestions if item],
        "key_numbers": [
            {"label": "Mulank (à¤®à¥‚à¤²à¤¾à¤‚à¤•)", "value": str(mulank) if mulank > 0 else "--"},
            {"label": "Bhagyank (à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤•)", "value": str(bhagyank) if bhagyank > 0 else "--"},
            {"label": "Destiny (à¤¡à¥‡à¤¸à¥à¤Ÿà¤¿à¤¨à¥€)", "value": str(destiny) if destiny > 0 else "--"},
            {"label": "Name Energy (à¤¨à¤¾à¤® à¤Šà¤°à¥à¤œà¤¾)", "value": str(name_energy) if name_energy > 0 else "--"},
            {"label": "Personal Year (à¤µà¥à¤¯à¤•à¥à¤¤à¤¿à¤—à¤¤ à¤µà¤°à¥à¤·)", "value": str(personal_year) if personal_year > 0 else "--"},
        ],
    }


NUMBER_TRAITS_HI = {
    1: {"strength": "नेतृत्व और स्पष्ट दिशा", "risk": "अति-नियंत्रण या जिद"},
    2: {"strength": "सहयोग और संतुलन", "risk": "अनिर्णय या अति-संवेदनशीलता"},
    3: {"strength": "संचार और रचनात्मकता", "risk": "बिखराव या अधूरापन"},
    4: {"strength": "अनुशासन और संरचना", "risk": "कठोरता या धीमापन"},
    5: {"strength": "अनुकूलन और गति", "risk": "अस्थिरता या जल्दी निर्णय"},
    6: {"strength": "ज़िम्मेदारी और देखभाल", "risk": "अति-त्याग या बोझ"},
    7: {"strength": "अंतर्दृष्टि और गहराई", "risk": "अलगाव या शंका"},
    8: {"strength": "धैर्य और अधिकार", "risk": "दबाव या कठोरता"},
    9: {"strength": "साहस और ऊर्जा", "risk": "आक्रामकता या जल्दबाजी"},
    11: {"strength": "उच्च अंतर्ज्ञान", "risk": "अति-उत्साह या भ्रम"},
    22: {"strength": "व्यावहारिक महारत", "risk": "अत्यधिक जिम्मेदारी"},
}


def _metric_extremes(metrics: Dict[str, Any]) -> tuple[str, str]:
    metric_map = {
        "जीवन स्थिरता": _safe_int(metrics.get("life_stability_index"), 0),
        "निर्णय स्पष्टता": _safe_int(metrics.get("confidence_score"), 0),
        "धर्म संरेखण": _safe_int(metrics.get("dharma_alignment_score"), 0),
        "भावनात्मक संतुलन": _safe_int(metrics.get("emotional_regulation_index"), 0),
        "वित्त अनुशासन": _safe_int(metrics.get("financial_discipline_index"), 0),
        "कर्म दबाव": _safe_int(metrics.get("karma_pressure_index"), 0),
    }
    filtered = {k: v for k, v in metric_map.items() if v > 0}
    if not filtered:
        return "जीवन स्थिरता", "कर्म दबाव"
    strongest = max(filtered, key=filtered.get)
    weakest = min(filtered, key=filtered.get)
    return strongest, weakest


def _format_metric_bullets(metrics: Dict[str, Any]) -> List[str]:
    labels = [
        ("जीवन स्थिरता", "life_stability_index"),
        ("निर्णय स्पष्टता", "confidence_score"),
        ("धर्म संरेखण", "dharma_alignment_score"),
        ("भावनात्मक संतुलन", "emotional_regulation_index"),
        ("वित्त अनुशासन", "financial_discipline_index"),
        ("कर्म दबाव", "karma_pressure_index"),
    ]
    bullets = []
    for label, key in labels:
        value = _safe_int(metrics.get(key), 0)
        if value > 0:
            bullets.append(f"{label}: {value}/100")
    return bullets


def _build_premium_section_content(
    *,
    key: str,
    title: str,
    raw_section: Dict[str, Any],
    identity: Dict[str, Any],
    birth_details: Dict[str, Any],
    canonical_input: Dict[str, Any],
    nested_input: Dict[str, Any],
    numerology_core: Dict[str, Any],
    metrics: Dict[str, Any],
    pythagorean: Dict[str, Any],
    chaldean: Dict[str, Any],
) -> Dict[str, Any]:
    date_of_birth = (
        canonical_input.get("dateOfBirth")
        or birth_details.get("date_of_birth")
        or identity.get("date_of_birth")
    )
    mulank = _derive_mulank(date_of_birth)
    bhagyank = _safe_int(pythagorean.get("life_path_number"), 0)
    destiny = _safe_int(pythagorean.get("destiny_number"), 0)
    expression = _safe_int(pythagorean.get("expression_number"), 0)
    name_number = _safe_int(chaldean.get("name_number"), 0)
    personal_year = _derive_personal_year(date_of_birth)

    mobile_analysis = numerology_core.get("mobile_analysis") or {}
    email_analysis = numerology_core.get("email_analysis") or {}
    guidance = numerology_core.get("guidance_profile") or {}
    dominant_planet = numerology_core.get("dominant_planet") or {}
    swar_profile = numerology_core.get("swar_profile") or {}
    business_analysis = numerology_core.get("business_analysis") or {}

    mobile_total = _safe_int(mobile_analysis.get("mobile_total"), 0)
    mobile_vibration = _safe_int(mobile_analysis.get("mobile_vibration"), 0)
    mobile_compatibility = _safe_text(mobile_analysis.get("compatibility_status"), "neutral")
    compatibility_hi = _map_value(
        mobile_compatibility,
        {
            "supportive": "सहायक",
            "neutral": "तटस्थ",
            "challenging": "संवेदनशील",
            "mixed": "मिश्रित",
        },
    )
    dominant_digits = _safe_list(mobile_analysis.get("dominant_digits"))
    missing_digits = _safe_list(mobile_analysis.get("missing_digits"))
    repeating_digits = _safe_list(mobile_analysis.get("repeating_digits"))

    email_number = _safe_int(email_analysis.get("email_number"), 0)

    supportive_numbers = _safe_list(guidance.get("supportiveNumbers"))
    caution_numbers = _safe_list(guidance.get("cautionNumbers"))
    colors = _map_list(guidance.get("colors"), COLOR_MAP)
    gemstone = _map_value(guidance.get("gemstone"), GEM_MAP)
    mantra = _hindi_only_text(guidance.get("mantra"), "उपलब्ध नहीं")
    direction = _map_value(guidance.get("direction"), {
        "East": "पूर्व",
        "West": "पश्चिम",
        "North": "उत्तर",
        "South": "दक्षिण",
        "North-East": "उत्तर-पूर्व",
        "North-West": "उत्तर-पश्चिम",
        "South-East": "दक्षिण-पूर्व",
        "South-West": "दक्षिण-पश्चिम",
    })
    day = _map_value(
        guidance.get("day"),
        {
            "Sunday": "रविवार",
            "Monday": "सोमवार",
            "Tuesday": "मंगलवार",
            "Wednesday": "बुधवार",
            "Thursday": "गुरुवार",
            "Friday": "शुक्रवार",
            "Saturday": "शनिवार",
        },
    )

    planet_hi = _map_value(dominant_planet.get("planet"), PLANET_MAP)
    qualities_hi = _map_list(dominant_planet.get("qualities"), QUALITY_MAP)
    element_hi = _map_value(dominant_planet.get("element"), {
        "Fire": "अग्नि",
        "Water": "जल",
        "Air": "वायु",
        "Earth": "पृथ्वी",
    })

    focus_text = _normalize_focus_text(
        canonical_input.get("currentProblem")
        or canonical_input.get("focusArea")
        or canonical_input.get("focus")
        or (nested_input.get("focus") or {}).get("life_focus")
    )
    goals_raw = (
        canonical_input.get("goals")
        or canonical_input.get("goal")
        or canonical_input.get("primaryGoal")
        or (canonical_input.get("preferences") or {}).get("primary_goal")
        or (nested_input.get("preferences") or {}).get("primary_goal")
    )
    goals = _join_premium_values(goals_raw, "उपलब्ध नहीं")
    alignment_state = _alignment_state([mulank, bhagyank, name_number, mobile_vibration])
    strongest_metric, weakest_metric = _metric_extremes(metrics)

    summary = ""
    narrative = ""
    risk = ""
    action = ""
    bullets: List[str] = []
    profile_fields: List[Dict[str, str]] = []

    if key == "full_identity_profile":
        full_name = _sanitize_premium_value(canonical_input.get("fullName") or identity.get("full_name"))
        dob = _sanitize_premium_value(date_of_birth)
        mobile = _sanitize_premium_value(canonical_input.get("mobileNumber") or identity.get("mobile_number"))
        city = _sanitize_premium_value(canonical_input.get("city") or canonical_input.get("currentCity") or identity.get("city"))
        gender = _sanitize_premium_value(canonical_input.get("gender") or identity.get("gender"))
        email = _sanitize_premium_value(canonical_input.get("email") or identity.get("email"))
        focus = focus_text
        name_variations_raw = canonical_input.get("nameVariations") or identity.get("name_variations") or []
        name_variations_list = [
            item
            for item in _safe_list(name_variations_raw)
            if _sanitize_premium_value(item, "") and _sanitize_premium_value(item, "") != full_name
        ]
        name_variations = _join_premium_values(name_variations_list, "उपलब्ध नहीं")
        birth_place = ", ".join(
            [part for part in [
                _safe_text(birth_details.get("birthplace_city")),
                _safe_text(birth_details.get("birthplace_country")),
            ] if part]
        )
        birth_time = _sanitize_premium_value(
            (nested_input.get("birth_details") or {}).get("time_of_birth")
            or birth_details.get("time_of_birth")
        )
        birth_details_text = " | ".join(
            [
                f"तिथि {dob}" if dob != "उपलब्ध नहीं" else "",
                f"समय {birth_time}" if birth_time != "उपलब्ध नहीं" else "",
                f"स्थान {birth_place}" if birth_place else "",
            ]
        ).strip(" |") or "उपलब्ध नहीं"

        profile_fields = [
            {"label": "नाम", "value": full_name},
            {"label": "जन्मतिथि", "value": dob},
            {"label": "मोबाइल", "value": mobile},
            {"label": "शहर", "value": city},
            {"label": "लिंग", "value": gender},
            {"label": "ईमेल", "value": email},
            {"label": "फोकस", "value": focus},
            {"label": "लक्ष्य", "value": goals},
            {"label": "नाम विकल्प", "value": name_variations},
            {"label": "जन्म विवरण", "value": birth_details_text},
        ]

        summary = "प्रोफ़ाइल आपके दिए गए विवरण और अंक-ऊर्जाओं पर आधारित है।"
        narrative = (
            f"मूलांक { _format_number(mulank) } और भाग्यांक { _format_number(bhagyank) } आपकी मूल दिशा तय करते हैं। "
            f"नाम अंक { _format_number(name_number) } और मोबाइल कंपन { _format_number(mobile_vibration) } आपके व्यवहार और संचार शैली को आकार देते हैं। "
            f"वर्तमान फोकस: {focus}।"
        )
        risk = "यदि लक्ष्य स्पष्ट नहीं होंगे तो ऊर्जा बिखर सकती है।"
        action = "एक मुख्य लक्ष्य चुनकर 21-दिवसीय अनुशासन तय करें।"
        bullets = [
            f"सिस्टम एलाइनमेंट: {alignment_state}",
            f"व्यक्तिगत वर्ष: {_format_number(personal_year)}",
        ]

    elif key == "core_numbers":
        summary = f"मूलांक { _format_number(mulank) } और भाग्यांक { _format_number(bhagyank) } आपके मुख्य आधार हैं।"
        narrative = (
            f"नाम अंक { _format_number(name_number) }, मोबाइल कंपन { _format_number(mobile_vibration) } और ईमेल ऊर्जा { _format_number(email_number) } "
            f"मिलकर आपकी निर्णय-गति और सार्वजनिक छवि को तय करते हैं।"
        )
        risk = "अंकों में दूरी होने पर निर्णयों में खिंचाव महसूस हो सकता है।"
        action = "सबसे स्थिर अंक के अनुरूप दिनचर्या और प्राथमिकताएँ सेट करें।"
        bullets = [
            f"डेस्टिनी: {_format_number(destiny)}",
            f"एक्सप्रेशन: {_format_number(expression)}",
            f"एलाइनमेंट: {alignment_state}",
        ]

    elif key == "advanced_name_numerology":
        summary = f"नाम अंक { _format_number(name_number) } आपकी अभिव्यक्ति ऊर्जा को परिभाषित करता है।"
        narrative = (
            f"नाम ऊर्जा आपके संवाद, भरोसे और पहचान की तीव्रता तय करती है। "
            f"यदि नाम अंक { _format_number(name_number) } और भाग्यांक { _format_number(bhagyank) } में सामंजस्य है, तो स्पष्टता बढ़ती है।"
        )
        risk = "नाम की अलग-अलग वर्तनी पहचान को कमजोर कर सकती है।"
        action = "एक स्थिर वर्तनी अपनाकर सभी दस्तावेज़ों में वही उपयोग करें।"
        bullets = [f"समर्थक अंक: {_join_numbers(supportive_numbers, default='-')}"]

    elif key == "karmic_name_analysis":
        summary = "नाम ऊर्जा से जुड़े कर्मिक पैटर्न इस अनुभाग में सामने आते हैं।"
        narrative = (
            f"नाम अंक { _format_number(name_number) } और भाग्यांक { _format_number(bhagyank) } बार-बार आने वाली सीखों को दर्शाते हैं। "
            f"इन पैटर्न को समझकर आप अपनी प्रतिक्रिया-शैली को संतुलित कर सकते हैं।"
        )
        risk = "पुराने पैटर्न पर टिके रहने से प्रगति धीमी हो सकती है।"
        action = "हर सप्ताह एक व्यवहारिक सुधार तय कर उसका ट्रैक रखें।"
        bullets = [f"वर्तमान फोकस: {focus_text}"]

    elif key == "planetary_name_support_mapping":
        summary = f"नाम ऊर्जा पर {planet_hi} का प्रभाव प्रमुख रूप से दिखता है।"
        narrative = (
            f"यह प्रभाव {qualities_hi} जैसे गुणों को सक्रिय करता है और नाम से जुड़े निर्णयों में दिशा देता है। "
            f"तत्व: {element_hi}।"
        )
        risk = "ग्रह-समर्थन का अति-उपयोग निर्णयों को कठोर बना सकता है।"
        action = f"{planet_hi} के दिन ({_safe_text(day) or '—'}) और दिशा ({direction}) में महत्त्वपूर्ण काम करें।"
        bullets = [f"मुख्य गुण: {qualities_hi}"]

    elif key == "multi_name_correction_options":
        summary = "एक से अधिक नाम विकल्पों में ऊर्जा का सूक्ष्म अंतर दिखता है।"
        narrative = (
            "विकल्पों की ऊर्जा अलग-अलग सामाजिक प्रभाव देती है। चुने हुए विकल्प को स्थिर रखना ही सर्वोत्तम परिणाम देता है।"
        )
        risk = "बहुत अधिक विकल्प पहचान में भ्रम पैदा कर सकते हैं।"
        action = "2 से 3 व्यावहारिक विकल्प चुनकर उसी पर टिके रहें।"
        bullets = [f"विकल्प: {_join_premium_values(canonical_input.get('nameVariations') or [], 'उपलब्ध नहीं')}"]

    elif key == "name_optimization_scoring":
        summary = f"नाम अनुकूलन स्कोर का संकेत: {alignment_state}।"
        narrative = (
            f"नाम अंक { _format_number(name_number) } और मूलांक { _format_number(mulank) } का सामंजस्य स्कोर को तय करता है। "
            f"मज़बूत क्षेत्र: {strongest_metric}, ध्यान योग्य: {weakest_metric}।"
        )
        risk = "यदि स्कोर कमजोर है तो पहचान-विश्वास में कमी आ सकती है।"
        action = "नाम में छोटे सुधार करके ऊर्जा को संतुलित रखें।"
        bullets = [f"समर्थक अंक: {_join_numbers(supportive_numbers, default='-')}"]

    elif key == "prefix_suffix_advanced_logic":
        summary = "प्रिफिक्स/सुफिक्स नाम ऊर्जा को सूक्ष्म रूप से बदलते हैं।"
        narrative = (
            f"नाम अंक { _format_number(name_number) } को मूलांक { _format_number(mulank) } या भाग्यांक { _format_number(bhagyank) } के साथ मिलाने पर सामंजस्य बेहतर हो सकता है।"
        )
        risk = "अत्यधिक जोड़ से नाम की स्पष्टता कम हो सकती है।"
        action = "केवल आवश्यक और छोटे जोड़ ही अपनाएँ।"
        bullets = [f"लक्ष्य सामंजस्य: {alignment_state}"]

    elif key == "mobile_numerology_advanced":
        summary = f"मोबाइल योगफल { _format_number(mobile_total) } और कंपन { _format_number(mobile_vibration) } प्रमुख संकेत देते हैं।"
        narrative = (
            f"मोबाइल कंपन और जीवन अंक का मेल {compatibility_hi} प्रकृति दिखाता है। "
            f"यह संचार शैली और निर्णय गति पर असर डालता है।"
        )
        risk = "यदि मेल कम है तो संवाद में असंगति दिख सकती है।"
        action = "महत्वपूर्ण कॉल/निर्णय उसी समय करें जब आप सबसे स्थिर हों।"
        bullets = [f"प्रमुख अंक: {_join_numbers(dominant_digits, default='-')}"]

    elif key == "mobile_digit_micro_analysis":
        summary = "मोबाइल अंकों के वितरण से सूक्ष्म ऊर्जा पैटर्न बनता है।"
        narrative = (
            f"प्रमुख अंक {_join_numbers(dominant_digits, default='-')} दोहराव को दर्शाते हैं, जबकि अनुपस्थित अंक {_join_numbers(missing_digits, default='-')} संभावित खालीपन दिखाते हैं।"
        )
        risk = "अत्यधिक दोहराव से एक ही व्यवहार-पैटर्न बढ़ सकता है।"
        action = "अनुपस्थित अंकों से जुड़ी आदतों पर ध्यान दें।"
        bullets = [
            f"दोहराव: {_join_numbers(repeating_digits, default='-')}",
            f"अनुपस्थित: {_join_numbers(missing_digits, default='-')}",
        ]

    elif key == "mobile_energy_forecasting":
        summary = "मोबाइल कंपन का प्रभाव वर्तमान वार्षिक चक्र से जुड़ता है।"
        narrative = (
            f"व्यक्तिगत वर्ष {_format_number(personal_year)} में मोबाइल कंपन { _format_number(mobile_vibration) } निर्णयों की गति तय कर सकता है। "
            "यह चरण संचार की स्पष्टता पर निर्भर रहेगा।"
        )
        risk = "अत्यधिक तेज़ निर्णय असंतुलन पैदा कर सकते हैं।"
        action = "सप्ताह में एक दिन संचार समीक्षा और प्राथमिकता तय करें।"

    elif key == "name_mobile_alignment":
        summary = f"नाम अंक { _format_number(name_number) } और मोबाइल कंपन { _format_number(mobile_vibration) } का संबंध {alignment_state} है।"
        narrative = (
            "जब नाम और मोबाइल ऊर्जा एक दिशा में हों, तो आपकी सार्वजनिक छवि अधिक स्थिर रहती है।"
        )
        risk = "मेल कमजोर होने पर बाहरी संदेश असंगत हो सकता है।"
        action = "एक स्थिर संवाद शैली अपनाएँ और उसी पर टिके रहें।"

    elif key == "dob_name_alignment":
        summary = f"जन्म अंक { _format_number(mulank) } और नाम अंक { _format_number(name_number) } के बीच सामंजस्य देखा जाता है।"
        narrative = "जन्म ऊर्जा आपकी स्वाभाविक प्रतिक्रिया तय करती है और नाम ऊर्जा बाहरी प्रस्तुति को संतुलित करती है।"
        risk = "दोनों में अधिक दूरी होने पर आत्मविश्वास में गिरावट हो सकती है।"
        action = "प्रोफ़ाइल में वही नाम-वर्तनी रखें जो सबसे स्थिर लगे।"

    elif key == "dob_mobile_alignment":
        summary = f"जन्म अंक { _format_number(mulank) } और मोबाइल कंपन { _format_number(mobile_vibration) } का मेल {alignment_state} है।"
        narrative = "यह मेल रोज़मर्रा की प्रतिक्रिया और संचार ऊर्जा को प्रभावित करता है।"
        risk = "मेल कमजोर होने पर थकान और निर्णय-भ्रम बढ़ सकता है।"
        action = "महत्त्वपूर्ण कॉल से पहले 2-3 मिनट का मानसिक रीसेट रखें।"

    elif key == "full_system_alignment_score":
        summary = f"पूर्ण सिस्टम एलाइनमेंट स्थिति: {alignment_state}।"
        narrative = (
            f"मूलांक, भाग्यांक, नाम अंक और मोबाइल कंपन का संयुक्त व्यवहार आपकी कुल स्थिरता तय करता है। "
            f"मज़बूत क्षेत्र: {strongest_metric}, सुधार क्षेत्र: {weakest_metric}।"
        )
        risk = "कमजोर क्षेत्र को नजरअंदाज करने से परिणाम धीमे हो सकते हैं।"
        action = "सुधार क्षेत्र पर 21-दिवसीय अनुशासन लागू करें।"
        bullets = _format_metric_bullets(metrics)[:4]

    elif key == "strength_vs_risk_matrix":
        summary = f"ताकत: {strongest_metric} | जोखिम: {weakest_metric}"
        narrative = "यह मैट्रिक्स बताता है कि किस क्षेत्र में स्वाभाविक समर्थन है और किसमें सतर्कता चाहिए।"
        risk = f"यदि {weakest_metric} कमजोर रहा तो प्रगति धीमी हो सकती है।"
        action = f"{weakest_metric} से जुड़ा साप्ताहिक रिव्यू और सुधार तय करें।"

    elif key == "life_area_scores":
        summary = "जीवन-क्षेत्र स्कोर आपके मुख्य क्षेत्रों की स्थिति दिखाते हैं।"
        narrative = "स्कोर यह बताते हैं कि किस क्षेत्र में स्थिरता है और कहाँ सुधार की जरूरत है।"
        risk = "कम स्कोर वाले क्षेत्रों में निर्णयों का दबाव बढ़ सकता है।"
        action = "प्राथमिकता वाले 2 क्षेत्रों पर फोकस रखें।"
        bullets = _format_metric_bullets(metrics)

    elif key == "mulank_deep_analysis":
        trait = NUMBER_TRAITS_HI.get(mulank, {"strength": "स्थिरता", "risk": "अनिश्चितता"})
        summary = f"मूलांक { _format_number(mulank) } आपकी स्वाभाविक प्रतिक्रिया तय करता है।"
        narrative = f"इस अंक से {trait['strength']} सक्रिय होती है और निर्णयों में दिशा मिलती है।"
        risk = f"यदि यह असंतुलित रहा तो {trait['risk']} बढ़ सकती है।"
        action = "रोज़ाना एक स्थिर आदत जोड़कर संतुलन रखें।"

    elif key == "bhagyank_destiny_roadmap":
        trait = NUMBER_TRAITS_HI.get(bhagyank, {"strength": "दिशा", "risk": "भटकाव"})
        summary = f"भाग्यांक { _format_number(bhagyank) } आपकी दीर्घकालिक दिशा दिखाता है।"
        narrative = f"यह अंक आपको {trait['strength']} की ओर ले जाता है और जीवन-थीम तय करता है।"
        risk = f"गलत समय पर निर्णय लेने से {trait['risk']} हो सकता है।"
        action = "लक्ष्यों को व्यक्तिगत वर्ष के साथ संरेखित करें।"

    elif key == "lo_shu_grid_advanced":
        summary = f"उपस्थित अंक: {_join_numbers(_safe_list(numerology_core.get('loshu_grid', {}).get('present_numbers')), default='-')} | अनुपस्थित अंक: {_join_numbers(_safe_list(numerology_core.get('loshu_grid', {}).get('missing_numbers')), default='-')}"
        narrative = "लो-शू ग्रिड ऊर्जा संतुलन और व्यवहारिक झुकाव बताता है।"
        risk = "अनुपस्थित अंक वाले क्षेत्रों में अनुशासन की कमी हो सकती है।"
        action = "अनुपस्थित अंक से जुड़ी आदतों पर छोटे सुधार लागू करें।"

    elif key == "planetary_influence_mapping":
        summary = f"प्रमुख ग्रह प्रभाव: {planet_hi}"
        narrative = f"{planet_hi} आपके निर्णय-स्वर और ऊर्जा प्रवाह को प्रभावित करता है।"
        risk = "अत्यधिक ग्रह-प्रभाव से प्रतिक्रिया कठोर हो सकती है।"
        action = f"{planet_hi} के अनुकूल दिन/दिशा का समर्थन लें।"

    elif key == "current_planetary_phase":
        summary = f"वर्तमान चरण {planet_hi} ऊर्जा के साथ जुड़ा है।"
        narrative = "इस चरण में निर्णयों में स्पष्टता और स्थिरता बढ़ाने पर ध्यान देना चाहिए।"
        risk = "अचानक बदलाव से असंतुलन बढ़ सकता है।"
        action = "हर सप्ताह एक स्थिर निर्णय नियम लागू करें।"

    elif key == "upcoming_transit_highlights":
        summary = "आगामी गोचर संकेत निर्णय समय को प्रभावित कर सकते हैं।"
        narrative = "आने वाले 90 दिनों में योजना और अनुशासन से प्रगति अधिक स्थिर होगी।"
        risk = "बिना योजना के बड़े निर्णय जोखिम बढ़ा सकते हैं।"
        action = "महत्वपूर्ण निर्णयों से पहले 48 घंटे का विचार समय रखें।"

    elif key == "personal_year_analysis":
        trait = NUMBER_TRAITS_HI.get(personal_year, {"strength": "परिवर्तन", "risk": "अनिश्चितता"})
        summary = f"व्यक्तिगत वर्ष { _format_number(personal_year) } का मुख्य संकेत {trait['strength']} है।"
        narrative = "इस वर्ष का टोन आपकी प्राथमिकताओं और गति को तय करता है।"
        risk = f"यदि यह असंतुलित रहा तो {trait['risk']} बढ़ सकती है।"
        action = "साल की शुरुआत में तीन मुख्य लक्ष्य तय करें।"

    elif key == "monthly_cycle_analysis":
        summary = "मासिक चक्र में ऊर्जा का उतार-चढ़ाव अपेक्षित है।"
        narrative = "हर माह के पहले सप्ताह को योजना, दूसरे को क्रियान्वयन और तीसरे को समीक्षा के लिए रखें।"
        risk = "अनियमित चक्र से फोकस टूट सकता है।"
        action = "मासिक लक्ष्य और समीक्षा निश्चित दिन पर करें।"

    elif key == "critical_decision_windows":
        summary = "निर्णय समय-खिड़कियाँ स्थिरता बनाए रखने में मदद करती हैं।"
        narrative = f"{day or 'उचित दिन'} और {direction} दिशा में किए गए निर्णय अधिक सहायक हो सकते हैं।"
        risk = "जल्दबाज़ी में निर्णय लेने से जोखिम बढ़ सकता है।"
        action = "महत्वपूर्ण निर्णयों के लिए पूर्व-निर्धारित समय चुनें।"

    elif key == "wealth_cycle_analysis":
        summary = "धन चक्र का आधार वित्त अनुशासन है।"
        narrative = f"वित्त अनुशासन स्कोर { _safe_int(metrics.get('financial_discipline_index'), 0) }/100 है, जो गति और स्थिरता बताता है।"
        risk = "यदि खर्च असंतुलित रहे तो बचत प्रभावित होगी।"
        action = "साप्ताहिक वित्त समीक्षा और एक बचत नियम तय करें।"

    elif key == "career_growth_timeline":
        summary = "करियर विकास स्थिरता और निर्णय स्पष्टता से जुड़ा है।"
        narrative = f"जीवन स्थिरता { _safe_int(metrics.get('life_stability_index'), 0) } और निर्णय स्पष्टता { _safe_int(metrics.get('confidence_score'), 0) }/100 के अनुसार ग्रोथ गति तय होगी।"
        risk = "लक्ष्य अस्पष्ट होने पर ग्रोथ धीमी हो सकती है।"
        action = "त्रैमासिक लक्ष्य और कौशल-सुधार योजना बनाएं।"

    elif key == "relationship_timing_patterns":
        summary = "संबंधों की टाइमिंग भावनात्मक संतुलन से जुड़ी है।"
        narrative = f"भावनात्मक संतुलन स्कोर { _safe_int(metrics.get('emotional_regulation_index'), 0) }/100 है, जिससे संबंधों का प्रवाह तय होगा।"
        risk = "अस्थिर भावनात्मक चक्र से गलतफहमियाँ बढ़ सकती हैं।"
        action = "नियमित संवाद और स्पष्ट सीमाएँ तय करें।"

    elif key == "dynamic_lucky_numbers":
        summary = "गतिशील शुभ अंक आपके वर्तमान चक्र में सहायता देते हैं।"
        narrative = "इन अंकों का उपयोग निर्णय और योजना के दौरान सहायक रह सकता है।"
        risk = "अंधा पालन करने से निर्णय गुणवत्ता घट सकती है।"
        action = "शुभ अंकों को प्राथमिकता संकेत की तरह उपयोग करें।"
        bullets = [f"शुभ अंक: {_join_numbers(supportive_numbers, default='-')}"]

    elif key == "situational_caution_numbers":
        summary = "कुछ अंक स्थितिजन्य सावधानी की मांग करते हैं।"
        narrative = "इन अंकों के प्रभाव में निर्णय अधिक सोच-समझकर करें।"
        risk = "जल्दबाजी से नुकसान हो सकता है।"
        action = "सावधानी अंकों के दिनों में बड़े फैसले टालें।"
        bullets = [f"सावधानी अंक: {_join_numbers(caution_numbers, default='-')}"]

    elif key == "neutral_number_strategy_usage":
        neutral_numbers = _dedupe_phrases([str(item) for item in [mulank, bhagyank, name_number] if item])
        summary = "तटस्थ अंक स्थिरता बनाए रखने में सहायक होते हैं।"
        narrative = "इन अंकों का उपयोग नियमित कार्यों और छोटे निर्णयों में किया जा सकता है।"
        risk = "तटस्थ अंकों का अत्यधिक उपयोग ऊर्जा को स्थिर कर सकता है।"
        action = "तटस्थ अंकों को बैकअप संकेत की तरह रखें।"
        bullets = [f"तटस्थ अंक: {', '.join(neutral_numbers) if neutral_numbers else 'उपलब्ध नहीं'}"]

    elif key == "color_strategy":
        summary = "रंग रणनीति मानसिक संतुलन को मजबूत करती है।"
        narrative = f"आपकी ऊर्जा के लिए सुझाए गए रंग: {colors}।"
        risk = "अत्यधिक गहरे रंग ऊर्जा को भारी बना सकते हैं।"
        action = "कपड़ों और कार्यस्थल में सुझाए गए रंग शामिल करें।"

    elif key == "energy_objects_recommendation":
        summary = "ऊर्जा वस्तुएँ स्थिरता और फोकस को सहारा देती हैं।"
        narrative = f"उपयुक्त रत्न/ऊर्जा वस्तु: {gemstone}।"
        risk = "गलत चयन से अपेक्षित लाभ नहीं मिलेगा।"
        action = "उपयोग से पहले उचित सलाह और समय तय करें।"

    elif key == "advanced_remedies_engine":
        summary = "उन्नत उपाय आपके कमजोर क्षेत्रों को संतुलित करते हैं।"
        narrative = f"दिशा {direction}, रंग {colors} और मंत्र का संयुक्त उपयोग ऊर्जा स्थिर करता है।"
        risk = "अनियमितता से असर कम हो सकता है।"
        action = "21 दिनों का नियमित उपाय चक्र अपनाएँ।"
        bullets = [
            f"नाम सुधार: {_format_number(name_number)}",
            f"अंक रणनीति: {_join_numbers(supportive_numbers, default='-')}",
            f"मंत्र: {mantra}",
            f"दिशा मार्गदर्शन: {direction}",
            f"स्थान संरेखण: {direction}",
        ]

    elif key == "business_brand_naming":
        business_number = _safe_int(business_analysis.get("business_number"), 0)
        summary = "व्यवसाय/ब्रांड नाम का अंक व्यावसायिक प्रभाव तय करता है।"
        narrative = f"ब्रांड अंक { _format_number(business_number) } और नाम अंक { _format_number(name_number) } का मेल भरोसा बढ़ाता है।"
        risk = "असंतुलित नाम से ब्रांड स्पष्टता घट सकती है।"
        action = "ब्रांड नाम को स्थिर और यादगार रखें।"

    elif key == "signature_energy_analysis":
        dominant_vowel = _hindi_only_text(swar_profile.get("dominantVowel"), "उपलब्ध नहीं")
        dominant_quality = _hindi_only_text(swar_profile.get("dominantQuality"), "उपलब्ध नहीं")
        summary = "हस्ताक्षर ऊर्जा सूक्ष्म पहचान संकेत देती है।"
        narrative = (
            f"प्रमुख स्वर {dominant_vowel or '—'} आपकी ऊर्जा टोन बनाता है और गुणवत्ता {dominant_quality or 'उपलब्ध नहीं'} संकेत करती है।"
        )
        risk = "यदि हस्ताक्षर बदलते रहें तो पहचान अस्थिर हो सकती है।"
        action = "एक स्थिर हस्ताक्षर पैटर्न अपनाएँ।"

    elif key == "mobile_optimization_strategy":
        summary = "मोबाइल अनुकूलन रणनीति संचार स्थिरता बढ़ाती है।"
        narrative = (
            f"मोबाइल कंपन { _format_number(mobile_vibration) } और जीवन अंक { _format_number(bhagyank) } के अनुसार उपयोग पैटर्न तय करें।"
        )
        risk = "अनियमित उपयोग से फोकस टूट सकता है।"
        action = "महत्वपूर्ण कॉल के लिए निश्चित समय स्लॉट और उपयोग सीमा तय करें।"
        bullets = [f"प्रमुख अंक: {_join_numbers(dominant_digits, default='-')}"]

    elif key == "life_strategy_recommendations":
        summary = "जीवन रणनीति आपके लक्ष्यों और अंक-ऊर्जा को जोड़ती है।"
        narrative = f"वर्तमान फोकस {focus_text} और लक्ष्य {goals} के अनुसार 90-दिवसीय योजना बनाएं।"
        risk = "लक्ष्य बिखरे होने पर ऊर्जा कमजोर हो सकती है।"
        action = "एक मुख्य लक्ष्य चुनकर शेष लक्ष्यों को सहायक भूमिका दें।"
        bullets = [
            "अल्पकाल: अगले 14 दिन का स्पष्ट लक्ष्य",
            "मध्यमकाल: 60 दिन की प्रगति तालिका",
            "दीर्घकाल: 6 माह का संरेखण लक्ष्य",
        ]

    elif key == "priority_action_plan":
        summary = "प्राथमिक कार्य योजना अगले 30-90 दिनों का रोडमैप देती है।"
        narrative = f"कमजोर क्षेत्र {weakest_metric} पर आधारित तीन प्राथमिक कदम तय करें।"
        risk = "बिना प्राथमिकता के प्रयास बिखर सकते हैं।"
        action = "हर सप्ताह एक measurable सुधार दर्ज करें।"
        bullets = [
            f"7 दिन: {weakest_metric} पर छोटा सुधार",
            "30 दिन: अनुशासन आधारित ट्रैकिंग",
            "90 दिन: परिणाम समीक्षा और नई दिशा",
        ]

    elif key == "risk_alerts_and_mitigation":
        summary = "जोखिम चेतावनी कमजोर क्षेत्रों में सतर्कता देती है।"
        narrative = f"{weakest_metric} कमजोर होने पर निर्णयों में दबाव बढ़ सकता है।"
        risk = "यदि इसे नजरअंदाज किया तो प्रगति धीमी होगी।"
        action = "सावधानी अंकों और स्थिर रूटीन से संतुलन रखें।"
        bullets = [f"सावधानी अंक: {_join_numbers(caution_numbers, default='-')}"]

    elif key == "premium_summary_narrative":
        summary = "प्रीमियम सार आपके पूरे प्रोफ़ाइल का निष्कर्ष है।"
        narrative = (
            f"मूलांक { _format_number(mulank) }, भाग्यांक { _format_number(bhagyank) }, नाम अंक { _format_number(name_number) } "
            f"और मोबाइल कंपन { _format_number(mobile_vibration) } मिलकर आपकी जीवन-दिशा तय करते हैं। "
            f"मुख्य फोकस {focus_text} और लक्ष्य {goals} हैं।"
        )
        risk = f"कमजोर क्षेत्र {weakest_metric} पर सतर्कता आवश्यक है।"
        action = "साप्ताहिक समीक्षा और अनुशासन से स्थिर प्रगति सुनिश्चित करें।"

    else:
        summary = f"{title} के लिए प्रमुख संकेत इस अनुभाग में दिए गए हैं।"
        narrative = "यह अनुभाग आपके इनपुट और संख्यात्मक ऊर्जा के आधार पर तैयार किया गया है।"
        risk = "यदि अनुशासन कमजोर हुआ तो प्रभाव घट सकता है।"
        action = "एक स्थिर रूटीन अपनाकर दिशा स्पष्ट रखें।"

    cards = [
        {"label": "सारांश", "value": _sanitize_premium_value(summary)},
        {"label": "जोखिम संकेत", "value": _sanitize_premium_value(risk)},
        {"label": "कार्रवाई सुझाव", "value": _sanitize_premium_value(action)},
    ]

    return {
        "summary": summary,
        "narrative": _sanitize_premium_value(narrative),
        "cards": cards,
        "bullets": [item for item in bullets if _safe_text(item)],
        "profile_fields": profile_fields,
    }

def _as_uri(path: Path) -> str:
    if path.exists():
        return path.resolve().as_uri()
    return ""


def _as_image_src(path: Path, max_dim: int = 220) -> str:
    if not path.exists():
        return ""
    try:
        from PIL import Image

        with Image.open(path) as image:
            image = image.copy()
            image.thumbnail((max_dim, max_dim))
            buffer = BytesIO()
            has_alpha = (
                "A" in image.getbands()
                or image.info.get("transparency") is not None
            )
            if has_alpha:
                if image.mode not in ("RGBA", "LA"):
                    image = image.convert("RGBA")
                image.save(
                    buffer,
                    format="PNG",
                    optimize=True,
                    compress_level=9,
                )
                mime = "image/png"
            else:
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.save(
                    buffer,
                    format="JPEG",
                    quality=68,
                    optimize=True,
                    progressive=True,
                )
                mime = "image/jpeg"
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "image/png"
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return _as_uri(path)
        return f"data:{mime};base64,{encoded}"

    if not encoded:
        return _as_uri(path)
    return f"data:{mime};base64,{encoded}"


def _as_background_src(path: Path, max_dim: int = 680) -> str:
    if not path.exists():
        return ""
    try:
        from PIL import Image

        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((max_dim, max_dim))
            buffer = BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=44,
                optimize=True,
                progressive=True,
            )
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return _as_uri(path)


def _build_context(data: Dict[str, Any], watermark: bool) -> Dict[str, Any]:
    payload = data or {}
    identity = payload.get("identity") or {}
    birth_details = payload.get("birth_details") or {}
    meta = payload.get("meta") or {}

    metrics = payload.get("core_metrics") or {}
    metric_explanations = payload.get("metric_explanations") or {}
    metrics_spine = payload.get("metrics_spine") or {}
    numerology_core = payload.get("numerology_core") or {}

    primary_insight = payload.get("primary_insight") or {}
    architecture_text = payload.get("numerology_architecture") or {}
    archetype = payload.get("archetype_intelligence") or {}
    loshu = payload.get("loshu_diagnostic") or {}
    planetary = payload.get("planetary_mapping") or {}
    deficit_model = payload.get("structural_deficit_model") or {}
    circadian = payload.get("circadian_alignment") or {}
    environment = payload.get("environment_alignment") or {}
    vedic = payload.get("vedic_remedy_protocol") or {}
    execution = payload.get("execution_plan") or {}
    report_sections = payload.get("report_sections") if isinstance(payload.get("report_sections"), list) else []
    report_blueprint = payload.get("report_blueprint") or {}
    canonical_input = payload.get("normalizedInput") if isinstance(payload.get("normalizedInput"), dict) else {}
    deterministic = payload.get("deterministic") if isinstance(payload.get("deterministic"), dict) else {}
    nested_input = (
        deterministic.get("normalizedInputNested")
        if isinstance(deterministic.get("normalizedInputNested"), dict)
        else {}
    )
    plan_tier = _safe_text(
        meta.get("plan_tier")
        or report_blueprint.get("plan_tier"),
        "basic",
    ).lower()

    has_structured_basic_sections = any(
        isinstance(item, dict) and _safe_text(item.get("key")).startswith("basic_")
        for item in report_sections
    )

    if plan_tier == "basic" and has_structured_basic_sections:
        section_payloads = _legacy_sections_to_payloads(report_sections)
    else:
        section_payloads = payload.get("section_payloads") or {}
        if not isinstance(section_payloads, dict) or not section_payloads:
            section_payloads = _legacy_sections_to_payloads(report_sections)

    pythagorean = numerology_core.get("pythagorean") or {}
    chaldean = numerology_core.get("chaldean") or {}
    loshu_grid = numerology_core.get("loshu_grid") or {}

    # Keep BASIC concise so each section reads as a clean waterfall page.
    narrative_limit = 360 if plan_tier == "basic" else 580
    card_limit = 120 if plan_tier == "basic" else 140

    foundation = architecture_text.get("foundation") or pythagorean.get("life_path_number")
    left_pillar = architecture_text.get("left_pillar") or pythagorean.get("destiny_number")
    right_pillar = architecture_text.get("right_pillar") or pythagorean.get("expression_number")
    facade = architecture_text.get("facade") or chaldean.get("name_number")

    metric_rows: List[Dict[str, Any]] = []
    radar_labels: List[str] = []
    radar_values: List[int] = []

    for metric in METRIC_CONFIG:
        key = metric["key"]
        value = max(0, min(100, _safe_int(metrics.get(key), 50)))
        details = metric_explanations.get(key) if isinstance(metric_explanations, dict) else {}
        details = details if isinstance(details, dict) else {}

        meaning = _clip_text(
            details.get("meaning"),
            max_chars=card_limit,
            default="à¤¯à¤¹ score numerology à¤”à¤° intake data à¤¸à¥‡ à¤¨à¤¿à¤•à¤²à¤¾ deterministic signal à¤¹à¥ˆà¥¤",
        )
        driver = _clip_text(
            details.get("driver"),
            max_chars=card_limit,
            default="Primary driver inference profile à¤”à¤° behavior signals à¤ªà¤° à¤†à¤§à¤¾à¤°à¤¿à¤¤ à¤¹à¥ˆà¥¤",
        )
        risk = _clip_text(
            details.get("risk"),
            max_chars=card_limit,
            default="à¤‡à¤¸ area à¤®à¥‡à¤‚ low score execution quality à¤•à¥‹ à¤•à¤® à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        )
        improvement = _clip_text(
            details.get("improvement"),
            max_chars=card_limit,
            default="à¤‡à¤¸ metric à¤•à¥‡ à¤²à¤¿à¤ measurable 21-day practice install à¤•à¤°à¥‡à¤‚à¥¤",
        )

        metric_rows.append(
            {
                "label": metric["label"],
                "value": value,
                "status": _status_label(_safe_text(details.get("status"), _status_from_score(value))),
                "meaning": _hindi_major_text(meaning),
                "driver": _hindi_major_text(driver),
                "risk": _hindi_major_text(risk),
                "improvement": _hindi_major_text(improvement),
            }
        )

        radar_labels.append(metric["chart_label"])
        radar_values.append(value)

    present_numbers = _safe_list(loshu.get("present_numbers") or loshu_grid.get("present_numbers"))
    missing_numbers = _safe_list(loshu.get("missing_numbers") or loshu_grid.get("missing_numbers"))

    center_presence = loshu.get("center_presence")
    if isinstance(center_presence, bool):
        center_present = center_presence
    else:
        center_present = 5 in {_safe_int(item, 0) for item in present_numbers}

    architecture_svg = build_numerology_architecture_svg(
        foundation=foundation,
        left_pillar=left_pillar,
        right_pillar=right_pillar,
        facade=facade,
    )
    loshu_svg = build_loshu_grid_svg(
        grid_counts=loshu_grid.get("grid_counts") or {},
        missing_numbers=missing_numbers,
    )
    deficit_svg = build_structural_deficit_svg(deficit_model)
    planetary_svg = build_planetary_orbit_svg(planetary, numerology_core)

    brand_logo_uri = _as_image_src(ASSETS_ROOT / "branding" / "numai_logo.png", max_dim=56)
    if not brand_logo_uri:
        brand_logo_uri = _as_image_src(ASSETS_ROOT / "branding" / "logo.png", max_dim=56)

    deva_font_regular = _as_uri(ASSETS_ROOT / "fonts" / "NotoSansDevanagari-Regular.ttf")
    deva_font_bold = _as_uri(ASSETS_ROOT / "fonts" / "NotoSansDevanagari-Bold.ttf")

    full_name = _safe_text(identity.get("full_name"), "Strategic Client")
    report_date = _format_timestamp(meta.get("generated_at"))
    cover_title = (
        "à¤…à¤‚à¤• à¤œà¥€à¤µà¤¨ à¤®à¤¾à¤°à¥à¤—à¤¦à¤°à¥à¤¶à¤¨ à¤°à¤¿à¤ªà¥‹à¤°à¥à¤Ÿ | NumAI Basic Numerology Report"
        if plan_tier == "basic"
        else "à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤œà¥€à¤µà¤¨ à¤‡à¤‚à¤Ÿà¥‡à¤²à¤¿à¤œà¥‡à¤‚à¤¸ à¤‘à¤¡à¤¿à¤Ÿ | Strategic Life Intelligence Audit"
    )
    cover_subtitle = (
        "Pure Numerology + Quick Insight + Correction (à¤¹à¤¿à¤‚à¤¦à¥€-à¤ªà¥à¤°à¤§à¤¾à¤¨ à¤¸à¤‚à¤¸à¥à¤•à¤°à¤£)"
        if plan_tier == "basic"
        else "Numerology Intelligence x AI Strategy (à¤¹à¤¿à¤‚à¤¦à¥€-à¤ªà¥à¤°à¤§à¤¾à¤¨ à¤¸à¤‚à¤¸à¥à¤•à¤°à¤£)"
    )

    cover_ganesha_uri = _as_image_src(ASSETS_ROOT / "cover" / "ganesha.png", max_dim=168)
    cover_krishna_uri = _as_image_src(ASSETS_ROOT / "cover" / "krishna.png", max_dim=152)
    cover_ganesh_yantra_uri = (
        _as_image_src(ASSETS_ROOT / "cover" / "ganesh_yantra.png", max_dim=300)
        or _as_image_src(ASSETS_ROOT / "cover" / "ganesh_yantra.png.png", max_dim=300)
    )
    lotus_gold_uri = _as_image_src(ASSETS_ROOT / "lotus" / "lotus_gold.png", max_dim=72)
    lotus_chart_uri = (
        _as_image_src(ASSETS_ROOT / "lotus" / "lotus_numerology_chart.svg", max_dim=300)
        or _as_image_src(ASSETS_ROOT / "lotus" / "lotus_numerology_chart.png", max_dim=300)
        or lotus_gold_uri
    )
    mandala_bg_uri = _as_background_src(ASSETS_ROOT / "sacred" / "mandala_bg.png", max_dim=680)
    om_gold_uri = _as_image_src(ASSETS_ROOT / "sacred" / "om_gold.png", max_dim=72)
    chakra_icon_uri = _as_image_src(ASSETS_ROOT / "icons" / "chakra.png", max_dim=72)

    deity_uris = {
        "surya": _as_image_src(ASSETS_ROOT / "deities" / "surya.png", max_dim=72),
        "chandra": _as_image_src(ASSETS_ROOT / "deities" / "chandra.png", max_dim=72),
        "guru": _as_image_src(ASSETS_ROOT / "deities" / "guru.png", max_dim=72),
        "rahu": _as_image_src(ASSETS_ROOT / "deities" / "rahu.png", max_dim=72),
        "budh": _as_image_src(ASSETS_ROOT / "deities" / "budh.png", max_dim=72),
        "shukra": _as_image_src(ASSETS_ROOT / "deities" / "shukra.png", max_dim=72),
        "ketu": _as_image_src(ASSETS_ROOT / "deities" / "ketu.png", max_dim=72),
        "shani": _as_image_src(ASSETS_ROOT / "deities" / "shani.png", max_dim=72),
        "mangal": _as_image_src(ASSETS_ROOT / "deities" / "mangal.png", max_dim=72),
    }

    blueprint_sections = report_blueprint.get("sections") if isinstance(report_blueprint, dict) else []
    blueprint_sections = blueprint_sections or []
    blueprint_title_by_key = {
        _safe_text(item.get("key")): _safe_text(item.get("title"))
        for item in blueprint_sections
        if isinstance(item, dict) and _safe_text(item.get("key"))
    }
    ordered_basic_keys = [
        _safe_text(item.get("key"))
        for item in blueprint_sections
        if isinstance(item, dict) and _safe_text(item.get("key")) in BASIC_SECTION_KEYS
    ]

    if plan_tier == "basic":
        ordered_from_report_sections = [
            _safe_text(item.get("key"))
            for item in report_sections
            if isinstance(item, dict)
            and _safe_text(item.get("key")).startswith("basic_")
            and _safe_text(item.get("key")) in section_payloads
        ]
        if ordered_from_report_sections:
            ordered_basic_keys = ordered_from_report_sections
        elif not ordered_basic_keys:
            ordered_basic_keys = [key for key in BASIC_SECTION_KEYS if key in section_payloads]
    elif not ordered_basic_keys:
        ordered_basic_keys = [key for key in BASIC_SECTION_KEYS if key in section_payloads]

    icon_by_section = {
        "profile": chakra_icon_uri,
        "dashboard": lotus_gold_uri,
        "executive_summary": cover_ganesha_uri,
        "core_numbers": cover_krishna_uri,
        "number_interaction": chakra_icon_uri,
        "personality_profile": deity_uris["mangal"],
        "focus_snapshot": deity_uris["guru"],
        "personal_year": deity_uris["guru"],
        "lucky_dates": lotus_gold_uri,
        "color_alignment": chakra_icon_uri,
        "remedy": om_gold_uri,
        "closing_summary": lotus_gold_uri,
        "lo_shu_grid": deity_uris["rahu"],
        "missing_numbers": deity_uris["ketu"],
        "repeating_numbers": deity_uris["shani"],
        "mobile_numerology": deity_uris["budh"],
        "mobile_life_compatibility": deity_uris["chandra"],
        "career_financial": deity_uris["shukra"],
        "relationship_patterns": deity_uris["chandra"],
        "health_tendencies": deity_uris["surya"],
        "decision_style": deity_uris["budh"],
        "growth_blockers": deity_uris["shani"],
        "action_plan_90_days": chakra_icon_uri,
        "life_timeline": deity_uris["guru"],
        "strategic_life_theme": lotus_gold_uri,
        "leadership_archetype": deity_uris["mangal"],
        "wealth_strategy": deity_uris["shukra"],
        "opportunity_windows": deity_uris["surya"],
        "decision_timing": deity_uris["budh"],
        "roadmap_12_months": chakra_icon_uri,
        "outlook_3_years": deity_uris["guru"],
        "life_alignment_scorecard": lotus_gold_uri,
        "strategic_correction": om_gold_uri,
        "growth_blueprint": lotus_gold_uri,
        "executive_numerology_summary": cover_ganesha_uri,
        "core_numbers_analysis": cover_krishna_uri,
        "mulank_description": deity_uris["surya"],
        "bhagyank_description": deity_uris["guru"],
        "name_number_analysis": deity_uris["budh"],
        "number_interaction_analysis": chakra_icon_uri,
        "loshu_grid_interpretation": deity_uris["rahu"],
        "missing_numbers_analysis": deity_uris["ketu"],
        "repeating_numbers_impact": deity_uris["shani"],
        "mobile_number_numerology": deity_uris["budh"],
        "mobile_life_number_compatibility": deity_uris["chandra"],
        "email_numerology": deity_uris["budh"],
        "numerology_personality_profile": deity_uris["mangal"],
        "current_life_phase_insight": deity_uris["guru"],
        "career_financial_tendencies": deity_uris["shukra"],
        "relationship_compatibility_patterns": deity_uris["chandra"],
        "health_tendencies_from_numbers": deity_uris["surya"],
        "personal_year_forecast": deity_uris["guru"],
        "lucky_numbers_favorable_dates": lotus_gold_uri,
        "color_alignment": chakra_icon_uri,
        "remedies_lifestyle_adjustments": om_gold_uri,
        "closing_numerology_guidance": lotus_gold_uri,
    }
    diagram_by_section = {
        "core_numbers": "numerology_architecture",
        "number_interaction": "numerology_architecture",
        "lo_shu_grid": "loshu_grid",
        "missing_numbers": "loshu_grid",
        "repeating_numbers": "loshu_grid",
        "personal_year": "planetary_orbit",
        "lucky_dates": "planetary_orbit",
        "remedy": "structural_deficit",
        "closing_summary": "structural_deficit",
        "core_numbers_analysis": "numerology_architecture",
        "number_interaction_analysis": "numerology_architecture",
        "loshu_grid_interpretation": "loshu_grid",
        "missing_numbers_analysis": "loshu_grid",
        "repeating_numbers_impact": "loshu_grid",
        "personal_year_forecast": "planetary_orbit",
        "lucky_numbers_favorable_dates": "planetary_orbit",
        "remedies_lifestyle_adjustments": "structural_deficit",
        "closing_numerology_guidance": "structural_deficit",
    }
    diagram_svg_by_key = {
        "numerology_architecture": architecture_svg,
        "loshu_grid": loshu_svg,
        "planetary_orbit": planetary_svg,
        "structural_deficit": deficit_svg,
    }

    basic_sections: List[Dict[str, Any]] = []
    for key in ordered_basic_keys:
        section = section_payloads.get(key)
        if not isinstance(section, dict):
            continue
        is_profile_snapshot = key in {"profile", "profile_snapshot"}
        is_structured_basic = key.startswith("basic_")
        card_cap = 0 if is_structured_basic else (10 if plan_tier == "basic" else 6)
        bullet_cap = 20 if is_structured_basic else (10 if plan_tier == "basic" else 4)
        narrative_default = "" if is_structured_basic else "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

        cards = []
        for card in _safe_list(section.get("cards"))[:card_cap]:
            if not isinstance(card, dict):
                continue
            label = _hindi_major_text(_safe_text(card.get("label"), "-"), "-")
            value = _hindi_major_text(
                _clip_text(card.get("value"), max_chars=card_limit, default="à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"),
                "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚",
            )
            cards.append({"label": label, "value": value})

        bullets = [
            _hindi_major_text(_clip_text(item, max_chars=card_limit))
            for item in _safe_list(section.get("bullets"))
            if _safe_text(item)
        ][:bullet_cap]

        diagram_key = diagram_by_section.get(key)
        basic_sections.append(
            {
                "key": key,
                "title": _safe_text(
                    section.get("title"),
                    blueprint_title_by_key.get(key, key.replace("_", " ").title()),
                ),
                "narrative": _hindi_major_text(
                    _clip_text(section.get("narrative"), max_chars=narrative_limit, default=narrative_default),
                    narrative_default,
                ),
                "cards": cards,
                "bullets": bullets,
                "icon_uri": icon_by_section.get(key, chakra_icon_uri),
                "diagram_key": diagram_key or "",
                "diagram_svg": diagram_svg_by_key.get(diagram_key or "", ""),
                "single_page_layout": is_profile_snapshot,
                "profile_ui": _build_profile_snapshot_ui(
                    section=section,
                    full_name=full_name,
                    payload=payload,
                    identity=identity,
                    birth_details=birth_details,
                    pythagorean=pythagorean,
                    chaldean=chaldean,
                )
                if is_profile_snapshot
                else {},
            }
        )

    basic_section_pages = [
        {
            "page_number": index + 2,
            "section": section,
        }
        for index, section in enumerate(basic_sections)
    ]
    basic_total_pages = 1 + len(basic_sections)

    raw_sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    raw_section_index = {
        _safe_text(section.get("sectionKey")): section
        for section in raw_sections
        if isinstance(section, dict) and _safe_text(section.get("sectionKey"))
    }

    premium_sections: List[Dict[str, Any]] = []
    if plan_tier == "enterprise":
        for key in ENTERPRISE_SECTIONS:
            raw_section = raw_section_index.get(key, {})
            title_hi = PREMIUM_HI_TITLES.get(
                key,
                _safe_text(raw_section.get("sectionTitle"), key.replace("_", " ").title()),
            )
            premium_content = _build_premium_section_content(
                key=key,
                title=title_hi,
                raw_section=raw_section,
                identity=identity,
                birth_details=birth_details,
                canonical_input=canonical_input,
                nested_input=nested_input,
                numerology_core=numerology_core,
                metrics=metrics,
                pythagorean=pythagorean,
                chaldean=chaldean,
            )

            premium_sections.append(
                {
                    "key": key,
                    "title": title_hi,
                    "subtitle": "",
                    "narrative": premium_content.get("narrative"),
                    "cards": premium_content.get("cards", [])[:6],
                    "bullets": premium_content.get("bullets", [])[:6],
                    "profile_fields": premium_content.get("profile_fields", []),
                }
            )

    premium_section_pages = [
        {"page_number": index + 2, "section": section}
        for index, section in enumerate(premium_sections)
    ]
    premium_total_pages = 1 + len(premium_sections) if premium_sections else 0

    return {
        "watermark": watermark,
        "report": payload,
        "meta": {
            "plan_tier": plan_tier,
            "report_date": report_date,
            "plan": plan_tier.upper(),
            "version": _safe_text(meta.get("report_version"), "6.0"),
            "engine_version": _safe_text(meta.get("engine_version"), "1.0.0"),
            "section_count": _safe_int(report_blueprint.get("section_count"), len(basic_sections)),
        },
        "cover": {
            "title": cover_title,
            "subtitle": cover_subtitle,
            "name": full_name,
            "dob": _safe_text(
                birth_details.get("date_of_birth") or identity.get("date_of_birth"),
                "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚",
            ),
            "risk_band": _risk_band(metrics),
        },
        "primary_insight": {
            "core_archetype": _hindi_major_text(_safe_text(
                primary_insight.get("core_archetype")
                or (payload.get("numerology_archetype") or {}).get("archetype_name"),
                "Strategic Adaptive Profile",
            )),
            "strength": _hindi_major_text(_safe_text(
                primary_insight.get("strength")
                or (payload.get("executive_brief") or {}).get("key_strength"),
                "Pattern recognition and adaptive execution.",
            )),
            "critical_deficit": _hindi_major_text(_safe_text(
                primary_insight.get("critical_deficit")
                or (payload.get("executive_brief") or {}).get("key_risk"),
                "Decision structure under pressure requires calibration.",
            )),
            "stability_risk": _hindi_major_text(_safe_text(
                primary_insight.get("stability_risk"),
                _risk_band(metrics),
            )),
            "phase_1": _hindi_major_text(_safe_text(
                primary_insight.get("phase_1_diagnostic")
                or (payload.get("growth_blueprint") or {}).get("phase_1"),
                "Establish baseline rhythm and signal clarity.",
            )),
            "phase_2": _hindi_major_text(_safe_text(
                primary_insight.get("phase_2_blueprint")
                or (payload.get("growth_blueprint") or {}).get("phase_2"),
                "Build structural blueprint around weakest metric.",
            )),
            "phase_3": _hindi_major_text(_safe_text(
                primary_insight.get("phase_3_intervention_protocol")
                or (payload.get("growth_blueprint") or {}).get("phase_3"),
                "Run 21-day intervention protocol with checkpoints.",
            )),
            "narrative": _hindi_major_text(_clip_text(
                primary_insight.get("narrative")
                or (payload.get("executive_brief") or {}).get("summary"),
                max_chars=narrative_limit,
                default="Deterministic insight indicates that long-term scaling depends on consistency and disciplined execution.",
            )),
        },
        "metrics": {
            "rows": metric_rows,
            "radar_labels_json": json.dumps(radar_labels, ensure_ascii=False),
            "radar_values_json": json.dumps(radar_values, ensure_ascii=False),
            "risk_band": _risk_band(metrics),
            "spine": {
                "primary_strength": _hindi_major_text(_safe_text(
                    metrics_spine.get("primary_strength"),
                    metric_rows[0]["label"] if metric_rows else "Life Stability",
                )),
                "primary_deficit": _hindi_major_text(_safe_text(
                    metrics_spine.get("primary_deficit"),
                    metric_rows[-1]["label"] if metric_rows else "Karma Pressure",
                )),
                "structural_cause": _hindi_major_text(_clip_text(
                    metrics_spine.get("structural_cause"),
                    max_chars=180,
                    default="Current weakest axis is linked to structural pattern gaps and stress-reactivity.",
                )),
                "intervention_focus": _hindi_major_text(_clip_text(
                    metrics_spine.get("intervention_focus"),
                    max_chars=180,
                    default="Install 21-day rhythm and decision protocol before scale actions.",
                )),
            },
        },
        "architecture": {
            "foundation": _safe_text(foundation, "-"),
            "left_pillar": _safe_text(left_pillar, "-"),
            "right_pillar": _safe_text(right_pillar, "-"),
            "facade": _safe_text(facade, "-"),
            "narrative": _hindi_major_text(_clip_text(
                architecture_text.get("narrative"),
                max_chars=narrative_limit,
                default="Foundation numbers interact as a system. Life Path sets the core operating baseline, Destiny and Expression define strategic movement, and Name Number shapes social projection.",
            )),
        },
        "archetype": {
            "signature": _hindi_major_text(_clip_text(
                archetype.get("signature"),
                max_chars=narrative_limit,
                default="This archetype blends analytical depth and adaptive strategy.",
            )),
            "leadership_traits": _hindi_major_text(_clip_text(
                archetype.get("leadership_traits"),
                max_chars=200,
                default="Leads through pattern recognition, timing, and structured execution.",
            )),
            "shadow_traits": _hindi_major_text(_clip_text(
                archetype.get("shadow_traits"),
                max_chars=200,
                default="Under pressure, this profile can over-analyze and delay decisive action.",
            )),
            "growth_path": _hindi_major_text(_clip_text(
                archetype.get("growth_path"),
                max_chars=200,
                default="Install cadence, track behavior weekly, and refine decisions with written filters.",
            )),
        },
        "loshu": {
            "present_numbers": _join_numbers(present_numbers, default="-"),
            "missing_numbers": _join_numbers(missing_numbers, default="-"),
            "center_presence": "à¤‰à¤ªà¤¸à¥à¤¥à¤¿à¤¤ | Present" if center_present else "à¤…à¤¨à¥à¤ªà¤¸à¥à¤¥à¤¿à¤¤ | Missing",
            "energy_imbalance": _hindi_major_text(_clip_text(
                loshu.get("energy_imbalance"),
                max_chars=120,
                default="Energy distribution suggests selective strength with patchable blind spots.",
            )),
            "narrative": _hindi_major_text(_clip_text(
                loshu.get("narrative"),
                max_chars=narrative_limit,
                default="Lo Shu geometry highlights where behavior is naturally stable versus where conscious design is required.",
            )),
            "missing_number_meanings": [
                _hindi_major_text(_clip_text(item, max_chars=100))
                for item in _safe_list(loshu.get("missing_number_meanings"))
                if _safe_text(item)
            ][:3],
        },
        "planetary": {
            "background_forces": _hindi_major_text(_clip_text(
                planetary.get("background_forces"),
                max_chars=190,
                default="Planetary map indicates background strategic pressure and momentum channels.",
            )),
            "primary_intervention_planet": _hindi_major_text(_safe_text(
                planetary.get("primary_intervention_planet"),
                "Budh",
            )),
            "calibration_cluster": _hindi_major_text(_clip_text(
                planetary.get("calibration_cluster"),
                max_chars=120,
                default="clarity, discipline, measured response",
            )),
            "narrative": _hindi_major_text(_clip_text(
                planetary.get("narrative"),
                max_chars=narrative_limit,
                default="Planetary mapping is treated as a calibration system for intervention, not a prediction table.",
            )),
        },
        "deficit": {
            "deficit": _hindi_major_text(_clip_text(
                deficit_model.get("deficit") or deficit_model.get("structural_deficit"),
                max_chars=140,
                default="Missing center 5",
            )),
            "symptom": _hindi_major_text(_clip_text(
                deficit_model.get("symptom") or deficit_model.get("behavioral_symptom"),
                max_chars=140,
                default="Decision instability during high-noise phases.",
            )),
            "patch": _hindi_major_text(_clip_text(
                deficit_model.get("patch") or deficit_model.get("engineered_patch"),
                max_chars=140,
                default="Deploy a daily protocol with measurable decision filters.",
            )),
            "summary": _hindi_major_text(_clip_text(
                deficit_model.get("summary"),
                max_chars=220,
                default="Deficit-symptom-patch framework translates numerology into operational behavior.",
            )),
        },
        "circadian": {
            "morning": _hindi_major_text(_clip_text(
                circadian.get("morning_routine"),
                max_chars=170,
                default="Start with light exposure, breath reset, and one strategic intention.",
            )),
            "work": _hindi_major_text(_clip_text(
                circadian.get("work_alignment"),
                max_chars=170,
                default="Anchor the first deep work block to the highest-leverage outcome.",
            )),
            "evening": _hindi_major_text(_clip_text(
                circadian.get("evening_shutdown"),
                max_chars=170,
                default="Close with device slowdown, review, and next-day priority lock.",
            )),
            "narrative": _hindi_major_text(_clip_text(
                circadian.get("narrative"),
                max_chars=220,
                default="Rhythm quality directly affects decision quality and emotional recovery.",
            )),
        },
        "environment": {
            "physical_space": _hindi_major_text(_clip_text(
                environment.get("physical_space"),
                max_chars=170,
                default="Use low-clutter zones for deep work, admin, and decompression.",
            )),
            "color_alignment": _hindi_major_text(_clip_text(
                environment.get("color_alignment"),
                max_chars=170,
                default="Use calming and grounding palettes in workspace and device themes.",
            )),
            "mobile_number_analysis": _hindi_major_text(_clip_text(
                environment.get("mobile_number_analysis"),
                max_chars=170,
                default="Mobile vibration signal should support focus and communication stability.",
            )),
            "digital_behavior": _hindi_major_text(_clip_text(
                environment.get("digital_behavior"),
                max_chars=170,
                default="Reduce notification noise and avoid high-impact decisions late at night.",
            )),
            "narrative": _hindi_major_text(_clip_text(
                environment.get("narrative"),
                max_chars=220,
                default="Environment and digital behavior are treated as strategic levers for stability.",
            )),
        },
        "vedic": {
            "focus": _hindi_major_text(_clip_text(
                vedic.get("focus"),
                max_chars=120,
                default="Primary focus: stabilize weakest intelligence metric.",
            )),
            "code": _safe_text(vedic.get("code"), "Om Budhaya Namah"),
            "parameter": _hindi_major_text(_clip_text(
                vedic.get("parameter"),
                max_chars=120,
                default="21 days x 108 chants with fixed timing.",
            )),
            "output": _hindi_major_text(_clip_text(
                vedic.get("output"),
                max_chars=120,
                default="Donate food or learning support weekly.",
            )),
            "purpose": _hindi_major_text(_clip_text(
                vedic.get("purpose"),
                max_chars=200,
                default="Remedy protocol aligns attention, discipline, and planetary calibration.",
            )),
            "pronunciation": _safe_text(vedic.get("pronunciation"), ""),
            "planetary_alignment": _hindi_major_text(_clip_text(
                vedic.get("planetary_alignment"),
                max_chars=120,
                default="Intervention aligned to dominant planetary pattern.",
            )),
        },
        "execution": {
            "install_rhythm": _hindi_major_text(_clip_text(
                execution.get("install_rhythm"),
                max_chars=140,
                default="Days 1-7: install rhythm, reset sleep, and simplify priorities.",
            )),
            "deploy_anchor": _hindi_major_text(_clip_text(
                execution.get("deploy_anchor"),
                max_chars=140,
                default="Days 8-14: deploy metric anchor and enforce decision rules.",
            )),
            "run_protocol": _hindi_major_text(_clip_text(
                execution.get("run_protocol"),
                max_chars=140,
                default="Days 15-21: run intervention without breaks and track checkpoints.",
            )),
            "summary": _hindi_major_text(_clip_text(
                execution.get("summary"),
                max_chars=220,
                default="Execution consistency converts insight into measurable life stability.",
            )),
            "checkpoints": [
                _hindi_major_text(_clip_text(item, max_chars=120))
                for item in _safe_list(execution.get("checkpoints"))
                if _safe_text(item)
            ][:3],
        },
        "diagrams": {
            "numerology_architecture": architecture_svg,
            "loshu_grid": loshu_svg,
            "structural_deficit": deficit_svg,
            "planetary_orbit": planetary_svg,
        },
        "basic_report": {
            "intro_sections": basic_sections[:2],
            "section_pages": basic_section_pages,
            "all_sections": basic_sections,
            "total_pages": basic_total_pages,
        },
        "premium_report": {
            "section_pages": premium_section_pages,
            "all_sections": premium_sections,
            "total_pages": premium_total_pages,
        },
        "assets": {
            "brand_logo_uri": brand_logo_uri,
            "deva_font_regular": deva_font_regular,
            "deva_font_bold": deva_font_bold,
            "cover_ganesha_uri": cover_ganesha_uri,
            "cover_krishna_uri": cover_krishna_uri,
            "cover_ganesh_yantra_uri": cover_ganesh_yantra_uri,
            "lotus_gold_uri": lotus_gold_uri,
            "lotus_chart_uri": lotus_chart_uri,
            "mandala_bg_uri": mandala_bg_uri,
            "om_gold_uri": om_gold_uri,
            "chakra_icon_uri": chakra_icon_uri,
            "deity_uris": deity_uris,
        },
    }


def _render_html(context: Dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    plan_tier = _safe_text((context.get("meta") or {}).get("plan_tier"), "basic").lower()
    if plan_tier == "basic":
        template_name = BASIC_TEMPLATE_NAME
    elif plan_tier == "enterprise":
        template_name = PREMIUM_TEMPLATE_NAME
    else:
        template_name = STRATEGIC_TEMPLATE_NAME
    template = env.get_template(template_name)
    return template.render(context)


def _render_pdf_with_playwright(html_content: str) -> bytes:
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright is not installed. Install dependency with `pip install playwright` and browser runtime with `playwright install chromium`."
        )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1240, "height": 1754})
            page.set_content(html_content, wait_until="networkidle")
            page.emulate_media(media="print")

            try:
                page.wait_for_function("window.__numaiReady === true", timeout=20000)
            except PlaywrightError:
                logger.warning("Timed out waiting for Chart.js readiness flag; continuing PDF render.")

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
                prefer_css_page_size=True,
            )
            browser.close()
            return pdf_bytes
    except PlaywrightError as exc:
        message = str(exc)
        if "Executable doesn't exist" in message:
            raise RuntimeError(
                "Playwright Chromium runtime is missing. Rebuild backend image so Dockerfile installs it, "
                "or run `python -m playwright install --with-deps chromium` inside the backend container."
            ) from exc
        raise RuntimeError(f"Playwright PDF generation failed: {exc}") from exc


def _optimize_pdf_bytes(pdf_bytes: bytes) -> bytes:
    if PdfReader is None or PdfWriter is None:
        return pdf_bytes

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        writer = PdfWriter(clone_from=reader)

        for page in writer.pages:
            try:
                page.compress_content_streams()
            except Exception:
                continue

        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

        output = BytesIO()
        writer.write(output)
        optimized = output.getvalue()
        if optimized and len(optimized) < len(pdf_bytes):
            logger.info(
                "Optimized PDF size from %s bytes to %s bytes",
                len(pdf_bytes),
                len(optimized),
            )
            return optimized
        return pdf_bytes
    except Exception:
        logger.exception("Post-processing PDF optimization failed; using original bytes")
        return pdf_bytes


def generate_report_pdf(data: Dict[str, Any], watermark: bool = False) -> BytesIO:
    context = _build_context(data, watermark=watermark)
    html_content = _render_html(context)
    pdf_bytes = _render_pdf_with_playwright(html_content)
    pdf_bytes = _optimize_pdf_bytes(pdf_bytes)
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer


from __future__ import annotations

from collections import deque
from datetime import datetime
from app.core.time_utils import UTC
from difflib import SequenceMatcher
import hashlib
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Tuple
import logging

from app.core.config import settings
from app.modules.reports.ai_payload_builder import build_ai_payload
from app.modules.reports.azure_report_client import generate_report_with_azure
from app.modules.reports.deterministic_pipeline import run_deterministic_pipeline
from app.modules.reports.fallback_templates import build_fallback_section
from app.modules.reports.plan_config import BASIC_SECTIONS, get_plan_config
from app.modules.reports.section_adapter import (
    normalize_ai_section_shape,
    to_legacy_report_sections,
    validate_sections_for_render,
)

logger = logging.getLogger(__name__)
PLAN_SECTION_CAPS = {
    "basic": len(BASIC_SECTIONS),
}

BASIC_UNIQUENESS_HISTORY: deque[Dict[str, Any]] = deque(maxlen=200)
BASIC_SIMILARITY_REWRITE_PRIORITY: Tuple[str, ...] = (
    "basic_key_insight",
    "basic_life_areas",
    "basic_remedies_table",
    "basic_upgrade_path",
    "basic_summary_table_v2",
    "basic_loshu_grid",
    "basic_life_path_context",
    "basic_recommendation",
    "basic_charging_direction",
    "basic_suggested_numbers",
    "basic_mobile_energy",
)

REPORT_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
REPORT_MOJIBAKE_EMOJI_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"Ã°Å¸\S*"),
    re.compile(r"ðŸ\S*"),
    re.compile(r"(?:âœ…|âš ï¸|âŒ|ï¸)"),
)
REPORT_CORRUPTED_SEGMENT_RE = re.compile(r"(?:Ã|Â|â|à|ð|Ð|Ñ|рџ|вњ|пё)")
REPORT_HINDI_REPAIR_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bसंकलप\b"), "संकल्प"),
    (re.compile(r"\bसधार\b"), "सुधार"),
    (re.compile(r"\bसपषट\b"), "स्पष्ट"),
    (re.compile(r"\bसथिति\b"), "स्थिति"),
    (re.compile(r"\bसथिरता\b"), "स्थिरता"),
    (re.compile(r"\bसथिर\b"), "स्थिर"),
    (re.compile(r"\bकरयर\b"), "करियर"),
    (re.compile(r"\bअनशासन\b"), "अनुशासन"),
    (re.compile(r"\bनिरणय\b"), "निर्णय"),
    (re.compile(r"\bअसंतलन\b"), "असंतुलन"),
    (re.compile(r"\bपराथमिकता\b"), "प्राथमिकता"),
    (re.compile(r"\bपरभव\b"), "प्रभाव"),
    (re.compile(r"\bप्रमख\b"), "प्रमुख"),
    (re.compile(r"\bमखय\b"), "मुख्य"),
    (re.compile(r"\bकषेत्र\b"), "क्षेत्र"),
    (re.compile(r"\bचनौती\b"), "चुनौती"),
    (re.compile(r"\bटरैकिंग\b"), "ट्रैकिंग"),
    (re.compile(r"\bसमीकषा\b"), "समीक्षा"),
    (re.compile(r"\bवरतमान\b"), "वर्तमान"),
    (re.compile(r"\bवयवहारिक\b"), "व्यावहारिक"),
    (re.compile(r"\bकंजी\b"), "कुंजी"),
    (re.compile(r"\bअनपसथित\b"), "अनुपस्थित"),
    (re.compile(r"\bआतमनिरभरता\b"), "आत्मनिर्भरता"),
    (re.compile(r"\bआतमिनरभरता\b"), "आत्मनिर्भरता"),
    (re.compile(r"\bअनकलनशीलता\b"), "अनुकूलनशीलता"),
    (re.compile(r"\bसवतंतरता\b"), "स्वतंत्रता"),
    (re.compile(r"\bपरवतन\b"), "परिवर्तन"),
    (re.compile(r"\bमारग\b"), "मार्ग"),
    (re.compile(r"\bजिममेदारी\b"), "जिम्मेदारी"),
    (re.compile(r"\bसकरिय\b"), "सक्रिय"),
    (re.compile(r"\bपूरणता\b"), "पूर्णता"),
    (re.compile(r"\bशकति\b"), "शक्ति"),
    (re.compile(r"\bलकषय\b"), "लक्ष्य"),
    (re.compile(r"\bमहतवाकांकषा\b"), "महत्वाकांक्षा"),
    (re.compile(r"\bपरेरणा\b"), "प्रेरणा"),
    (re.compile(r"\bखद\b"), "खुद"),
    (re.compile(r"\bसव-?निरणय\b"), "स्व-निर्णय"),
    (re.compile(r"\bपरयापत\b"), "पर्याप्त"),
    (re.compile(r"\bजलदी\b"), "जल्दी"),
    (re.compile(r"\bकषमता\b"), "क्षमता"),
    (re.compile(r"\bकारय\b"), "कार्य"),
    (re.compile(r"\bमहतवपूर्ण\b"), "महत्वपूर्ण"),
    (re.compile(r"(?<!अ)ग्नि"), "अग्नि"),
    (re.compile(r"21 weekly number-manage change", re.IGNORECASE), "21-दिवसीय ट्रैकिंग के बाद निर्णय अपडेट करें"),
)

PREMIUM_BAD_TOKENS: Tuple[str, ...] = (
    "->",
    "| |",
    "@.",
    "?.",
    "????",
    "उपलब्ध नहीं।हीं",
)

PREMIUM_PROFILE_FIELDS: Tuple[str, ...] = (
    "fullName",
    "dateOfBirth",
    "mobileNumber",
    "email",
    "gender",
    "city",
    "currentCity",
    "country",
)


def _needs_premium_fallback(section: Dict[str, Any]) -> bool:
    if not isinstance(section, dict):
        return True
    fields = [
        str(section.get("summary") or "").strip(),
        str(section.get("keyStrength") or "").strip(),
        str(section.get("keyRisk") or "").strip(),
        str(section.get("practicalGuidance") or "").strip(),
    ]
    if any(not text for text in fields):
        return True
    lowered = [re.sub(r"\s+", " ", text.lower()) for text in fields]
    if len(set(lowered)) < len(lowered):
        return True
    if any(any(token in text for token in PREMIUM_BAD_TOKENS) for text in fields):
        return True
    if any(re.fullmatch(r"[\|.@\\-]+", text) for text in fields):
        return True
    return False

REPORT_ENGLISH_SPLIT_WORDS: Tuple[str, ...] = (
    "Health",
    "Wealth",
    "Moderate",
    "Compatibility",
    "Primary",
    "Stability",
    "Research",
    "Architecture",
    "Remedy",
    "Remedies",
    "Execution",
    "Alignment",
    "Preferred",
    "Correctable",
    "Confidence",
    "Decision",
    "Strategy",
    "Growth",
    "Signify",
    "Systems",
    "Points",
    "Steps",
    "YELLOW",
)


def _is_hindi_dominant_text(value: str) -> bool:
    text = str(value or "")
    devanagari = sum(1 for ch in text if "\u0900" <= ch <= "\u097f")
    latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    return devanagari >= max(1, latin)


def _repair_split_english_words(value: str) -> str:
    text = str(value or "")
    for word in REPORT_ENGLISH_SPLIT_WORDS:
        letters = list(word)
        pattern = r"\b" + r"\s*".join(re.escape(letter) for letter in letters) + r"\b"
        text = re.sub(pattern, word, text, flags=re.IGNORECASE)
    return text


def _normalize_report_copy(value: str) -> str:
    text = str(value or "")
    if not text:
        return text
    text = _repair_split_english_words(text)
    if "N/A" in text or "Not Provided" in text:
        if _is_hindi_dominant_text(text):
            text = text.replace("N/A", "उपलब्ध नहीं").replace("Not Provided", "उपलब्ध नहीं")
        else:
            text = text.replace("N/A", "Not available").replace("Not Provided", "Not provided")
    text = re.sub(r" {2,}", " ", text).strip()
    return text


def _segment_quality_score(value: str) -> int:
    text = str(value or "").strip()
    if not text:
        return -999
    devanagari = sum(1 for ch in text if "\u0900" <= ch <= "\u097f")
    latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    digits = sum(1 for ch in text if ch.isdigit())
    corrupted = len(REPORT_CORRUPTED_SEGMENT_RE.findall(text))
    questions = text.count("?")
    return (devanagari * 4) + latin + digits - (corrupted * 5) - (questions * 2)


def _clean_report_corrupted_segments(value: str) -> str:
    text = str(value or "").strip()
    if not text or not REPORT_CORRUPTED_SEGMENT_RE.search(text):
        return text

    # If the left label before ":" is corrupted, keep the right informative part.
    if ":" in text:
        left, right = text.split(":", 1)
        left_score = _segment_quality_score(left)
        right_score = _segment_quality_score(right)
        if left_score < 0 and right_score >= 0:
            text = right.strip()
        elif left_score >= 0 and right_score < 0:
            text = left.strip()

    # If pipe-separated content exists, keep only segments with non-negative quality.
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
        scored_parts = [(part, _segment_quality_score(part)) for part in parts if part]
        kept = [part for part, score in scored_parts if score >= 0]
        if kept:
            text = " | ".join(kept)

    # Remove standalone corrupted runs that survive blending.
    text = re.sub(r"(?:[ÃÂâàðÐÑрвп][^\s|:]{0,24}){2,}", " ", text)
    # Trim trailing corrupted token fragments, e.g. "... Kochi à¤…"
    text = re.sub(r"\s+[ÃÂâàðÐÑрвп][^\s|:]{0,30}$", "", text)
    text = re.sub(r" {2,}", " ", text).strip()
    return text


def _repair_report_hindi_text(value: str) -> str:
    text = str(value or "")
    if not text:
        return text
    for pattern, replacement in REPORT_HINDI_REPAIR_PATTERNS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _repair_hindi_element_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    lowered = text.lower()
    if "fire" in lowered and ("अग्नि" not in text) and ("ग्नि" in text or text.startswith("्")):
        return "\u0905\u0917\u094d\u0928\u093f (Fire)"
    return text


def _strip_report_emoji_text(value: str) -> str:
    cleaned = str(value or "")
    cleaned = REPORT_EMOJI_RE.sub("", cleaned)
    for pattern in REPORT_MOJIBAKE_EMOJI_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = unicodedata.normalize("NFC", cleaned)
    # Guard against duplicated Hindi vowel-matra artifacts in rendered PDF text.
    cleaned = re.sub(r"(ों){2,}", "ों", cleaned)
    cleaned = re.sub(r"(ें){2,}", "ें", cleaned)
    cleaned = _clean_report_corrupted_segments(cleaned)
    cleaned = _repair_report_hindi_text(cleaned)
    cleaned = re.sub(r"(?<!\S)र(?!\S)", "और", cleaned)
    cleaned = _normalize_report_copy(cleaned)
    # Last-resort guard: if mojibake survives all decode/cleanup passes,
    # keep only safe leading label text to avoid rendering gibberish in PDFs.
    residual_tokens = ("Ã", "Â", "à¤", "à¥", "ï¿½", "Ãƒ", "Ã‚")
    if any(token in cleaned for token in residual_tokens):
        first_hit = min((cleaned.find(token) for token in residual_tokens if token in cleaned), default=-1)
        if first_hit >= 0:
            safe_prefix = cleaned[:first_hit].strip(" \t:-|;,.")
            if safe_prefix and _segment_quality_score(safe_prefix) >= 0 and len(safe_prefix) >= 6:
                cleaned = safe_prefix
            else:
                cleaned = ""
    cleaned = re.sub(r" {2,}", " ", cleaned)
    return cleaned


def _strip_report_emoji_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return _strip_report_emoji_text(payload)
    if isinstance(payload, list):
        return [_strip_report_emoji_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _strip_report_emoji_payload(value) for key, value in payload.items()}
    return payload


_EMAIL_TOKEN_RE = re.compile(r"\b[^@\s]+@[^@\s]+\b")
_VALID_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _sanitize_premium_text(value: Any) -> str:
    text = _strip_report_emoji_text(value)
    if not text:
        return ""
    for token in PREMIUM_BAD_TOKENS:
        text = text.replace(token, " ")
    # Replace malformed email-like tokens to avoid broken identity lines in premium report.
    def _clean_email_token(match: re.Match[str]) -> str:
        token = match.group(0)
        return token if _VALID_EMAIL_RE.match(token) else "उपलब्ध नहीं"

    text = _EMAIL_TOKEN_RE.sub(_clean_email_token, text)
    text = re.sub(r"\s*,\s*", ", ", text).strip().strip(", ")
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"^\|\s*", "", text)
    text = re.sub(r"\s*\|$", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if re.fullmatch(r"[\s|.@\u0964-]+", text):
        return ""
    return text


def _sanitize_premium_profile_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(snapshot or {})
    for key in PREMIUM_PROFILE_FIELDS:
        value = _sanitize_premium_text(cleaned.get(key))
        cleaned[key] = value if value else "उपलब्ध नहीं"
    return cleaned


def _sanitize_premium_section(
    section: Dict[str, Any],
    *,
    fallback: Dict[str, Any] | None = None,
    force_summary_from_fallback: bool = False,
) -> Dict[str, Any]:
    if not isinstance(section, dict):
        return section
    cleaned = dict(section)
    fallback = fallback or {}
    fields = ["summary", "keyStrength", "keyRisk", "practicalGuidance"]
    def _fix_identity_blanks(text: str) -> str:
        replacements = {
            "नाम": "नाम उपलब्ध नहीं",
            "जन्मतिथि": "जन्मतिथि उपलब्ध नहीं",
            "मोबाइल": "मोबाइल उपलब्ध नहीं",
            "शहर": "शहर उपलब्ध नहीं",
            "लिंग": "लिंग उपलब्ध नहीं",
            "ईमेल": "ईमेल उपलब्ध नहीं",
        }
        for label, replacement in replacements.items():
            text = re.sub(rf"{label}\s*,", f"{replacement},", text)
            text = re.sub(rf"{label}\s+[,|।]", f"{replacement} ", text)
        text = re.sub(r"फोकस/चुनौती:\s*\|\s*लक्ष्य:", "फोकस/चुनौती: उपलब्ध नहीं | लक्ष्य: उपलब्ध नहीं", text)
        text = re.sub(r"लक्ष्य:\s*,", "लक्ष्य: उपलब्ध नहीं,", text)
        return text
    for field in fields:
        value = _sanitize_premium_text(cleaned.get(field))
        if not value:
            value = _sanitize_premium_text(fallback.get(field))
        if cleaned.get("sectionKey") == "full_identity_profile" and value:
            value = _fix_identity_blanks(value)
        cleaned[field] = value
    if force_summary_from_fallback:
        forced = _sanitize_premium_text(fallback.get("summary"))
        if forced:
            cleaned["summary"] = forced
    if fallback.get("loadedEnergies"):
        cleaned["loadedEnergies"] = fallback.get("loadedEnergies")
    # de-duplicate identical fields
    if cleaned.get("summary") == cleaned.get("keyStrength"):
        cleaned["keyStrength"] = _sanitize_premium_text(fallback.get("keyStrength")) or cleaned["summary"]
    if cleaned.get("summary") == cleaned.get("keyRisk"):
        cleaned["keyRisk"] = _sanitize_premium_text(fallback.get("keyRisk")) or cleaned["summary"]
    if cleaned.get("summary") == cleaned.get("practicalGuidance"):
        cleaned["practicalGuidance"] = _sanitize_premium_text(fallback.get("practicalGuidance")) or cleaned["summary"]
    return cleaned


BASIC_REMEDY_LANGUAGE_PACKS: Dict[str, Dict[str, List[str]]] = {
    "consistency": {
        "spiritual": [
            "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â° Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¥ 90-Ã Â¤Â¸Ã Â¥â€¡Ã Â¤â€¢Ã Â¤â€šÃ Â¤Â¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â°Ã Â¥ÂÃ Â¤â€ Ã Â¤Â¤ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤ÂÃ Â¤â€¢ Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¥Â¤",
            "Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â° Ã Â¤Å“Ã Â¤Âª Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â‚¬ 3 Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¥Ã Â¤Â®Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾Ã Â¤ÂÃ Â¤â€š Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š; Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¿Ã Â¤â€“Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Å“Ã Â¤Â¾Ã Â¤Â¯ Ã Â¤â€¢Ã Â¥â€¡Ã Â¤â€šÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â°Ã Â¤Â¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Å“Ã Â¤Âª Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â°Ã Â¤â€šÃ Â¤Â¤ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â°Ã Â¥â€š Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š, Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤â€ Ã Â¤Â§Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â§Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¯Ã Â¤Â¨ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â²Ã Â¤â€”Ã Â¥â€¡Ã Â¥Â¤",
        ],
        "physical": [
            "Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¯ Ã Â¤ÂÃ Â¤â€¢ Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Å“Ã Â¤â€”Ã Â¤Â¹ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š; Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â°-Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤Â¬Ã Â¤Â¦Ã Â¤Â²Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯-Ã Â¤Â²Ã Â¤Â¯ Ã Â¤Â¤Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Å¡Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¸Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¤Ã Â¤Â¾Ã Â¤Â¹ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¢Ã Â¤Â® Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â® 5 Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š; Ã Â¤â€¦Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¦Ã Â¤Â­Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¸ Ã Â¤â€¦Ã Â¤Â¸Ã Â¤Â° Ã Â¤ËœÃ Â¤Å¸Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¡Ã Â¥â€¡Ã Â¤Â¸Ã Â¥ÂÃ Â¤â€¢ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤Â¤Ã Â¤Â¯ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤â€°Ã Â¤Â¸Ã Â¥â‚¬ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š, Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        ],
        "digital": [
            "DND Ã Â¤ÂµÃ Â¤Â¿Ã Â¤â€šÃ Â¤Â¡Ã Â¥â€¹ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¢Ã Â¥â€¡Ã Â¤ÂµÃ Â¤Â² Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤â€¢Ã Â¥â€°Ã Â¤Â² Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š; Ã Â¤Â¨Ã Â¥â€¹Ã Â¤Å¸Ã Â¤Â¿Ã Â¤Â«Ã Â¤Â¿Ã Â¤â€¢Ã Â¥â€¡Ã Â¤Â¶Ã Â¤Â¨ Ã Â¤Â¶Ã Â¥â€¹Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â°Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â«Ã Â¥â€¹Ã Â¤â€¢Ã Â¤Â¸ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤ÂÃ Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â®Ã Â¤Â¸Ã Â¥ÂÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂÃ Â¤ÂªÃ Â¥ÂÃ Â¤Â¸ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â®/Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿Ã Â¤â€”Ã Â¤Â¤ Ã Â¤ÂÃ Â¤Âª Ã Â¤â€¦Ã Â¤Â²Ã Â¤â€” Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€¢Ã Â¥Ë†Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€šÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¦Ã Â¥â€¹ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã¢â‚¬Ëœexecution windowsÃ¢â‚¬â„¢ Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â²Ã Â¥â€°Ã Â¤â€¢ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤â€°Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
    },
    "career": {
        "spiritual": [
            "Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â° Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â°-Ã Â¤â€°Ã Â¤Â¦Ã Â¥ÂÃ Â¤Â¦Ã Â¥â€¡Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂÃ Â¤â€¢ Ã Â¤ÂªÃ Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¬Ã Â¥â€¹Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€š: Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â²Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€”Ã Â¥ÂÃ Â¤Â£Ã Â¤ÂµÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Â¹Ã Â¤Â° Ã Â¤Â®Ã Â¤â€šÃ Â¤â€”Ã Â¤Â²Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°/Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â° Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤ÂÃ Â¤â€š Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â²Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¥Â¤",
            "Ã Â¤Å“Ã Â¤Âª Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¥ Ã¢â‚¬ËœÃ Â¤ÂÃ Â¤â€¢ Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€šÃ Â¤â€šÃ Â¤â€”Ã Â¤Â¾Ã¢â‚¬â„¢ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â·Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â¾Ã Â¤Â¦Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        ],
        "physical": [
            "Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤â€¢Ã Â¥â€°Ã Â¤Â²/Ã Â¤Â®Ã Â¥â‚¬Ã Â¤Å¸Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ 3 Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Å¸ Ã Â¤Â¶Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¤ Ã Â¤Â¬Ã Â¥Ë†Ã Â¤Â Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤Å¡Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¦Ã Â¥Å’Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¦Ã Â¥Æ’Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤ÂÃ Â¤Â; Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Å¡Ã Â¤Â²Ã Â¤Â¨ Ã Â¤ËœÃ Â¤Å¸Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¡Ã Â¥â€¡Ã Â¤Â¸Ã Â¥ÂÃ Â¤â€¢ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤ÂÃ Â¤â€¢ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤ÂÃ Â¤â€šÃ Â¤â€¢Ã Â¤Â°-Ã Â¤ÂªÃ Â¥â€°Ã Â¤â€¡Ã Â¤â€šÃ Â¤Å¸ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤ÂÃ Â¤â€š Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â¸Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯-Ã Â¤Â²Ã Â¤Â¯ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¥Â¤",
        ],
        "digital": [
            "Ã Â¤Ë†Ã Â¤Â®Ã Â¥â€¡Ã Â¤Â²/Ã Â¤â€¢Ã Â¥â€°Ã Â¤Â² Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â 2 Ã Â¤Â¤Ã Â¤Â¯ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â²Ã Â¥â€°Ã Â¤Å¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š, Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¯ deep-work mode Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â° Ã Â¤ÂÃ Â¤ÂªÃ Â¥ÂÃ Â¤Â¸ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥â€¹Ã Â¤Â¶Ã Â¤Â² Ã Â¤ÂÃ Â¤ÂªÃ Â¥ÂÃ Â¤Â¸ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤â€¦Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â¿Ã Â¤Â® Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¶Ã Â¥â‚¬Ã Â¤Â°Ã Â¥ÂÃ Â¤Â· 3 Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¥Ã Â¤Â®Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾Ã Â¤ÂÃ Â¤Â Ã Â¤Â¨Ã Â¥â€¹Ã Â¤Å¸Ã Â¥ÂÃ Â¤Â¸ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤ÂªÃ Â¤Â¿Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤Â¶Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¸Ã Â¤Â®Ã Â¥â‚¬Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
    },
    "confidence": {
        "spiritual": [
            "Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â° Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ 1 Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Å¸ Ã Â¤Å Ã Â¤â€šÃ Â¤Å¡Ã Â¥â‚¬ Ã Â¤â€ Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Å“ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¦Ã Â¤ÂªÃ Â¤Â¨Ã Â¤Â¾ affirmation Ã Â¤ÂªÃ Â¤Â¢Ã Â¤Â¼Ã Â¥â€¡Ã Â¤â€š; Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂÃ Â¤â€šÃ Â¤â€¢Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Å“Ã Â¤Âª Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¥ Ã¢â‚¬ËœÃ Â¤Â®Ã Â¥Ë†Ã Â¤â€š Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¶Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¤ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â²Ã Â¥â€¡Ã Â¤Â¤Ã Â¤Â¾/Ã Â¤Â²Ã Â¥â€¡Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥â€šÃ Â¤ÂÃ¢â‚¬â„¢ Ã Â¤ÂµÃ Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤ÂÃ Â¤ÂÃ Â¥Â¤",
            "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª Ã Â¤â€Ã Â¤Â° Ã Â¤Â¶Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â¸Ã Â¤Â®Ã Â¥â‚¬Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
        "physical": [
            "Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤ÂµÃ Â¤Â°/Ã Â¤ÂµÃ Â¥â€°Ã Â¤Â²Ã Â¤ÂªÃ Â¥â€¡Ã Â¤ÂªÃ Â¤Â° Ã Â¤â€°Ã Â¤Â¸Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾-Ã Â¤Â°Ã Â¤â€šÃ Â¤â€” Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Â¦Ã Â¥Æ’Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¥â€¡Ã Â¤Â¤ Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Å“Ã Â¤â€”Ã Â¤Â¾Ã Â¤ÂÃ Â¤ÂÃ Â¥Â¤",
            "Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Å¡Ã Â¥â‚¬Ã Â¤Â¤ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ 30 Ã Â¤Â¸Ã Â¥â€¡Ã Â¤â€¢Ã Â¤â€šÃ Â¤Â¡ Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¡Ã Â¤Â¼Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€¢Ã Â¥â€°Ã Â¤Â² Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ posture-reset Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š; Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â¶Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¥â€¡Ã Â¤Â¤ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â­Ã Â¤Â°Ã Â¥â€¹Ã Â¤Â¸Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤",
        ],
        "digital": [
            "Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤â€¢Ã Â¥â€°Ã Â¤Â² Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â 2 Ã Â¤Â«Ã Â¤Â¿Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¸ Ã Â¤ÂµÃ Â¤Â¿Ã Â¤â€šÃ Â¤Â¡Ã Â¥â€¹ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Â¤Ã Â¥Ë†Ã Â¤Â¯Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¹Ã Â¤â€š Ã Â¤Â¬Ã Â¥â€¡Ã Â¤Â¹Ã Â¤Â¤Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â²Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¥â€¹Ã Â¤â€š Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤â€¢Ã Â¥Ë†Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€šÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â²Ã Â¥â€°Ã Â¤Å¸ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¡Ã Â¤Â¿Ã Â¤Å“Ã Â¤Â¿Ã Â¤Å¸Ã Â¤Â² Ã Â¤Â¨Ã Â¥â€¹Ã Â¤Å¸ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã¢â‚¬Ëœ3 winsÃ¢â‚¬â„¢ Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤ÂªÃ Â¤Â¢Ã Â¤Â¼Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
    },
    "finance": {
        "spiritual": [
            "Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â° Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ Ã¢â‚¬ËœÃ Â¤â€ Ã Â¤Å“ Ã Â¤Â¬Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€“Ã Â¤Â°Ã Â¥ÂÃ Â¤Å¡ Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€šÃ¢â‚¬â„¢ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤Â¶Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Å“Ã Â¤Â¾Ã Â¤ÂÃ Â¤Å¡ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¸Ã Â¤Â¾Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¤Ã Â¤Â¾Ã Â¤Â¹Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤ÂÃ Â¤â€¢ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤-Ã Â¤Â¸Ã Â¤Â®Ã Â¥â‚¬Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤Â§Ã Â¤Â¨ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¥ Ã Â¤Å¡Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Å“Ã Â¤Âª Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ 1 Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤â€°Ã Â¤Â¸Ã Â¥â‚¬ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
        "physical": [
            "Ã Â¤Â­Ã Â¥ÂÃ Â¤â€”Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â¨/Ã Â¤Â¨Ã Â¤Â¿Ã Â¤ÂµÃ Â¥â€¡Ã Â¤Â¶ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¯ Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¤â€¢Ã Â¤Â° 60 Ã Â¤Â¸Ã Â¥â€¡Ã Â¤â€¢Ã Â¤â€šÃ Â¤Â¡ Ã Â¤Â°Ã Â¥ÂÃ Â¤â€¢Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€“Ã Â¤Â°Ã Â¥ÂÃ Â¤Å¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ Ã Â¤ÂÃ Â¤â€¢ Ã¢â‚¬Ëœpause ritualÃ¢â‚¬â„¢ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š: 3 Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¸ + Ã Â¤â€°Ã Â¤Â¦Ã Â¥ÂÃ Â¤Â¦Ã Â¥â€¡Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Å“Ã Â¤Â¾Ã Â¤ÂÃ Â¤Å¡Ã Â¥Â¤",
            "Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤Â¡Ã Â¥â€¡Ã Â¤Â¸Ã Â¥ÂÃ Â¤â€¢ Ã Â¤ÂªÃ Â¤Â° Ã Â¤â€¦Ã Â¤Â²Ã Â¤â€” Ã Â¤â€ºÃ Â¥â€¹Ã Â¤Å¸Ã Â¤Â¾ Ã Â¤ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š; Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â®Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â§Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        ],
        "digital": [
            "UPI/Ã Â¤Â¬Ã Â¥Ë†Ã Â¤â€šÃ Â¤â€¢ Ã Â¤ÂÃ Â¤ÂªÃ Â¥ÂÃ Â¤Â¸ Ã Â¤â€¦Ã Â¤Â²Ã Â¤â€” Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° impulse apps Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¦Ã Â¥â€šÃ Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€“Ã Â¤Â°Ã Â¥ÂÃ Â¤Å¡ Ã Â¤Å¸Ã Â¥ÂÃ Â¤Â°Ã Â¥Ë†Ã Â¤â€¢Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤ Ã Â¤â€¢Ã Â¤Â¾ 5-Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Å¸ Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¬Ã Â¤Â¡Ã Â¤Â¼Ã Â¥â€¡ Ã Â¤â€“Ã Â¤Â°Ã Â¥ÂÃ Â¤Å¡ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â 24-Ã Â¤ËœÃ Â¤â€šÃ Â¤Å¸Ã Â¥â€¡ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â® Ã Â¤â€Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â®Ã Â¤Â¾Ã Â¤â€¡Ã Â¤â€šÃ Â¤Â¡Ã Â¤Â° Ã Â¤â€¦Ã Â¤Â¨Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
    },
    "default": {
        "spiritual": [
            "Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â° + Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª + Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯: Ã Â¤â€¡Ã Â¤Â¸ Ã Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¨-Ã Â¤Å¡Ã Â¤Â°Ã Â¤Â£ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¹ 21 Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¶Ã Â¤Â¾Ã Â¤Â® 2 Ã Â¤â€ºÃ Â¥â€¹Ã Â¤Å¸Ã Â¥â€¡ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾-Ã Â¤Å¡Ã Â¥â€¡Ã Â¤â€¢ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤ÂÃ Â¤â€š; Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Å“Ã Â¤Âª Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤ÂÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â®Ã Â¤Â¾Ã Â¤ÂªÃ Â¤Â¨Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤â€šÃ Â¥Â¤",
        ],
        "physical": [
            "Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤ÂÃ Â¤â€¢ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Å¡Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¯ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤â€Ã Â¤Â° Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â¯Ã Â¥â€¹Ã Â¤â€” Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â®Ã Â¤Â¾ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¤Ã Â¤Â¯ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤â€ºÃ Â¥â€¹Ã Â¤Å¸Ã Â¥â€¡ Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤Â²Ã Â¤â€”Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â­Ã Â¥Å’Ã Â¤Â¤Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¯ Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â¤Ã Â¥â€¡Ã Â¤Å“Ã Â¤Â¼ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤",
        ],
        "digital": [
            "DND Ã Â¤â€Ã Â¤Â° notification hygiene Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¥Ã Â¤Â®Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¦Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
            "Ã Â¤ÂÃ Â¤Âª Ã Â¤Â«Ã Â¥â€¹Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â° Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â®Ã Â¤Â¾ Ã Â¤Â°Ã Â¤â€“Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â¡Ã Â¤Â¿Ã Â¤Å“Ã Â¤Â¿Ã Â¤Å¸Ã Â¤Â² Ã Â¤â€¦Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¾ Ã Â¤ËœÃ Â¤Å¸Ã Â¤Â¾Ã Â¤ÂÃ Â¤ÂÃ Â¥Â¤",
            "Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ 5 Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Å¸ Ã Â¤Â¸Ã Â¤Â®Ã Â¥â‚¬Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â§Ã Â¤Â¾Ã Â¤Â° Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        ],
    },
}

PLANET_BY_VIBRATION = {
    1: "Sun",
    2: "Moon",
    3: "Jupiter",
    4: "Rahu",
    5: "Mercury",
    6: "Venus",
    7: "Ketu",
    8: "Saturn",
    9: "Mars",
}

ELEMENT_BY_VIBRATION = {
    1: "Fire",
    2: "Water",
    3: "Fire",
    4: "Earth",
    5: "Air",
    6: "Earth",
    7: "Water",
    8: "Earth",
    9: "Fire",
}

CHARGING_DIRECTION_BY_VIBRATION = {
    1: "East",
    2: "North-West",
    3: "East",
    4: "South-West",
    5: "North",
    6: "West",
    7: "South-East",
    8: "South",
    9: "East",
}

CORE_ENERGY_KEYWORDS = {
    1: ["leadership", "initiative", "independence", "drive"],
    2: ["cooperation", "sensitivity", "balance", "harmony"],
    3: ["expression", "creativity", "communication", "optimism"],
    4: ["discipline", "order", "consistency", "structure"],
    5: ["adaptability", "curiosity", "freedom", "movement"],
    6: ["responsibility", "care", "stability", "service"],
    7: ["analysis", "introspection", "wisdom", "reflection"],
    8: ["management", "ambition", "authority", "execution"],
    9: ["compassion", "vision", "humanity", "completion"],
}

VIBRATION_TRAITS = {
    1: ["Independent", "Decisive", "Pioneering", "Self-driven"],
    2: ["Diplomatic", "Supportive", "Patient", "Emotionally aware"],
    3: ["Expressive", "Creative", "Social", "Enthusiastic"],
    4: ["Practical", "Reliable", "Methodical", "Consistent"],
    5: ["Flexible", "Quick-learning", "Curious", "Versatile"],
    6: ["Responsible", "Caring", "Balanced", "Protective"],
    7: ["Analytical", "Insightful", "Thoughtful", "Observant"],
    8: ["Ambitious", "Organized", "Result-focused", "Resilient"],
    9: ["Compassionate", "Idealistic", "Generous", "Broad-minded"],
}

VIBRATION_CHALLENGES = {
    1: ["Impatience", "Ego rigidity", "Over-control"],
    2: ["Over-sensitivity", "Indecision", "Emotional drift"],
    3: ["Scattered focus", "Inconsistent follow-through", "Over-promising"],
    4: ["Rigidity", "Resistance to change", "Work-stress buildup"],
    5: ["Restlessness", "Impulsive choices", "Routine instability"],
    6: ["Over-responsibility", "People-pleasing", "Emotional load"],
    7: ["Isolation", "Over-analysis", "Delay in decisions"],
    8: ["Pressure buildup", "Control conflicts", "Harsh self-expectations"],
    9: ["Emotional overflow", "Closure issues", "Energy drain"],
}

LIFE_PATH_MEANINGS = {
    1: "A path of initiative, self-direction, and leadership.",
    2: "A path of collaboration, diplomacy, and emotional balance.",
    3: "A path of communication, creativity, and social expression.",
    4: "A path of structure, discipline, and steady execution.",
    5: "A path of adaptability, exploration, and dynamic change.",
    6: "A path of responsibility, care, and family-oriented service.",
    7: "A path of study, reflection, and inner wisdom.",
    8: "A path of management, power, and material results.",
    9: "A path of compassion, purpose, and contribution.",
}

DESTINY_MEANINGS = {
    1: "Expresses directness, individuality, and pioneering drive.",
    2: "Expresses tact, harmony, and relationship intelligence.",
    3: "Expresses creativity, ideas, and persuasive communication.",
    4: "Expresses practicality, discipline, and system building.",
    5: "Expresses flexibility, variety, and fast adaptation.",
    6: "Expresses care, accountability, and supportive leadership.",
    7: "Expresses depth, analysis, and thoughtful decision-making.",
    8: "Expresses ambition, authority, and strategic execution.",
    9: "Expresses empathy, vision, and large-scale impact.",
}

SUPPORTIVE_NUMBERS = {
    1: {1, 3, 5, 9},
    2: {2, 4, 6, 7},
    3: {1, 3, 5, 6, 9},
    4: {2, 4, 6, 8},
    5: {1, 3, 5, 7, 9},
    6: {2, 3, 6, 9},
    7: {2, 5, 7},
    8: {4, 6, 8},
    9: {1, 3, 6, 9},
}

MANTRA_BY_VIBRATION = {
    1: "Om Hraam Hreem Hraum Suryaya Namah",
    2: "Om Som Somaya Namah",
    3: "Om Brim Brihaspataye Namah",
    4: "Om Raam Rahave Namah",
    5: "Om Bum Budhaya Namah",
    6: "Om Shum Shukraya Namah",
    7: "Om Kem Ketave Namah",
    8: "Om Sham Shanicharaya Namah",
    9: "Om Kraam Kreem Kraum Bhaumaya Namah",
}

COLOR_BY_VIBRATION = {
    1: "Gold / Orange",
    2: "White / Pearl",
    3: "Yellow",
    4: "Smoky Blue",
    5: "Green",
    6: "Pastel Pink / Cream",
    7: "Sea Green / Aqua",
    8: "Navy / Indigo",
    9: "Red / Maroon",
}

# Final BASIC deterministic architecture (D1-D17).
BASIC_RULE_PLANET_MAP = {
    1: {"name": "सूर्य (Sun)", "element": "अग्नि (Fire)", "energy": ["नेतृत्व", "साहस", "आत्मविश्वास"]},
    2: {"name": "चंद्र (Moon)", "element": "जल (Water)", "energy": ["सहानुभूति", "धैर्य", "अंतर्ज्ञान"]},
    3: {"name": "बृहस्पति (Jupiter)", "element": "वायु (Air)", "energy": ["रचनात्मकता", "अभिव्यक्ति", "ज्ञान"]},
    4: {"name": "राहु (Rahu)", "element": "पृथ्वी (Earth)", "energy": ["अनुशासन", "संरचना", "स्थिरता"]},
    5: {"name": "बुध (Mercury)", "element": "वायु (Air)", "energy": ["संचार", "अनुकूलनशीलता", "गति"]},
    6: {"name": "शुक्र (Venus)", "element": "जल (Water)", "energy": ["संतुलन", "सौंदर्य", "जिम्मेदारी"]},
    7: {"name": "केतु (Ketu)", "element": "अग्नि (Fire)", "energy": ["विश्लेषण", "गहराई", "आध्यात्मिकता"]},
    8: {"name": "शनि (Saturn)", "element": "पृथ्वी (Earth)", "energy": ["करियर", "महत्वाकांक्षा", "अनुशासन"]},
    9: {"name": "मंगल (Mars)", "element": "अग्नि (Fire)", "energy": ["करुणा", "साहस", "नेतृत्व", "पूर्णता"]},
}

BASIC_RULE_COMPATIBILITY_MATRIX = {
    1: {"compatible": [1, 3, 5, 9], "neutral": [2, 4], "incompatible": [6, 7, 8]},
    2: {"compatible": [2, 4, 6, 8], "neutral": [1, 7], "incompatible": [3, 5, 9]},
    3: {"compatible": [3, 5, 7, 9], "neutral": [1, 8], "incompatible": [2, 4, 6]},
    4: {"compatible": [4, 6, 8], "neutral": [2, 7], "incompatible": [1, 3, 5, 9]},
    5: {"compatible": [5, 3, 7, 9], "neutral": [1, 8], "incompatible": [2, 4, 6]},
    6: {"compatible": [6, 2, 4, 8], "neutral": [1, 7], "incompatible": [3, 5, 9]},
    7: {"compatible": [7, 3, 5, 9], "neutral": [2, 4], "incompatible": [1, 6, 8]},
    8: {"compatible": [8, 2, 4, 6], "neutral": [1, 7], "incompatible": [3, 5, 9]},
    9: {"compatible": [9, 3, 5, 7], "neutral": [1, 8], "incompatible": [2, 4, 6]},
}

BASIC_RULE_CHARGING_DIRECTION = {
    1: {"direction": "Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Âµ (East)", "day": "Ã Â¤Â°Ã Â¤ÂµÃ Â¤Â¿Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Â¦Ã Â¤Â¯", "method": "Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥â€¹Ã Â¤Â¶Ã Â¤Â¨Ã Â¥â‚¬ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š 10-15 Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Å¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    2: {"direction": "Ã Â¤â€°Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â°-Ã Â¤ÂªÃ Â¤Â¶Ã Â¥ÂÃ Â¤Å¡Ã Â¤Â¿Ã Â¤Â® (North-West)", "day": "Ã Â¤Â¸Ã Â¥â€¹Ã Â¤Â®Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 6-8 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤Å“Ã Â¤Â² Ã Â¤Â¤Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    3: {"direction": "Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Âµ (East)", "day": "Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 7-9 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤ÂªÃ Â¥â‚¬Ã Â¤Â²Ã Â¥â‚¬ Ã Â¤ÂµÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¤Ã Â¥Â Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    4: {"direction": "Ã Â¤Â¦Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¿Ã Â¤Â£-Ã Â¤ÂªÃ Â¤Â¶Ã Â¥ÂÃ Â¤Å¡Ã Â¤Â¿Ã Â¤Â® (South-West)", "day": "Ã Â¤Â¶Ã Â¤Â¨Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 5-7 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤Â²Ã Â¤â€¢Ã Â¤Â¡Ã Â¤Â¼Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤Â¤Ã Â¤Â¹ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    5: {"direction": "Ã Â¤â€°Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â° (North)", "day": "Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â§Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 8-10 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤Â¹Ã Â¤Â°Ã Â¥â€¡ Ã Â¤Â°Ã Â¤â€šÃ Â¤â€” Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂµÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¤Ã Â¥Â Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    6: {"direction": "Ã Â¤ÂªÃ Â¤Â¶Ã Â¥ÂÃ Â¤Å¡Ã Â¤Â¿Ã Â¤Â® (West)", "day": "Ã Â¤Â¶Ã Â¥ÂÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 6-8 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤Â«Ã Â¥â€šÃ Â¤Â²Ã Â¥â€¹Ã Â¤â€š/Ã Â¤Å¡Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¦Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    7: {"direction": "Ã Â¤Â¦Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¿Ã Â¤Â£-Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Âµ (South-East)", "day": "Ã Â¤Â®Ã Â¤â€šÃ Â¤â€”Ã Â¤Â²Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 4-6 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤Â§Ã Â¥â€šÃ Â¤Âª Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â¦Ã Â¥â‚¬Ã Â¤ÂªÃ Â¤â€¢ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    8: {"direction": "Ã Â¤Â¦Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¿Ã Â¤Â£ (South)", "day": "Ã Â¤Â¶Ã Â¤Â¨Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¬Ã Â¤Â¹ 7-9 Ã Â¤Â¬Ã Â¤Å“Ã Â¥â€¡", "method": "Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤Â¤Ã Â¤Â¹ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
    9: {"direction": "Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Âµ (East)", "day": "Ã Â¤Â®Ã Â¤â€šÃ Â¤â€”Ã Â¤Â²Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°", "time": "Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Â¦Ã Â¤Â¯", "method": "Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â² Ã Â¤ÂµÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¤Ã Â¥Â Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤â€“Ã Â¥ÂÃ Â¤Â²Ã Â¥â‚¬ Ã Â¤Å“Ã Â¤â€”Ã Â¤Â¹ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€š"},
}

BASIC_RULE_MANTRA_MAP = {
    1: "Ã Â¥Â Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¯ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    2: "Ã Â¥Â Ã Â¤Å¡Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¯ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    3: "Ã Â¥Â Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤ÂµÃ Â¥â€¡ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    4: "Ã Â¥Â Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¹Ã Â¤ÂµÃ Â¥â€¡ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    5: "Ã Â¥Â Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â§Ã Â¤Â¾Ã Â¤Â¯ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    6: "Ã Â¥Â Ã Â¤Â¶Ã Â¥ÂÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¯ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    7: "Ã Â¥Â Ã Â¤â€¢Ã Â¥â€¡Ã Â¤Â¤Ã Â¤ÂµÃ Â¥â€¡ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    8: "Ã Â¥Â Ã Â¤Â¶Ã Â¤Â¨Ã Â¤Â¯Ã Â¥â€¡ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
    9: "Ã Â¥Â Ã Â¤Â®Ã Â¤â€šÃ Â¤â€”Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â¯ Ã Â¤Â¨Ã Â¤Â®Ã Â¤Æ’",
}

BASIC_RULE_GEMSTONE_MAP = {
    1: {"name": "Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â£Ã Â¤Â¿Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¯ (Ruby)", "color": "Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â²"},
    2: {"name": "Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¤Ã Â¥â‚¬ (Pearl)", "color": "Ã Â¤Â¸Ã Â¤Â«Ã Â¥â€¡Ã Â¤Â¦"},
    3: {"name": "Ã Â¤ÂªÃ Â¤Â¨Ã Â¥ÂÃ Â¤Â¨Ã Â¤Â¾ (Emerald)", "color": "Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾"},
    4: {"name": "Ã Â¤â€”Ã Â¥â€¹Ã Â¤Â®Ã Â¥â€¡Ã Â¤Â¦ (Hessonite)", "color": "Ã Â¤Â­Ã Â¥â€šÃ Â¤Â°Ã Â¤Â¾"},
    5: {"name": "Ã Â¤ÂªÃ Â¤Â¨Ã Â¥ÂÃ Â¤Â¨Ã Â¤Â¾ (Emerald)", "color": "Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾"},
    6: {"name": "Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤Â°Ã Â¤Â¾ (Diamond)", "color": "Ã Â¤Â¸Ã Â¤Â«Ã Â¥â€¡Ã Â¤Â¦"},
    7: {"name": "Ã Â¤Â²Ã Â¤Â¹Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¨Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾ (Cat's Eye)", "color": "Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾-Ã Â¤Â­Ã Â¥â€šÃ Â¤Â°Ã Â¤Â¾"},
    8: {"name": "Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â® (Blue Sapphire)", "color": "Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾"},
    9: {"name": "Ã Â¤Â®Ã Â¥â€šÃ Â¤â€šÃ Â¤â€”Ã Â¤Â¾ (Coral)", "color": "Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â²"},
}

BASIC_RULE_RUDRAKSHA_MISSING = {
    1: "1 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    2: "2 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    3: "3 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    4: "4 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    5: "5 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    6: "6 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    7: "7 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    8: "8 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
    9: "9 Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·",
}

BASIC_RULE_YANTRA_MAP = {
    1: "Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    2: "Ã Â¤Å¡Ã Â¤â€šÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â° Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    3: "Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥Â Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    4: "Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¹Ã Â¥Â Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    5: "Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â§ Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    6: "Ã Â¤Â¶Ã Â¥ÂÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â° Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    7: "Ã Â¤â€¢Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Â Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    8: "Ã Â¤Â¶Ã Â¤Â¨Ã Â¤Â¿ Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    9: "Ã Â¤Â®Ã Â¤â€šÃ Â¤â€”Ã Â¤Â² Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
}

BASIC_RULE_COVER_COLOR = {
    1: "Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â°Ã Â¤â€šÃ Â¤â€”Ã Â¥â‚¬ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â²",
    2: "Ã Â¤Â¸Ã Â¤Â«Ã Â¥â€¡Ã Â¤Â¦ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Å¡Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¦Ã Â¥â‚¬",
    3: "Ã Â¤ÂªÃ Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¨Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾",
    4: "Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾",
    5: "Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾",
    6: "Ã Â¤Â¸Ã Â¤Â«Ã Â¥â€¡Ã Â¤Â¦ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤â€”Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¾Ã Â¤Â¬Ã Â¥â‚¬",
    7: "Ã Â¤Â¬Ã Â¥Ë†Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¨Ã Â¥â‚¬",
    8: "Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¾ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾ Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾",
    9: "Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â² Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾ Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â²",
}

BASIC_RULE_WALLPAPER_THEME = {
    1: "Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Â¦Ã Â¤Â¯ Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯",
    2: "Ã Â¤Å¡Ã Â¤Â¾Ã Â¤ÂÃ Â¤Â¦, Ã Â¤Â¸Ã Â¤Â®Ã Â¥ÂÃ Â¤Â¦Ã Â¥ÂÃ Â¤Â°, Ã Â¤Å“Ã Â¤Â² Ã Â¤Â¦Ã Â¥Æ’Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯",
    3: "Ã Â¤â€ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â¶, Ã Â¤ÂªÃ Â¥â‚¬Ã Â¤Â²Ã Â¥â€¡ Ã Â¤Â«Ã Â¥â€šÃ Â¤Â², Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â°Ã Â¥â€¡",
    4: "Ã Â¤Å“Ã Â¤â€šÃ Â¤â€”Ã Â¤Â², Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â¡Ã Â¤Â¼, Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾Ã Â¤Â²Ã Â¥â‚¬",
    5: "Ã Â¤Â¹Ã Â¤ÂµÃ Â¤Â¾, Ã Â¤â€“Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¾ Ã Â¤â€ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â¨",
    6: "Ã Â¤Â«Ã Â¥â€šÃ Â¤Â², Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€¢Ã Â¥Æ’Ã Â¤Â¤Ã Â¤Â¿, Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤Â¦Ã Â¥Æ’Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯",
    7: "Ã Â¤Â®Ã Â¤â€šÃ Â¤Â¡Ã Â¤Â²Ã Â¤Â¾, Ã Â¤Â§Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¨, Ã Â¤â€ Ã Â¤Â§Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Å¡Ã Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â°",
    8: "Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â¡Ã Â¤Â¼, Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾, Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾ Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾ Ã Â¤Â¦Ã Â¥Æ’Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â¯",
    9: "Ã Â¤Â¸Ã Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¤, Ã Â¤â€¦Ã Â¤â€”Ã Â¥ÂÃ Â¤Â¨Ã Â¤Â¿, Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â² Ã Â¤Â¥Ã Â¥â‚¬Ã Â¤Â®",
}

BASIC_RULE_POSITIVE_ATTRIBUTES = {
    1: ["Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ", "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â®Ã Â¤Â¤Ã Â¤Â¾", "Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸"],
    2: ["Ã Â¤Â¸Ã Â¤Â¹Ã Â¤Â¯Ã Â¥â€¹Ã Â¤â€”", "Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â", "Ã Â¤Â§Ã Â¥Ë†Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯"],
    3: ["Ã Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â­Ã Â¤Â¿Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿", "Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤â€“Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â®Ã Â¤Â¤Ã Â¤Â¾", "Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â®Ã Â¤Â¾Ã Â¤Å“Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ"],
    4: ["Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨", "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾", "Ã Â¤Â¦Ã Â¥â‚¬Ã Â¤Â°Ã Â¥ÂÃ Â¤ËœÃ Â¤â€¢Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾"],
    5: ["Ã Â¤Â¤Ã Â¥â€¡Ã Â¤Å“ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤â€¢Ã Â¥â€šÃ Â¤Â²Ã Â¤Â¨", "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Å¡Ã Â¤Â¾Ã Â¤Â°", "Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿Ã Â¤Â¶Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¤Ã Â¤Â¾"],
    6: ["Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â®Ã Â¥â€¡Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬", "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨", "Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¨ Ã Â¤Â¶Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿"],
    7: ["Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â²Ã Â¥â€¡Ã Â¤Â·Ã Â¤Â£", "Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Ë†", "Ã Â¤â€ Ã Â¤Â§Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥Æ’Ã Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¿"],
    8: ["Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â° Ã Â¤Â«Ã Â¥â€¹Ã Â¤â€¢Ã Â¤Â¸", "Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¬Ã Â¤â€šÃ Â¤Â§Ã Â¤Â¨", "Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â®Ã Â¥â€¡Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬"],
    9: ["Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¹Ã Â¤Â¸", "Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¤Ã Â¤Â¾", "Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾"],
}

BASIC_RULE_NEGATIVE_ATTRIBUTES = {
    1: ["Ã Â¤â€¦Ã Â¤Â¹Ã Â¤â€š Ã Â¤Â¸Ã Â¤â€šÃ Â¤ËœÃ Â¤Â°Ã Â¥ÂÃ Â¤Â·", "Ã Â¤Å“Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Å“Ã Â¤Â¼Ã Â¥â‚¬", "Ã Â¤ÂÃ Â¤â€¢Ã Â¤Â¤Ã Â¤Â°Ã Â¤Â«Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯"],
    2: ["Ã Â¤â€œÃ Â¤ÂµÃ Â¤Â°Ã Â¤Â¥Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€”", "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â°Ã Â¥â‚¬", "Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤â€°Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â°-Ã Â¤Å¡Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Âµ"],
    3: ["Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤Ã Â¤Â¤Ã Â¤Â¾", "Ã Â¤Â§Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤Â­Ã Â¤Å¸Ã Â¤â€¢Ã Â¤Â¨Ã Â¤Â¾", "Ã Â¤â€¦Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯"],
    4: ["Ã Â¤â€¢Ã Â¤Â Ã Â¥â€¹Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾", "Ã Â¤Â¤Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Âµ Ã Â¤Å“Ã Â¤Â®Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¤Â¾", "Ã Â¤Â²Ã Â¤Å¡Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾Ã Â¤ÂªÃ Â¤Â¨ Ã Â¤â€¢Ã Â¤Â®"],
    5: ["Ã Â¤Â¬Ã Â¥â€¡Ã Â¤Å¡Ã Â¥Ë†Ã Â¤Â¨Ã Â¥â‚¬", "Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Å¸Ã Â¥â€šÃ Â¤Å¸Ã Â¤Â¨Ã Â¤Â¾", "Ã Â¤â€¡Ã Â¤Â®Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â²Ã Â¥ÂÃ Â¤Â¸ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯"],
    6: ["Ã Â¤â€œÃ Â¤ÂµÃ Â¤Â°-Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¥â€°Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¸Ã Â¤Â¿Ã Â¤Â¬Ã Â¤Â¿Ã Â¤Â²Ã Â¤Â¿Ã Â¤Å¸Ã Â¥â‚¬", "Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¬Ã Â¥â€¹Ã Â¤Â", "Ã Â¤Â²Ã Â¥â€¹Ã Â¤â€”Ã Â¥â€¹Ã Â¤â€š Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤â€“Ã Â¥ÂÃ Â¤Â¶ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ"],
    7: ["Ã Â¤â€¦Ã Â¤Â²Ã Â¤â€”Ã Â¤Â¾Ã Â¤Âµ", "Ã Â¤â€¦Ã Â¤Â§Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â²Ã Â¥â€¡Ã Â¤Â·Ã Â¤Â£", "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â²Ã Â¤â€šÃ Â¤Â¬"],
    8: ["Ã Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â® Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ", "Ã Â¤â€¢Ã Â¤Â Ã Â¥â€¹Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾", "Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¬Ã Â¥â€¹Ã Â¤Â"],
    9: ["Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨", "Ã Â¤Â¸Ã Â¤â€šÃ Â¤ËœÃ Â¤Â°Ã Â¥ÂÃ Â¤Â· Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿", "Ã Â¤Â¬Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¨Ã Â¤â€ Ã Â¤â€°Ã Â¤Å¸ Ã Â¤Å“Ã Â¥â€¹Ã Â¤â€“Ã Â¤Â¿Ã Â¤Â®"],
}


class ReportPayloadValidationError(ValueError):
    def __init__(self, *, plan_key: str, missing_fields: List[str]):
        self.plan_key = plan_key
        self.missing_fields = missing_fields
        message = (
            f"Payload validation failed for plan '{plan_key}'. "
            f"Missing required fields: {', '.join(missing_fields)}"
        )
        super().__init__(message)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            if value.strip():
                return value
            continue
        if value not in (None, "", [], {}):
            return value
    return values[-1] if values else None


def _legacy_input_normalized_from_canonical(
    canonical_normalized_input: Dict[str, Any],
    *,
    current_problem: str = "",
    plan_key: str = "basic",
) -> Dict[str, Any]:
    city = str(canonical_normalized_input.get("city") or "").strip()
    country = str(canonical_normalized_input.get("country") or "").strip()
    if city and country:
        birth_place = f"{city}, {country}"
    else:
        birth_place = city or country

    return {
        "name": str(canonical_normalized_input.get("fullName") or "").strip(),
        "mobile": str(canonical_normalized_input.get("mobileNumber") or "").strip(),
        "email": str(canonical_normalized_input.get("email") or "").strip(),
        "date_of_birth": str(canonical_normalized_input.get("dateOfBirth") or "").strip(),
        "birth_place": birth_place,
        "gender": str(canonical_normalized_input.get("gender") or "").strip(),
        "language": str(canonical_normalized_input.get("language") or "").strip(),
        "current_problem": str(
            current_problem
            or canonical_normalized_input.get("currentProblem")
            or canonical_normalized_input.get("focusArea")
            or ""
        ).strip(),
        "report_format": str(plan_key or "basic"),
    }


def _merge_profile_snapshot(
    *,
    deterministic_profile_snapshot: Dict[str, Any],
    ai_profile_snapshot: Any,
    canonical_normalized_input: Dict[str, Any],
) -> Dict[str, Any]:
    merged = dict(deterministic_profile_snapshot or {})
    if isinstance(ai_profile_snapshot, dict):
        for key, value in ai_profile_snapshot.items():
            if value not in (None, "", [], {}):
                merged[key] = value

    # Canonical identity fields always win for hydration reliability.
    merged["fullName"] = str(canonical_normalized_input.get("fullName") or "").strip()
    merged["dateOfBirth"] = str(canonical_normalized_input.get("dateOfBirth") or "").strip()
    merged["mobileNumber"] = str(canonical_normalized_input.get("mobileNumber") or "").strip()
    merged["email"] = str(canonical_normalized_input.get("email") or "").strip()
    merged["gender"] = str(canonical_normalized_input.get("gender") or "").strip()
    return merged


def _merge_dashboard(*, deterministic_dashboard: Dict[str, Any], ai_dashboard: Any) -> Dict[str, Any]:
    merged = dict(deterministic_dashboard or {})
    if isinstance(ai_dashboard, dict):
        merged["riskBand"] = _first_non_empty(ai_dashboard.get("riskBand"), merged.get("riskBand"))
        merged["confidenceScore"] = _first_non_empty(
            ai_dashboard.get("confidenceScore"),
            merged.get("confidenceScore"),
        )
        ai_loaded = ai_dashboard.get("loadedEnergyMetrics")
        if isinstance(ai_loaded, list) and ai_loaded:
            merged["loadedEnergyMetrics"] = ai_loaded
    return merged


def _read_path(data: Dict[str, Any], dotted_path: str) -> Any:
    cursor: Any = data
    for part in dotted_path.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return cursor


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _validate_required_fields(
    normalized_input: Dict[str, Any],
    required_fields: Iterable[str],
    *,
    plan_key: str,
) -> None:
    missing = [field for field in required_fields if _is_missing(_read_path(normalized_input, field))]
    if missing:
        raise ReportPayloadValidationError(plan_key=plan_key, missing_fields=missing)


def _validate_profile_identity(canonical_normalized_input: Dict[str, Any]) -> None:
    required = {
        "fullName": canonical_normalized_input.get("fullName"),
        "dateOfBirth": canonical_normalized_input.get("dateOfBirth"),
        "mobileNumber": canonical_normalized_input.get("mobileNumber"),
    }
    failed = [field for field, value in required.items() if _is_missing(value)]
    if failed:
        logger.error("Renderer identity validation failed. Missing canonical fields: %s", failed)
        raise ValueError(f"Renderer identity validation failed: missing {', '.join(failed)}")


def _digits_only(value: str) -> List[int]:
    return [int(char) for char in str(value or "") if char.isdigit()]


def _sum_expression(values: List[int]) -> str:
    if not values:
        return "Not available"
    return " + ".join(str(value) for value in values)


def _reduce_to_single_digit(value: int) -> Tuple[List[int], int]:
    if value <= 0:
        return [0], 0

    steps = [value]
    current = value
    while current > 9:
        current = sum(int(char) for char in str(current))
        steps.append(current)
    return steps, current


def _format_dob_display(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "Not Provided"

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def _compatibility_label(vibration: int, life_path: int, destiny: int) -> str:
    anchors = [value for value in (life_path, destiny) if isinstance(value, int) and value > 0]
    if not anchors or vibration <= 0:
        return "Moderate"
    if any(vibration == anchor for anchor in anchors):
        return "High"
    if any(vibration in SUPPORTIVE_NUMBERS.get(anchor, set()) for anchor in anchors):
        return "Moderate"
    if any(abs(vibration - anchor) <= 1 for anchor in anchors):
        return "Moderate"
    return "Low"


def _single_digit_anchor(value: int) -> int:
    if value in {11, 22, 33}:
        return sum(int(ch) for ch in str(value))
    return value


def _lo_shu_from_mobile_digits(digits: List[int]) -> Dict[str, Any]:
    counts = {digit: 0 for digit in range(10)}
    for digit in digits:
        counts[digit] += 1

    present = [digit for digit in range(1, 10) if counts[digit] > 0]
    missing = [digit for digit in range(1, 10) if counts[digit] == 0]
    repeating = [digit for digit in range(1, 10) if counts[digit] > 1]

    return {
        "counts": counts,
        "present": present,
        "missing": missing,
        "repeating": repeating,
    }


def _impact_level(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Moderate"
    return "Low"


def _fix_mojibake_text(value: Any) -> Any:
    if isinstance(value, str):
        repaired = value
        mojibake_tokens = (
            "ÃƒÂ Ã‚Â¤",
            "ÃƒÂ Ã‚Â¥",
            "ÃƒÂ¢Ã…â€œ",
            "ÃƒÂ¢Ã…Â¡",
            "ÃƒÂ¢Ã‚Â",
            "ÃƒÂ°Ã…Â¸",
            "Ã Â¤",
            "Ã Â¥",
            "à¤",
            "à¥",
            "Ã¢Å“",
            "Ã¢Å¡",
            "Ã¢Â",
            "Ã°Å¸",
            "Ã¯Â¸",
            "â",
            "ð",
            "рџ",
            "вњ",
            "вљ",
            "вќ",
            "пё",
            "Ð",
            "Ñ",
            "Â",
            "Ã",
        )
        cp1252_reverse = {
            "â‚¬": 0x80,
            "â€š": 0x82,
            "Æ’": 0x83,
            "â€ž": 0x84,
            "â€¦": 0x85,
            "â€ ": 0x86,
            "â€¡": 0x87,
            "Ë†": 0x88,
            "â€°": 0x89,
            "Å ": 0x8A,
            "â€¹": 0x8B,
            "Å’": 0x8C,
            "Å½": 0x8E,
            "â€˜": 0x91,
            "â€™": 0x92,
            "â€œ": 0x93,
            "â€": 0x94,
            "â€¢": 0x95,
            "â€“": 0x96,
            "â€”": 0x97,
            "Ëœ": 0x98,
            "â„¢": 0x99,
            "Å¡": 0x9A,
            "â€º": 0x9B,
            "Å“": 0x9C,
            "Å¾": 0x9E,
            "Å¸": 0x9F,
        }

        def _mojibake_hit_count(text: str) -> int:
            return sum(text.count(token) for token in mojibake_tokens)

        def _devanagari_count(text: str) -> int:
            return sum(1 for ch in text if "\u0900" <= ch <= "\u097f")

        def _question_mark_count(text: str) -> int:
            return text.count("?")

        def _rebuild_bytes(text: str) -> bytes | None:
            buf = bytearray()
            for ch in text:
                code = ord(ch)
                if code <= 0xFF:
                    buf.append(code)
                    continue
                mapped = cp1252_reverse.get(ch)
                if mapped is None:
                    return None
                buf.append(mapped)
            return bytes(buf)

        def _decode_via_encoding(text: str, source_encoding: str, encode_errors: str, decode_errors: str) -> str | None:
            try:
                payload = text.encode(source_encoding, errors=encode_errors)
                return payload.decode("utf-8", errors=decode_errors)
            except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                return None

        for _ in range(3):
            if not any(token in repaired for token in mojibake_tokens):
                break
            best = repaired
            best_score = (
                _devanagari_count(repaired),
                -_mojibake_hit_count(repaired),
                -_question_mark_count(repaired),
            )

            raw_bytes = _rebuild_bytes(repaired)
            if raw_bytes is not None:
                for err_mode in ("strict", "replace", "ignore"):
                    try:
                        decoded = raw_bytes.decode("utf-8", errors=err_mode)
                    except UnicodeDecodeError:
                        continue
                    candidate_score = (
                        _devanagari_count(decoded),
                        -_mojibake_hit_count(decoded),
                        -_question_mark_count(decoded),
                    )
                    if candidate_score > best_score:
                        best = decoded
                        best_score = candidate_score
                    # Some strings need two decode rounds before Devanagari becomes readable.
                    for source_encoding in ("latin-1", "cp1252", "cp1251"):
                        decoded_twice = _decode_via_encoding(decoded, source_encoding, "ignore", "ignore")
                        if not decoded_twice:
                            continue
                        second_score = (
                            _devanagari_count(decoded_twice),
                            -_mojibake_hit_count(decoded_twice),
                            -_question_mark_count(decoded_twice),
                        )
                        if second_score > best_score:
                            best = decoded_twice
                            best_score = second_score

            for source_encoding in ("latin-1", "cp1252", "cp1251"):
                for encode_errors, decode_errors in (
                    ("strict", "strict"),
                    ("strict", "replace"),
                    ("replace", "replace"),
                    ("ignore", "ignore"),
                ):
                    decoded = _decode_via_encoding(repaired, source_encoding, encode_errors, decode_errors)
                    if not decoded:
                        continue
                    candidate_score = (
                        _devanagari_count(decoded),
                        -_mojibake_hit_count(decoded),
                        -_question_mark_count(decoded),
                    )
                    if candidate_score > best_score:
                        best = decoded
                        best_score = candidate_score
                    for second_encoding in ("latin-1", "cp1252", "cp1251"):
                        decoded_twice = _decode_via_encoding(decoded, second_encoding, "ignore", "ignore")
                        if not decoded_twice:
                            continue
                        second_score = (
                            _devanagari_count(decoded_twice),
                            -_mojibake_hit_count(decoded_twice),
                            -_question_mark_count(decoded_twice),
                        )
                        if second_score > best_score:
                            best = decoded_twice
                            best_score = second_score

            if best == repaired:
                break
            repaired = best
        return repaired
    if isinstance(value, list):
        return [_fix_mojibake_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _fix_mojibake_text(item) for key, item in value.items()}
    return value


def _build_basic_mobile_report_sections_legacy(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
) -> List[Dict[str, Any]]:
    full_name = str(canonical_normalized_input.get("fullName") or "Not Provided").strip() or "Not Provided"
    first_name = full_name.split()[0] if full_name and full_name != "Not Provided" else "User"
    dob_raw = str(canonical_normalized_input.get("dateOfBirth") or "").strip()
    dob_display = _format_dob_display(dob_raw)
    mobile_number = str(canonical_normalized_input.get("mobileNumber") or "Not Provided").strip() or "Not Provided"
    city = str(canonical_normalized_input.get("city") or "").strip() or "Not Provided"
    primary_challenge = str(
        canonical_normalized_input.get("currentProblem")
        or canonical_normalized_input.get("focusArea")
        or "consistency"
    ).strip() or "consistency"

    digits = _digits_only(mobile_number)
    total = sum(digits) if digits else 0
    reduction_steps, reduced = _reduce_to_single_digit(total)

    mobile_analysis = numerology_values.get("mobile_analysis") or {}
    vibration = int(mobile_analysis.get("mobile_vibration") or reduced or 0)
    if vibration <= 0:
        vibration = reduced

    pyth = numerology_values.get("pythagorean") or {}
    life_path_raw = int(pyth.get("life_path_number") or 0)
    life_path = _single_digit_anchor(life_path_raw)

    associated_planet = PLANET_BY_VIBRATION.get(vibration, "Unknown")
    associated_element = ELEMENT_BY_VIBRATION.get(vibration, "Air")
    core_energy = ", ".join(CORE_ENERGY_KEYWORDS.get(vibration, ["adaptive", "practical", "steady"]))
    planet_name = str(associated_planet or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(str(associated_element or "तत्व उपलब्ध नहीं").strip())
    planet_energy_text = str(core_energy or "स्थिरता").strip()
    strengths = VIBRATION_TRAITS.get(vibration, ["Practical", "Balanced", "Adaptive"])
    risks = VIBRATION_CHALLENGES.get(vibration, ["Inconsistency", "Decision drift", "Stress reactivity"])
    compatibility = _compatibility_label(vibration, life_path, 0)
    compatibility_sentence = (
        f"Vibration {vibration or 'N/A'} has {compatibility} alignment with your "
        f"Life Path {life_path_raw or 'N/A'}."
    )

    loshu = _lo_shu_from_mobile_digits(digits)
    digit_counts = loshu["counts"]
    present_with_zero = [digit for digit in range(10) if digit_counts[digit] > 0]
    present_text = ", ".join(str(v) for v in loshu["present"]) or "None"
    present_with_zero_text = ", ".join(str(v) for v in present_with_zero) or "None"
    missing_text = ", ".join(str(v) for v in loshu["missing"]) or "None"
    repeating_text = ", ".join(str(v) for v in loshu["repeating"]) or "None"
    repeating_detail_parts = []
    for digit in range(10):
        count = digit_counts[digit]
        if count > 1:
            repeating_detail_parts.append(f"{digit} ({count}x)")
    repeating_detail_text = ", ".join(repeating_detail_parts) or repeating_text
    repeating_digits = _basic_repeating_digits(digit_counts)

    def _mark(number: int) -> str:
        return "Y" if digit_counts[number] > 0 else "N"

    lo_shu_grid_block = (
        f"4:{_mark(4)} | 9:{_mark(9)} | 2:{_mark(2)}\n"
        f"3:{_mark(3)} | 5:{_mark(5)} | 7:{_mark(7)}\n"
        f"8:{_mark(8)} | 1:{_mark(1)} | 6:{_mark(6)}"
    )

    missing_for_consistency = {4, 6, 8}
    has_consistency_gap = bool(missing_for_consistency.intersection(set(loshu["missing"])))
    if has_consistency_gap:
        loshu_insight = (
            f"Missing {missing_text} indicates structural gaps; consistency discipline needs conscious reinforcement."
        )
    elif 5 in loshu["repeating"]:
        loshu_insight = "Repeating 5 amplifies movement energy; routines must be anchored for stability."
    else:
        loshu_insight = "Grid distribution is workable; consistency improves with fixed execution windows."

    missing_count = len(loshu["missing"])
    comp_score = {"High": 82, "Moderate": 62, "Low": 38}.get(compatibility, 58)
    friction_penalty = missing_count * 5
    challenge_penalty = 8 if "consist" in primary_challenge.lower() and has_consistency_gap else 3

    consistency_score = max(15, comp_score - friction_penalty - challenge_penalty)
    confidence_score = max(20, comp_score + 6 - (4 if 1 in loshu["missing"] else 0))
    finance_score = max(20, comp_score - (8 if 8 in loshu["missing"] else 0))
    career_score = max(20, comp_score + 4 - (6 if 4 in loshu["missing"] else 0))
    relationship_score = max(20, comp_score + (3 if 2 in loshu["present"] else -4))
    decision_score = max(20, comp_score + (4 if 5 in loshu["present"] else -5))

    keep_change_verdict = "MANAGE"
    if compatibility == "High" and missing_count <= 3:
        keep_change_verdict = "KEEP"
    elif compatibility == "Low" or missing_count >= 5:
        keep_change_verdict = "CHANGE"

    anchors = [value for value in {life_path} if value > 0]
    preferred_vibrations = sorted(
        {
            value
            for anchor in anchors
            for value in ({anchor} | SUPPORTIVE_NUMBERS.get(anchor, set()))
            if 1 <= value <= 9
        }
    )[:3]
    if not preferred_vibrations:
        preferred_vibrations = sorted(SUPPORTIVE_NUMBERS.get(vibration, {1, 3, 5}))[:3]

    avoid_vibrations = [value for value in range(1, 10) if value not in preferred_vibrations][:3]
    preferred_digits_tail = ", ".join(str(value) for value in preferred_vibrations)
    avoid_digits = ", ".join(str(value) for value in avoid_vibrations)

    charging_direction = CHARGING_DIRECTION_BY_VIBRATION.get(vibration, "East")
    best_time = "6:00 AM - 7:00 AM"
    if city and city != "Not Provided":
        best_time = f"6:00 AM - 7:00 AM ({city} local time)"

    mantra = MANTRA_BY_VIBRATION.get(vibration, "Om Namah Shivaya")
    color = COLOR_BY_VIBRATION.get(vibration, "Neutral Earth tones")
    digital_nickname = f"{first_name}-{preferred_vibrations[0] if preferred_vibrations else vibration}"

    summary_generated_at = datetime.now(UTC).strftime("%d %b %Y")
    key_insight = (
        f"{first_name}, your mobile vibration {vibration} is usable, but your '{primary_challenge}' "
        f"improves fastest when consistency routines are locked for 21 days."
    )

    effects_positive, effects_negative = _basic_mobile_effects_lines(
        strengths=strengths,
        risks=risks,
        missing_digits=loshu["missing"],
        repeating_digits=repeating_digits,
        primary_challenge=primary_challenge,
    )

    return _fix_mojibake_text([
        {
            "order": 1,
            "key": "basic_mobile_energy",
            "title": "1. Mobile Energy\nÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â² ÃƒÂ Ã‚Â¤Ã…Â ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¤Ã‚Â¾ | Mobile Energy",
            "subtitle": "Core vibration signature of the current mobile number.",
            "layout": "center_feature",
            "blocks": [
                f"\u092e\u094b\u092c\u093e\u0907\u0932 \u0928\u0902\u092c\u0930: {inputs['mobile_number']}",
                f"\u092e\u0942\u0932 \u0905\u0902\u0915 (Vibration): {core['mobile']['vibration']}",
                f"\u0917\u094d\u0930\u0939: {planet_name}",
                f"\u0924\u0924\u094d\u0935: {planet_element}",
                f"\u092a\u094d\u0930\u092e\u0941\u0916 \u090a\u0930\u094d\u091c\u093e \u0938\u0902\u0915\u0947\u0924: {planet_energy_text}",
                profile_line,
                *([f"\u0935\u094d\u092f\u0915\u094d\u0924\u093f\u0917\u0924 \u091f\u093f\u092a\u094d\u092a\u0923\u0940: {ai_mobile_clean}"] if ai_mobile_clean else []),
                *mobile_insight_lines,

            ],
        },
        {
            "order": 2,
            "key": "basic_lo_shu_grid",
            "title": "2. Lo Shu Grid\nÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã¢â‚¬â€ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¡ | Lo Shu Grid",
            "subtitle": "Digit presence, missing numbers, and pattern signal from mobile number.",
            "layout": "premium_card",
            "blocks": [
                f"Your Number: {mobile_number}",
                "Digit Frequency (1-9,0): "
                + ", ".join(f"{digit}={digit_counts[digit]}" for digit in range(1, 10))
                + f", 0={digit_counts[0]}",
                f"Lo Shu Grid (Y=present / N=missing):\n{lo_shu_grid_block}",
                f"Present Digits: {present_with_zero_text}",
                f"Missing Digits: {missing_text}",
                f"Repeating Digits: {repeating_detail_text}",
                f"Pattern Insight: {loshu_insight}",
            ],
        },
        {
            "order": 3,
            "key": "basic_positive_negative_impact",
            "title": "3. Positive/Negative Impact\nÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢/ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â­ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Âµ | Impact",
            "subtitle": "Balanced view of strengths and risk patterns.",
            "layout": "split_analysis",
            "blocks": [
                f"Positive 1: {effects_positive[0]}",
                f"Positive 2: {effects_positive[1]}",
                f"Positive 3: {effects_positive[2]}",
                f"Risk 1: {effects_negative[0]}",
                f"Risk 2: {effects_negative[1]}",
                f"Risk 3: {effects_negative[2]}",
            ],
        },
        {
            "order": 4,
            "key": "basic_life_path_context",
            "title": "4. Life Path Context\nÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¨ ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¥ ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â­ | Life Path Context",
            "subtitle": "Mobile vibration alignment against your core life direction.",
            "layout": "comparison_meter",
            "blocks": [
                f"Life Path Number: {life_path_raw or 'N/A'}",
                f"Compatibility: {compatibility}",
                f"Context: {compatibility_sentence}",
                "Meaning: Dynamic energy is strong, but consistency improves with structured routines",
            ],
        },
        {
            "order": 5,
            "key": "basic_life_area_impact",
            "title": "5. Impact on Life Areas\nÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¨ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â·ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â° ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â­ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Âµ | Life Areas",
            "subtitle": f"Primary challenge focus: {primary_challenge}",
            "layout": "four_card_grid",
            "blocks": [
                f"Consistency: {_impact_level(consistency_score)} ({consistency_score}/100) - Start speed high, sustain rhythm variable",
                f"Confidence: {_impact_level(confidence_score)} ({confidence_score}/100) - Communication intent is strong under focus",
                f"Financial Discipline: {_impact_level(finance_score)} ({finance_score}/100) - Impulsive decisions need guardrails",
                f"Career Execution: {_impact_level(career_score)} ({career_score}/100) - Best results with weekly execution review",
                f"Relationships: {_impact_level(relationship_score)} ({relationship_score}/100) - Tone management improves harmony",
                f"Decision Quality: {_impact_level(decision_score)} ({decision_score}/100) - Use pause-before-response rule",
            ],
        },
        {
            "order": 6,
            "key": "basic_keep_change_verdict",
            "title": "6. Keep/Change Verdict\nÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡/ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â£ÃƒÂ Ã‚Â¤Ã‚Â¯ | Verdict",
            "subtitle": "Decision based on compatibility + Lo Shu friction + challenge context.",
            "layout": "closing_reflection",
            "blocks": [
                f"Verdict: {keep_change_verdict}",
                f"Reason 1: Compatibility = {compatibility}, Missing digits = {missing_count}",
                f"Reason 2: Challenge '{primary_challenge}' shows strongest sensitivity in consistency axis",
                "Reason 3: Use remedies first if verdict is Manage; move to change guide if drift persists",
                "Decision Rule: Re-evaluate after 21-day tracker completion",
            ],
        },
        {
            "order": 7,
            "key": "basic_if_changing_guide",
            "title": "7. If Changing Guide\nÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â¿ ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬â€ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ | Change Guide",
            "subtitle": "What to look for in a future number structure.",
            "layout": "triad_cards",
            "blocks": [
                f"Preferred Vibrations: {', '.join(str(v) for v in preferred_vibrations)}",
                f"Preferred Digits (last 4): {preferred_digits_tail}",
                f"Avoid Vibrations: {', '.join(str(v) for v in avoid_vibrations)}",
                f"Avoid Digits/Patterns: {avoid_digits}; avoid 555, 333, 111 clusters",
                "Sample Pattern: X 4 X X 6 X X 8 X X",
            ],
        },
        {
            "order": 8,
            "key": "basic_charging_direction",
            "title": "8. Charging Direction\nÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã¢â‚¬â€ ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¾ | Charging Direction",
            "subtitle": "Directional protocol to stabilize daily signal rhythm.",
            "layout": "split_insight",
            "blocks": [
                f"Direction: Face {charging_direction}",
                f"Best Time: {best_time}",
                "Method: Place phone flat, screen up, for 11 minutes before first major communication",
                "Discipline: Repeat minimum 5 days/week for 21 days",
            ],
        },
        {
            "order": 9,
            "key": "basic_remedies_table",
            "title": "9. Remedies Table\nÃƒÂ Ã‚Â¤Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¯ ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ | Remedies",
            "subtitle": "Deterministic remedy stack for mobile vibration balancing.",
            "layout": "remedy_cards",
            "blocks": [
                f"Mantra: {mantra} (108 repetitions daily)",
                f"Color: Use {color} in case/wallpaper daily",
                "Placement: Keep phone on a wooden surface during focused work blocks",
                "Communication Window: 10:00-12:00 and 16:00-18:00 for important calls",
                f"Digital Remedy: Save own number as '{digital_nickname}'",
            ],
        },
        {
            "order": 10,
            "key": "basic_21_day_tracker",
            "title": "10. 21-Day Tracker\n21-ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Â¯ ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â° | 21-Day Tracker",
            "subtitle": "Execution cadence for behavior-level stabilization.",
            "layout": "timeline_strategy",
            "blocks": [
                "Week 1 (Days 1-7): Mantra + Charging Direction discipline",
                "Week 2 (Days 8-14): Add color + placement protocol",
                "Week 3 (Days 15-21): Full protocol + fixed communication windows",
                "Daily Check: Mark Done/Not Done for 5 actions and review every 3rd day",
            ],
        },
        {
            "order": 11,
            "key": "basic_summary_table_v2",
            "title": "11. Summary Table\nÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¶ ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ | Summary",
            "subtitle": "Current status and immediate direction in one view.",
            "layout": "four_card_grid",
            "blocks": [
                f"Mobile Number: {mobile_number}",
                f"Mobile Vibration: {vibration}",
                f"Missing Grid Digits: {missing_text}",
                f"Compatibility: {compatibility}",
                f"Recommendation: {keep_change_verdict}",
                f"Primary Remedy: Mantra + {charging_direction} charging direction",
            ],
        },
        {
            "order": 12,
            "key": "basic_key_insight",
            "title": "12. Key Insight\nÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¯ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã†â€™ÃƒÂ Ã‚Â¤Ã‚Â·ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â¿ | Key Insight",
            "subtitle": "Single-line strategic interpretation for action focus.",
            "layout": "main_card_plus_strips",
            "blocks": [
                f"Key Insight: {key_insight}",
                "Action Lens: Stabilize routine first, optimize number second, scale execution third",
            ],
        },
        {
            "order": 13,
            "key": "basic_upgrade_path",
            "title": "13. Upgrade Path\nÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã¢â‚¬â€ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¡ ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¥ | Next Steps",
            "subtitle": "How to expand from mobile-only to full-stack numerology intelligence.",
            "layout": "split_analysis",
            "blocks": [
                "Standard Report: Basic + Name Numerology (Destiny, Soul Urge, Personality, correction strategy)",
                "Premium Report: Basic + Standard + Premium intelligence sections (career, finance, relationships, health, roadmap)",
            ],
        },
        {
            "order": 14,
            "key": "basic_footer",
            "title": "14. Footer\nÃƒÂ Ã‚Â¤Ã‚Â«ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â° | Report Footer",
            "subtitle": "Identity, plan, and generation stamp.",
            "layout": "closing_reflection",
            "blocks": [
                f"Report Type: Basic (Mobile Numerology)",
                f"Generated For: {full_name}",
                f"Date: {summary_generated_at}",
                f"Location Context: {city}",
            ],
        },
    ])


def _basic_reduce_number(value: int, *, preserve_master: bool = False) -> Tuple[List[int], int]:
    if value <= 0:
        return [0], 0
    steps = [value]
    current = value
    while current > 9:
        if preserve_master and current in {11, 22, 33}:
            break
        current = sum(int(char) for char in str(current))
        steps.append(current)
    return steps, current


def _basic_digits_from_date(raw_date: str) -> List[int]:
    return [int(ch) for ch in str(raw_date or "") if ch.isdigit()]


def _basic_normalize_willingness(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"yes", "y", "willing", "change", "ready"}:
        return "yes"
    if normalized in {"no", "n", "not now", "keep"}:
        return "no"
    return "undecided"


def _basic_life_path_from_dob(raw_dob: str) -> Dict[str, Any]:
    digits = _basic_digits_from_date(raw_dob)
    total = sum(digits)
    steps, result = _basic_reduce_number(total, preserve_master=True)
    anchor = result if result <= 9 else sum(int(ch) for ch in str(result))
    return {
        "digits": digits,
        "total": total,
        "steps": steps,
        "value": result,
        "anchor": anchor if 1 <= anchor <= 9 else 9,
    }


def _basic_mobile_vibration_from_number(mobile_number: str) -> Dict[str, Any]:
    digits = _digits_only(mobile_number)
    total = sum(digits)
    steps, result = _basic_reduce_number(total, preserve_master=False)
    return {"digits": digits, "total": total, "steps": steps, "value": result}


def _basic_digit_frequency(digits: List[int]) -> Dict[int, int]:
    counts = {digit: 0 for digit in range(10)}
    for digit in digits:
        counts[digit] = counts[digit] + 1
    return counts


def _basic_lo_shu_grid_marks(frequency: Dict[int, int]) -> Dict[int, str]:
    marks: Dict[int, str] = {}
    for number in (4, 9, 2, 3, 5, 7, 8, 1, 6):
        marks[number] = "Ã¢Å“â€œ" if frequency.get(number, 0) > 0 else "Ã¢Å“â€”"
    return marks


def _basic_missing_digits(frequency: Dict[int, int]) -> List[int]:
    return [digit for digit in range(1, 10) if frequency.get(digit, 0) == 0]


def _basic_repeating_digits(frequency: Dict[int, int]) -> List[Dict[str, int]]:
    repeating = [
        {"digit": digit, "count": frequency.get(digit, 0)}
        for digit in range(10)
        if frequency.get(digit, 0) > 1
    ]
    repeating.sort(key=lambda item: (-item["count"], item["digit"]))
    return repeating


def _basic_mobile_effects_lines(
    *,
    strengths: List[str],
    risks: List[str],
    missing_digits: List[int],
    repeating_digits: List[Dict[str, int]],
    primary_challenge: str,
    ai_narrative: str = "",
    uniqueness_seed: str = "",
) -> Tuple[List[str], List[str]]:
    positives = [str(item) for item in strengths if str(item).strip()]
    challenges = [str(item) for item in risks if str(item).strip()]

    context_line = _basic_mobile_effects_context_line(
        missing_digits=missing_digits,
        repeating_digits=repeating_digits,
        primary_challenge=primary_challenge,
    )

    if context_line:
        if len(challenges) >= 2:
            challenges = challenges[:2] + [context_line]
        else:
            challenges = challenges + [context_line]

    if ai_narrative:
        blended_positives: List[str] = []
        for idx, item in enumerate(positives):
            blended = _basic_blend_with_ai_variant(
                fallback_options=[item],
                ai_text=ai_narrative,
                uniqueness_seed=uniqueness_seed,
                slot=f"mobile_effects_positive:{idx}",
                max_chars=140,
            )
            blended_positives.append(blended or item)
        positives = blended_positives

        blended_challenges: List[str] = []
        for idx, item in enumerate(challenges):
            blended = _basic_blend_with_ai_variant(
                fallback_options=[item],
                ai_text=ai_narrative,
                uniqueness_seed=uniqueness_seed,
                slot=f"mobile_effects_challenge:{idx}",
                max_chars=140,
            )
            blended_challenges.append(blended or item)
        challenges = blended_challenges

    if not positives:
        positives = ["Balanced drive"]
    if not challenges:
        challenges = ["Overdrive without review"]

    while len(positives) < 3:
        positives.append(positives[-1])
    while len(challenges) < 3:
        challenges.append(challenges[-1])

    return positives[:3], challenges[:3]


def _basic_mobile_effects_context_line(
    *,
    missing_digits: List[int],
    repeating_digits: List[Dict[str, int]],
    primary_challenge: str,
) -> str:
    context_bits: List[str] = []
    if missing_digits:
        missing_focus = 4 if 4 in missing_digits else missing_digits[0]
        context_bits.append(
            f"Missing digit {missing_focus} can reduce structure and consistency; guard execution rhythm."
        )
    if repeating_digits:
        dominant = repeating_digits[0]
        digit = int(dominant.get("digit") or 0)
        count = int(dominant.get("count") or 0)
        if digit and count:
            context_bits.append(
                f"Repeating digit {digit} ({count}x) amplifies that energy; balance is required."
            )
    if primary_challenge:
        context_bits.append(
            f"Primary challenge '{primary_challenge}' is directly sensitive to this pattern."
        )
    return " ".join(context_bits[:2]).strip()


def _basic_enforce_lo_shu_consistency(*, frequency: Dict[int, int], lo_shu: Dict[str, Any]) -> Dict[str, Any]:
    corrected = dict(lo_shu or {})
    corrected["grid"] = _basic_lo_shu_grid_marks(frequency)
    corrected["missing"] = _basic_missing_digits(frequency)
    corrected["present"] = [digit for digit in range(1, 10) if frequency.get(digit, 0) > 0]
    corrected["present_with_zero"] = [digit for digit in range(10) if frequency.get(digit, 0) > 0]
    corrected["repeating"] = _basic_repeating_digits(frequency)
    return corrected


def _basic_compatibility_from_matrix(mobile_vibration: int, life_path_anchor: int) -> Dict[str, str]:
    matrix = BASIC_RULE_COMPATIBILITY_MATRIX.get(life_path_anchor) or BASIC_RULE_COMPATIBILITY_MATRIX[5]
    if mobile_vibration in matrix["compatible"]:
        return {"level": "HIGH", "color": "GREEN", "text": "à¤‰à¤šà¥à¤š", "english": "High"}
    if mobile_vibration in matrix["neutral"]:
        return {"level": "MODERATE", "color": "YELLOW", "text": "à¤®à¤§à¥à¤¯à¤®", "english": "Moderate"}
    return {"level": "LOW", "color": "RED", "text": "à¤¨à¤¿à¤®à¥à¤¨", "english": "Low"}


def _basic_verdict_from_rules(
    *,
    compatibility_level: str,
    missing_digits: List[int],
    repeating_digits: List[Dict[str, int]],
) -> str:
    missing_4 = 4 in set(missing_digits or [])
    missing_critical = len(missing_digits or []) >= 2
    if compatibility_level == "LOW" or (missing_4 and missing_critical):
        return "CHANGE"
    if missing_4 or compatibility_level == "MODERATE":
        return "MANAGE"
    return "KEEP"


def _basic_suggested_vibrations_for_life_path(life_path_anchor: int) -> List[int]:
    ideal_vibrations = {
        1: [1, 3, 5, 9],
        2: [2, 4, 6, 8],
        3: [3, 5, 7, 9],
        4: [4, 6, 8],
        5: [4, 6, 8],
        6: [6, 2, 4, 8],
        7: [7, 3, 5, 9],
        8: [8, 2, 4, 6],
        9: [9, 3, 5, 7],
    }
    return ideal_vibrations.get(life_path_anchor, [4, 6, 8])


def _basic_suggested_number_patterns(life_path_anchor: int, missing_digits: List[int]) -> Dict[str, Any]:
    suggested_vibrations = _basic_suggested_vibrations_for_life_path(life_path_anchor)
    primary_missing = 4 if 4 in missing_digits else (missing_digits[0] if missing_digits else 5)
    secondary_missing = (
        missing_digits[1]
        if len(missing_digits) > 1 and missing_digits[1] != primary_missing
        else (6 if primary_missing != 6 else 2)
    )
    balancing_digit = 8 if primary_missing != 8 and secondary_missing != 8 else 2

    preferred_vibrations = suggested_vibrations[:3]
    if 4 in missing_digits and 4 not in preferred_vibrations:
        preferred_vibrations = [4] + preferred_vibrations[:2]

    # India-focused constraint: suggested mobile patterns should start with 6/7/8/9 only.
    start_digit_by_vibration = {
        1: 9,
        2: 8,
        3: 9,
        4: 8,
        5: 9,
        6: 6,
        7: 7,
        8: 8,
        9: 9,
    }
    start_digits: List[int] = []
    for vib in preferred_vibrations:
        candidate = int(start_digit_by_vibration.get(int(vib), 9))
        if candidate not in {6, 7, 8, 9}:
            candidate = 9
        if candidate not in start_digits:
            start_digits.append(candidate)
        if len(start_digits) >= 3:
            break
    for fallback_start in (9, 8, 7, 6):
        if len(start_digits) >= 3:
            break
        if fallback_start not in start_digits:
            start_digits.append(fallback_start)

    # Pattern safety: avoid explicit repetition >2 and avoid triple streak templates.
    option_1 = f"[{start_digits[0]}] [X] [X] [{primary_missing}] [X] [{secondary_missing}] [X] [{balancing_digit}] [X] [4]"
    option_2 = f"[{start_digits[1]}] [X] [X] [4] [X] [X] [2] [X] [X] [6]"
    option_3 = f"[{start_digits[2]}] [X] [X] [6] [X] [X] [4] [X] [X] [8]"

    avoid_vibrations = [digit for digit in range(1, 10) if digit not in suggested_vibrations][:3]
    preferred_digits = sorted(set([primary_missing, secondary_missing, 4, 6, 8]))[:4]
    return {
        "preferred_vibrations": preferred_vibrations,
        "avoid_vibrations": avoid_vibrations,
        "preferred_digits": preferred_digits,
        "patterns": [option_1, option_2, option_3],
    }


def _basic_lookup_section_narrative(section_lookup: Dict[str, Dict[str, Any]], section_key: str) -> str:
    section = section_lookup.get(section_key) or {}
    if not isinstance(section, dict):
        return ""
    parts = [
        str(section.get("summary") or "").strip(),
        str(section.get("keyStrength") or "").strip(),
        str(section.get("keyRisk") or "").strip(),
        str(section.get("practicalGuidance") or "").strip(),
    ]
    text = " ".join(part for part in parts if part).strip()
    if text:
        sentences = re.split(r"(?<=[.!?।])\s+", text)
        sentences = [
            sentence
            for sentence in sentences
            if "N/A" not in sentence and "Not Provided" not in sentence
        ]
        text = " ".join(sentences).strip()
    return text[:320]


def _basic_lookup_any_section_narrative(
    section_lookup: Dict[str, Dict[str, Any]],
    section_keys: List[str],
) -> str:
    for key in section_keys:
        text = _basic_lookup_section_narrative(section_lookup, key)
        if text:
            return text
    return ""


def _stable_variant_index(*parts: Any, modulo: int) -> int:
    if modulo <= 1:
        return 0
    seed = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def _pick_variant(options: List[str], *seed_parts: Any) -> str:
    cleaned = [str(item or "").strip() for item in options if str(item or "").strip()]
    if not cleaned:
        return ""
    idx = _stable_variant_index(*seed_parts, modulo=len(cleaned))
    return cleaned[idx]


def _basic_sentence_variants_from_ai(ai_text: str, *, min_chars: int = 24, max_items: int = 5) -> List[str]:
    cleaned = str(_fix_mojibake_text(ai_text or "")).strip()
    if not cleaned:
        return []

    normalized = " ".join(cleaned.replace("\n", " ").split())
    chunks = re.split(r"[।!?]+|(?<!\d)\.(?!\d)", normalized)
    seen: set[str] = set()
    variants: List[str] = []
    for chunk in chunks:
        sentence = " ".join(chunk.split()).strip()
        if len(sentence) < min_chars:
            continue
        lowered = sentence.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        variants.append(sentence)
        if len(variants) >= max_items:
            break
    return variants


def _basic_blend_with_ai_variant(
    *,
    fallback_options: List[str],
    ai_text: str,
    uniqueness_seed: str,
    slot: str,
    max_chars: int = 320,
) -> str:
    candidates = [str(_fix_mojibake_text(item or "")).strip() for item in fallback_options if str(item or "").strip()]
    candidates.extend(_basic_sentence_variants_from_ai(ai_text))
    if not candidates:
        return ""
    line = _pick_variant(candidates, uniqueness_seed, slot, len(candidates))
    return str(line or "").strip()[:max_chars]


def _basic_bucket_from_problem_profile(problem_profile: Any) -> str:
    if not isinstance(problem_profile, dict):
        return ""
    category = str(problem_profile.get("category") or "").strip().lower()
    return {
        "career": "career",
        "business": "business",
        "confidence": "confidence",
        "finance": "finance",
        "consistency": "consistency",
    }.get(category, "")


def _basic_challenge_bucket(primary_challenge: str, *, problem_profile: Dict[str, Any] | None = None) -> str:
    profile_bucket = _basic_bucket_from_problem_profile(problem_profile)
    if profile_bucket:
        return profile_bucket

    text = str(primary_challenge or "").lower()
    if any(token in text for token in ("business", "startup", "revenue", "sales", "client")):
        return "business"
    if any(token in text for token in ("career", "job", "work", "execution", "promotion", "interview")):
        return "career"
    if any(token in text for token in ("confidence", "self", "visibility", "fear", "hesitation", "public speaking")):
        return "confidence"
    if any(token in text for token in ("money", "finance", "cash", "income", "debt", "loan", "emi", "credit")):
        return "finance"
    if any(token in text for token in ("consist", "focus", "discipline", "routine", "procrast", "habit", "Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤")):
        return "consistency"
    return "default"


def _basic_effective_problem_bucket(*, core: Dict[str, Any], challenge: str = "") -> str:
    inputs = core.get("inputs") or {}
    challenge_text = str(challenge or inputs.get("primary_challenge") or "")
    return _basic_challenge_bucket(
        challenge_text,
        problem_profile=core.get("problem_profile"),
    )


def _basic_problem_first_primary_actions(*, bucket: str, challenge: str) -> str:
    challenge_text = challenge or "your current challenge"
    if bucket == "finance":
        return "24-hour spending pause + weekly cashflow review + fixed debt-reduction checkpoint."
    if bucket == "business":
        return "Revenue priority list + client follow-up cadence + weekly pipeline review."
    if bucket == "career":
        return "Top-3 daily priorities + execution block scheduling + weekly outcome review."
    if bucket == "confidence":
        return "2-minute pre-call script + one daily visibility action + decision journal."
    if bucket == "consistency":
        return "Same-start-time routine + no-skip tracker + Sunday reset review."
    return f"One high-leverage action per day for '{challenge_text}' + weekly progress audit."


def _basic_problem_first_remedy_bundle(*, bucket: str, challenge: str) -> str:
    challenge_text = challenge or "your current challenge"
    if bucket == "finance":
        return f"Cash discipline bundle for '{challenge_text}': expense cap, debt checkpoint, weekly review."
    if bucket == "business":
        return f"Business growth bundle for '{challenge_text}': pipeline hygiene, conversion focus, weekly review cadence."
    if bucket == "career":
        return f"Career execution bundle for '{challenge_text}': priority stack, deep-work blocks, review cadence."
    if bucket == "confidence":
        return f"Confidence activation bundle for '{challenge_text}': prep script, visibility reps, reflection loop."
    if bucket == "consistency":
        return f"Consistency bundle for '{challenge_text}': stable routine, friction removal, daily scoreboard."
    return f"Problem-first bundle for '{challenge_text}': structured action, measurement, weekly correction."

REPORT_CORRUPTED_TEXT_RE = re.compile(r"(?:Ã|Â|â|ð|�)")


def _is_corrupted_report_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if REPORT_CORRUPTED_TEXT_RE.search(text):
        return True
    question_count = text.count("?")
    if question_count < 6:
        return False
    return (question_count / max(1, len(text))) >= 0.2


def _basic_safe_remedy_options(bucket: str) -> Dict[str, List[str]]:
    focus_map = {
        "career": "career execution and decision quality",
        "business": "business pipeline and conversion discipline",
        "finance": "cashflow discipline and debt reduction",
        "confidence": "confidence and visibility",
        "consistency": "daily consistency and follow-through",
    }
    focus = focus_map.get(bucket, "your current challenge")
    return {
        "spiritual": [
            f"Start the day with a 2-minute sankalp for {focus}, then commit one clear action.",
            f"Use one short mantra or breath cycle before deep work so attention stays on {focus}.",
            f"Close the day with 60-second gratitude and intent reset to reinforce {focus}.",
        ],
        "physical": [
            "Lock a fixed work start time and keep phone placement stable during execution hours.",
            "Use a 60-second pause before major decisions to reduce impulsive actions.",
            "Maintain one non-negotiable execution block daily to build compounding outcomes.",
        ],
        "digital": [
            "Run DND in two fixed windows and allow only priority contacts during focus time.",
            "Keep home screen minimal: only high-impact apps on the first page.",
            "End each day with a 5-minute digital reset and top-3 priorities for tomorrow.",
        ],
    }


def _basic_remedy_pack_lines(*, core: Dict[str, Any], uniqueness_seed: str) -> Dict[str, str]:
    inputs = core.get("inputs") or {}
    bucket = _basic_effective_problem_bucket(core=core, challenge=str(inputs.get("primary_challenge") or ""))
    pack = BASIC_REMEDY_LANGUAGE_PACKS.get(bucket) or BASIC_REMEDY_LANGUAGE_PACKS["default"]
    safe_pack = _basic_safe_remedy_options(bucket)

    spiritual = str(_fix_mojibake_text(_pick_variant(pack.get("spiritual") or [], uniqueness_seed, bucket, "spiritual")))
    physical = str(_fix_mojibake_text(_pick_variant(pack.get("physical") or [], uniqueness_seed, bucket, "physical")))
    digital = str(_fix_mojibake_text(_pick_variant(pack.get("digital") or [], uniqueness_seed, bucket, "digital")))

    if _is_corrupted_report_text(spiritual):
        spiritual = _pick_variant(safe_pack["spiritual"], uniqueness_seed, bucket, "safe_spiritual")
    if _is_corrupted_report_text(physical):
        physical = _pick_variant(safe_pack["physical"], uniqueness_seed, bucket, "safe_physical")
    if _is_corrupted_report_text(digital):
        digital = _pick_variant(safe_pack["digital"], uniqueness_seed, bucket, "safe_digital")

    return {
        "spiritual": _strip_report_emoji_text(str(spiritual or "").strip()),
        "physical": _strip_report_emoji_text(str(physical or "").strip()),
        "digital": _strip_report_emoji_text(str(digital or "").strip()),
    }


def _basic_area_message(
    *,
    area_key: str,
    score: int,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> str:
    challenge = str((core.get("inputs") or {}).get("primary_challenge") or "consistency")
    missing = ", ".join(str(d) for d in (core.get("lo_shu") or {}).get("missing") or []) or "à¤•à¥‹à¤ˆ à¤¨à¤¹à¥€à¤‚"
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    tone = "à¤‰à¤šà¥à¤š" if score <= 35 else ("à¤®à¤§à¥à¤¯à¤®" if score <= 70 else "à¤¨à¤¿à¤®à¥à¤¨")
    options = [
        f"{area_key} à¤ªà¤° à¤ªà¥à¤°à¤­à¤¾à¤µ {tone} à¤¹à¥ˆ; missing digits ({missing}) à¤‡à¤¸ à¤•à¥à¤·à¥‡à¤¤à¥à¤° à¤®à¥‡à¤‚ à¤…à¤¸à¤‚à¤¤à¥à¤²à¤¨ à¤¬à¤¢à¤¼à¤¾ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
        f"'{challenge}' à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤•à¥‡ à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤®à¥‡à¤‚ {area_key} à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ à¤›à¥‹à¤Ÿà¥‡ à¤¦à¥ˆà¤¨à¤¿à¤• à¤•à¤¦à¤® à¤”à¤° à¤¸à¤¾à¤ªà¥à¤¤à¤¾à¤¹à¤¿à¤• à¤¸à¤®à¥€à¤•à¥à¤·à¤¾ à¤œà¤°à¥‚à¤°à¥€ à¤¹à¥ˆà¥¤",
        f"{area_key} à¤®à¥‡à¤‚ à¤¸à¥à¤§à¤¾à¤° à¤•à¥€ à¤•à¥à¤‚à¤œà¥€: à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾, à¤¨à¤¿à¤¯à¤®à¤¿à¤¤ à¤Ÿà¥à¤°à¥ˆà¤•à¤¿à¤‚à¤— à¤”à¤° à¤µà¤¿à¤šà¤²à¤¨ à¤¨à¤¿à¤¯à¤‚à¤¤à¥à¤°à¤£à¥¤",
    ]
    if bucket == "career" and area_key in {"Career Execution", "Decision Quality"}:
        options.append("à¤•à¤°à¤¿à¤¯à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¬à¥‡à¤¹à¤¤à¤° à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ à¤¹à¤° à¤¬à¤¡à¤¼à¥‡ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ 60-à¤¸à¥‡à¤•à¤‚à¤¡ pause rule à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤")
    if bucket == "consistency" and area_key == "Consistency":
        options.append("à¤¹à¤° à¤¦à¤¿à¤¨ à¤à¤• à¤¹à¥€ à¤¸à¤®à¤¯ à¤ªà¤° à¤ªà¤¹à¤²à¤¾ à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ à¤•à¤¾à¤°à¥à¤¯ à¤¶à¥à¤°à¥‚ à¤•à¤°à¥‡à¤‚; à¤¯à¤¹à¥€ à¤†à¤ªà¤•à¥€ à¤¨à¤¿à¤°à¤‚à¤¤à¤°à¤¤à¤¾ à¤•à¤¾ à¤®à¥à¤–à¥à¤¯ à¤²à¥€à¤µà¤° à¤¹à¥ˆà¥¤")
    if bucket == "confidence" and area_key == "Confidence":
        options.append("à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤¬à¤¢à¤¼à¤¾à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ high-stakes à¤•à¥‰à¤² à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ 2 à¤®à¤¿à¤¨à¤Ÿ à¤•à¥€ à¤¤à¥ˆà¤¯à¤¾à¤°à¥€ à¤¸à¥à¤•à¥à¤°à¤¿à¤ªà¥à¤Ÿ à¤ªà¤¢à¤¼à¥‡à¤‚à¥¤")
    if bucket == "finance" and area_key == "Financial Discipline":
        options.append("à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤¨à¤¿à¤°à¥à¤£à¤¯à¥‹à¤‚ à¤®à¥‡à¤‚ 24-à¤˜à¤‚à¤Ÿà¥‡ à¤•à¤¾ à¤¨à¤¿à¤¯à¤® à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ impulsive à¤–à¤°à¥à¤š à¤”à¤° debt-pressure à¤•à¤® à¤¹à¥‹à¥¤")
    return _basic_blend_with_ai_variant(
        fallback_options=options,
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"area_message:{area_key}",
        max_chars=300,
    )


def _impact_severity_badge(score: int) -> str:
    issue_pressure = 100 - int(score)
    if issue_pressure >= 55:
        return "RED **Ã Â¤â€°Ã Â¤Å¡Ã Â¥ÂÃ Â¤Å¡**"
    if issue_pressure >= 30:
        return "YELLOW **Ã Â¤Â®Ã Â¤Â§Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â®**"
    return "GREEN **Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â¨**"


def _basic_life_area_rows(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> List[Dict[str, str]]:
    lo_shu = core.get("lo_shu") or {}
    missing = set(lo_shu.get("missing") or [])
    repeating = list(lo_shu.get("repeating") or [])
    repeat_map = {int(item.get("digit") or 0): int(item.get("count") or 0) for item in repeating}
    repeating_8_high = int(repeat_map.get(8, 0)) >= 3

    area_levels: List[Tuple[str, str, str]] = [
        ("**à¤¨à¤¿à¤°à¤‚à¤¤à¤°à¤¤à¤¾ (Consistency)**", "Consistency", "HIGH" if 4 in missing else "MODERATE"),
        ("**à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ (Confidence)**", "Confidence", "LOW" if 1 in missing else "MODERATE"),
        ("**à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ (Financial Discipline)**", "Financial Discipline", "HIGH" if 4 in missing else "MODERATE"),
        ("**à¤•à¤°à¤¿à¤¯à¤° à¤¨à¤¿à¤·à¥à¤ªà¤¾à¤¦à¤¨ (Career Execution)**", "Career Execution", "HIGH" if repeating_8_high else "MODERATE"),
        ("**à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤•à¥à¤·à¤®à¤¤à¤¾ (Decision Quality)**", "Decision Quality", "HIGH" if (4 in missing or repeating_8_high) else "MODERATE"),
        ("**à¤…à¤­à¤¿à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ (Self-Expression)**", "Self-Expression", "HIGH" if 3 in missing else "MODERATE"),
    ]
    impact_map = {"HIGH": "RED **à¤‰à¤šà¥à¤š**", "MODERATE": "YELLOW **à¤®à¤§à¥à¤¯à¤®**", "LOW": "GREEN **à¤¨à¤¿à¤®à¥à¤¨**"}
    score_map = {"HIGH": 28, "MODERATE": 56, "LOW": 82}

    rows: List[Dict[str, str]] = []
    for area_label, area_key, level in area_levels:
        score = score_map.get(level, 56)
        rows.append(
            {
                "area": area_label,
                "impact": impact_map.get(level, "YELLOW **à¤®à¤§à¥à¤¯à¤®**"),
                "meaning": _basic_area_message(
                    area_key=area_key,
                    score=score,
                    core=core,
                    uniqueness_seed=uniqueness_seed,
                    ai_narrative=ai_narrative,
                ),
            }
        )
    return rows


def _basic_verdict_box_text(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> str:
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    verdict_en = str(core.get("verdict") or "MANAGE")
    verdict_hi_map = {
        "KEEP": "à¤°à¤–à¥‡à¤‚",
        "MANAGE": "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚",
        "CHANGE": "à¤¬à¤¦à¤²à¥‡à¤‚",
    }
    verdict_hi = verdict_hi_map.get(verdict_en, "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚")
    mobile_vibration = int((core.get("mobile") or {}).get("vibration") or 0)
    energy_terms = list((core.get("planet") or {}).get("energy") or [])
    energy_pair = " Ã Â¤â€Ã Â¤Â° ".join(energy_terms[:2]) if len(energy_terms) >= 2 else (energy_terms[0] if energy_terms else "Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾")

    lo_shu = core.get("lo_shu") or {}
    missing = list(lo_shu.get("missing") or [])
    missing_text = ", ".join(str(item) for item in missing) if missing else "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    repeat_items = list(lo_shu.get("repeating") or [])
    repeat_map = {
        int(item.get("digit")): int(item.get("count"))
        for item in repeat_items
        if isinstance(item, dict) and item.get("digit") is not None and item.get("count") is not None
    }
    dominant_repeat_digit = max(repeat_map, key=lambda d: repeat_map[d]) if repeat_map else None
    dominant_repeat_count = int(repeat_map.get(dominant_repeat_digit, 0)) if dominant_repeat_digit is not None else 0
    repeat_8_count = int(repeat_map.get(8, 0))

    suggestions = core.get("suggestions") or {}
    preferred_vibrations = list(suggestions.get("preferred_vibrations") or [])
    preferred_digits = list(suggestions.get("preferred_digits") or [])
    pref_vibration_text = ", ".join(str(item) for item in preferred_vibrations[:3]) or "4, 6, 8"
    pref_digit_text = ", ".join(str(item) for item in preferred_digits[:4]) or "4"

    reason_1 = (
        f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {mobile_vibration} {energy_pair} Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ '{challenge}' Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Å“Ã Â¤Â¼Ã Â¤Â°Ã Â¥â€šÃ Â¤Â°Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
    )
    if repeat_8_count >= 2:
        reason_2 = (
            f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 8 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤Â§Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ ({repeat_8_count} Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â°) Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ Ã Â¤â€Ã Â¤Â° Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â®Ã Â¥â€¡Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¤Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Âµ-Ã Â¤â€ Ã Â¤Â§Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤"
        )
    elif dominant_repeat_digit is not None and dominant_repeat_count >= 2:
        reason_2 = (
            f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {dominant_repeat_digit} Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¨Ã Â¤Â°Ã Â¤Â¾Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ ({dominant_repeat_count} Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â°) Ã Â¤â€°Ã Â¤Â¸Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¤Ã Â¥â€¡Ã Â¤Å“ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤Â¨ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° challenge Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    else:
        reason_2 = "Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤ÂªÃ Â¥Ë†Ã Â¤Å¸Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¨ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Âµ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¤Ã Â¤Æ’ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯-Ã Â¤Â²Ã Â¤Â¯ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¤â€šÃ Â¤â€”Ã Â¥â€¡Ã Â¥Â¤"

    if 4 in missing:
        reason_3 = (
            f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 4 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° execution structure Ã Â¤â€¢Ã Â¤Â®Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¯Ã Â¤Â¹Ã Â¥â‚¬ '{challenge}' Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â°Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Å¸ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â£ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    else:
        reason_3 = (
            f"Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ ({missing_text}) Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¯Ã Â¥â€¹Ã Â¤â€š Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Å“Ã Â¤Â°Ã Â¥â€šÃ Â¤Â°Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë† Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¥Â¤"
        )

    reason_1 = _basic_blend_with_ai_variant(
        fallback_options=[reason_1],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot="verdict_reason_1",
        max_chars=220,
    )
    reason_2 = _basic_blend_with_ai_variant(
        fallback_options=[reason_2],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot="verdict_reason_2",
        max_chars=220,
    )
    reason_3 = _basic_blend_with_ai_variant(
        fallback_options=[reason_3],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot="verdict_reason_3",
        max_chars=220,
    )

    if verdict_en == "CHANGE":
        action_line = (
            f"Ã Â¤â€¡Ã Â¤Â¸ Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¤Ã Â¥â€¡Ã Â¤Å“Ã Â¤Â¼Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¹Ã Â¤Â² Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â {pref_vibration_text} vibration Ã Â¤â€Ã Â¤Â° {pref_digit_text} Ã Â¤Â¯Ã Â¥ÂÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â¤ Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤Â¸Ã Â¤Â¬Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¥â‚¬ Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¤â€”Ã Â¤Â¾Ã Â¥Â¤"
        )
    elif verdict_en == "MANAGE":
        action_line = (
            f"Ã Â¤â€¦Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° manage Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Å“Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ {pref_vibration_text} vibration Ã Â¤Âµ {pref_digit_text} digit-focus Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â²Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤Â¦Ã Â¥â‚¬Ã Â¤Â°Ã Â¥ÂÃ Â¤ËœÃ Â¤â€¢Ã Â¤Â¾Ã Â¤Â² Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¬Ã Â¥â€¡Ã Â¤Â¹Ã Â¤Â¤Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¤â€”Ã Â¤Â¾Ã Â¥Â¤"
        )
    else:
        action_line = (
            f"Ã Â¤ÂµÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¾ Ã Â¤Å“Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â«Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â­Ã Â¥â‚¬ {pref_digit_text} Ã Â¤Å“Ã Â¥Ë†Ã Â¤Â¸Ã Â¥â‚¬ grounding digits Ã Â¤â€¢Ã Â¥â€¹ remedies Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¸Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤"
        )
    action_line = _basic_blend_with_ai_variant(
        fallback_options=[
            action_line,
            "à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤•à¥€ à¤ªà¥à¤·à¥à¤Ÿà¤¿ à¤•à¥‡ à¤²à¤¿à¤ 21 à¤¦à¤¿à¤¨ à¤•à¤¾ disciplined trial à¤°à¤–à¥‡à¤‚ à¤”à¤° measurable progress à¤¨à¥‹à¤Ÿ à¤•à¤°à¥‡à¤‚à¥¤",
            "à¤…à¤—à¤²à¥‡ 21 à¤¦à¤¿à¤¨à¥‹à¤‚ à¤•à¥€ weekly à¤¸à¤®à¥€à¤•à¥à¤·à¤¾ à¤¸à¥‡ à¤¤à¤¯ à¤•à¤°à¥‡à¤‚ à¤•à¤¿ number-manage à¤ªà¤°à¥à¤¯à¤¾à¤ªà¥à¤¤ à¤¹à¥ˆ à¤¯à¤¾ change à¤œà¤°à¥‚à¤°à¥€à¥¤",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot="verdict_action",
        max_chars=300,
    )

    box_lines = [
        "Ã¢â€¢â€Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢â€”",
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜",
        f"Ã¢â€¢â€˜              Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯: {verdict_hi} ({verdict_en})              Ã¢â€¢â€˜",
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜",
        f"Ã¢â€¢â€˜    {reason_1}",
        f"Ã¢â€¢â€˜    {reason_2}",
        f"Ã¢â€¢â€˜    {reason_3}",
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜",
        f"Ã¢â€¢â€˜    {action_line}",
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜",
        "Ã¢â€¢Å¡Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â",
    ]
    return "\n".join(box_lines)


def _basic_suggested_numbers_payload(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> Dict[str, Any]:
    inputs = core.get("inputs") or {}
    life_path = int((core.get("life_path") or {}).get("value") or 5)
    lo_shu = core.get("lo_shu") or {}
    missing = list(lo_shu.get("missing") or [])
    missing_focus = 4 if 4 in missing else (missing[0] if missing else 5)
    challenge = str(inputs.get("primary_challenge") or "consistency")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    verdict = str(core.get("verdict") or "MANAGE").upper()

    intro_by_bucket = {
        "finance": (
            f"à¤¯à¤¦à¤¿ à¤†à¤ª à¤¨à¤‚à¤¬à¤° à¤¬à¤¦à¤²à¤¨à¤¾ à¤šà¤¾à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤¤à¥‹ à¤¯à¥‡ 3 à¤¨à¤‚à¤¬à¤° à¤†à¤ªà¤•à¥‡ à¤²à¤¿à¤ à¤¸à¤¬à¤¸à¥‡ à¤‰à¤ªà¤¯à¥à¤•à¥à¤¤ à¤¹à¥ˆà¤‚à¥¤ "
            f"à¤¯à¥‡ à¤†à¤ªà¤•à¥‡ à¤œà¥€à¤µà¤¨ à¤ªà¤¥ {life_path} à¤•à¥‡ à¤…à¤¨à¥à¤•à¥‚à¤² à¤¹à¥ˆà¤‚ à¤”à¤° à¤²à¥‹ à¤¶à¥‚ à¤—à¥à¤°à¤¿à¤¡ à¤•à¥€ à¤®à¥à¤–à¥à¤¯ à¤•à¤®à¥€â€”à¤…à¤‚à¤• {missing_focus}â€”à¤•à¥‹ à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ à¤šà¥à¤¨à¥‡ à¤—à¤ à¤¹à¥ˆà¤‚à¥¤ "
            "à¤¯à¥‡ à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤”à¤° à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤¬à¤¢à¤¼à¤¾à¤¨à¥‡ à¤®à¥‡à¤‚ à¤®à¤¦à¤¦ à¤•à¤°à¥‡à¤‚à¤—à¥‡à¥¤"
        ),
        "career": (
            f"à¤¯à¤¦à¤¿ à¤†à¤ª à¤¨à¤‚à¤¬à¤° à¤¬à¤¦à¤²à¤¨à¤¾ à¤šà¤¾à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤¤à¥‹ à¤¯à¥‡ 3 à¤µà¤¿à¤•à¤²à¥à¤ª à¤†à¤ªà¤•à¥‡ à¤œà¥€à¤µà¤¨ à¤ªà¤¥ {life_path} à¤”à¤° à¤†à¤ªà¤•à¥€ '{challenge}' à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾ à¤•à¥‡ à¤…à¤¨à¥à¤¸à¤¾à¤° à¤¤à¥ˆà¤¯à¤¾à¤° à¤•à¤¿à¤ à¤—à¤ à¤¹à¥ˆà¤‚à¥¤ "
            f"à¤‡à¤¨à¤•à¤¾ à¤«à¥‹à¤•à¤¸ à¤…à¤‚à¤• {missing_focus} à¤¸à¤¹à¤¿à¤¤ grounding digits à¤•à¥‹ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤•à¤°à¤¨à¤¾ à¤¹à¥ˆ, à¤¤à¤¾à¤•à¤¿ execution à¤”à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¸à¥à¤¥à¤¿à¤° à¤¹à¥‹à¤‚à¥¤"
        ),
        "confidence": (
            f"à¤¯à¤¦à¤¿ à¤†à¤ª à¤¨à¤‚à¤¬à¤° à¤¬à¤¦à¤²à¤¨à¤¾ à¤šà¤¾à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤¤à¥‹ à¤¯à¥‡ 3 à¤µà¤¿à¤•à¤²à¥à¤ª à¤†à¤ªà¤•à¥‡ à¤œà¥€à¤µà¤¨ à¤ªà¤¥ {life_path} à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¬à¥‡à¤¹à¤¤à¤° alignment à¤•à¥‡ à¤²à¤¿à¤ à¤šà¥à¤¨à¥‡ à¤—à¤ à¤¹à¥ˆà¤‚à¥¤ "
            f"à¤¯à¥‡ à¤…à¤‚à¤• {missing_focus} à¤œà¥ˆà¤¸à¥€ à¤•à¤®à¥€ à¤•à¥‹ à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ à¤•à¤°à¤•à¥‡ à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤”à¤° à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤¸à¥à¤§à¤¾à¤°à¤¨à¥‡ à¤®à¥‡à¤‚ à¤®à¤¦à¤¦ à¤•à¤°à¥‡à¤‚à¤—à¥‡à¥¤"
        ),
        "default": (
            f"à¤¯à¤¦à¤¿ à¤†à¤ª à¤¨à¤‚à¤¬à¤° à¤¬à¤¦à¤²à¤¨à¤¾ à¤šà¤¾à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤¤à¥‹ à¤¯à¥‡ 3 à¤µà¤¿à¤•à¤²à¥à¤ª à¤†à¤ªà¤•à¥‡ à¤œà¥€à¤µà¤¨ à¤ªà¤¥ {life_path} à¤•à¥‡ à¤…à¤¨à¥à¤•à¥‚à¤² à¤¹à¥ˆà¤‚ à¤”à¤° à¤²à¥‹ à¤¶à¥‚ à¤•à¥€ à¤•à¤®à¥€â€”à¤…à¤‚à¤• {missing_focus}â€”à¤•à¥‹ à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ à¤šà¥à¤¨à¥‡ à¤—à¤ à¤¹à¥ˆà¤‚à¥¤ "
            "à¤‡à¤¨à¤•à¤¾ à¤‰à¤¦à¥à¤¦à¥‡à¤¶à¥à¤¯ à¤¦à¥ˆà¤¨à¤¿à¤• à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤¬à¤¢à¤¼à¤¾à¤¨à¤¾ à¤¹à¥ˆà¥¤"
        ),
    }
    if verdict == "CHANGE":
        intro_seed = intro_by_bucket.get(bucket, intro_by_bucket["default"])
    elif verdict == "KEEP":
        intro_seed = (
            "अभी नंबर बदलने की जरूरत नहीं है। "
            "यदि भविष्य में बदलाव की आवश्यकता लगे, तो नीचे दिए पैटर्न सिर्फ संदर्भ के लिए रखें।"
        )
    else:
        intro_seed = (
            "अभी 21-दिवसीय सुधार और ट्रैकिंग चलाएँ। "
            "यदि स्थिरता नहीं आती, तब नंबर बदलने के विकल्पों पर जाएँ।"
        )
    intro_text = _basic_blend_with_ai_variant(
        fallback_options=[intro_seed],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"suggested_intro:{bucket}",
        max_chars=360,
    )

    title_1 = "à¤µà¤¿à¤•à¤²à¥à¤ª 1: à¤¸à¤°à¥à¤µà¤¶à¥à¤°à¥‡à¤·à¥à¤  â€“ à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤•à¥‡ à¤²à¤¿à¤ (Best for Financial Stability)" if bucket == "finance" else "à¤µà¤¿à¤•à¤²à¥à¤ª 1: à¤¸à¤°à¥à¤µà¤¶à¥à¤°à¥‡à¤·à¥à¤  â€“ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤•à¥‡ à¤²à¤¿à¤ (Best for Stability)"
    title_2 = "à¤µà¤¿à¤•à¤²à¥à¤ª 2: à¤•à¤°à¤¿à¤¯à¤° à¤”à¤° à¤†à¤¯ à¤µà¥ƒà¤¦à¥à¤§à¤¿ à¤•à¥‡ à¤²à¤¿à¤ (Career & Income Growth)"
    title_3 = "à¤µà¤¿à¤•à¤²à¥à¤ª 3: à¤¸à¤‚à¤¤à¥à¤²à¤¨ à¤”à¤° à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤•à¥‡ à¤²à¤¿à¤ (Balance & Stability)"
    titles = [title_1, title_2, title_3]

    suggested = list(core.get("suggested_numbers") or [])
    while len(suggested) < 3:
        fallback_pattern = (
            "[9] [X] [X] [4] [X] [X] [6] [X] [X] [8]"
            if len(suggested) == 0
            else ("[8] [X] [X] [4] [X] [X] [2] [X] [X] [6]" if len(suggested) == 1 else "[7] [X] [X] [6] [X] [X] [4] [X] [X] [8]")
        )
        suggested.append(
            {
                "pattern": fallback_pattern,
                "vibration": 4 if len(suggested) == 0 else (8 if len(suggested) == 1 else 6),
                "key_digits": [4, 6, 8],
            }
        )

    reason_bank = {
        0: f"à¤¯à¤¹ à¤µà¤¿à¤•à¤²à¥à¤ª à¤…à¤‚à¤• {missing_focus} à¤•à¥€ à¤•à¤®à¥€ à¤•à¥‹ à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾ à¤¸à¥‡ à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤ à¤‡à¤¸à¤¸à¥‡ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨, à¤¸à¤‚à¤°à¤šà¤¨à¤¾ à¤”à¤° à¤¨à¤¿à¤°à¤‚à¤¤à¤°à¤¤à¤¾ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆ, à¤œà¥‹ à¤†à¤ªà¤•à¥€ '{challenge}' à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤•à¥‡ à¤²à¤¿à¤ à¤¸à¥€à¤§à¥‡ à¤‰à¤ªà¤¯à¥‹à¤—à¥€ à¤¹à¥ˆà¥¤",
        1: f"à¤¯à¤¹ à¤µà¤¿à¤•à¤²à¥à¤ª growth à¤”à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤®-à¤‰à¤¨à¥à¤®à¥à¤– à¤Šà¤°à¥à¤œà¤¾ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤ à¤…à¤‚à¤• {missing_focus} à¤œà¥ˆà¤¸à¥€ grounding digits execution à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤°à¤–à¤¤à¥€ à¤¹à¥ˆà¤‚ à¤”à¤° à¤•à¤°à¤¿à¤¯à¤°/à¤†à¤¯ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤¬à¤¢à¤¼à¤¾à¤¨à¥‡ à¤®à¥‡à¤‚ à¤®à¤¦à¤¦ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
        2: f"à¤¯à¤¹ à¤µà¤¿à¤•à¤²à¥à¤ª à¤¸à¤‚à¤¤à¥à¤²à¤¨ à¤”à¤° à¤œà¤¿à¤®à¥à¤®à¥‡à¤¦à¤¾à¤°à¥€ à¤¬à¤¢à¤¼à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤ à¤‡à¤¸à¤¸à¥‡ à¤¨à¤¿à¤°à¥à¤£à¤¯à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤†à¤¤à¥€ à¤¹à¥ˆ à¤”à¤° à¤†à¤ªà¤•à¥€ '{challenge}' à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤®à¥‡à¤‚ à¤‰à¤¤à¤¾à¤°-à¤šà¤¢à¤¼à¤¾à¤µ à¤•à¤® à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    }

    options: List[Dict[str, str]] = []
    for idx in range(3):
        item = suggested[idx]
        key_digits = item.get("key_digits") or []
        key_digits_text = ", ".join(str(d) for d in key_digits[:4]) or str(missing_focus)
        reason_text = _basic_blend_with_ai_variant(
            fallback_options=[
                reason_bank[idx],
                f"à¤‡à¤¸ à¤µà¤¿à¤•à¤²à¥à¤ª à¤•à¤¾ à¤«à¥‹à¤•à¤¸ '{challenge}' à¤•à¥‹ practical execution à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¤¾ à¤¹à¥ˆà¥¤",
            ],
            ai_text=ai_narrative,
            uniqueness_seed=uniqueness_seed,
            slot=f"suggested_reason:{idx}",
            max_chars=280,
        )
        options.append(
            {
                "title": titles[idx],
                "pattern": str(item.get("pattern") or ""),
                "vibration": str(item.get("vibration") or ""),
                "key_digits": key_digits_text,
                "fills": f"à¤…à¤‚à¤• {missing_focus}",
                "reason": reason_text,
            }
        )

    if verdict == "CHANGE":
        steps = [
            "Contact your telecom provider (Jio/Airtel/Vi/BSNL).",
            "Ask if a number matching the suggested pattern is available.",
            "If option 1 is unavailable, try option 2 or option 3.",
            "Activate the new SIM once the number is confirmed.",
            "Keep old and new numbers in dual-SIM mode for 30 days (important calls).",
        ]
    else:
        steps = [
            "No number change is required right now.",
            "Run the 21-day correction plan and review outcomes.",
            "If change is still needed, check availability for the suggested patterns.",
            "Activate the new SIM only after confirmation.",
            "Keep old and new numbers in dual-SIM mode for 30 days if you switch.",
        ]

    return {
        "intro": intro_text,
        "options": options,
        "steps": steps,
    }


def _basic_charging_payload(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str = "",
    ai_narrative: str = "",
) -> Dict[str, str]:
    inputs = core.get("inputs") or {}
    charging = core.get("charging") or {}
    bucket = _basic_effective_problem_bucket(core=core, challenge=str(inputs.get("primary_challenge") or "consistency"))
    verdict = str(core.get("verdict") or "MANAGE").upper()
    direction = str(charging.get("direction") or "à¤ªà¥‚à¤°à¥à¤µ (East)")
    day_hi = str(charging.get("day") or "à¤®à¤‚à¤—à¤²à¤µà¤¾à¤°")
    time_text = str(charging.get("time") or "à¤¸à¥‚à¤°à¥à¤¯à¥‹à¤¦à¤¯")
    method = str(charging.get("method") or "à¤«à¥‹à¤¨ à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ à¤°à¤–à¥‡à¤‚")

    day_en_map = {
        "à¤°à¤µà¤¿à¤µà¤¾à¤°": "Sunday",
        "à¤¸à¥‹à¤®à¤µà¤¾à¤°": "Monday",
        "à¤®à¤‚à¤—à¤²à¤µà¤¾à¤°": "Tuesday",
        "à¤¬à¥à¤§à¤µà¤¾à¤°": "Wednesday",
        "à¤—à¥à¤°à¥à¤µà¤¾à¤°": "Thursday",
        "à¤¶à¥à¤•à¥à¤°à¤µà¤¾à¤°": "Friday",
        "à¤¶à¤¨à¤¿à¤µà¤¾à¤°": "Saturday",
    }
    day_en = day_en_map.get(day_hi, "")
    if day_en:
        best_time = f"{day_hi} ({day_en}) à¤•à¥‹ {time_text} à¤•à¥‡ à¤¸à¤®à¤¯"
    else:
        best_time = f"{day_hi} à¤•à¥‹ {time_text} à¤•à¥‡ à¤¸à¤®à¤¯"

    sankalp_by_bucket = {
        "finance": "à¤®à¥ˆà¤‚ à¤…à¤ªà¤¨à¥€ à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤Šà¤°à¥à¤œà¤¾ à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤”à¤° à¤•à¥‡à¤‚à¤¦à¥à¤°à¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥‚à¤à¥¤ à¤®à¥ˆà¤‚ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤¸à¥‡ à¤•à¤°à¥à¤œ à¤šà¥à¤•à¤¾à¤Šà¤‚à¤—à¤¾à¥¤",
        "career": "à¤®à¥ˆà¤‚ à¤…à¤ªà¤¨à¥€ à¤•à¤°à¤¿à¤¯à¤° à¤Šà¤°à¥à¤œà¤¾ à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤”à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤®-à¤•à¥‡à¤‚à¤¦à¥à¤°à¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥‚à¤à¥¤",
        "confidence": "à¤®à¥ˆà¤‚ à¤…à¤ªà¤¨à¥€ à¤…à¤­à¤¿à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤”à¤° à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤•à¥‹ à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥‚à¤à¥¤",
        "consistency": "à¤®à¥ˆà¤‚ à¤…à¤ªà¤¨à¥€ à¤Šà¤°à¥à¤œà¤¾ à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤”à¤° à¤•à¥‡à¤‚à¤¦à¥à¤°à¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥‚à¤à¥¤ à¤®à¥ˆà¤‚ à¤¨à¤¿à¤°à¤‚à¤¤à¤°à¤¤à¤¾ à¤•à¥‡ à¤¸à¤¾à¤¥ à¤•à¤¾à¤°à¥à¤¯ à¤ªà¥‚à¤°à¤¾ à¤•à¤°à¥‚à¤à¤—à¤¾à¥¤",
        "default": "à¤®à¥ˆà¤‚ à¤…à¤ªà¤¨à¥€ à¤Šà¤°à¥à¤œà¤¾ à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤”à¤° à¤•à¥‡à¤‚à¤¦à¥à¤°à¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥‚à¤à¥¤",
    }
    sankalp = sankalp_by_bucket.get(bucket, sankalp_by_bucket["default"])

    uniqueness_seed = str(uniqueness_seed or core.get("uniqueness_seed") or "basic-charging-seed")
    how_text_base = (
        f"à¤«à¥‹à¤¨ à¤•à¥‹ {direction} à¤•à¥€ à¤“à¤° à¤°à¤–à¥‡à¤‚, {method}, 10-15 à¤®à¤¿à¤¨à¤Ÿ à¤¸à¥‚à¤°à¥à¤¯ à¤•à¥€ à¤°à¥‹à¤¶à¤¨à¥€ à¤®à¥‡à¤‚à¥¤ "
        f"à¤®à¤¾à¤¨à¤¸à¤¿à¤• à¤°à¥‚à¤ª à¤¸à¥‡ à¤¸à¤‚à¤•à¤²à¥à¤ª à¤²à¥‡à¤‚: \"{sankalp}\""
    )
    how_text = _basic_blend_with_ai_variant(
        fallback_options=[
            how_text_base,
            f"Charging ritual: {day_hi} à¤•à¥‹ {time_text} à¤•à¥‡ à¤†à¤¸à¤ªà¤¾à¤¸ 10-15 à¤®à¤¿à¤¨à¤Ÿ directional alignment à¤°à¤–à¥‡à¤‚ à¤”à¤° à¤¸à¤‚à¤•à¤²à¥à¤ª à¤¦à¥‹à¤¹à¤°à¤¾à¤à¤à¥¤",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"charging_how:{bucket}",
        max_chars=320,
    )

    if verdict == "CHANGE":
        intro_seed = "यदि अभी नंबर नहीं बदल सकते, तो सही दिशा में चार्ज करके ऊर्जा-अलाइनमेंट सुधारें।"
    elif verdict == "KEEP":
        intro_seed = "नंबर सही है; रोज़ाना चार्जिंग-अलाइनमेंट से ऊर्जा स्थिर रखें।"
    else:
        intro_seed = "अभी नंबर संभालें और चार्जिंग-अलाइनमेंट से स्थिरता बढ़ाएँ।"
    intro = _basic_blend_with_ai_variant(
        fallback_options=[intro_seed],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"charging_intro:{bucket}",
        max_chars=240,
    )
    return {
        "intro": intro,
        "direction_label": "à¤¦à¤¿à¤¶à¤¾ (Direction)",
        "direction_value": f"{direction} à¤•à¥€ à¤“à¤° à¤°à¤–à¥‡à¤‚",
        "time_label": "à¤¸à¤°à¥à¤µà¥‹à¤¤à¥à¤¤à¤® à¤¸à¤®à¤¯ (Best Time)",
        "time_value": best_time,
        "how_label": "à¤•à¥ˆà¤¸à¥‡ à¤•à¤°à¥‡à¤‚ (How)",
        "how_value": how_text,
    }


def _basic_remedies_payload(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    remedy_lines: Dict[str, str] | None = None,
    ai_narrative: str = "",
) -> Dict[str, Any]:
    inputs = core.get("inputs") or {}
    first_name = str(inputs.get("first_name") or "User")
    challenge = str(inputs.get("primary_challenge") or "consistency")
    lo_shu = core.get("lo_shu") or {}
    missing = list(lo_shu.get("missing") or [])
    missing_focus = 4 if 4 in missing else (missing[0] if missing else 5)

    mantra = str(_fix_mojibake_text(core.get("mantra") or "Om Mangalaya Namah"))
    gemstone_name = str((core.get("gemstone") or {}).get("name") or "Red Coral")
    cover_color = str(core.get("cover_color") or "Deep Red")
    wallpaper = str(core.get("wallpaper_theme") or "Sunrise")
    yantra = str(core.get("yantra") or "Navgrah Yantra")
    primary_rudraksha = str(core.get("primary_rudraksha") or _basic_primary_rudraksha(missing))
    dnd_morning = str(core.get("dnd_morning") or "7:00-8:30 AM")
    dnd_evening = str(core.get("dnd_evening") or "7:00-9:00 PM")
    app_folder_limit = int(core.get("app_folder_limit") or 4)
    contact_prefix = str(core.get("contact_prefix_digit") or missing_focus)
    nickname_base = str(core.get("nickname_base") or f"{first_name} Focus {missing_focus}")

    challenge_bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    primary_actions = _basic_problem_first_primary_actions(bucket=challenge_bucket, challenge=challenge)
    remedy_bundle = _basic_problem_first_remedy_bundle(bucket=challenge_bucket, challenge=challenge)

    intro = _basic_blend_with_ai_variant(
        fallback_options=[
            f"If number change is not immediate, run a 21-day problem-first correction plan for '{challenge}'.",
            f"Your remedies are aligned to '{challenge}', not generic debt-only advice. Focus bundle: {remedy_bundle}",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"remedy_intro:{challenge_bucket}",
        max_chars=280,
    )

    spiritual_rows = [
        {
            "remedy": "Focus Protocol",
            "action": primary_actions,
            "frequency": "Daily",
        },
        {
            "remedy": "Core Bundle",
            "action": remedy_bundle,
            "frequency": "21 days",
        },
        {
            "remedy": "Mantra",
            "action": f"Repeat '{mantra}' with steady breathing before key actions",
            "frequency": "Morning + Evening",
        },
        {
            "remedy": "Support Item",
            "action": f"{primary_rudraksha} with {gemstone_name}",
            "frequency": "Daily",
        },
        {
            "remedy": "Energy Anchor",
            "action": f"Keep {yantra} near work/decision zone",
            "frequency": "Permanent",
        },
    ]

    digital_rows = [
        {
            "remedy": "Mobile Cover",
            "action": f"{cover_color}",
            "why": "Daily visual cue improves execution consistency.",
        },
        {
            "remedy": "Wallpaper",
            "action": wallpaper,
            "why": "Keeps challenge-priority visible during the day.",
        },
        {
            "remedy": "Saved Name",
            "action": nickname_base,
            "why": "Identity prompt reinforces discipline intent.",
        },
        {
            "remedy": "Contact Prefix",
            "action": f"Use '{contact_prefix} -' for top 5-7 contacts",
            "why": "Creates structure and intentional communication.",
        },
        {
            "remedy": "DND Windows",
            "action": f"{dnd_morning} and {dnd_evening}",
            "why": "Protects focus blocks for key outcomes.",
        },
    ]

    setup_rows = [
        {"item": "Problem Bucket", "recommendation": challenge_bucket},
        {"item": "Primary Actions", "recommendation": primary_actions},
        {"item": "Remedy Bundle", "recommendation": remedy_bundle},
        {"item": "Cover", "recommendation": cover_color},
        {"item": "Wallpaper", "recommendation": wallpaper},
        {"item": "Saved Name", "recommendation": nickname_base},
        {"item": "DND", "recommendation": f"{dnd_morning} + {dnd_evening}"},
        {"item": "App Folders", "recommendation": f"Max {app_folder_limit} apps per folder"},
    ]

    reset_rows = [
        {
            "week": "सप्ताह 1 (दिन 1-7)",
            "actions": f"Install anchors: cover + wallpaper + saved name + mantra start for '{challenge}'.",
        },
        {
            "week": "सप्ताह 2 (दिन 8-14)",
            "actions": "Run strict focus blocks, DND windows, and contact-prefix discipline.",
        },
        {
            "week": "सप्ताह 3 (दिन 15-21)",
            "actions": f"Review outcomes, remove friction, lock weekly cadence for {challenge_bucket}.",
        },
    ]

    checklist = [
        "Did I execute the top action today?",
        "Were focus windows protected?",
        "Did I avoid impulsive reversals?",
        "Did I track one measurable result?",
        "Did I complete mantra/anchor routine?",
        "Did I run the same process without skip?",
    ]

    context_line = ""
    if remedy_lines:
        context_line = (
            f"Ref pack -> spiritual: {remedy_lines.get('spiritual', '')}; "
            f"physical: {remedy_lines.get('physical', '')}; "
            f"digital: {remedy_lines.get('digital', '')}"
        ).strip()
    comment = _basic_blend_with_ai_variant(
        fallback_options=[
            f"{context_line} | Keep this protocol specific to '{challenge}'.",
            f"{context_line} | Do not drift into unrelated remedies; track challenge outcomes weekly.",
            f"{context_line} | Keep it crisp: one challenge, one protocol, one review cadence.",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"remedy_comment:{challenge_bucket}",
        max_chars=320,
    )

    return {
        "intro": intro,
        "spiritual_title": "Spiritual & Physical Remedies",
        "spiritual_rows": spiritual_rows,
        "digital_title": "Digital & Visual Remedies",
        "digital_rows": digital_rows,
        "setup_title": "Personalized Digital Setup",
        "setup_rows": setup_rows,
        "reset_title": "21-Day Correction Plan",
        "reset_rows": reset_rows,
        "check_title": "Daily Checklist",
        "checklist": checklist,
        "comment": comment,
    }


def _basic_tracker_payload(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str = "",
    ai_narrative: str = "",
) -> Dict[str, Any]:
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    challenge_bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    charging = core.get("charging") or {}
    direction = str(charging.get("direction") or "East")
    day = str(charging.get("day") or "Tuesday")
    mantra = str(_fix_mojibake_text(core.get("mantra") or "Om Mangalaya Namah"))
    primary_actions = _basic_problem_first_primary_actions(bucket=challenge_bucket, challenge=challenge)
    reset_bundle = _basic_problem_first_remedy_bundle(bucket=challenge_bucket, challenge=challenge)
    seed = str(uniqueness_seed or core.get("uniqueness_seed") or "basic-tracker-seed")

    week1_task = _basic_blend_with_ai_variant(
        fallback_options=[
            f"Start protocol: mantra + direction ritual ({direction}, {day}) + first action block for '{challenge}'.",
            f"Install day-1 system for '{challenge}': mantra, anchor setup, and execution trigger.",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=seed,
        slot=f"tracker_w1:{challenge_bucket}",
        max_chars=220,
    )
    week2_task = _basic_blend_with_ai_variant(
        fallback_options=[
            f"Operate primary actions daily: {primary_actions}",
            "Protect DND/focus windows and run no-skip execution logs.",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=seed,
        slot=f"tracker_w2:{challenge_bucket}",
        max_chars=220,
    )
    week3_task = _basic_blend_with_ai_variant(
        fallback_options=[
            f"Weekly review | compare outcomes | lock next-cycle plan for {challenge_bucket}",
            f"Stabilize routine | remove friction | continue 21-day bundle: {reset_bundle}",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=seed,
        slot=f"tracker_w3:{challenge_bucket}",
        max_chars=220,
    )
    if "|" not in week3_task:
        week3_task = f"{week3_task} | weekly review | next-cycle lock"

    rows = [
        {"week": "सप्ताह 1 (दिन 1-7)", "task": week1_task, "status": "[ ]"},
        {"week": "सप्ताह 2 (दिन 8-14)", "task": week2_task, "status": "[ ]"},
        {"week": "सप्ताह 3 (दिन 15-21)", "task": week3_task, "status": "[ ]"},
    ]
    return {"rows": rows}


def _basic_summary_payload(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> Dict[str, Any]:
    suggestions = core.get("suggestions") or {}
    lo_shu = core.get("lo_shu") or {}
    life_path = core.get("life_path") or {}
    compatibility = core.get("compatibility") or {}
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    challenge_bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    # Summary rows are structured and should remain deterministic; avoid long cross-slot AI spillover.
    summary_ai = ""

    preferred_vibrations = list(suggestions.get("preferred_vibrations") or [])
    preferred_text = ", ".join(str(v) for v in preferred_vibrations[:2])
    preferred_tail = str(preferred_vibrations[2]) if len(preferred_vibrations) >= 3 else ""
    if preferred_text and preferred_tail:
        preferred_base = f"{preferred_text}, or {preferred_tail}"
    elif preferred_text:
        preferred_base = preferred_text
    else:
        preferred_base = "Use supportive vibration"
    preferred_suggestion = _basic_blend_with_ai_variant(
        fallback_options=[
            f"Pick from: {preferred_base}",
            f"Choose a number aligned to '{challenge}' goals.",
        ],
        ai_text=summary_ai,
        uniqueness_seed=uniqueness_seed,
        slot="summary_pref_vibration",
        max_chars=140,
    )

    missing_digits = list(lo_shu.get("missing") or [])
    missing_text = ", ".join(str(d) for d in missing_digits) or "None"
    if 4 in missing_digits:
        missing_base = "Ensure digit 4 appears in corrected setup."
    elif missing_digits:
        missing_base = f"Ensure digit {missing_digits[0]} appears in corrected setup."
    else:
        missing_base = "No major missing digit pressure."
    missing_suggestion = _basic_blend_with_ai_variant(
        fallback_options=[
            missing_base,
            f"Map missing-digit correction directly to '{challenge}' outcomes.",
        ],
        ai_text=summary_ai,
        uniqueness_seed=uniqueness_seed,
        slot="summary_missing_digit",
        max_chars=160,
    )

    count_words = {2: "two times", 3: "three times", 4: "four times", 5: "five times"}
    repeating = list(lo_shu.get("repeating") or [])
    if repeating:
        rep_items: List[str] = []
        for item in repeating:
            digit = int(item.get("digit") or 0)
            count = int(item.get("count") or 0)
            rep_items.append(f"{digit} ({count_words.get(count, f'{count} times')})")
        repeating_text = ", ".join(rep_items)
        if any(int(item.get("digit") or 0) == 8 and int(item.get("count") or 0) >= 2 for item in repeating):
            repeating_base = "Reduce over-pressure from repeated 8 patterns."
        else:
            repeating_base = "Balance repeated-digit patterns in next cycle."
    else:
        repeating_text = "None"
        repeating_base = "No major repeating-digit distortion."
    repeating_suggestion = _basic_blend_with_ai_variant(
        fallback_options=[
            repeating_base,
            f"Keep repeated-digit handling tied to '{challenge}' priorities.",
        ],
        ai_text=summary_ai,
        uniqueness_seed=uniqueness_seed,
        slot="summary_repeating_digit",
        max_chars=160,
    )

    level = str(compatibility.get("level") or "MODERATE").upper()
    compatibility_text = (
        f"{compatibility.get('english', 'Moderate')} / {compatibility.get('text', 'Moderate')}"
    )
    if level == "HIGH":
        compatibility_base = "Current setup can work with discipline."
    elif level == "LOW":
        compatibility_base = "Change path may improve alignment."
    else:
        compatibility_base = "Manage path first, then reassess."
    compatibility_suggestion = _basic_blend_with_ai_variant(
        fallback_options=[
            compatibility_base,
            f"Prioritize compatibility decisions by '{challenge}' impact.",
        ],
        ai_text=summary_ai,
        uniqueness_seed=uniqueness_seed,
        slot="summary_compatibility",
        max_chars=150,
    )

    verdict_raw = str(core.get("verdict") or "MANAGE")
    verdict_upper = verdict_raw.upper()
    if "KEEP" in verdict_upper:
        verdict_text = "KEEP"
    elif "CHANGE" in verdict_upper:
        verdict_text = "CHANGE"
    else:
        verdict_text = "MANAGE"
    verdict_suggestion = _basic_blend_with_ai_variant(
        fallback_options=[
            "Use measurable weekly review before final decision.",
            "Apply a strict correction routine, then reassess with real outcomes.",
            "Take decision only after stable behavior is maintained for two review cycles.",
        ],
        ai_text=summary_ai,
        uniqueness_seed=uniqueness_seed,
        slot="summary_verdict_suggestion",
        max_chars=150,
    )

    remedy_text = _basic_problem_first_remedy_bundle(bucket=challenge_bucket, challenge=challenge)
    remedy_suggestion = _basic_blend_with_ai_variant(
        fallback_options=[
            "Apply for 21 days with zero skip.",
            _basic_problem_first_primary_actions(bucket=challenge_bucket, challenge=challenge),
            f"Track weekly progress strictly for '{challenge}'.",
        ],
        ai_text=summary_ai,
        uniqueness_seed=uniqueness_seed,
        slot="summary_primary_remedy",
        max_chars=190,
    )

    rows = [
        {
            "field": "Mobile Vibration",
            "status": str((core.get("mobile") or {}).get("vibration") or "—"),
            "suggestion": preferred_suggestion,
        },
        {
            "field": "Missing Digits",
            "status": missing_text,
            "suggestion": missing_suggestion,
        },
        {
            "field": "Repeating Digits",
            "status": repeating_text,
            "suggestion": repeating_suggestion,
        },
        {
            "field": "Life Path",
            "status": str(life_path.get("value") or "—"),
            "suggestion": "Use as strategic anchor.",
        },
        {
            "field": "Compatibility",
            "status": compatibility_text,
            "suggestion": compatibility_suggestion,
        },
        {
            "field": "Recommendation",
            "status": verdict_text,
            "suggestion": verdict_suggestion,
        },
        {
            "field": "Primary Remedy",
            "status": remedy_text,
            "suggestion": remedy_suggestion,
        },
    ]
    return {"rows": rows}


def _basic_key_insight_payload(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> Dict[str, str]:
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    lo_shu = core.get("lo_shu") or {}
    missing = set(lo_shu.get("missing") or [])
    present = set(lo_shu.get("present") or [])
    repeating = list(lo_shu.get("repeating") or [])
    repeat_map = {int(item.get("digit") or 0): int(item.get("count") or 0) for item in repeating}
    repeat8 = int(repeat_map.get(8, 0))

    if repeat8 >= 2 and bucket == "finance":
        p1_open = "Your current number pattern shows high pressure around money decisions."
    elif repeat8 >= 2:
        p1_open = "Your current number pattern shows high pressure under performance stress."
    else:
        p1_open = f"Mobile vibration {str((core.get('mobile') or {}).get('vibration') or '—')} can work, but structure is critical."

    if 4 in missing:
        p1_mid = "Missing digit 4 indicates weak system discipline; effort may not convert into stable outcomes."
    else:
        p1_mid = "Structure exists, but consistency under pressure still needs reinforcement."

    if 1 in present:
        p1_end = "Leadership energy is available, so execution upgrades can improve results quickly."
    else:
        p1_end = "Initiation energy needs support through small daily commitment loops."

    p1 = _basic_blend_with_ai_variant(
        fallback_options=[
            f"{p1_open} {p1_mid} {p1_end}",
            f"Core insight for '{challenge}': {p1_mid} {p1_end}",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"key_insight_p1:{bucket}",
        max_chars=360,
    )

    verdict = str(core.get("verdict") or "MANAGE")
    verdict_upper = verdict.upper()
    is_change = "CHANGE" in verdict_upper
    is_manage = "MANAGE" in verdict_upper
    problem_bundle = _basic_problem_first_remedy_bundle(bucket=bucket, challenge=challenge)
    problem_actions = _basic_problem_first_primary_actions(bucket=bucket, challenge=challenge)

    if is_change and 4 in missing:
        p2_base = (
            f"Current pattern suggests correction is needed for '{challenge}'. "
            f"If immediate number change is not possible, run this bundle for 21 days: {problem_bundle}"
        )
    elif is_manage:
        p2_base = (
            f"Keep the current number for now, but run a strict 21-day correction cycle for '{challenge}'. "
            f"Primary actions: {problem_actions}"
        )
    else:
        p2_base = (
            f"Current setup can still perform for '{challenge}' when discipline is stable. "
            f"Use this reinforcement bundle: {problem_bundle}"
        )
    p2 = _basic_blend_with_ai_variant(
        fallback_options=[p2_base],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"key_insight_p2:{bucket}",
        max_chars=360,
    )
    return {"p1": p1, "p2": p2}

def _basic_next_steps_payload(*, core: Dict[str, Any], uniqueness_seed: str = "", ai_narrative: str = "") -> Dict[str, Any]:
    inputs = core.get("inputs") or {}
    uniqueness_seed = str(uniqueness_seed or core.get("uniqueness_seed") or "basic-next-steps-seed")
    first_name = str(inputs.get("first_name") or "User")
    full_name = str(inputs.get("full_name") or "Not Provided")
    challenge = str(inputs.get("primary_challenge") or "consistency")
    city = str(inputs.get("city") or "Not Provided")
    challenge_bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    willingness = str(inputs.get("willingness_to_change") or "undecided").lower()
    life_path_value = str((core.get("life_path") or {}).get("value") or "â€”")
    mobile_vibration = str((core.get("mobile") or {}).get("vibration") or "â€”")
    missing_digits = ", ".join(str(d) for d in (core.get("lo_shu") or {}).get("missing") or []) or "à¤•à¥‹à¤ˆ à¤¨à¤¹à¥€à¤‚"
    verdict = str(core.get("verdict") or "MANAGE")

    if willingness == "yes":
        readiness_line = "à¤†à¤ª à¤ªà¤°à¤¿à¤µà¤°à¥à¤¤à¤¨ à¤•à¥‡ à¤²à¤¿à¤ à¤¤à¥ˆà¤¯à¤¾à¤° à¤¹à¥ˆà¤‚, à¤‡à¤¸à¤²à¤¿à¤ change-path à¤•à¥‹ à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾ à¤¦à¥‡à¤¨à¤¾ à¤†à¤ªà¤•à¥‡ à¤²à¤¿à¤ à¤²à¤¾à¤­à¤•à¤¾à¤°à¥€ à¤°à¤¹à¥‡à¤—à¤¾à¥¤"
    elif willingness == "no":
        readiness_line = "à¤†à¤ª à¤«à¤¿à¤²à¤¹à¤¾à¤² à¤¨à¤‚à¤¬à¤° à¤¬à¤¦à¤²à¤¨à¤¾ à¤¨à¤¹à¥€à¤‚ à¤šà¤¾à¤¹à¤¤à¥‡, à¤‡à¤¸à¤²à¤¿à¤ manage-path à¤•à¥‹ disciplined à¤¤à¤°à¥€à¤•à¥‡ à¤¸à¥‡ à¤šà¤²à¤¾à¤¨à¤¾ à¤¸à¤¬à¤¸à¥‡ à¤¬à¥‡à¤¹à¤¤à¤° à¤°à¤¹à¥‡à¤—à¤¾à¥¤"
    else:
        readiness_line = "à¤†à¤ª à¤…à¤­à¥€ evaluate mode à¤®à¥‡à¤‚ à¤¹à¥ˆà¤‚, à¤‡à¤¸à¤²à¤¿à¤ à¤…à¤—à¤²à¥‡ 21 à¤¦à¤¿à¤¨ evidence-based review à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤²à¥‡à¤‚à¥¤"

    standard_row_base = (
        "à¤¨à¤¾à¤® à¤…à¤‚à¤• à¤µà¤¿à¤œà¥à¤žà¤¾à¤¨ (Name Numerology) â€“ à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤•, à¤†à¤¤à¥à¤®à¤¿à¤• à¤‡à¤šà¥à¤›à¤¾, à¤µà¥à¤¯à¤•à¥à¤¤à¤¿à¤¤à¥à¤µ + à¤¨à¤¾à¤® à¤¸à¥à¤§à¤¾à¤° à¤¸à¤¿à¤«à¤¾à¤°à¤¿à¤¶"
    )
    enterprise_row_base = (
        "à¤¸à¤‚à¤ªà¥‚à¤°à¥à¤£ à¤œà¥€à¤µà¤¨ à¤¬à¥à¤²à¥‚à¤ªà¥à¤°à¤¿à¤‚à¤Ÿ (Complete Life Blueprint) â€“ 34 à¤ªà¥à¤°à¥€à¤®à¤¿à¤¯à¤® à¤¸à¥‡à¤•à¥à¤¶à¤¨: à¤œà¥€à¤µà¤¨ à¤°à¤£à¤¨à¥€à¤¤à¤¿, à¤µà¤¾à¤°à¥à¤·à¤¿à¤• à¤®à¤¾à¤°à¥à¤—à¤¦à¤°à¥à¤¶à¤¨, à¤•à¤°à¤¿à¤¯à¤°, à¤µà¤¿à¤¤à¥à¤¤, à¤¸à¤‚à¤¬à¤‚à¤§, à¤¸à¥à¤µà¤¾à¤¸à¥à¤¥à¥à¤¯, 90-à¤¦à¤¿à¤µà¤¸à¥€à¤¯ à¤¯à¥‹à¤œà¤¨à¤¾, à¤§à¤¨ à¤°à¤£à¤¨à¥€à¤¤à¤¿, à¤”à¤° à¤µà¤¿à¤•à¤¾à¤¸ à¤¬à¥à¤²à¥‚à¤ªà¥à¤°à¤¿à¤‚à¤Ÿ"
    )

    standard_row = _basic_blend_with_ai_variant(
        fallback_options=[
            standard_row_base,
            f"{standard_row_base} | Life Path {life_path_value} à¤”à¤° Mobile {mobile_vibration} à¤•à¥‡ à¤¬à¥€à¤š deeper alignment à¤•à¥‡ à¤²à¤¿à¤",
            f"{standard_row_base} | Missing digits ({missing_digits}) à¤•à¥€ name-energy à¤­à¤°à¤ªà¤¾à¤ˆ à¤•à¥‡ à¤²à¤¿à¤",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"next_steps_standard:{challenge_bucket}",
        max_chars=310,
    )
    enterprise_row = _basic_blend_with_ai_variant(
        fallback_options=[
            enterprise_row_base,
            f"{enterprise_row_base} | '{challenge}' à¤•à¥‡ à¤²à¤¿à¤ full strategic roadmap à¤”à¤° execution scorecards à¤•à¥‡ à¤¸à¤¾à¤¥",
            f"{enterprise_row_base} | {city} context à¤”à¤° à¤†à¤ªà¤•à¥€ readiness '{willingness}' à¤•à¥‡ à¤…à¤¨à¥à¤¸à¤¾à¤° high-precision personalization à¤•à¥‡ à¤¸à¤¾à¤¥",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"next_steps_premium:{challenge_bucket}",
        max_chars=430,
    )

    rows = [
        {
            "if_you_want": standard_row,
            "upgrade_to": "Standard Report",
        },
        {
            "if_you_want": enterprise_row,
            "upgrade_to": "Premium Report",
        },
    ]

    context_line = _basic_blend_with_ai_variant(
        fallback_options=[
            f"à¤…à¤¬ à¤†à¤ª à¤…à¤ªà¤¨à¥‡ à¤®à¥‹à¤¬à¤¾à¤‡à¤² à¤¨à¤‚à¤¬à¤° à¤•à¥€ à¤ªà¥‚à¤°à¥€ à¤Šà¤°à¥à¤œà¤¾ à¤¸à¤®à¤ à¤šà¥à¤•à¥‡ à¤¹à¥ˆà¤‚â€”à¤•à¥ˆà¤¸à¥‡ à¤¯à¤¹ à¤†à¤ªà¤•à¥€ {challenge} à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆ, à¤”à¤° à¤‡à¤¸à¤¸à¥‡ à¤•à¥ˆà¤¸à¥‡ à¤¬à¤¾à¤¹à¤° à¤¨à¤¿à¤•à¤²à¤¨à¤¾ à¤¹à¥ˆà¥¤",
            f"à¤†à¤ªà¤•à¥‡ profile à¤®à¥‡à¤‚ {challenge} à¤®à¥à¤–à¥à¤¯ à¤«à¥‹à¤•à¤¸ à¤¹à¥ˆ; à¤…à¤¬ à¤…à¤—à¤²à¤¾ à¤•à¤¦à¤® execution system à¤¬à¤¨à¤¾à¤¨à¤¾ à¤¹à¥ˆ à¤œà¥‹ à¤°à¥‹à¤œà¤¼à¤¾à¤¨à¤¾ à¤²à¤¾à¤—à¥‚ à¤¹à¥‹à¥¤",
            f"à¤¯à¤¹ à¤°à¤¿à¤ªà¥‹à¤°à¥à¤Ÿ à¤†à¤ªà¤•à¥€ {challenge} à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤•à¤¾ numerology-grounded map à¤¦à¥‡à¤¤à¥€ à¤¹à¥ˆ; à¤…à¤¬ action rhythm à¤¤à¤¯ à¤•à¤°à¤¨à¤¾ à¤¸à¤¬à¤¸à¥‡ à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ à¤¹à¥ˆà¥¤",
            f"{city} à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤”à¤° à¤†à¤ªà¤•à¥€ readiness '{willingness}' à¤•à¥‹ à¤§à¥à¤¯à¤¾à¤¨ à¤®à¥‡à¤‚ à¤°à¤–à¤¤à¥‡ à¤¹à¥à¤ à¤…à¤¬ structured action path à¤šà¥à¤¨à¤¨à¤¾ à¤¸à¤¹à¥€ à¤…à¤—à¤²à¤¾ à¤•à¤¦à¤® à¤¹à¥ˆà¥¤",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"next_steps_context:{challenge_bucket}",
        max_chars=320,
    )

    option_pool = {
        "finance": [
            "change path: नया नंबर लें – 4/6/8 alignment वाला pattern चुनें ताकि financial discipline मजबूत हो",
            "manage path: मौजूदा नंबर संभालें – 21 दिन debt-control remedies + DND financial windows लागू करें",
            "deeper analysis: Standard/Premium लेकर wealth strategy और execution map जोड़ें",
        ],
        "career": [
            "change path: नया नंबर लें – execution-support digits के साथ pattern चुनें ताकि results stable हों",
            "manage path: मौजूदा नंबर संभालें – 21 दिन career discipline protocol और communication windows लागू करें",
            "deeper analysis: Standard/Premium लेकर name synergy + 90-day action plan जोड़ें",
        ],
        "confidence": [
            "change path: नया नंबर लें – expression-support pattern चुनें ताकि decision और visibility मजबूत हों",
            "manage path: मौजूदा नंबर संभालें – 21 दिन confidence protocol (script, DND, ritual) लागू करें",
            "deeper analysis: Standard/Premium लेकर name-correction और behavior blueprint जोड़ें",
        ],
        "default": [
            "change path: नया नंबर लें – सुझाए गए patterns में से चुनें",
            "manage path: मौजूदा नंबर संभालें – 21 दिन के उपाय लागू करें",
            "deeper analysis: Standard या Premium रिपोर्ट लें",
        ],
    }
    options = list(option_pool.get(challenge_bucket, option_pool["default"]))
    if willingness == "no":
        options[0], options[1] = options[1], options[0]
    elif willingness == "yes":
        options = [options[0], options[2], options[1]]

    closing_options = {
        "finance": [
            "à¤†à¤ªà¤•à¥€ à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° à¤•à¤°à¥à¤œ à¤®à¥à¤•à¥à¤¤à¤¿ à¤•à¥€ à¤¯à¤¾à¤¤à¥à¤°à¤¾ à¤…à¤¬ à¤¶à¥à¤°à¥‚ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "à¤…à¤¬ à¤†à¤ªà¤•à¤¾ focus debt-pressure à¤¸à¥‡ disciplined wealth flow à¤•à¥€ à¤“à¤° à¤¶à¤¿à¤«à¥à¤Ÿ à¤¹à¥‹à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤à¥¤",
            "à¤…à¤—à¤²à¥‡ 30 à¤¦à¤¿à¤¨à¥‹à¤‚ à¤•à¤¾ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¿à¤¤ à¤…à¤­à¥à¤¯à¤¾à¤¸ à¤†à¤ªà¤•à¥€ financial recovery à¤•à¥‹ à¤¤à¥‡à¤œà¤¼ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        ],
        "career": [
            "à¤†à¤ªà¤•à¥€ à¤•à¤°à¤¿à¤¯à¤° à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° execution growth à¤•à¥€ à¤¯à¤¾à¤¤à¥à¤°à¤¾ à¤…à¤¬ à¤¶à¥à¤°à¥‚ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "à¤…à¤¬ à¤²à¤•à¥à¤·à¥à¤¯ à¤¸à¤¿à¤°à¥à¤« à¤®à¥‡à¤¹à¤¨à¤¤ à¤¨à¤¹à¥€à¤‚, à¤¬à¤²à¥à¤•à¤¿ measurable execution cadence à¤¬à¤¨à¤¾à¤¨à¤¾ à¤¹à¥ˆà¥¤",
            "à¤•à¥ˆà¤°à¤¿à¤¯à¤° momentum à¤•à¥‹ à¤¸à¥à¤¥à¤¿à¤° à¤°à¤–à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ daily focus + weekly review à¤…à¤¨à¤¿à¤µà¤¾à¤°à¥à¤¯ à¤°à¤–à¥‡à¤‚à¥¤",
        ],
        "confidence": [
            "à¤†à¤ªà¤•à¥€ à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤”à¤° à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤•à¥€ à¤¯à¤¾à¤¤à¥à¤°à¤¾ à¤…à¤¬ à¤¶à¥à¤°à¥‚ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "à¤…à¤¬ hesitation à¤¸à¥‡ clarity à¤•à¥€ à¤“à¤° à¤œà¤¾à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ daily expression drills à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤",
            "à¤›à¥‹à¤Ÿà¥‡ consistent wins à¤…à¤—à¤²à¥‡ 30 à¤¦à¤¿à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤•à¤¾ à¤¨à¤¯à¤¾ baseline à¤¬à¤¨à¤¾à¤à¤à¤—à¥‡à¥¤",
        ],
        "default": [
            "à¤†à¤ªà¤•à¥€ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤®-à¤¸à¤‚à¤¤à¥à¤²à¤¨ à¤•à¥€ à¤¯à¤¾à¤¤à¥à¤°à¤¾ à¤…à¤¬ à¤¶à¥à¤°à¥‚ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "à¤…à¤¬ key à¤²à¤•à¥à¤·à¥à¤¯ à¤¹à¥ˆ: routine consistency, clearer decisions, and practical progress.",
            "21 à¤¦à¤¿à¤¨ à¤•à¤¾ disciplined protocol à¤†à¤ªà¤•à¥‡ à¤ªà¤°à¤¿à¤£à¤¾à¤®à¥‹à¤‚ à¤•à¥‹ visibly improve à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        ],
    }
    closing_line = _basic_blend_with_ai_variant(
        fallback_options=closing_options.get(challenge_bucket, closing_options["default"]),
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"next_steps_closing:{challenge_bucket}",
        max_chars=280,
    )
    closing_line = f"{closing_line} {readiness_line}".strip()
    thanks_line = _basic_blend_with_ai_variant(
        fallback_options=[
            f"à¤§à¤¨à¥à¤¯à¤µà¤¾à¤¦, {first_name}",
            f"à¤§à¤¨à¥à¤¯à¤µà¤¾à¤¦, {first_name} à¤œà¥€",
            f"à¤¶à¥à¤­à¤•à¤¾à¤®à¤¨à¤¾à¤à¤, {first_name} à¤œà¥€",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"next_steps_thanks:{challenge_bucket}",
        max_chars=60,
    )

    return {
        "rows": rows,
        "thanks": thanks_line,
        "context": context_line,
        "options": options,
        "closing": closing_line,
        "footer_lines": [
            "à¤°à¤¿à¤ªà¥‹à¤°à¥à¤Ÿ à¤ªà¥à¤°à¤•à¤¾à¤° (Report Type): Basic (à¤®à¥‹à¤¬à¤¾à¤‡à¤² à¤…à¤‚à¤• à¤µà¤¿à¤œà¥à¤žà¤¾à¤¨)",
            f"à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ (Generated For): {full_name}",
            f"à¤¦à¤¿à¤¨à¤¾à¤‚à¤• (Date): {str(core.get('generated_on') or '')}",
        ],
    }


def _basic_footer_payload(*, core: Dict[str, Any], uniqueness_seed: str = "", ai_narrative: str = "") -> Dict[str, str]:
    inputs = core.get("inputs") or {}
    uniqueness_seed = str(uniqueness_seed or core.get("uniqueness_seed") or "basic-footer-seed")
    full_name = str(inputs.get("full_name") or "Not Provided")
    first_name = str(inputs.get("first_name") or "User")
    challenge = str(inputs.get("primary_challenge") or "consistency")
    city = str(inputs.get("city") or "Not Provided")
    willingness = str(inputs.get("willingness_to_change") or "undecided")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    mobile_vibration = str((core.get("mobile") or {}).get("vibration") or "â€”")
    life_path_value = str((core.get("life_path") or {}).get("value") or "â€”")

    gratitude_options = {
        "finance": [
            f"{first_name} à¤œà¥€, à¤†à¤ªà¤•à¤¾ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤¹à¥€ à¤†à¤ªà¤•à¥€ à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤¸à¥à¤µà¤¤à¤‚à¤¤à¥à¤°à¤¤à¤¾ à¤•à¤¾ à¤¸à¤¬à¤¸à¥‡ à¤¬à¤¡à¤¼à¤¾ à¤¸à¥‚à¤¤à¥à¤° à¤¹à¥ˆà¥¤",
            f"{first_name} à¤œà¥€, à¤†à¤œ à¤•à¤¾ à¤¸à¤‚à¤°à¤šà¤¿à¤¤ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤•à¤² à¤•à¥€ debt-free clarity à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            f"{first_name} à¤œà¥€, à¤§à¤¨-à¤¸à¤‚à¤¤à¥à¤²à¤¨ à¤•à¥€ à¤¯à¤¾à¤¤à¥à¤°à¤¾ à¤›à¥‹à¤Ÿà¥‡ à¤²à¥‡à¤•à¤¿à¤¨ à¤²à¤—à¤¾à¤¤à¤¾à¤° à¤•à¤¦à¤®à¥‹à¤‚ à¤¸à¥‡ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
        ],
        "career": [
            f"{first_name} à¤œà¥€, à¤†à¤ªà¤•à¥€ execution consistency à¤¹à¥€ à¤†à¤ªà¤•à¥€ professional à¤ªà¤¹à¤šà¤¾à¤¨ à¤¬à¤¨à¤¾à¤à¤—à¥€à¥¤",
            f"{first_name} à¤œà¥€, focused action + clear priorities = sustained career growth.",
            f"{first_name} à¤œà¥€, disciplined rhythm à¤†à¤ªà¤•à¥€ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤•à¥‹ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
        ],
        "confidence": [
            f"{first_name} à¤œà¥€, à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤…à¤­à¤¿à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤”à¤° à¤¸à¥à¤¥à¤¿à¤° à¤¦à¤¿à¤¨à¤šà¤°à¥à¤¯à¤¾ à¤†à¤ªà¤•à¤¾ à¤†à¤¤à¥à¤®à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤—à¥à¤£à¤¾ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            f"{first_name} à¤œà¥€, à¤œà¤¬ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤†à¤ªà¤•à¥€ à¤Šà¤°à¥à¤œà¤¾ à¤¸à¥à¤µà¤¾à¤­à¤¾à¤µà¤¿à¤• à¤°à¥‚à¤ª à¤¸à¥‡ à¤ªà¥à¤°à¤­à¤¾à¤µà¥€ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
            f"{first_name} à¤œà¥€, daily confidence rituals à¤†à¤ªà¤•à¥€ visibility à¤”à¤° à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¦à¥‹à¤¨à¥‹à¤‚ à¤¬à¤¢à¤¼à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
        ],
        "default": [
            f"{first_name} à¤œà¥€, à¤¸à¥à¤¥à¤¿à¤° à¤¦à¤¿à¤¨à¤šà¤°à¥à¤¯à¤¾ à¤†à¤ªà¤•à¥€ à¤Šà¤°à¥à¤œà¤¾ à¤•à¥‹ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¥‡ à¤•à¥€ à¤•à¥à¤‚à¤œà¥€ à¤¹à¥ˆà¥¤",
            f"{first_name} à¤œà¥€, consistency à¤†à¤ªà¤•à¥€ numerology strengths à¤•à¥‹ practical outcomes à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            f"{first_name} à¤œà¥€, structured practice à¤¹à¥€ long-term stability à¤•à¤¾ à¤µà¤¾à¤¸à¥à¤¤à¤µà¤¿à¤• à¤†à¤§à¤¾à¤° à¤¹à¥ˆà¥¤",
        ],
    }
    gratitude_line = _basic_blend_with_ai_variant(
        fallback_options=gratitude_options.get(bucket, gratitude_options["default"]),
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"footer_gratitude:{bucket}",
        max_chars=240,
    )

    tagline_line = _basic_blend_with_ai_variant(
        fallback_options=[
            "Tagline: à¤Šà¤°à¥à¤œà¤¾ à¤¸à¤¹à¥€ à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚, à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¤¹à¥€ à¤¸à¤®à¤¯ à¤ªà¤°, à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¸à¤¹à¥€ à¤—à¤¤à¤¿ à¤¸à¥‡à¥¤",
            "Tagline: Numerology à¤¤à¤¬ à¤ªà¥à¤°à¤­à¤¾à¤µà¥€ à¤¹à¥ˆ à¤œà¤¬ à¤‡à¤¸à¥‡ daily action discipline à¤¸à¥‡ à¤œà¥‹à¤¡à¤¼à¤¾ à¤œà¤¾à¤à¥¤",
            "Tagline: Clarity + Consistency + Correction = Sustainable Growth.",
            f"Tagline: Vibration {mobile_vibration} + Life Path {life_path_value} à¤•à¥€ aligned action-rhythm à¤¹à¥€ sustainable à¤¸à¤«à¤²à¤¤à¤¾ à¤•à¤¾ à¤¸à¥‚à¤¤à¥à¤° à¤¹à¥ˆà¥¤",
            f"Tagline: {city} à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤®à¥‡à¤‚ '{challenge}' à¤ªà¤° focused, consistent à¤”à¤° measurable action à¤¹à¥€ breakthrough à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            f"Tagline: Readiness ({willingness}) + Routine + Review = Real Transformation.",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"footer_tagline:{bucket}",
        max_chars=220,
    )

    return {
        "report_type_line": "Report Type: Basic (Mobile Numerology)",
        "generated_for_line": f"Generated For: {full_name}",
        "date_line": f"Date: {str(core.get('generated_on') or '')}",
        "gratitude_line": gratitude_line,
        "tagline_line": tagline_line,
    }


def _basic_loshu_challenge_lines(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> List[str]:
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    lo_shu = core.get("lo_shu") or {}
    missing = set(lo_shu.get("missing") or [])
    present = set(lo_shu.get("present") or [])
    repeating = lo_shu.get("repeating") or []
    repeat_map = {int(item.get("digit")): int(item.get("count")) for item in repeating if isinstance(item, dict)}

    if bucket == "finance":
        anchor = "Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ, Ã Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â¨Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤â€¦Ã Â¤Â¸Ã Â¤Â°"
        structure = "Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨, Ã Â¤Â¬Ã Â¤Å“Ã Â¤Å¸Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤â€Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“ Ã Â¤Å¡Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â¾Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾"
    elif bucket == "career":
        anchor = "Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â° Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â®Ã Â¥â€¹Ã Â¤â€š Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾"
        structure = "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾, execution rhythm Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨"
    elif bucket == "confidence":
        anchor = "Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤â€Ã Â¤Â° self-expression Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€°Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â°-Ã Â¤Å¡Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Âµ"
        structure = "Ã Â¤â€ Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¶Ã Â¥Ë†Ã Â¤Â²Ã Â¥â‚¬"
    else:
        anchor = "Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾"
        structure = "Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾"

    lines: List[str] = []
    if repeat_map.get(8, 0) >= 2:
        lines.append(
            f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 8 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤Â§Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ ({repeat_map.get(8)} Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â°) Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤â€¢Ã Â¤Â¾Ã Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ {anchor} Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¥â€¡Ã Â¤Å“ Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    elif repeat_map:
        repeat_digit = sorted(repeat_map.keys(), key=lambda d: repeat_map[d], reverse=True)[0]
        lines.append(
            f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {repeat_digit} Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¨Ã Â¤Â°Ã Â¤Â¾Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€°Ã Â¤Â¸Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â€¹ amplify Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; imbalance Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° {anchor} Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    else:
        lines.append("Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Âµ Ã Â¤â€¢Ã Â¤Â® Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¤Ã Â¤Æ’ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ consistency Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â° Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤")

    if 4 in missing:
        lines.append(
            f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 4 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤Â¬Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¥â€¡Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†; {structure} Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â®Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤Â§Ã Â¥â€šÃ Â¤Â°Ã Â¥â‚¬ Ã Â¤Â°Ã Â¤Â¹ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    else:
        lines.append("Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 4 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤â€¦Ã Â¤Å¡Ã Â¥ÂÃ Â¤â€ºÃ Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â®Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¦Ã Â¤Â¬ Ã Â¤â€¡Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤â€”Ã Â¤Â¾Ã Â¥Â¤")

    if 3 in missing:
        lines.append("Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 3 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¦Ã Â¤Â­Ã Â¤Â¿Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥â€¹ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¤â€šÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¦ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â¨ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¸Ã Â¤Â¹Ã Â¤Â¯Ã Â¥â€¹Ã Â¤â€” Ã Â¤â€Ã Â¤Â° negotiation Ã Â¤â€¢Ã Â¤Â®Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â¡Ã Â¤Â¼Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤")
    elif 3 in present:
        lines.append("Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 3 Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤â€šÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¦ Ã Â¤Â¶Ã Â¥Ë†Ã Â¤Â²Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤ÂªÃ Â¤Â¨Ã Â¤Â¾Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° clarity, persuasion Ã Â¤â€Ã Â¤Â° execution coordination Ã Â¤Â®Ã Â¤Å“Ã Â¤Â¬Ã Â¥â€šÃ Â¤Â¤ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤")

    if 1 in present:
        lines.append("Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 1 Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤â€Ã Â¤Â° Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¡Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤â€šÃ Â¤â€”Ã Â¥â€¡Ã Â¥Â¤")
    else:
        lines.append("Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 1 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â² Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤ÂÃ Â¤Â¿Ã Â¤ÂÃ Â¤â€¢ Ã Â¤â€  Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤â€ºÃ Â¥â€¹Ã Â¤Å¸Ã Â¥â€¡ daily commitment Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â§Ã Â¥â‚¬Ã Â¤Â°Ã Â¥â€¡-Ã Â¤Â§Ã Â¥â‚¬Ã Â¤Â°Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤")

    ai_conclusion = _basic_blend_with_ai_variant(
        fallback_options=[
            "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â·Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â·: Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤ÂªÃ Â¥Ë†Ã Â¤Å¸Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¨ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â¬Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë† Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Â¸Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¿Ã Â¤â€“Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â·Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â·: missing digits Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â­Ã Â¤Â°Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Ë† Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â­Ã Â¤Âµ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â·Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â·: challenge-oriented daily structure Ã Â¤Â¹Ã Â¥â‚¬ grid imbalance Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â°Ã Â¥â€šÃ Â¤Âª Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        ],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"loshu_conclusion:{bucket}",
        max_chars=260,
    )
    if ai_conclusion:
        if len(lines) >= 4:
            lines[3] = ai_conclusion
        else:
            lines.append(ai_conclusion)
    if len(lines) < 4:
        lines.append(
            _pick_variant(
                [
                    "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â·Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â·: Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤ÂªÃ Â¥Ë†Ã Â¤Å¸Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¨ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â¬Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë† Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤Â¸Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¿Ã Â¤â€“Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
                    "Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â·Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â·: missing digits Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â­Ã Â¤Â°Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Ë† Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â­Ã Â¤Âµ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
                ],
                uniqueness_seed,
                "loshu_conclusion_fallback",
            )
        )
    return lines[:4]


def _basic_positive_impact_rows(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str = "",
    ai_narrative: str = "",
) -> List[Dict[str, str]]:
    lo_shu = core.get("lo_shu") or {}
    present = set(lo_shu.get("present") or [])
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    planet = core.get("planet") or {}
    planet_energy = ", ".join((planet.get("energy") or [])[:2]) or "Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾"

    rows: List[Dict[str, str]] = [
        {
            "effect": "Ã°Å¸â€™Âª Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾",
            "impact": "Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¹ Ã Â¤Â®Ã Â¥ÂÃ Â¤Â¶Ã Â¥ÂÃ Â¤â€¢Ã Â¤Â¿Ã Â¤Â² Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¯ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤â€ Ã Â¤â€”Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â¤Ã Â¤Â¯ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¤ Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        },
        {
            "effect": "Ã°Å¸â€Â¥ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¹Ã Â¤Â¸ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€¢Ã Â¤Â²Ã Â¥ÂÃ Â¤Âª",
            "impact": "Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â¨ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â¨Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â§Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤â€“Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â¨Ã Â¤Â¸Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯ Ã Â¤Â°Ã Â¤Â¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        },
        {
            "effect": "Ã°Å¸Å½Â¯ Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¶Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿",
            "impact": "Ã Â¤ÂÃ Â¤â€¢ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â²Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â¹Ã Â¥â€¹ Ã Â¤Å“Ã Â¤Â¾Ã Â¤Â Ã Â¤Â¤Ã Â¥â€¹ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤â€¦Ã Â¤â€šÃ Â¤Â¤ Ã Â¤Â¤Ã Â¤â€¢ Ã Â¤Â²Ã Â¥â€¡ Ã Â¤Å“Ã Â¤Â¾Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤ÂÃ Â¥ÂÃ Â¤â€¢Ã Â¤Â¾Ã Â¤Âµ Ã Â¤Â®Ã Â¤Å“Ã Â¤Â¬Ã Â¥â€šÃ Â¤Â¤ Ã Â¤Â°Ã Â¤Â¹Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        },
        {
            "effect": "Ã°Å¸Å¡â‚¬ Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤â€¢Ã Â¤Â¾Ã Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾",
            "impact": "Ã Â¤Â¬Ã Â¤Â¡Ã Â¤Â¼Ã Â¥â€¡ Ã Â¤Â²Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¦Ã Â¥â€¡Ã Â¤â€“Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â®-Ã Â¤â€°Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â®Ã Â¥ÂÃ Â¤â€“ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â°Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Ë† Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¥â€¡Ã Â¤Â°Ã Â¤Â£Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        },
    ]

    if 1 in present:
        rows.append(
            {
                "effect": "Ã°Å¸â€˜â€˜ Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾",
                "impact": "Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 1 Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤â€“Ã Â¥ÂÃ Â¤Â¦ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â­Ã Â¤Â°Ã Â¥â€¹Ã Â¤Â¸Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Âµ-Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â®Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Å“Ã Â¤Â¬Ã Â¥â€šÃ Â¤Â¤ Ã Â¤â€ Ã Â¤Â§Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            }
        )
    else:
        rows.append(
            {
                "effect": "Ã°Å¸Â§Â­ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾-Ã Â¤Â¸Ã Â¤â€šÃ Â¤ÂµÃ Â¥â€¡Ã Â¤Â¦Ã Â¤Â¨",
                "impact": f"Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¹ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ ({planet_energy}) Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¹ Ã Â¤â€ Ã Â¤â€”Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¤ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¥â‚¬ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            }
        )
    challenge_adaptations: Dict[str, List[Dict[str, str]]] = {
        "finance": [
            {
                "effect": "ðŸ’° à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤•à¥à¤·à¤®à¤¤à¤¾",
                "impact": "à¤¸à¤¹à¥€ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¯à¤¹ à¤Šà¤°à¥à¤œà¤¾ debt pressure à¤•à¤® à¤•à¤°à¤•à¥‡ structured repayment support à¤•à¤° à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            },
            {
                "effect": "ðŸ“Š à¤¨à¤¿à¤°à¥à¤£à¤¯-à¤†à¤§à¤¾à¤°à¤¿à¤¤ à¤§à¤¨ à¤ªà¥à¤°à¤¬à¤‚à¤§à¤¨",
                "impact": "à¤¬à¤¡à¤¼à¥‡ à¤–à¤°à¥à¤šà¥‹à¤‚ à¤®à¥‡à¤‚ pause-rule à¤…à¤ªà¤¨à¤¾à¤¨à¥‡ à¤ªà¤° à¤†à¤ªà¤•à¤¾ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¬à¥‡à¤¹à¤¤à¤° à¤”à¤° cashflow à¤…à¤§à¤¿à¤• à¤¸à¥à¤¥à¤¿à¤° à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            },
        ],
        "career": [
            {
                "effect": "ðŸŽ¯ execution readiness",
                "impact": "à¤•à¥ˆà¤°à¤¿à¤¯à¤° à¤²à¤•à¥à¤·à¥à¤¯à¥‹à¤‚ à¤•à¥‹ à¤šà¤°à¤£à¤¬à¤¦à¥à¤§ à¤¯à¥‹à¤œà¤¨à¤¾ à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¥‡ à¤•à¥€ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤®à¤œà¤¬à¥‚à¤¤ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            },
            {
                "effect": "ðŸš€ growth-oriented leadership",
                "impact": "à¤Ÿà¥€à¤® à¤”à¤° à¤ªà¤°à¤¿à¤¯à¥‹à¤œà¤¨à¤¾à¤“à¤‚ à¤®à¥‡à¤‚ à¤œà¤¿à¤®à¥à¤®à¥‡à¤¦à¤¾à¤°à¥€ à¤²à¥‡à¤•à¤° measurable output à¤¦à¥‡à¤¨à¥‡ à¤•à¥€ à¤ªà¥à¤°à¤µà¥ƒà¤¤à¥à¤¤à¤¿ à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆà¥¤",
            },
        ],
        "confidence": [
            {
                "effect": "ðŸ—£ï¸ clear self-expression potential",
                "impact": "à¤¤à¥ˆà¤¯à¤¾à¤° à¤¸à¥à¤•à¥à¤°à¤¿à¤ªà¥à¤Ÿ à¤”à¤° à¤¸à¤®à¤¯à¤¬à¤¦à¥à¤§ à¤¸à¤‚à¤šà¤¾à¤° à¤¸à¥‡ à¤†à¤ªà¤•à¥€ visibility à¤”à¤° à¤µà¤¿à¤¶à¥à¤µà¤¾à¤¸ à¤¤à¥‡à¤œà¤¼à¥€ à¤¸à¥‡ à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            },
            {
                "effect": "ðŸ§­ self-directed momentum",
                "impact": "à¤›à¥‹à¤Ÿà¥‡ daily wins à¤¸à¥‡ confidence loop à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ à¤”à¤° hesitation à¤˜à¤Ÿà¤¤à¤¾ à¤¹à¥ˆà¥¤",
            },
        ],
    }

    if bucket in challenge_adaptations:
        rows = rows[:3] + challenge_adaptations[bucket] + rows[3:]

    uniqueness_seed = str(uniqueness_seed or core.get("uniqueness_seed") or "basic-positive-seed")
    if rows:
        rows[0]["impact"] = _basic_blend_with_ai_variant(
            fallback_options=[
                rows[0]["impact"],
                "à¤¸à¤¹à¥€ routine à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¯à¤¹ à¤Šà¤°à¥à¤œà¤¾ à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤•à¥‡ à¤¬à¥€à¤š à¤­à¥€ steady progress à¤¬à¤¨à¤¾à¤ à¤°à¤–à¤¨à¥‡ à¤®à¥‡à¤‚ à¤®à¤¦à¤¦ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            ],
            ai_text=ai_narrative,
            uniqueness_seed=uniqueness_seed,
            slot=f"positive_row_0:{bucket}",
            max_chars=220,
        )

    return rows[:5]


def _basic_challenge_rows(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str = "",
    ai_narrative: str = "",
) -> List[Dict[str, str]]:
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    lo_shu = core.get("lo_shu") or {}
    missing = set(lo_shu.get("missing") or [])

    if bucket == "finance":
        connection_main = "Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â§Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â£"
        connection_focus = "Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Å“Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â¼Ã Â¤Â¾"
    elif bucket == "career":
        connection_main = "Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â§Ã Â¤Â¾ execution delay Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â£"
        connection_focus = "Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â®Ã Â¥â€¹Ã Â¤â€š Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â§Ã Â¥â€¡ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†"
    elif bucket == "confidence":
        connection_main = "Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¸ Ã Â¤â€”Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â£"
        connection_focus = "Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â§Ã Â¥â€¡ Ã Â¤Å“Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â¼Ã Â¤Â¾"
    else:
        connection_main = "Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â£"
        connection_focus = "Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â‚¬Ã Â¤Â§Ã Â¥â€¡ Ã Â¤Å“Ã Â¥ÂÃ Â¤Â¡Ã Â¤Â¼Ã Â¤Â¾"

    rows: List[Dict[str, str]] = [
        {
            "challenge": "Ã°Å¸Å’Å  Ã Â¤â€¦Ã Â¤Â§Ã Â¥â‚¬Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ (Impulsiveness)",
            "appearance": "Ã Â¤Â¬Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤ÂªÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¤ Ã Â¤Â¸Ã Â¤Â®Ã Â¥â‚¬Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Å“Ã Â¤Â²Ã Â¥ÂÃ Â¤Â¦Ã Â¥â‚¬ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤Â²Ã Â¥â€¡Ã Â¤Â¨Ã Â¤Â¾, Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â¸Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¦ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â§Ã Â¤Â¾Ã Â¤Â° Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Å“Ã Â¤Â°Ã Â¥â€šÃ Â¤Â°Ã Â¤Â¤ Ã Â¤ÂªÃ Â¤Â¡Ã Â¤Â¼Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "connection": connection_main,
        },
        {
            "challenge": "Ã°Å¸â€™Â¸ Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬",
            "appearance": "Ã Â¤â€ Ã Â¤Â¯ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾, Ã Â¤Â¬Ã Â¤Å¡Ã Â¤Â¤ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¥Ã Â¤Â®Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾-Ã Â¤â€ Ã Â¤Â§Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€“Ã Â¤Â°Ã Â¥ÂÃ Â¤Å¡ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¦Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤â€“ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "connection": connection_focus,
        },
        {
            "challenge": "Ã°Å¸â€”Â£Ã¯Â¸Â Ã Â¤â€¦Ã Â¤Â­Ã Â¤Â¿Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¢Ã Â¤Â Ã Â¤Â¿Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Ë†",
            "appearance": "Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 3 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤â€¦Ã Â¤ÂªÃ Â¤Â¨Ã Â¥â‚¬ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¤ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸ Ã Â¤Â°Ã Â¥â€šÃ Â¤Âª Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° negotiation Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤Â¹Ã Â¥â€¹ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
            if 3 in missing
            else "Ã Â¤Â¸Ã Â¤â€šÃ Â¤ÂµÃ Â¤Â¾Ã Â¤Â¦ Ã Â¤Â¶Ã Â¥Ë†Ã Â¤Â²Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Å¸Ã Â¥â‚¬Ã Â¤Â®/Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€”Ã Â¤Â²Ã Â¤Â¤Ã Â¤Â«Ã Â¤Â¹Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "connection": "Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¤Â¹Ã Â¤Â¯Ã Â¥â€¹Ã Â¤â€” Ã Â¤ËœÃ Â¤Å¸Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾ Ã Â¤Â²Ã Â¤â€šÃ Â¤Â¬Ã Â¥â‚¬ Ã Â¤Å¡Ã Â¤Â² Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        },
        {
            "challenge": "Ã¢Å¡Â¡ Ã Â¤Â¬Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¨Ã Â¤â€ Ã Â¤â€°Ã Â¤Å¸ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Å“Ã Â¥â€¹Ã Â¤â€“Ã Â¤Â¿Ã Â¤Â®",
            "appearance": "Ã Â¤Å“Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾Ã Â¤Â¦Ã Â¤Â¾ Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â®Ã Â¥â€¡Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾Ã Â¤Â Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â° Ã Â¤Â²Ã Â¤â€”Ã Â¤Â¾Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¥Ã Â¤â€¢Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Å¸ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€”Ã Â¥ÂÃ Â¤Â£Ã Â¤ÂµÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¾ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥â€¹ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "connection": "Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€”Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â°Ã Â¤Â«Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¾Ã Â¤Â° Ã Â¤Å¸Ã Â¥â€šÃ Â¤Å¸Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
        },
        {
            "challenge": "Ã°Å¸â€Â Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤Ã Â¤Â¤Ã Â¤Â¾",
            "appearance": "Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â°Ã Â¥ÂÃ Â¤â€ Ã Â¤Â¤ Ã Â¤Â¤Ã Â¥â€¡Ã Â¤Å“ Ã Â¤Â°Ã Â¤Â¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤Â¬Ã Â¥â‚¬Ã Â¤Å¡ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¢Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¾ Ã Â¤ÂªÃ Â¤Â¡Ã Â¤Â¼Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° continuity Ã Â¤Å¸Ã Â¥â€šÃ Â¤Å¸Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤",
            "connection": "Ã Â¤Â¦Ã Â¥â‚¬Ã Â¤Â°Ã Â¥ÂÃ Â¤ËœÃ Â¤â€¢Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â²Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¸Ã Â¤Â®Ã Â¤Â¯ Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥â€¡ Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š Ã Â¤Â¹Ã Â¥â€¹ Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¤Ã Â¥â€¡Ã Â¥Â¤",
        },
    ]
    uniqueness_seed = str(uniqueness_seed or core.get("uniqueness_seed") or "basic-challenge-seed")
    if rows:
        rows[0]["connection"] = _basic_blend_with_ai_variant(
            fallback_options=[
                rows[0]["connection"],
                f"à¤¯à¤¹ à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨ '{challenge}' à¤•à¥‡ à¤ªà¤°à¤¿à¤£à¤¾à¤®à¥‹à¤‚ à¤•à¥‹ à¤¸à¥€à¤§à¥‡ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ preventive routine à¤œà¤°à¥‚à¤°à¥€ à¤¹à¥ˆà¥¤",
            ],
            ai_text=ai_narrative,
            uniqueness_seed=uniqueness_seed,
            slot=f"challenge_row_0:{bucket}",
            max_chars=220,
        )
    return rows[:3]


def _basic_life_path_context_lines(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> List[str]:
    inputs = core.get("inputs") or {}
    challenge = str(inputs.get("primary_challenge") or "consistency")
    bucket = _basic_effective_problem_bucket(core=core, challenge=challenge)
    life_path = int((core.get("life_path") or {}).get("value") or 0)
    mobile_vibration = int((core.get("mobile") or {}).get("vibration") or 0)
    missing = set((core.get("lo_shu") or {}).get("missing") or [])
    present = set((core.get("lo_shu") or {}).get("present") or [])

    if bucket == "finance":
        line1 = (
            f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ {life_path} Ã Â¤â€Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {mobile_vibration} Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¹Ã Â¤â€š Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿Ã Â¤Â¶Ã Â¥â‚¬Ã Â¤Â² Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€š, "
            f"Ã Â¤Å“Ã Â¥â€¹ '{challenge}' Ã Â¤Å“Ã Â¥Ë†Ã Â¤Â¸Ã Â¥â‚¬ Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€ Ã Â¤â€”Ã Â¥â€¡ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â®Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤"
        )
    elif bucket == "career":
        line1 = (
            f"Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ {life_path} Ã Â¤â€Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {mobile_vibration} Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨ Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â®-Ã Â¤â€°Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â®Ã Â¥ÂÃ Â¤â€“ Ã Â¤Â¹Ã Â¥Ë†, "
            f"Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â¸Ã Â¤Â¸Ã Â¥â€¡ '{challenge}' Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â²Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    else:
        line1 = (
            f"Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ {life_path} Ã Â¤â€Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {mobile_vibration} Ã Â¤Â®Ã Â¤Â¿Ã Â¤Â²Ã Â¤â€¢Ã Â¤Â° Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¸Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯ Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¹Ã Â¥Ë†Ã Â¤â€šÃ Â¥Â¤"
        )

    if 4 in missing:
        line2 = (
            f"Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â§Ã Â¥ÂÃ Â¤Â°Ã Â¥â‚¬ (Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 4) Ã Â¤â€¢Ã Â¤Â®Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ '{challenge}' Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â° execution Ã Â¤Å¸Ã Â¥â€šÃ Â¤Å¸ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
        )
    else:
        line2 = "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾-Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ (4) Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â²Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â§ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€°Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†; consistency Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â Ã Â¤Â°Ã Â¤â€“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥ÂÃ Â¤â€šÃ Â¤Å“Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"

    if 1 in present:
        line3 = "Ã Â¤â€¦Ã Â¤Å¡Ã Â¥ÂÃ Â¤â€ºÃ Â¥â‚¬ Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Â¤ Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤Â¹Ã Â¥Ë† Ã Â¤â€¢Ã Â¤Â¿ Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 1 Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤â€Ã Â¤Â° Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤â€¢Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤â€¡Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¤â€¢Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤"
    else:
        line3 = "Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 1 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â² Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤ÂÃ Â¤Â¿Ã Â¤ÂÃ Â¤â€¢ Ã Â¤â€  Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤â€ºÃ Â¥â€¹Ã Â¤Å¸Ã Â¥â€¡ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯-Ã Â¤ÂÃ Â¤â€šÃ Â¤â€¢Ã Â¤Â° Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤Â¸Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤"

    line_1 = _basic_blend_with_ai_variant(
        fallback_options=[line1],
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot=f"life_path_line_1:{bucket}",
        max_chars=280,
    )
    return [
        line_1,
        _pick_variant([line2], uniqueness_seed, "life_path_line_2"),
        _pick_variant([line3], uniqueness_seed, "life_path_line_3"),
    ]


def _basic_profile_conditioned_line(
    *,
    core: Dict[str, Any],
    uniqueness_seed: str,
    ai_narrative: str = "",
) -> str:
    inputs = core.get("inputs") or {}
    city = str(inputs.get("city") or "Not Provided")
    challenge = str(inputs.get("primary_challenge") or "consistency")
    willingness = str(inputs.get("willingness_to_change") or "undecided")
    missing = ", ".join(str(d) for d in (core.get("lo_shu") or {}).get("missing") or []) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    compatibility = (core.get("compatibility") or {}).get("english", "Moderate")
    options = [
        f"{city} Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¾Ã Â¤Â¥Ã Â¤Â®Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ '{challenge}' Ã Â¤Â¹Ã Â¥Ë†; missing digits ({missing}) Ã Â¤ÂªÃ Â¤Â° Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¨Ã Â¥â€¡ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤â€”Ã Â¥â‚¬Ã Â¥Â¤",
        f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤ÂµÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â¨ alignment {compatibility} Ã Â¤Â¹Ã Â¥Ë† Ã Â¤â€Ã Â¤Â° readiness='{willingness}' Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â§Ã Â¤Â¾Ã Â¤Â° Ã Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤ÂµÃ Â¤Â¹Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
        f"Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ + Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤Â¬Ã Â¤Â¶Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¤Ã Â¥â€¡ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ execution discipline Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â Ã Â¤Â°Ã Â¤â€“Ã Â¥â€¡Ã Â¤â€šÃ Â¥Â¤",
    ]
    return _basic_blend_with_ai_variant(
        fallback_options=options,
        ai_text=ai_narrative,
        uniqueness_seed=uniqueness_seed,
        slot="profile_line",
        max_chars=260,
    )


def _normalized_similarity(left: str, right: str) -> float:
    if not left.strip() or not right.strip():
        return 0.0
    return SequenceMatcher(None, left.lower().strip(), right.lower().strip()).ratio()


def _section_text_blob(section: Dict[str, Any]) -> str:
    if not isinstance(section, dict):
        return ""
    title = str(section.get("title") or "")
    blocks = section.get("blocks") or []
    if not isinstance(blocks, list):
        blocks = [str(blocks)]
    return " ".join([title] + [str(item or "") for item in blocks]).strip()


def _report_text_blob(sections: List[Dict[str, Any]]) -> str:
    return "\n".join(_section_text_blob(section) for section in sections if isinstance(section, dict)).strip()


def _basic_similarity_priority_rank(section_key: str) -> int:
    try:
        return BASIC_SIMILARITY_REWRITE_PRIORITY.index(section_key)
    except ValueError:
        return len(BASIC_SIMILARITY_REWRITE_PRIORITY)


def _rewrite_overlap_section(
    *,
    section: Dict[str, Any],
    core: Dict[str, Any],
    uniqueness_seed: str,
    attempt: int,
) -> Dict[str, Any]:
    cloned = dict(section)
    blocks = list(cloned.get("blocks") or [])
    if not blocks:
        return cloned
    key = str(cloned.get("key") or "")
    inputs = core.get("inputs") or {}
    city = str(inputs.get("city") or "Not Provided")
    challenge = str(inputs.get("primary_challenge") or "consistency")
    mobile_vibration = int((core.get("mobile") or {}).get("vibration") or 0)
    missing = ", ".join(str(d) for d in (core.get("lo_shu") or {}).get("missing") or []) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    extra_options = [
        f"à¤ªà¤°à¥à¤¸à¤¨à¤²à¤¾à¤‡à¤œà¤¼à¥‡à¤¶à¤¨ à¤¨à¥‹à¤Ÿ: {city} à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤®à¥‡à¤‚ à¤…à¤‚à¤• {mobile_vibration} à¤•à¥‡ à¤¸à¤¾à¤¥ '{challenge}' à¤ªà¤° à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤• à¤«à¥‹à¤•à¤¸ à¤°à¤–à¥‡à¤‚à¥¤",
        f"à¤Šà¤°à¥à¤œà¤¾ à¤«à¥‹à¤•à¤¸ à¤²à¤¾à¤‡à¤¨: missing digits ({missing}) à¤•à¥€ à¤­à¤°à¤ªà¤¾à¤ˆ à¤µà¥à¤¯à¤µà¤¹à¤¾à¤°à¤¿à¤• à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤¸à¥‡ à¤•à¤°à¥‡à¤‚à¥¤",
        "à¤ªà¥à¤°à¤—à¤¤à¤¿ à¤¸à¤‚à¤•à¥‡à¤¤: à¤…à¤—à¤²à¥‡ 21 à¤¦à¤¿à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¦à¥ˆà¤¨à¤¿à¤• à¤›à¥‹à¤Ÿà¥‡ à¤¸à¥à¤§à¤¾à¤° cumulative à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¦à¥‡à¤‚à¤—à¥‡à¥¤",
    ]
    if key == "basic_remedies_table":
        remedy_lines = _basic_remedy_pack_lines(core=core, uniqueness_seed=f"{uniqueness_seed}|{attempt}|remedy")
        extra_options.append(f"à¤¸à¤‚à¤¦à¤°à¥à¤­à¤¿à¤¤ à¤‰à¤ªà¤¾à¤¯: {remedy_lines['digital']}")

    def _replace_value(block_line: str, new_value: str) -> str:
        label, separator, _ = str(block_line).partition(":")
        if not separator:
            return str(block_line)
        return f"{label}: {str(new_value).strip()}"

    mutated = False

    # Summary rows: rewrite only suggestion (third column), keep deterministic field/status unchanged.
    if key == "basic_summary_table_v2":
        rewritten_blocks: List[str] = []
        for idx, block in enumerate(blocks):
            block_text = str(block)
            if block_text.startswith("SUMMARY_ROW"):
                _, _, payload = block_text.partition(":")
                parts = [part.strip() for part in payload.split("||")]
                if len(parts) >= 3:
                    parts[2] = _pick_variant(
                        [
                            "21 à¤¦à¤¿à¤¨ à¤•à¥‡ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¸à¥à¤à¤¾à¤µ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚",
                            f"'{challenge}' à¤¸à¥à¤§à¤¾à¤° à¤•à¥‡ à¤²à¤¿à¤ à¤‡à¤¸ à¤ªà¤‚à¤•à¥à¤¤à¤¿ à¤•à¤¾ à¤¸à¥à¤à¤¾à¤µ à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤• à¤°à¤–à¥‡à¤‚",
                            f"{city} à¤¦à¤¿à¤¨à¤šà¤°à¥à¤¯à¤¾ à¤•à¥‡ à¤…à¤¨à¥à¤¸à¤¾à¤° à¤‡à¤¸ à¤¸à¥à¤§à¤¾à¤° à¤¬à¤¿à¤‚à¤¦à¥ à¤•à¥‹ à¤°à¥‹à¤œ à¤Ÿà¥à¤°à¥ˆà¤• à¤•à¤°à¥‡à¤‚",
                        ],
                        uniqueness_seed,
                        key,
                        attempt,
                        idx,
                        "summary",
                    )
                    block_text = f"SUMMARY_ROW {idx + 1}: {parts[0]} || {parts[1]} || {parts[2]}"
                    mutated = True
            rewritten_blocks.append(block_text)
        cloned["blocks"] = rewritten_blocks
        return cloned

    target_prefixes_by_key: Dict[str, Tuple[str, ...]] = {
        "basic_loshu_grid": ("LOSHU_CONCLUSION:",),
        "basic_life_path_context": ("LIFEPATH_LINE 1:", "LIFEPATH_LINE 2:", "LIFEPATH_LINE 3:"),
        "basic_recommendation": ("VERDICT_BOX:",),
        "basic_suggested_numbers": ("SUGGESTED_INTRO:", "SUGGESTED_REASON"),
        "basic_charging_direction": ("CHARGING_INTRO:", "CHARGING_ROW 3:"),
        "basic_remedies_table": ("REMEDY_COMMENT:", "REMEDY_INTRO:"),
        "basic_key_insight": ("KEY_INSIGHT_P2:", "KEY_INSIGHT_P1:"),
        "basic_upgrade_path": ("NEXTSTEP_CONTEXT:", "NEXTSTEP_CLOSING:"),
        "basic_life_areas": ("LIFE_AREA_ROW",),
        "basic_mobile_energy": ("MOBILE_ENERGY_INSIGHT:",),
    }
    target_prefixes = target_prefixes_by_key.get(key, tuple())

    candidate_indices = [
        idx
        for idx, block in enumerate(blocks)
        if any(str(block).startswith(prefix) for prefix in target_prefixes)
    ]
    if not candidate_indices:
        candidate_indices = [_stable_variant_index(uniqueness_seed, key, attempt, modulo=len(blocks))]

    rewrite_cap = min(2, len(candidate_indices))
    for sequence, index in enumerate(candidate_indices[:rewrite_cap]):
        block = str(blocks[index])
        label, separator, value = block.partition(":")
        if not separator:
            continue
        value_text = value.strip()

        if "||" in value_text:
            parts = [part.strip() for part in value_text.split("||")]
            if len(parts) >= 2:
                parts[-1] = _pick_variant(
                    extra_options,
                    uniqueness_seed,
                    key,
                    attempt,
                    index,
                    sequence,
                    "parts",
                )
                blocks[index] = f"{label}: {' || '.join(parts)}"
                mutated = True
                continue

        blended = _pick_variant(
            [
                value_text,
                f"{value_text} {_pick_variant(extra_options, uniqueness_seed, key, attempt, index, sequence, 'tail')}",
                _pick_variant(extra_options, uniqueness_seed, key, attempt, index, sequence, "full"),
            ],
            uniqueness_seed,
            key,
            attempt,
            index,
            sequence,
            "blend",
        )
        blocks[index] = _replace_value(block, str(blended)[:420])
        mutated = True

    if not mutated:
        fallback_index = _stable_variant_index(uniqueness_seed, key, attempt, "fallback", modulo=len(blocks))
        fallback_block = str(blocks[fallback_index])
        fallback_label, fallback_separator, fallback_value = fallback_block.partition(":")
        if fallback_separator:
            fallback_variant = _pick_variant(extra_options, uniqueness_seed, key, attempt, "fallback-value")
            blocks[fallback_index] = f"{fallback_label}: {str(fallback_value).strip()} {fallback_variant}".strip()[:420]

    cloned["blocks"] = blocks
    return cloned


def _apply_basic_similarity_gate(
    *,
    sections: List[Dict[str, Any]],
    core: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not sections:
        return sections
    if not bool(getattr(settings, "AI_BASIC_UNIQUENESS_GATE_ENABLED", True)):
        return sections

    threshold = float(getattr(settings, "AI_BASIC_UNIQUENESS_GATE_THRESHOLD", 0.80) or 0.80)
    max_passes = max(1, int(getattr(settings, "AI_BASIC_UNIQUENESS_GATE_MAX_PASSES", 2) or 2))

    fingerprint = str(((core.get("inputs") or {}).get("mobile_number") or "")) + "|" + str(core.get("generated_on") or "")
    uniqueness_seed = str((core.get("uniqueness_seed") or fingerprint or "basic-seed"))
    current = [dict(section) for section in sections]

    def _best_reference(current_blob: str) -> Tuple[float, Dict[str, Any] | None]:
        best_score = 0.0
        best_item = None
        for item in BASIC_UNIQUENESS_HISTORY:
            if str(item.get("fingerprint") or "") == fingerprint:
                continue
            score = _normalized_similarity(current_blob, str(item.get("report_blob") or ""))
            if score > best_score:
                best_score = score
                best_item = item
        return best_score, best_item

    for attempt in range(max_passes):
        blob = _report_text_blob(current)
        max_similarity, reference = _best_reference(blob)
        if max_similarity <= (1.0 - threshold) or not reference:
            break

        reference_sections = reference.get("section_blobs") or {}
        scored: List[Tuple[float, int, int, Dict[str, Any]]] = []
        for idx, section in enumerate(current):
            key = str(section.get("key") or "")
            current_text = _section_text_blob(section)
            reference_text = str(reference_sections.get(key) or "")
            score = _normalized_similarity(current_text, reference_text)
            scored.append((score, _basic_similarity_priority_rank(key), idx, section))

        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        section_cap = max(2, int(getattr(settings, "AI_BASIC_UNIQUENESS_GATE_SECTION_CAP", 4) or 4))
        target_indices = {
            idx
            for score, _, idx, _ in scored[:section_cap]
            if score >= 0.72
        }
        if not target_indices:
            break

        rewritten: List[Dict[str, Any]] = []
        changed = False
        for idx, section in enumerate(current):
            if idx in target_indices:
                rewritten.append(
                    _rewrite_overlap_section(
                        section=section,
                        core=core,
                        uniqueness_seed=uniqueness_seed,
                        attempt=attempt + 1,
                    )
                )
                changed = changed or rewritten[-1] != section
            else:
                rewritten.append(section)
        if not changed:
            break
        current = rewritten

    BASIC_UNIQUENESS_HISTORY.append(
        {
            "fingerprint": fingerprint,
            "report_blob": _report_text_blob(current),
            "section_blobs": {
                str(section.get("key") or ""): _section_text_blob(section)
                for section in current
                if isinstance(section, dict)
            },
        }
    )
    return current


def _build_basic_mobile_deterministic_core(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
) -> Dict[str, Any]:
    full_name = str(canonical_normalized_input.get("fullName") or "Not Provided").strip() or "Not Provided"
    first_name = full_name.split()[0] if full_name != "Not Provided" else "User"
    dob_raw = str(canonical_normalized_input.get("dateOfBirth") or "").strip()
    dob_display = _format_dob_display(dob_raw)
    mobile_number = str(canonical_normalized_input.get("mobileNumber") or "").strip()
    city = str(canonical_normalized_input.get("city") or "").strip()
    gender = str(canonical_normalized_input.get("gender") or "").strip().lower()
    primary_challenge_raw = str(
        canonical_normalized_input.get("currentProblem") or canonical_normalized_input.get("focusArea") or ""
    ).strip()
    willingness_to_change = _basic_normalize_willingness(canonical_normalized_input.get("willingnessToChange"))

    mobile_calc = _basic_mobile_vibration_from_number(mobile_number)
    mobile_analysis = numerology_values.get("mobile_analysis") or {}
    mobile_vibration = int(mobile_calc["value"] or 0)
    if not 1 <= mobile_vibration <= 9:
        mobile_vibration = mobile_calc["value"] if 1 <= mobile_calc["value"] <= 9 else 5

    life_path_data = _basic_life_path_from_dob(dob_raw)
    pyth = numerology_values.get("pythagorean") or {}
    life_path = int(pyth.get("life_path_number") or life_path_data["value"] or 0)
    life_path_anchor = (
        life_path_data["anchor"] if life_path <= 0 else (life_path if life_path <= 9 else life_path_data["anchor"])
    )

    frequency = _basic_digit_frequency(mobile_calc["digits"])
    lo_shu = _basic_lo_shu_grid_marks(frequency)
    missing = _basic_missing_digits(frequency)
    repeating = _basic_repeating_digits(frequency)
    present = [digit for digit in range(1, 10) if frequency[digit] > 0]
    present_with_zero = [digit for digit in range(10) if frequency[digit] > 0]

    compatibility = _basic_compatibility_label_v2(
        mobile_vibration,
        life_path_anchor,
        missing_digits=missing,
        repeating_digits=repeating,
    )
    verdict = _basic_verdict_from_rules(
        compatibility_level=compatibility["level"],
        missing_digits=missing,
        repeating_digits=repeating,
    )

    suggestions = _basic_suggested_number_patterns(life_path_anchor, missing)
    planet = _fix_mojibake_text(BASIC_RULE_PLANET_MAP.get(mobile_vibration, BASIC_RULE_PLANET_MAP[5]))
    charging = _fix_mojibake_text(BASIC_RULE_CHARGING_DIRECTION.get(mobile_vibration, BASIC_RULE_CHARGING_DIRECTION[5]))
    gemstone = _fix_mojibake_text(BASIC_RULE_GEMSTONE_MAP.get(mobile_vibration, BASIC_RULE_GEMSTONE_MAP[5]))
    mantra = _fix_mojibake_text(BASIC_RULE_MANTRA_MAP.get(mobile_vibration, BASIC_RULE_MANTRA_MAP[5]))
    yantra = BASIC_RULE_YANTRA_MAP.get(mobile_vibration, "Ã Â¤Â¨Ã Â¤ÂµÃ Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¹ Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°")
    cover_color = BASIC_RULE_COVER_COLOR.get(mobile_vibration, "Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾")
    wallpaper_theme = BASIC_RULE_WALLPAPER_THEME.get(mobile_vibration, "Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€¢Ã Â¥Æ’Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¥Ã Â¥â‚¬Ã Â¤Â®")

    missing_for_consistency = {4, 6, 8}
    has_consistency_gap = bool(missing_for_consistency.intersection(set(missing)))
    inferred_challenge = (
        "Career Focus"
        if has_consistency_gap
        else ("Decision Quality" if 5 not in present else "Consistency")
    )
    primary_challenge = primary_challenge_raw or inferred_challenge
    challenge_lower = primary_challenge.lower()
    challenge_bias = 8 if any(token in challenge_lower for token in ("consist", "career", "focus", "Ã Â¤â€¦Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤")) else 3
    compatibility_base = {"HIGH": 82, "MODERATE": 62, "LOW": 40}.get(compatibility["level"], 58)
    consistency_score = max(20, compatibility_base - (len(missing) * 5) - challenge_bias)
    confidence_score = max(20, compatibility_base + 6 - (5 if 1 in missing else 0))
    finance_score = max(20, compatibility_base - (8 if 8 in missing else 2))
    career_score = max(20, compatibility_base + 4 - (7 if 4 in missing else 1))
    relationship_score = max(20, compatibility_base + (4 if 2 in present else -4))
    decision_score = max(20, compatibility_base + (4 if 5 in present else -5))
    expression_score = max(20, compatibility_base + (5 if 3 in present else -18))

    missing_rudraksha = [
        _fix_mojibake_text(
            BASIC_RULE_RUDRAKSHA_MISSING.get(
                int(digit),
                f"{int(digit)} \u092e\u0941\u0916\u0940 \u0930\u0941\u0926\u094d\u0930\u093e\u0915\u094d\u0937",
            )
        )
        for digit in missing[:3]
    ]
    if has_consistency_gap:
        lo_shu_insight = "Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š 4/6/8 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥â€¹ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
    elif any(item["digit"] == 5 for item in repeating):
        lo_shu_insight = "Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 5 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¨Ã Â¤Â°Ã Â¤Â¾Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤Â¬Ã Â¥â€¡Ã Â¤Â¹Ã Â¤Â¤Ã Â¤Â° Ã Â¤Â¹Ã Â¥â€¹Ã Â¤â€”Ã Â¤Â¾Ã Â¥Â¤"
    else:
        lo_shu_insight = "Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†, Ã Â¤â€¡Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¤â€šÃ Â¤â€”Ã Â¥â€¡Ã Â¥Â¤"

    generated_on = datetime.now(UTC).strftime("%d %B %Y")
    life_path_meanings_hi = {
        1: "Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ, Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â² Ã Â¤â€Ã Â¤Â° Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®-Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥â€¡Ã Â¤Â¶Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        2: "Ã Â¤Â¸Ã Â¤Â¹Ã Â¤Â¯Ã Â¥â€¹Ã Â¤â€”, Ã Â¤Â§Ã Â¥Ë†Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€Ã Â¤Â° Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        3: "Ã Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â­Ã Â¤Â¿Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¤â€šÃ Â¤Å¡Ã Â¤Â¾Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        4: "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¯Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        5: "Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¤Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¤Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤â€¢Ã Â¥â€šÃ Â¤Â²Ã Â¤Â¨Ã Â¤Â¶Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        6: "Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â®Ã Â¥â€¡Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬, Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥â€¡Ã Â¤ÂµÃ Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        7: "Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â²Ã Â¥â€¡Ã Â¤Â·Ã Â¤Â£, Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Ë† Ã Â¤â€Ã Â¤Â° Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Å¡Ã Â¤Â¿Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        8: "Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¬Ã Â¤â€šÃ Â¤Â§Ã Â¤Â¨, Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤â€¢Ã Â¤Â¾Ã Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        9: "Ã Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¾, Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
    }
    primary_missing_digit = missing[0] if missing else (4 if 4 in missing else 5)
    contact_prefix_digit = 4 if 4 in missing else (primary_missing_digit or 5)
    app_folder_limit = 4 if 4 in missing else 5
    nickname_quality = "Leader" if mobile_vibration in {1, 8, 9} else "Focus"
    nickname_base = f"{first_name} {nickname_quality} {contact_prefix_digit}"
    affirmation_base = "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨, Ã Â¤Â¸Ã Â¤Â«Ã Â¤Â²Ã Â¤Â¤Ã Â¤Â¾" if has_consistency_gap else "Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¤Ã Â¤Â¾, Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨, Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿"

    city_hash = sum(ord(ch) for ch in city.lower()) % 3 if city else -1
    dnd_map = {
        -1: ("7:00-8:30 AM", "7:00-9:00 PM"),
        0: ("6:45-8:15 AM", "7:15-9:00 PM"),
        1: ("7:00-8:30 AM", "7:00-9:00 PM"),
        2: ("7:15-8:45 AM", "7:30-9:15 PM"),
    }
    dnd_morning, dnd_evening = dnd_map.get(city_hash, dnd_map[-1])

    verdict_reasoning = (
        f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {mobile_vibration} Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¹ {', '.join(planet['energy'][:2])} Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†, "
        f"Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€¢Ã Â¤Â¿Ã Â¤Â¨ missing digits ({', '.join(str(d) for d in missing) or 'none'}) Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â£ "
        f"'{primary_challenge}' Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š execution consistency Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥â€¹Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
    )

    suggested_number_options = [
        {
            "pattern": pattern,
            "vibration": suggestions["preferred_vibrations"][idx]
            if idx < len(suggestions["preferred_vibrations"])
            else suggestions["preferred_vibrations"][0],
            "key_digits": suggestions["preferred_digits"],
            "reason": "Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° missing-digit Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨",
        }
        for idx, pattern in enumerate(suggestions["patterns"][:3])
    ]

    return _fix_mojibake_text({
        "inputs": {
            "full_name": full_name,
            "first_name": first_name,
            "date_of_birth_raw": dob_raw,
            "date_of_birth_display": dob_display,
            "mobile_number": mobile_number,
            "gender": gender or "other",
            "city": city or "Not Provided",
            "primary_challenge": primary_challenge,
            "willingness_to_change": willingness_to_change,
        },
        "mobile": {
            "digits": mobile_calc["digits"],
            "sum_total": mobile_calc["total"],
            "reduction_steps": mobile_calc["steps"],
            "vibration": mobile_vibration,
        },
        "life_path": {
            "value": life_path if life_path > 0 else life_path_data["value"],
            "anchor": life_path_anchor,
            "steps": life_path_data["steps"],
            "meaning": life_path_meanings_hi.get(life_path_anchor, "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¬Ã Â¤â€šÃ Â¤Â§Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”"),
        },
        "frequency": frequency,
        "lo_shu": {
            "grid": lo_shu,
            "present": present,
            "present_with_zero": present_with_zero,
            "missing": missing,
            "repeating": repeating,
            "insight": lo_shu_insight,
        },
        "planet": planet,
        "compatibility": compatibility,
        "verdict": verdict,
        "suggestions": suggestions,
        "suggested_numbers": suggested_number_options,
        "charging": charging,
        "mantra": mantra,
        "gemstone": gemstone,
        "yantra": yantra,
        "cover_color": cover_color,
        "wallpaper_theme": wallpaper_theme,
        "affirmation_base": affirmation_base,
        "nickname_base": nickname_base,
        "contact_prefix_digit": contact_prefix_digit,
        "dnd_morning": dnd_morning,
        "dnd_evening": dnd_evening,
        "app_folder_limit": app_folder_limit,
        "verdict_reasoning": verdict_reasoning,
        "missing_rudraksha": missing_rudraksha,
        "traits_positive": BASIC_RULE_POSITIVE_ATTRIBUTES.get(mobile_vibration, BASIC_RULE_POSITIVE_ATTRIBUTES[5]),
        "traits_negative": BASIC_RULE_NEGATIVE_ATTRIBUTES.get(mobile_vibration, BASIC_RULE_NEGATIVE_ATTRIBUTES[5]),
        "scores": {
            "consistency": consistency_score,
            "confidence": confidence_score,
            "finance": finance_score,
            "career": career_score,
            "relationships": relationship_score,
            "decision_quality": decision_score,
            "expression": expression_score,
        },
        "generated_on": generated_on,
    })


def _build_basic_mobile_report_sections(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    basic_mobile_core: Dict[str, Any],
    section_narratives: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    core = basic_mobile_core or _build_basic_mobile_deterministic_core(
        canonical_normalized_input=canonical_normalized_input,
        numerology_values=numerology_values,
    )
    inputs = core["inputs"]
    frequency = core["frequency"]
    lo_shu = core["lo_shu"]
    scores = core["scores"]
    suggestions = core["suggestions"]
    charging = core["charging"]
    uniqueness_seed = str(core.get("uniqueness_seed") or "basic-seed")
    section_lookup = {
        str(section.get("sectionKey") or "").strip(): section
        for section in section_narratives
        if isinstance(section, dict)
    }
    ai_mobile = _basic_lookup_section_narrative(section_lookup, "mobile_numerology")
    ai_lo_shu = _basic_lookup_section_narrative(section_lookup, "lo_shu_grid")
    ai_compat = _basic_lookup_section_narrative(section_lookup, "mobile_life_compatibility")
    ai_remedy = _basic_lookup_section_narrative(section_lookup, "remedy")
    ai_closing = _basic_lookup_section_narrative(section_lookup, "closing_summary")
    ai_focus = _basic_lookup_any_section_narrative(section_lookup, ["focus_snapshot", "mobile_numerology", "closing_summary"])
    ai_growth = _basic_lookup_any_section_narrative(section_lookup, ["growth_blueprint", "closing_summary", "remedy"])
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "\u0938\u094d\u0925\u093f\u0930\u0924\u093e"
    mobile_insight_lines = [
        f"\u2022 \u0906\u092a\u0915\u093e \u092e\u094b\u092c\u093e\u0907\u0932 vibration {core['mobile']['vibration']} \u0938\u0902\u091a\u093e\u0930 \u0915\u094b \u0924\u0947\u091c\u093c \u0915\u0930\u0924\u093e \u0939\u0948; \u0924\u0947\u091c\u093c reply \u0938\u0947 \u092a\u0939\u0932\u0947 10 \u0938\u0947\u0915\u0902\u0921 pause \u0932\u0947\u0902\u0964",
        f"\u2022 {planet_name} + {planet_element} \u090a\u0930\u094d\u091c\u093e {energy_hint} \u092e\u094b\u0921 \u092e\u0947\u0902 \u0915\u093e\u092e \u0915\u0930\u0924\u0940 \u0939\u0948; \u092c\u0921\u093c\u0947 decision \u0938\u0947 \u092a\u0939\u0932\u0947 1 \u0932\u093f\u0916\u093f\u0924 checklist \u092c\u0928\u093e\u090f\u0901\u0964",
        f"\u2022 \u0906\u091c \u0915\u093e focus \"{inputs['primary_challenge']}\" \u0939\u0948; \u0938\u0941\u092c\u0939 1 \u0938\u094d\u092a\u0937\u094d\u091f priority \u0932\u093f\u0916\u0947\u0902 \u0914\u0930 \u0926\u093f\u0928 \u092d\u0930 \u0909\u0938\u0940 \u092a\u0930 \u0932\u094c\u091f\u0947\u0902\u0964",
        "\u2022 Key intent: \"\u092e\u0948\u0902 \u0905\u092a\u0928\u0940 \u092e\u094b\u092c\u093e\u0907\u0932 \u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0938\u094d\u092a\u0937\u094d\u0924\u093e \u0914\u0930 \u0928\u093f\u0930\u0902\u0924\u0930\u0924\u093e \u092e\u0947\u0902 \u092c\u0926\u0932 \u0930\u0939\u093e \u0939\u0942\u0901\u0964\"",
    ]
    life_area_rows = _basic_life_area_rows(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_focus or ai_closing,
    )
    effects_positive, effects_negative = _basic_mobile_effects_lines(
        strengths=list(core.get("traits_positive") or []),
        risks=list(core.get("traits_negative") or []),
        missing_digits=list((lo_shu or {}).get("missing") or []),
        repeating_digits=list((lo_shu or {}).get("repeating") or []),
        primary_challenge=str(inputs.get("primary_challenge") or "consistency"),
        ai_narrative=ai_mobile or ai_focus or ai_closing,
        uniqueness_seed=uniqueness_seed,
    )
    verdict_box_text = _basic_verdict_box_text(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_compat,
    )
    suggested_payload = _basic_suggested_numbers_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_growth or ai_closing,
    )
    charging_payload = _basic_charging_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_remedy or ai_closing,
    )
    remedy_lines = _basic_remedy_pack_lines(core=core, uniqueness_seed=uniqueness_seed)
    remedies_payload = _basic_remedies_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        remedy_lines=remedy_lines,
        ai_narrative=ai_remedy or ai_closing,
    )
    tracker_payload = _basic_tracker_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_remedy or ai_closing,
    )
    summary_payload = _basic_summary_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_focus,
    )
    key_insight_payload = _basic_key_insight_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_growth,
    )
    next_steps_payload = _basic_next_steps_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_growth,
    )
    footer_payload = _basic_footer_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_growth,
    )

    repeat_text = ", ".join(f"{item['digit']} ({item['count']}x)" for item in lo_shu["repeating"]) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    missing_text = ", ".join(str(digit) for digit in lo_shu["missing"]) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    present_text = ", ".join(str(digit) for digit in lo_shu["present"]) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    preferred_text = ", ".join(str(item) for item in suggestions["preferred_vibrations"])
    avoid_text = ", ".join(str(item) for item in suggestions["avoid_vibrations"])
    preferred_digits = ", ".join(str(item) for item in suggestions["preferred_digits"])
    verdict_hi = {"KEEP": "à¤°à¤–à¥‡à¤‚", "MANAGE": "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚", "CHANGE": "à¤¬à¤¦à¤²à¥‡à¤‚"}.get(core["verdict"], "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚")
    verdict_en = core["verdict"]
    loshu_challenge_lines = _basic_loshu_challenge_lines(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_lo_shu or ai_focus,
    )
    frequency_row = "|".join(str(frequency[d]) for d in [1, 2, 3, 4, 5, 6, 7, 8, 9, 0])

    lo_shu_grid_block = (
        "Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â\n"
        "Ã¢â€â€š    4    Ã¢â€â€š    9    Ã¢â€â€š    2    Ã¢â€â€š\n"
        f"Ã¢â€â€š    {lo_shu['grid'][4]}    Ã¢â€â€š    {lo_shu['grid'][9]}    Ã¢â€â€š    {lo_shu['grid'][2]}    Ã¢â€â€š\n"
        "Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¤\n"
        "Ã¢â€â€š    3    Ã¢â€â€š    5    Ã¢â€â€š    7    Ã¢â€â€š\n"
        f"Ã¢â€â€š    {lo_shu['grid'][3]}    Ã¢â€â€š    {lo_shu['grid'][5]}    Ã¢â€â€š    {lo_shu['grid'][7]}    Ã¢â€â€š\n"
        "Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¤\n"
        "Ã¢â€â€š    8    Ã¢â€â€š    1    Ã¢â€â€š    6    Ã¢â€â€š\n"
        f"Ã¢â€â€š    {lo_shu['grid'][8]}    Ã¢â€â€š    {lo_shu['grid'][1]}    Ã¢â€â€š    {lo_shu['grid'][6]}    Ã¢â€â€š\n"
        "Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ"
    )

    sections: List[Dict[str, Any]] = [
        {
            "order": 1,
            "key": "basic_mobile_energy",
            "title": "1. Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ | YOUR MOBILE NUMBER ENERGY",
            "subtitle": "Deterministic values",
            "layout": "center_feature",
            "blocks": [
                f"Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â°: {inputs['mobile_number']}",
                f"Ã Â¤Â®Ã Â¥â€šÃ Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ (Vibration): {core['mobile']['vibration']}",
                f"Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¹: {core['planet']['name']}",
                f"Ã Â¤Â¤Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ: {core['planet']['element']}",
                f"Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾: {', '.join(core['planet']['energy'])}",
                f"Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿Ã Â¤â€”Ã Â¤Â¤ Ã Â¤Å¸Ã Â¤Â¿Ã Â¤ÂªÃ Â¥ÂÃ Â¤ÂªÃ Â¤Â£Ã Â¥â‚¬: {ai_mobile or 'Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¯ Ã Â¤â€Ã Â¤Â° Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾-Ã Â¤Â¶Ã Â¥Ë†Ã Â¤Â²Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¥â€¹ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¢Ã Â¤Â°Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤'}",
            ],
        },
        {
            "order": 2,
            "key": "basic_lo_shu_grid",
            "title": "2. Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ | LO SHU GRID",
            "subtitle": "Digit pattern and challenge linkage",
            "layout": "premium_card",
            "blocks": [
                f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â°: {inputs['mobile_number']}",
                f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤â€ Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤ÂªÃ Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿: {frequency_row}",
                f"Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â²Ã Â¥â€°Ã Â¤â€¢:\n{lo_shu_grid_block}\n\nÃ¢Å“â€œ = Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦    Ã¢Å“â€” = Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤",
                f"Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾: {present_text}",
                f"Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾: {missing_text}",
                f"Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾: {repeat_text}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€¢: {inputs['primary_challenge']}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 1: {loshu_challenge_lines[0]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 2: {loshu_challenge_lines[1]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 3: {loshu_challenge_lines[2]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 4: {loshu_challenge_lines[3]}",
                f"Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿Ã Â¤â€”Ã Â¤Â¤ Ã Â¤Å¸Ã Â¤Â¿Ã Â¤ÂªÃ Â¥ÂÃ Â¤ÂªÃ Â¤Â£Ã Â¥â‚¬: {ai_lo_shu or lo_shu['insight']}",
            ],
        },
        {
            "order": 3,
            "key": "basic_positive_negative_impact",
            "title": "3. Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ | HOW YOUR MOBILE NUMBER AFFECTS YOU",
            "subtitle": "3 strengths + 3 challenges",
            "layout": "split_analysis",
            "blocks": [
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ 1: {effects_positive[0]}",
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ 2: {effects_positive[1]}",
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ 3: {effects_positive[2]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ 1: {effects_negative[0]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ 2: {effects_negative[1]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ 3: {effects_negative[2]}",
            ],
        },
        {
            "order": 4,
            "key": "basic_life_path_context",
            "title": "4. Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­ | YOUR LIFE PATH CONTEXT",
            "subtitle": "Life path + compatibility",
            "layout": "comparison_meter",
            "blocks": [
                f"Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¾: {core['life_path']['value']}",
                f"Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤â€¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¥: {core['life_path']['meaning']}",
                f"Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤â€¢Ã Â¥â€šÃ Â¤Â²Ã Â¤Â¤Ã Â¤Â¾: {core['compatibility']['color']} {core['compatibility']['text']} ({core['compatibility']['english']})",
                f"Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿Ã Â¤â€”Ã Â¤Â¤ Ã Â¤Å¸Ã Â¤Â¿Ã Â¤ÂªÃ Â¥ÂÃ Â¤ÂªÃ Â¤Â£Ã Â¥â‚¬: {ai_compat or 'Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨ Ã Â¤Â¸Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤â€¦Ã Â¤Å¡Ã Â¥ÂÃ Â¤â€ºÃ Â¤Â¾ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ Ã Â¤Â¦Ã Â¥â€¡Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤'}",
            ],
        },
        {
            "order": 5,
            "key": "basic_life_area_impact",
            "title": "5. Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“ Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¥â€¡Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â°Ã Â¥â€¹Ã Â¤â€š Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ | IMPACT ON KEY LIFE AREAS",
            "subtitle": f"Primary challenge: {inputs['primary_challenge']}",
            "layout": "four_card_grid",
            "blocks": [
                f"LIFE_AREA_FOCUS: {inputs['primary_challenge']}",
                f"LIFE_AREA_ROW 1: {life_area_rows[0]['area']} | {life_area_rows[0]['impact']} | {life_area_rows[0]['meaning']}",
                f"LIFE_AREA_ROW 2: {life_area_rows[1]['area']} | {life_area_rows[1]['impact']} | {life_area_rows[1]['meaning']}",
                f"LIFE_AREA_ROW 3: {life_area_rows[2]['area']} | {life_area_rows[2]['impact']} | {life_area_rows[2]['meaning']}",
                f"LIFE_AREA_ROW 4: {life_area_rows[3]['area']} | {life_area_rows[3]['impact']} | {life_area_rows[3]['meaning']}",
                f"LIFE_AREA_ROW 5: {life_area_rows[4]['area']} | {life_area_rows[4]['impact']} | {life_area_rows[4]['meaning']}",
                f"LIFE_AREA_ROW 6: {life_area_rows[5]['area']} | {life_area_rows[5]['impact']} | {life_area_rows[5]['meaning']}",
            ],
        },
        {
            "order": 6,
            "key": "basic_keep_change_verdict",
            "title": "6. Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤Â¸Ã Â¤Â¿Ã Â¤Â«Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¶ | MOBILE NUMBER RECOMMENDATION",
            "subtitle": "Keep / Manage / Change",
            "layout": "closing_reflection",
            "blocks": [
                f"VERDICT_BOX:\n{verdict_box_text}",
                f"VERDICT_COMMENT: {ai_closing or '21-à¤¦à¤¿à¤µà¤¸à¥€à¤¯ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤•à¥‡ à¤¬à¤¾à¤¦ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¸à¤®à¥€à¤•à¥à¤·à¤¾ à¤•à¤°à¥‡à¤‚à¥¤'}",
            ],
        },
    ]

    if inputs["willingness_to_change"] != "no":
        sections.append(
            {
                "order": 7,
                "key": "basic_suggested_numbers",
                "title": "7. Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂÃ Â¤Â¾Ã Â¤Â Ã Â¤â€”Ã Â¤Â Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° | SUGGESTED MOBILE NUMBERS",
                "subtitle": "3 deterministic options",
                "layout": "triad_cards",
                "blocks": [
                    f"SUGGESTED_INTRO: {suggested_payload['intro']}",
                    f"SUGGESTED_OPTION 1: {suggested_payload['options'][0]['title']} || {suggested_payload['options'][0]['pattern']} || {suggested_payload['options'][0]['vibration']} || {suggested_payload['options'][0]['key_digits']} || {suggested_payload['options'][0]['fills']} || {suggested_payload['options'][0]['reason']}",
                    f"SUGGESTED_OPTION 2: {suggested_payload['options'][1]['title']} || {suggested_payload['options'][1]['pattern']} || {suggested_payload['options'][1]['vibration']} || {suggested_payload['options'][1]['key_digits']} || {suggested_payload['options'][1]['fills']} || {suggested_payload['options'][1]['reason']}",
                    f"SUGGESTED_OPTION 3: {suggested_payload['options'][2]['title']} || {suggested_payload['options'][2]['pattern']} || {suggested_payload['options'][2]['vibration']} || {suggested_payload['options'][2]['key_digits']} || {suggested_payload['options'][2]['fills']} || {suggested_payload['options'][2]['reason']}",
                    f"SUGGESTED_STEP 1: {suggested_payload['steps'][0]}",
                    f"SUGGESTED_STEP 2: {suggested_payload['steps'][1]}",
                    f"SUGGESTED_STEP 3: {suggested_payload['steps'][2]}",
                    f"SUGGESTED_STEP 4: {suggested_payload['steps'][3]}",
                    f"SUGGESTED_STEP 5: {suggested_payload['steps'][4]}",
                ],
            }
        )

    sections.extend(
        [
            {
                "order": 8,
                "key": "basic_charging_direction",
            "title": "8. Ã Â¤Å¡Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ | CHARGING YOUR MOBILE NUMBER",
            "subtitle": "Direction-day-time-method",
            "layout": "split_insight",
            "blocks": [
                f"CHARGING_INTRO: {charging_payload['intro']}",
                f"CHARGING_ROW 1: {charging_payload['direction_label']} | {charging_payload['direction_value']}",
                f"CHARGING_ROW 2: {charging_payload['time_label']} | {charging_payload['time_value']}",
                f"CHARGING_ROW 3: {charging_payload['how_label']} | {charging_payload['how_value']}",
            ],
        },
            {
                "order": 9,
                "key": "basic_remedies_table",
                "title": "9. Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¯ | REMEDIES FOR YOUR CURRENT NUMBER",
                "subtitle": "Spiritual + Physical + Digital setup",
                "layout": "remedy_cards",
                "blocks": [
                    f"REMEDY_INTRO: {remedies_payload['intro']}",
                    f"REMEDY_SP_TITLE: {remedies_payload['spiritual_title']}",
                    *[
                        f"REMEDY_SP_ROW {idx}: {row['remedy']} || {row['action']} || {row['frequency']}"
                        for idx, row in enumerate(remedies_payload["spiritual_rows"], start=1)
                    ],
                    f"REMEDY_DG_TITLE: {remedies_payload['digital_title']}",
                    *[
                        f"REMEDY_DG_ROW {idx}: {row['remedy']} || {row['action']} || {row['why']}"
                        for idx, row in enumerate(remedies_payload["digital_rows"], start=1)
                    ],
                    f"REMEDY_SETUP_TITLE: {remedies_payload['setup_title']}",
                    *[
                        f"REMEDY_SETUP_ROW {idx}: {row['item']} || {row['recommendation']}"
                        for idx, row in enumerate(remedies_payload["setup_rows"], start=1)
                    ],
                    f"REMEDY_RESET_TITLE: {remedies_payload['reset_title']}",
                    *[
                        f"REMEDY_RESET_ROW {idx}: {row['week']} || {row['actions']}"
                        for idx, row in enumerate(remedies_payload["reset_rows"], start=1)
                    ],
                    f"REMEDY_CHECK_TITLE: {remedies_payload['check_title']}",
                    *[
                        f"REMEDY_CHECK {idx}: {line}"
                        for idx, line in enumerate(remedies_payload["checklist"], start=1)
                    ],
                    f"REMEDY_COMMENT: {ai_remedy or remedies_payload['comment'] or 'à¤‰à¤ªà¤¾à¤¯à¥‹à¤‚ à¤•à¥‹ à¤•à¤® à¤¸à¥‡ à¤•à¤® 21 à¤¦à¤¿à¤¨ à¤¨à¤¿à¤¯à¤®à¤¿à¤¤ à¤°à¥‚à¤ª à¤¸à¥‡ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤'}",
                ],
            },
            {
                "order": 10,
                "key": "basic_21_day_tracker",
                "title": "10. 21-Ã Â¤Â¦Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¸Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Å¸Ã Â¥ÂÃ Â¤Â°Ã Â¥Ë†Ã Â¤â€¢Ã Â¤Â° | 21-DAY REMEDY TRACKER",
                "subtitle": "Week-wise plan",
                "layout": "timeline_strategy",
                "blocks": [
                    f"TRACKER_ROW 1: {tracker_payload['rows'][0]['week']} || {tracker_payload['rows'][0]['task']} || {tracker_payload['rows'][0]['status']}",
                    f"TRACKER_ROW 2: {tracker_payload['rows'][1]['week']} || {tracker_payload['rows'][1]['task']} || {tracker_payload['rows'][1]['status']}",
                    f"TRACKER_ROW 3: {tracker_payload['rows'][2]['week']} || {tracker_payload['rows'][2]['task']} || {tracker_payload['rows'][2]['status']}",
                ],
            },
            {
                "order": 11,
                "key": "basic_summary_table_v2",
                "title": "11. Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¶ | SUMMARY",
                "subtitle": "Current vs recommended",
                "layout": "four_card_grid",
                "blocks": [
                    f"SUMMARY_ROW 1: {summary_payload['rows'][0]['field']} || {summary_payload['rows'][0]['status']} || {summary_payload['rows'][0]['suggestion']}",
                    f"SUMMARY_ROW 2: {summary_payload['rows'][1]['field']} || {summary_payload['rows'][1]['status']} || {summary_payload['rows'][1]['suggestion']}",
                    f"SUMMARY_ROW 3: {summary_payload['rows'][2]['field']} || {summary_payload['rows'][2]['status']} || {summary_payload['rows'][2]['suggestion']}",
                    f"SUMMARY_ROW 4: {summary_payload['rows'][3]['field']} || {summary_payload['rows'][3]['status']} || {summary_payload['rows'][3]['suggestion']}",
                    f"SUMMARY_ROW 5: {summary_payload['rows'][4]['field']} || {summary_payload['rows'][4]['status']} || {summary_payload['rows'][4]['suggestion']}",
                    f"SUMMARY_ROW 6: {summary_payload['rows'][5]['field']} || {summary_payload['rows'][5]['status']} || {summary_payload['rows'][5]['suggestion']}",
                    f"SUMMARY_ROW 7: {summary_payload['rows'][6]['field']} || {summary_payload['rows'][6]['status']} || {summary_payload['rows'][6]['suggestion']}",
                ],
            },
            {
                "order": 12,
                "key": "basic_key_insight",
                "title": "12. Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¦Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥Æ’Ã Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¿ | YOUR KEY INSIGHT",
                "subtitle": "One-line synthesis",
                "layout": "main_card_plus_strips",
                "blocks": [
                    f"KEY_INSIGHT_P1: {key_insight_payload['p1']}",
                    f"KEY_INSIGHT_P2: {key_insight_payload['p2']}",
                ],
            },
            {
                "order": 13,
                "key": "basic_upgrade_path",
                "title": "13. Ã Â¤â€¦Ã Â¤â€”Ã Â¤Â²Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¦Ã Â¤Â® | NEXT STEPS",
                "subtitle": "Upgrade path",
                "layout": "split_analysis",
                "blocks": [
                    f"NEXTSTEP_ROW 1: {next_steps_payload['rows'][0]['if_you_want']} || {next_steps_payload['rows'][0]['upgrade_to']}",
                    f"NEXTSTEP_ROW 2: {next_steps_payload['rows'][1]['if_you_want']} || {next_steps_payload['rows'][1]['upgrade_to']}",
                    f"NEXTSTEP_THANKS: {next_steps_payload['thanks']}",
                    f"NEXTSTEP_CONTEXT: {next_steps_payload['context']}",
                    f"NEXTSTEP_OPTION 1: {next_steps_payload['options'][0]}",
                    f"NEXTSTEP_OPTION 2: {next_steps_payload['options'][1]}",
                    f"NEXTSTEP_OPTION 3: {next_steps_payload['options'][2]}",
                    f"NEXTSTEP_CLOSING: {next_steps_payload['closing']}",
                    f"NEXTSTEP_FOOTER 1: {next_steps_payload['footer_lines'][0]}",
                    f"NEXTSTEP_FOOTER 2: {next_steps_payload['footer_lines'][1]}",
                    f"NEXTSTEP_FOOTER 3: {next_steps_payload['footer_lines'][2]}",
                ],
            },
            {
                "order": 14,
                "key": "basic_footer",
                "title": "14. Ã Â¤Â«Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â° | FOOTER",
                "subtitle": "Identity stamp",
                "layout": "closing_reflection",
                "blocks": [
                    footer_payload["report_type_line"],
                    footer_payload["generated_for_line"],
                    footer_payload["date_line"],
                    footer_payload["gratitude_line"],
                    footer_payload["tagline_line"],
                ],
            },
            {
                "order": 15,
                "key": "basic_upsell_page",
                "title": "Upgrade Page | Ã Â¤â€¦Ã Â¤ÂªÃ Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥â€¡Ã Â¤Â¡ Ã Â¤â€˜Ã Â¤Â«Ã Â¤Â°",
                "subtitle": "Grow from Basic to Standard/Premium",
                "layout": "center_feature",
                "blocks": [
                    "Standard Report: Name Numerology + Destiny + Soul Urge + Personality + Name Remedies",
                    "Premium Report: Complete Life Blueprint with 34 premium intelligence sections",
                    "Ã Â¤â€¢Ã Â¤Â¸Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â® Ã Â¤â€˜Ã Â¤Â«Ã Â¤Â°: Ã Â¤â€¦Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤ÂªÃ Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥â€¡Ã Â¤Â¡ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤â€¦Ã Â¤ÂªÃ Â¤Â¨Ã Â¥â‚¬ Ã Â¤Â°Ã Â¤Â£Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â¤Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤ÂÃ Â¤ÂÃ Â¥Â¤",
                ],
            },
        ]
    )

    ordered: List[Dict[str, Any]] = []
    for idx, section in enumerate(sections, start=1):
        cloned = dict(section)
        cloned["order"] = idx
        if cloned["key"] != "basic_upsell_page":
            title_text = str(cloned.get("title") or "")
            if ". " in title_text:
                cloned["title"] = f"{idx}. {title_text.split('. ', 1)[1]}"
        ordered.append(cloned)
    return _fix_mojibake_text(ordered)


def _basic_reduce_compatibility_level(level: str) -> str:
    normalized = str(level or "MODERATE").upper()
    if normalized == "HIGH":
        return "MODERATE"
    if normalized == "MODERATE":
        return "LOW"
    return "LOW"


def _basic_repeating_count(repeating_digits: List[Dict[str, int]], digit: int) -> int:
    for item in repeating_digits:
        try:
            if int(item.get("digit") or -1) == digit:
                return int(item.get("count") or 0)
        except (TypeError, ValueError):
            continue
    return 0


def _format_ampm_window(start_minutes: int, duration_minutes: int) -> str:
    start_minutes = max(0, min(start_minutes, 23 * 60 + 59))
    end_minutes = max(0, min(start_minutes + duration_minutes, 23 * 60 + 59))

    def _fmt(total_minutes: int) -> Tuple[int, int, str]:
        hour_24, minute = divmod(total_minutes, 60)
        suffix = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12
        if hour_12 == 0:
            hour_12 = 12
        return hour_12, minute, suffix

    s_h, s_m, s_ap = _fmt(start_minutes)
    e_h, e_m, e_ap = _fmt(end_minutes)
    if s_ap == e_ap:
        return f"{s_h}:{s_m:02d}-{e_h}:{e_m:02d} {s_ap}"
    return f"{s_h}:{s_m:02d} {s_ap}-{e_h}:{e_m:02d} {e_ap}"


def _basic_dynamic_dnd_windows(*, full_name: str, city: str, mobile_number: str) -> Tuple[str, str]:
    seed = f"{full_name.strip().lower()}|{city.strip().lower()}|{str(mobile_number)[-4:]}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()

    morning_offset = int(digest[:6], 16) % 76  # 06:30 -> 07:45
    morning_duration = 75 + (int(digest[6:10], 16) % 31)  # 75-105 mins
    evening_offset = int(digest[10:16], 16) % 91  # 18:30 -> 20:00
    evening_duration = 90 + (int(digest[16:20], 16) % 46)  # 90-135 mins

    morning_window = _format_ampm_window((6 * 60 + 30) + morning_offset, morning_duration)
    evening_window = _format_ampm_window((18 * 60 + 30) + evening_offset, evening_duration)
    return morning_window, evening_window


def _basic_primary_rudraksha(missing_digits: List[int]) -> str:
    default_label = f"5 \u092e\u0941\u0916\u0940 \u0930\u0941\u0926\u094d\u0930\u093e\u0915\u094d\u0937"
    if not missing_digits:
        return _fix_mojibake_text(default_label)
    primary_missing = int(missing_digits[0])
    raw = BASIC_RULE_RUDRAKSHA_MISSING.get(
        primary_missing,
        f"{primary_missing} \u092e\u0941\u0916\u0940 \u0930\u0941\u0926\u094d\u0930\u093e\u0915\u094d\u0937",
    )
    return _fix_mojibake_text(raw)


def _basic_compatibility_label_v2(
    mobile_vibration: int,
    life_path_anchor: int,
    missing_digits: List[int] | None = None,
    repeating_digits: List[Dict[str, int]] | None = None,
) -> Dict[str, str]:
    matrix = BASIC_RULE_COMPATIBILITY_MATRIX.get(life_path_anchor) or BASIC_RULE_COMPATIBILITY_MATRIX[5]
    if mobile_vibration in matrix["compatible"]:
        level = "HIGH"
    elif mobile_vibration in matrix["neutral"]:
        level = "MODERATE"
    else:
        level = "LOW"

    missing = set(missing_digits or [])
    if 4 in missing:
        level = _basic_reduce_compatibility_level(level)

    labels = {
        "HIGH": {"level": "HIGH", "color": "GREEN", "text": "à¤‰à¤šà¥à¤š", "english": "High"},
        "MODERATE": {"level": "MODERATE", "color": "YELLOW", "text": "à¤®à¤§à¥à¤¯à¤®", "english": "Moderate"},
        "LOW": {"level": "LOW", "color": "RED", "text": "à¤¨à¤¿à¤®à¥à¤¨", "english": "Low"},
    }
    return labels.get(level, labels["MODERATE"])


def _basic_verdict_v2(*, compatibility_level: str, missing_digits: List[int], repeating_digits: List[Dict[str, int]]) -> str:
    missing_4 = 4 in set(missing_digits or [])
    missing_critical = len(missing_digits or []) >= 2

    if compatibility_level == "LOW" or (missing_4 and missing_critical):
        return "CHANGE"
    if missing_4 or compatibility_level == "MODERATE":
        return "MANAGE"
    return "KEEP"


def _build_basic_mobile_deterministic_core_v2(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    problem_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    full_name = str(canonical_normalized_input.get("fullName") or "Not Provided").strip() or "Not Provided"
    first_name = full_name.split()[0] if full_name != "Not Provided" else "User"
    dob_raw = str(canonical_normalized_input.get("dateOfBirth") or "").strip()
    mobile_number = str(canonical_normalized_input.get("mobileNumber") or "").strip()
    gender = str(canonical_normalized_input.get("gender") or "other").strip().lower()
    city = str(canonical_normalized_input.get("city") or "").strip() or "Not Provided"
    challenge = str(
        canonical_normalized_input.get("currentProblem")
        or canonical_normalized_input.get("focusArea")
        or "consistency"
    ).strip() or "consistency"
    willingness_to_change = _basic_normalize_willingness(canonical_normalized_input.get("willingnessToChange"))
    resolved_problem_profile = problem_profile if isinstance(problem_profile, dict) else {}
    problem_bucket = _basic_challenge_bucket(challenge, problem_profile=resolved_problem_profile)

    mobile_calc = _basic_mobile_vibration_from_number(mobile_number)
    mobile_analysis = numerology_values.get("mobile_analysis") or {}
    # Always use reduced single digit (1-9) from current mobile digits.
    mobile_vibration = int(mobile_calc.get("value") or 0)
    if not 1 <= mobile_vibration <= 9:
        mobile_vibration = 5

    life_path_data = _basic_life_path_from_dob(dob_raw)
    pyth = numerology_values.get("pythagorean") or {}
    life_path_value = int(pyth.get("life_path_number") or life_path_data.get("value") or 0)
    if life_path_value <= 0:
        life_path_value = int(life_path_data.get("value") or 5)
    life_path_anchor = int(life_path_data.get("anchor") or (life_path_value if life_path_value <= 9 else 5))

    frequency = _basic_digit_frequency(mobile_calc.get("digits") or [])
    lo_shu_grid = _basic_lo_shu_grid_marks(frequency)
    missing_digits = _basic_missing_digits(frequency)
    repeating_digits = _basic_repeating_digits(frequency)
    present_digits = [digit for digit in range(1, 10) if frequency.get(digit, 0) > 0]
    present_with_zero = [digit for digit in range(10) if frequency.get(digit, 0) > 0]

    compatibility = _basic_compatibility_label_v2(
        mobile_vibration,
        life_path_anchor,
        missing_digits=missing_digits,
        repeating_digits=repeating_digits,
    )
    verdict = _basic_verdict_v2(
        compatibility_level=compatibility["level"],
        missing_digits=missing_digits,
        repeating_digits=repeating_digits,
    )

    suggestions = _basic_suggested_number_patterns(life_path_anchor, missing_digits)
    planet = BASIC_RULE_PLANET_MAP.get(mobile_vibration, BASIC_RULE_PLANET_MAP[5])
    charging = BASIC_RULE_CHARGING_DIRECTION.get(mobile_vibration, BASIC_RULE_CHARGING_DIRECTION[5])
    gemstone = BASIC_RULE_GEMSTONE_MAP.get(mobile_vibration, BASIC_RULE_GEMSTONE_MAP[5])
    mantra = BASIC_RULE_MANTRA_MAP.get(mobile_vibration, BASIC_RULE_MANTRA_MAP[5])
    yantra = BASIC_RULE_YANTRA_MAP.get(mobile_vibration, "Ã Â¤Â¨Ã Â¤ÂµÃ Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¹ Ã Â¤Â¯Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°")
    cover_color = BASIC_RULE_COVER_COLOR.get(mobile_vibration, "Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾")
    wallpaper_theme = BASIC_RULE_WALLPAPER_THEME.get(mobile_vibration, "Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€¢Ã Â¥Æ’Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¥Ã Â¥â‚¬Ã Â¤Â®")

    missing_for_consistency = {4, 6, 8}
    has_consistency_gap = bool(missing_for_consistency.intersection(set(missing_digits)))
    if has_consistency_gap:
        lo_shu_insight = "Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š 4/6/8 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â®Ã Â¥â‚¬ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¦Ã Â¤Â¬Ã Â¤Â¾Ã Â¤Âµ Ã Â¤Â¬Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
    elif any(item.get("digit") == 5 for item in repeating_digits):
        lo_shu_insight = "Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ 5 Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â¨Ã Â¤Â°Ã Â¤Â¾Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤Å“Ã Â¥â€¹Ã Â¤Â¡Ã Â¤Â¼Ã Â¤Â¨Ã Â¤Â¾ Ã Â¤â€¦Ã Â¤Â¨Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤"
    else:
        lo_shu_insight = "Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Â¹Ã Â¥Ë†; Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯Ã Â¤Â¤Ã Â¤Æ’ Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¦Ã Â¥Ë†Ã Â¤Â¨Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤ÂªÃ Â¤Â° Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­Ã Â¤Â° Ã Â¤Â°Ã Â¤Â¹Ã Â¥â€¡Ã Â¤â€šÃ Â¤â€”Ã Â¥â€¡Ã Â¥Â¤"

    repeat_map = {int(item.get("digit") or 0): int(item.get("count") or 0) for item in repeating_digits}
    repeating_8_high = int(repeat_map.get(8, 0)) >= 3
    consistency_score = 28 if 4 in missing_digits else 56
    confidence_score = 82 if 1 in missing_digits else 56
    finance_score = 28 if 4 in missing_digits else 56
    career_score = 28 if repeating_8_high else 56
    relationships_score = 56 if 2 in present_digits else 46
    decision_score = 28 if (4 in missing_digits or repeating_8_high) else 56
    expression_score = 28 if 3 in missing_digits else 56

    lo_shu = _basic_enforce_lo_shu_consistency(
        frequency=frequency,
        lo_shu={
            "grid": lo_shu_grid,
            "present": present_digits,
            "present_with_zero": present_with_zero,
            "missing": missing_digits,
            "repeating": repeating_digits,
            "insight": lo_shu_insight,
        },
    )
    missing_digits = list(lo_shu.get("missing") or [])
    repeating_digits = list(lo_shu.get("repeating") or [])
    present_digits = list(lo_shu.get("present") or [])
    present_with_zero = list(lo_shu.get("present_with_zero") or [])
    lo_shu_grid = dict(lo_shu.get("grid") or {})

    compatibility = _basic_compatibility_label_v2(
        mobile_vibration,
        life_path_anchor,
        missing_digits=missing_digits,
        repeating_digits=repeating_digits,
    )
    verdict = _basic_verdict_v2(
        compatibility_level=compatibility["level"],
        missing_digits=missing_digits,
        repeating_digits=repeating_digits,
    )

    missing_rudraksha = [
        _fix_mojibake_text(
            BASIC_RULE_RUDRAKSHA_MISSING.get(
                int(digit),
                f"{int(digit)} \u092e\u0941\u0916\u0940 \u0930\u0941\u0926\u094d\u0930\u093e\u0915\u094d\u0937",
            )
        )
        for digit in missing_digits
    ]
    primary_missing_digit = missing_digits[0] if missing_digits else 5
    primary_rudraksha = _basic_primary_rudraksha(missing_digits)
    contact_prefix_digit = 4 if 4 in missing_digits else primary_missing_digit
    app_folder_limit = 4 if 4 in missing_digits else 5
    nickname_quality = "Leader" if mobile_vibration in {1, 8, 9} else "Focus"
    nickname_base = f"{first_name} {nickname_quality} {contact_prefix_digit}"
    affirmation_base = "Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â°Ã Â¤Â¤Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨, Ã Â¤Â¸Ã Â¤Â«Ã Â¤Â²Ã Â¤Â¤Ã Â¤Â¾" if has_consistency_gap else "Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¤Ã Â¤Â¾, Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨, Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤â€”Ã Â¤Â¤Ã Â¤Â¿"
    dnd_morning, dnd_evening = _basic_dynamic_dnd_windows(
        full_name=full_name,
        city=city,
        mobile_number=mobile_number,
    )

    verdict_reasoning = (
        f"à¤…à¤‚à¤• {mobile_vibration} à¤†à¤ªà¤•à¥€ à¤®à¥à¤–à¥à¤¯ à¤Šà¤°à¥à¤œà¤¾ ({', '.join(planet['energy'][:2])}) à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ, "
        f"à¤²à¥‡à¤•à¤¿à¤¨ à¤…à¤¨à¥à¤ªà¤¸à¥à¤¥à¤¿à¤¤ à¤…à¤‚à¤• ({', '.join(str(d) for d in missing_digits) or 'none'}) à¤”à¤° à¤¦à¥‹à¤¹à¤°à¤¾à¤µ à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨ "
        f"'{challenge}' à¤šà¥à¤¨à¥Œà¤¤à¥€ à¤®à¥‡à¤‚ à¤¸à¥à¤¥à¤¿à¤° à¤•à¥à¤°à¤¿à¤¯à¤¾à¤¨à¥à¤µà¤¯à¤¨ à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤"
    )

    suggested_number_options = [
        {
            "pattern": pattern,
            "vibration": suggestions["preferred_vibrations"][idx]
            if idx < len(suggestions["preferred_vibrations"])
            else suggestions["preferred_vibrations"][0],
            "key_digits": suggestions["preferred_digits"],
            "reason": "Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¸Ã Â¤â€šÃ Â¤â€”Ã Â¤Â¤Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° missing-digit Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨",
        }
        for idx, pattern in enumerate(suggestions["patterns"][:3])
    ]

    seed_payload = "|".join(
        [
            full_name,
            dob_raw,
            mobile_number,
            challenge,
            city,
            willingness_to_change,
            str(mobile_vibration),
            str(life_path_anchor),
        ]
    )
    uniqueness_seed = hashlib.sha256(seed_payload.encode("utf-8")).hexdigest()[:16]

    life_path_meanings_hi = {
        1: "Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ, Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â² Ã Â¤â€Ã Â¤Â° Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®-Ã Â¤Â¨Ã Â¤Â¿Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥â€¡Ã Â¤Â¶Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        2: "Ã Â¤Â¸Ã Â¤Â¹Ã Â¤Â¯Ã Â¥â€¹Ã Â¤â€”, Ã Â¤Â§Ã Â¥Ë†Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€Ã Â¤Â° Ã Â¤Â­Ã Â¤Â¾Ã Â¤ÂµÃ Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        3: "Ã Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤â€¦Ã Â¤Â­Ã Â¤Â¿Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¤â€šÃ Â¤Å¡Ã Â¤Â¾Ã Â¤Â° Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        4: "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â°Ã Â¤Å¡Ã Â¤Â¨Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¾Ã Â¤Â¸Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â° Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¯Ã Â¤Â¾Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¯Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        5: "Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¤Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¤Ã Â¤Â¾, Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤â€¢Ã Â¥â€šÃ Â¤Â²Ã Â¤Â¨Ã Â¤Â¶Ã Â¥â‚¬Ã Â¤Â²Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â°Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        6: "Ã Â¤Å“Ã Â¤Â¿Ã Â¤Â®Ã Â¥ÂÃ Â¤Â®Ã Â¥â€¡Ã Â¤Â¦Ã Â¤Â¾Ã Â¤Â°Ã Â¥â‚¬, Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¨ Ã Â¤â€Ã Â¤Â° Ã Â¤Â¸Ã Â¥â€¡Ã Â¤ÂµÃ Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        7: "Ã Â¤ÂµÃ Â¤Â¿Ã Â¤Â¶Ã Â¥ÂÃ Â¤Â²Ã Â¥â€¡Ã Â¤Â·Ã Â¤Â£, Ã Â¤â€”Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Ë† Ã Â¤â€Ã Â¤Â° Ã Â¤â€ Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤Å¡Ã Â¤Â¿Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        8: "Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¬Ã Â¤â€šÃ Â¤Â§Ã Â¤Â¨, Ã Â¤Â®Ã Â¤Â¹Ã Â¤Â¤Ã Â¥ÂÃ Â¤ÂµÃ Â¤Â¾Ã Â¤â€¢Ã Â¤Â¾Ã Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¤Â¾ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
        9: "Ã Â¤â€¢Ã Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¾, Ã Â¤Â¨Ã Â¥â€¡Ã Â¤Â¤Ã Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Âµ Ã Â¤â€Ã Â¤Â° Ã Â¤ÂªÃ Â¥â€šÃ Â¤Â°Ã Â¥ÂÃ Â¤Â£Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”",
    }

    return {
        "inputs": {
            "full_name": full_name,
            "first_name": first_name,
            "date_of_birth_raw": dob_raw,
            "date_of_birth_display": _format_dob_display(dob_raw),
            "mobile_number": mobile_number,
            "gender": gender,
            "city": city,
            "primary_challenge": challenge,
            "problem_bucket": problem_bucket,
            "problem_category": str(resolved_problem_profile.get("category") or ""),
            "willingness_to_change": willingness_to_change,
        },
        "mobile": {
            "digits": mobile_calc["digits"],
            "sum_total": mobile_calc["total"],
            "reduction_steps": mobile_calc["steps"],
            "vibration": mobile_vibration,
        },
        "life_path": {
            "value": life_path_value,
            "anchor": life_path_anchor,
            "steps": life_path_data["steps"],
            "meaning": life_path_meanings_hi.get(life_path_anchor, "Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¤Ã Â¥ÂÃ Â¤Â²Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â¬Ã Â¤â€šÃ Â¤Â§Ã Â¤Â¨ Ã Â¤â€¢Ã Â¤Â¾ Ã Â¤Â®Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤â€”"),
        },
        "frequency": frequency,
        "lo_shu": {
            "grid": lo_shu_grid,
            "present": present_digits,
            "present_with_zero": present_with_zero,
            "missing": missing_digits,
            "repeating": repeating_digits,
            "insight": lo_shu_insight,
        },
        "planet": planet,
        "compatibility": compatibility,
        "verdict": verdict,
        "suggestions": suggestions,
        "suggested_numbers": suggested_number_options,
        "charging": charging,
        "mantra": mantra,
        "gemstone": gemstone,
        "yantra": yantra,
        "cover_color": cover_color,
        "wallpaper_theme": wallpaper_theme,
        "affirmation_base": affirmation_base,
        "nickname_base": nickname_base,
        "contact_prefix_digit": contact_prefix_digit,
        "dnd_morning": dnd_morning,
        "dnd_evening": dnd_evening,
        "app_folder_limit": app_folder_limit,
        "verdict_reasoning": verdict_reasoning,
        "missing_rudraksha": missing_rudraksha,
        "primary_rudraksha": primary_rudraksha,
        "traits_positive": BASIC_RULE_POSITIVE_ATTRIBUTES.get(mobile_vibration, BASIC_RULE_POSITIVE_ATTRIBUTES[5]),
        "traits_negative": BASIC_RULE_NEGATIVE_ATTRIBUTES.get(mobile_vibration, BASIC_RULE_NEGATIVE_ATTRIBUTES[5]),
        "scores": {
            "consistency": consistency_score,
            "confidence": confidence_score,
            "finance": finance_score,
            "career": career_score,
            "relationships": relationships_score,
            "decision_quality": decision_score,
            "expression": expression_score,
        },
        "generated_on": datetime.now(UTC).strftime("%d %B %Y"),
        "uniqueness_seed": uniqueness_seed,
        "problem_profile": resolved_problem_profile,
    }


def _build_basic_mobile_report_sections_v2(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    basic_mobile_core: Dict[str, Any],
    section_narratives: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    core = basic_mobile_core or _build_basic_mobile_deterministic_core_v2(
        canonical_normalized_input=canonical_normalized_input,
        numerology_values=numerology_values,
    )
    inputs = core["inputs"]
    frequency = core["frequency"]
    lo_shu = core["lo_shu"]
    scores = core["scores"]
    suggestions = core["suggestions"]
    charging = core["charging"]
    uniqueness_seed = str(core.get("uniqueness_seed") or "basic-seed")
    remedy_lines = _basic_remedy_pack_lines(core=core, uniqueness_seed=uniqueness_seed)

    section_lookup = {
        str(section.get("sectionKey") or "").strip(): section
        for section in section_narratives
        if isinstance(section, dict)
    }
    ai_mobile = _basic_lookup_section_narrative(section_lookup, "mobile_numerology")
    ai_lo_shu = _basic_lookup_section_narrative(section_lookup, "lo_shu_grid")
    ai_compat = _basic_lookup_section_narrative(section_lookup, "mobile_life_compatibility")
    ai_remedy = _basic_lookup_section_narrative(section_lookup, "remedy")
    ai_closing = _basic_lookup_section_narrative(section_lookup, "closing_summary")
    ai_focus = _basic_lookup_any_section_narrative(section_lookup, ["focus_snapshot", "mobile_numerology", "closing_summary"])
    ai_growth = _basic_lookup_any_section_narrative(section_lookup, ["growth_blueprint", "closing_summary", "remedy"])
    planet_name = str((core.get("planet") or {}).get("name") or "ग्रह उपलब्ध नहीं").strip()
    planet_element = _repair_hindi_element_label(
        str((core.get("planet") or {}).get("element") or "तत्व उपलब्ध नहीं").strip()
    )
    planet_energy_list = (core.get("planet") or {}).get("energy") or []
    planet_energy_text = ", ".join([str(item).strip() for item in planet_energy_list if str(item).strip()]) or "स्थिरता"
    ai_mobile_clean = str(ai_mobile or "").strip()
    if any(token in ai_mobile_clean for token in ("N/A", "Not Provided", "उपलब्ध नहीं")):
        ai_mobile_clean = ""
    energy_hint = planet_energy_list[0] if planet_energy_list else "स्थिरता"
    mobile_insight_lines = [
        f"• आपका मोबाइल vibration {core['mobile']['vibration']} संचार को तेज़ करता है; तेज़ reply से पहले 10 सेकंड pause लें।",
        f"• {planet_name} + {planet_element} ऊर्जा {energy_hint} मोड में काम करती है; बड़े decision से पहले 1 लिखित checklist बनाएँ।",
        f"• आज का focus \"{inputs['primary_challenge']}\" है; सुबह 1 स्पष्ट priority लिखें और दिन भर उसी पर लौटें।",
        "• Key intent: \"मैं अपनी मोबाइल ऊर्जा को अनुशासन, स्पष्टता और निरंतरता में बदल रहा हूँ।\"",
    ]
    life_area_rows = _basic_life_area_rows(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_focus or ai_closing,
    )
    positive_rows = _basic_positive_impact_rows(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_mobile or ai_focus,
    )
    challenge_rows = _basic_challenge_rows(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_lo_shu or ai_focus,
    )
    effects_context = _basic_mobile_effects_context_line(
        missing_digits=list((lo_shu or {}).get("missing") or []),
        repeating_digits=list((lo_shu or {}).get("repeating") or []),
        primary_challenge=str(inputs.get("primary_challenge") or "consistency"),
    )
    if effects_context and challenge_rows:
        challenge_rows[-1]["connection"] = f"{challenge_rows[-1]['connection']} | {effects_context}"
    life_context_lines = _basic_life_path_context_lines(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_compat or ai_focus,
    )
    verdict_box_text = _basic_verdict_box_text(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_compat,
    )
    suggested_payload = _basic_suggested_numbers_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_growth or ai_closing,
    )
    charging_payload = _basic_charging_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_remedy or ai_closing,
    )
    remedies_payload = _basic_remedies_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        remedy_lines=remedy_lines,
        ai_narrative=ai_remedy or ai_closing,
    )
    tracker_payload = _basic_tracker_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_remedy or ai_closing,
    )
    summary_payload = _basic_summary_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_focus,
    )
    key_insight_payload = _basic_key_insight_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_growth,
    )
    next_steps_payload = _basic_next_steps_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_growth,
    )
    footer_payload = _basic_footer_payload(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_closing or ai_growth,
    )

    repeat_text = ", ".join(f"{item['digit']} ({item['count']}x)" for item in lo_shu["repeating"]) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    missing_text = ", ".join(str(digit) for digit in lo_shu["missing"]) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    present_text = ", ".join(str(digit) for digit in lo_shu["present"]) or "Ã Â¤â€¢Ã Â¥â€¹Ã Â¤Ë† Ã Â¤Â¨Ã Â¤Â¹Ã Â¥â‚¬Ã Â¤â€š"
    avoid_text = ", ".join(str(item) for item in suggestions["avoid_vibrations"])
    preferred_digits = ", ".join(str(item) for item in suggestions["preferred_digits"])
    verdict_hi = {"KEEP": "à¤°à¤–à¥‡à¤‚", "MANAGE": "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚", "CHANGE": "à¤¬à¤¦à¤²à¥‡à¤‚"}.get(core["verdict"], "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚")
    verdict_en = core["verdict"]
    loshu_challenge_lines = _basic_loshu_challenge_lines(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_lo_shu or ai_focus,
    )
    frequency_row = "|".join(str(frequency[d]) for d in [1, 2, 3, 4, 5, 6, 7, 8, 9, 0])

    lo_shu_grid_block = (
        "Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â\n"
        "Ã¢â€â€š    4    Ã¢â€â€š    9    Ã¢â€â€š    2    Ã¢â€â€š\n"
        f"Ã¢â€â€š    {lo_shu['grid'][4]}    Ã¢â€â€š    {lo_shu['grid'][9]}    Ã¢â€â€š    {lo_shu['grid'][2]}    Ã¢â€â€š\n"
        "Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¤\n"
        "Ã¢â€â€š    3    Ã¢â€â€š    5    Ã¢â€â€š    7    Ã¢â€â€š\n"
        f"Ã¢â€â€š    {lo_shu['grid'][3]}    Ã¢â€â€š    {lo_shu['grid'][5]}    Ã¢â€â€š    {lo_shu['grid'][7]}    Ã¢â€â€š\n"
        "Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¤\n"
        "Ã¢â€â€š    8    Ã¢â€â€š    1    Ã¢â€â€š    6    Ã¢â€â€š\n"
        f"Ã¢â€â€š    {lo_shu['grid'][8]}    Ã¢â€â€š    {lo_shu['grid'][1]}    Ã¢â€â€š    {lo_shu['grid'][6]}    Ã¢â€â€š\n"
        "Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ"
    )
    life_path_box = (
        "Ã¢â€¢â€Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢â€”\n"
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜\n"
        f"Ã¢â€¢â€˜    Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ (Life Path):  {core['life_path']['value']:<2}                          Ã¢â€¢â€˜\n"
        f"Ã¢â€¢â€˜    \"{core['life_path']['meaning']}\"              Ã¢â€¢â€˜\n"
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜\n"
        f"Ã¢â€¢â€˜    Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ {core['mobile']['vibration']} + Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ {core['life_path']['value']}                              Ã¢â€¢â€˜\n"
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜\n"
        f"Ã¢â€¢â€˜    Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤â€¢Ã Â¥â€šÃ Â¤Â²Ã Â¤Â¤Ã Â¤Â¾ (Alignment):  {core['compatibility']['color']} {core['compatibility']['text']} ({core['compatibility']['english']})            Ã¢â€¢â€˜\n"
        "Ã¢â€¢â€˜                                                           Ã¢â€¢â€˜\n"
        "Ã¢â€¢Å¡Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â"
    )

    profile_line = _basic_profile_conditioned_line(
        core=core,
        uniqueness_seed=uniqueness_seed,
        ai_narrative=ai_mobile or ai_closing,
    )

    sections: List[Dict[str, Any]] = [
        {
            "order": 1,
            "key": "basic_mobile_energy",
            "title": "1. Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤Å Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¾ | YOUR MOBILE NUMBER ENERGY",
            "subtitle": "Deterministic values",
            "layout": "center_feature",
            "blocks": [
                f"\u092e\u094b\u092c\u093e\u0907\u0932 \u0928\u0902\u092c\u0930: {inputs['mobile_number']}",
                f"\u092e\u0942\u0932 \u0905\u0902\u0915 (Vibration): {core['mobile']['vibration']}",
                f"\u0917\u094d\u0930\u0939: {planet_name}",
                f"\u0924\u0924\u094d\u0935: {planet_element}",
                f"\u092a\u094d\u0930\u092e\u0941\u0916 \u090a\u0930\u094d\u091c\u093e \u0938\u0902\u0915\u0947\u0924: {planet_energy_text}",
                profile_line,
                *([f"\u0935\u094d\u092f\u0915\u094d\u0924\u093f\u0917\u0924 \u091f\u093f\u092a\u094d\u092a\u0923\u0940: {ai_mobile_clean}"] if ai_mobile_clean else []),
                *mobile_insight_lines,




            ],
        },
        {
            "order": 2,
            "key": "basic_lo_shu_grid",
            "title": "2. Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ | LO SHU GRID",
            "subtitle": "Digit pattern and challenge linkage",
            "layout": "premium_card",
            "blocks": [
                f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¤Â¾ Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â°: {inputs['mobile_number']}",
                f"Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤â€ Ã Â¤ÂµÃ Â¥Æ’Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿ Ã Â¤ÂªÃ Â¤â€šÃ Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿: {frequency_row}",
                f"Ã Â¤Â²Ã Â¥â€¹ Ã Â¤Â¶Ã Â¥â€š Ã Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â¡ Ã Â¤Â¬Ã Â¥ÂÃ Â¤Â²Ã Â¥â€°Ã Â¤â€¢:\n{lo_shu_grid_block}\n\nÃ¢Å“â€œ = Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦    Ã¢Å“â€” = Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤",
                f"Ã Â¤Â®Ã Â¥Å’Ã Â¤Å“Ã Â¥â€šÃ Â¤Â¦ Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾: {present_text}",
                f"Ã Â¤â€¦Ã Â¤Â¨Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â¸Ã Â¥ÂÃ Â¤Â¥Ã Â¤Â¿Ã Â¤Â¤ Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾: {missing_text}",
                f"Ã Â¤Â¦Ã Â¥â€¹Ã Â¤Â¹Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â Ã Â¤â€¦Ã Â¤â€šÃ Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾: {repeat_text}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€¢: {inputs['primary_challenge']}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 1: {loshu_challenge_lines[0]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 2: {loshu_challenge_lines[1]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 3: {loshu_challenge_lines[2]}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Â¨Ã Â¥â€¡Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¶Ã Â¤Â¨ 4: {loshu_challenge_lines[3]}",
                f"Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿Ã Â¤â€”Ã Â¤Â¤ Ã Â¤Å¸Ã Â¤Â¿Ã Â¤ÂªÃ Â¥ÂÃ Â¤ÂªÃ Â¤Â£Ã Â¥â‚¬: {ai_lo_shu or lo_shu['insight']}",
            ],
        },
        {
            "order": 3,
            "key": "basic_positive_negative_impact",
            "title": "3. Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ | HOW YOUR MOBILE NUMBER AFFECTS YOU",
            "subtitle": "3 strengths + 3 challenges",
            "layout": "split_analysis",
            "blocks": [
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 1: {positive_rows[0]['effect']} | {positive_rows[0]['impact']}",
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 2: {positive_rows[1]['effect']} | {positive_rows[1]['impact']}",
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 3: {positive_rows[2]['effect']} | {positive_rows[2]['impact']}",
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 4: {positive_rows[3]['effect']} | {positive_rows[3]['impact']}",
                f"Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â®Ã Â¤â€¢ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 5: {positive_rows[4]['effect']} | {positive_rows[4]['impact']}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 1: {challenge_rows[0]['challenge']} | {challenge_rows[0]['appearance']} | {challenge_rows[0]['connection']}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 2: {challenge_rows[1]['challenge']} | {challenge_rows[1]['appearance']} | {challenge_rows[1]['connection']}",
                f"Ã Â¤Å¡Ã Â¥ÂÃ Â¤Â¨Ã Â¥Å’Ã Â¤Â¤Ã Â¥â‚¬ Ã Â¤Â¤Ã Â¤Â¾Ã Â¤Â²Ã Â¤Â¿Ã Â¤â€¢Ã Â¤Â¾ 3: {challenge_rows[2]['challenge']} | {challenge_rows[2]['appearance']} | {challenge_rows[2]['connection']}",
            ],
        },
        {
            "order": 4,
            "key": "basic_life_path_context",
            "title": "4. Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â­ | YOUR LIFE PATH CONTEXT",
            "subtitle": "Life path + compatibility",
            "layout": "comparison_meter",
            "blocks": [
                f"Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤ÂªÃ Â¤Â¥ Ã Â¤Â¬Ã Â¥â€°Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¸:\n{life_path_box}",
                f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤â€¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¥ 1: {life_context_lines[0]}",
                f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤â€¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¥ 2: {life_context_lines[1]}",
                f"Ã Â¤â€ Ã Â¤ÂªÃ Â¤â€¢Ã Â¥â€¡ Ã Â¤Â²Ã Â¤Â¿Ã Â¤Â Ã Â¤â€¦Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¥ 3: {life_context_lines[2]}",
                f"Ã Â¤ÂµÃ Â¥ÂÃ Â¤Â¯Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â¤Ã Â¤Â¿Ã Â¤â€”Ã Â¤Â¤ Ã Â¤Å¸Ã Â¤Â¿Ã Â¤ÂªÃ Â¥ÂÃ Â¤ÂªÃ Â¤Â£Ã Â¥â‚¬: {ai_compat or 'Ã Â¤Â¯Ã Â¤Â¹ Ã Â¤Â¸Ã Â¤â€šÃ Â¤Â¯Ã Â¥â€¹Ã Â¤Å“Ã Â¤Â¨ Ã Â¤Â¸Ã Â¤Â¹Ã Â¥â‚¬ Ã Â¤Â°Ã Â¥â€šÃ Â¤Å¸Ã Â¥â‚¬Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â¥ Ã Â¤â€¦Ã Â¤Å¡Ã Â¥ÂÃ Â¤â€ºÃ Â¥â€¡ Ã Â¤ÂªÃ Â¤Â°Ã Â¤Â¿Ã Â¤Â£Ã Â¤Â¾Ã Â¤Â® Ã Â¤Â¦Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤â€¢Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¹Ã Â¥Ë†Ã Â¥Â¤'}",
            ],
        },
        {
            "order": 5,
            "key": "basic_life_area_impact",
            "title": "5. Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“ Ã Â¤Å“Ã Â¥â‚¬Ã Â¤ÂµÃ Â¤Â¨ Ã Â¤â€¢Ã Â¥ÂÃ Â¤Â·Ã Â¥â€¡Ã Â¤Â¤Ã Â¥ÂÃ Â¤Â°Ã Â¥â€¹Ã Â¤â€š Ã Â¤ÂªÃ Â¤Â° Ã Â¤ÂªÃ Â¥ÂÃ Â¤Â°Ã Â¤Â­Ã Â¤Â¾Ã Â¤Âµ | IMPACT ON KEY LIFE AREAS",
            "subtitle": f"Primary challenge: {inputs['primary_challenge']}",
            "layout": "four_card_grid",
            "blocks": [
                f"LIFE_AREA_FOCUS: {inputs['primary_challenge']}",
                f"LIFE_AREA_ROW 1: {life_area_rows[0]['area']} | {life_area_rows[0]['impact']} | {life_area_rows[0]['meaning']}",
                f"LIFE_AREA_ROW 2: {life_area_rows[1]['area']} | {life_area_rows[1]['impact']} | {life_area_rows[1]['meaning']}",
                f"LIFE_AREA_ROW 3: {life_area_rows[2]['area']} | {life_area_rows[2]['impact']} | {life_area_rows[2]['meaning']}",
                f"LIFE_AREA_ROW 4: {life_area_rows[3]['area']} | {life_area_rows[3]['impact']} | {life_area_rows[3]['meaning']}",
                f"LIFE_AREA_ROW 5: {life_area_rows[4]['area']} | {life_area_rows[4]['impact']} | {life_area_rows[4]['meaning']}",
                f"LIFE_AREA_ROW 6: {life_area_rows[5]['area']} | {life_area_rows[5]['impact']} | {life_area_rows[5]['meaning']}",
            ],
        },
        {
            "order": 6,
            "key": "basic_keep_change_verdict",
            "title": "6. Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° Ã Â¤Â¸Ã Â¤Â¿Ã Â¤Â«Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¿Ã Â¤Â¶ | MOBILE NUMBER RECOMMENDATION",
            "subtitle": "Keep / Manage / Change",
            "layout": "closing_reflection",
            "blocks": [
                f"VERDICT_BOX:\n{verdict_box_text}",
                f"VERDICT_COMMENT: {ai_closing or '21-à¤¦à¤¿à¤µà¤¸à¥€à¤¯ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤•à¥‡ à¤¬à¤¾à¤¦ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¸à¤®à¥€à¤•à¥à¤·à¤¾ à¤•à¤°à¥‡à¤‚à¥¤'}",
            ],
        },
    ]

    if inputs["willingness_to_change"] != "no":
        sections.append(
            {
                "order": 7,
                "key": "basic_suggested_numbers",
                "title": "7. Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂÃ Â¤Â¾Ã Â¤Â Ã Â¤â€”Ã Â¤Â Ã Â¤Â®Ã Â¥â€¹Ã Â¤Â¬Ã Â¤Â¾Ã Â¤â€¡Ã Â¤Â² Ã Â¤Â¨Ã Â¤â€šÃ Â¤Â¬Ã Â¤Â° | SUGGESTED MOBILE NUMBERS",
                "subtitle": "3 deterministic options",
                "layout": "triad_cards",
                "blocks": [
                    f"SUGGESTED_INTRO: {suggested_payload['intro']}",
                    f"SUGGESTED_OPTION 1: {suggested_payload['options'][0]['title']} || {suggested_payload['options'][0]['pattern']} || {suggested_payload['options'][0]['vibration']} || {suggested_payload['options'][0]['key_digits']} || {suggested_payload['options'][0]['fills']} || {suggested_payload['options'][0]['reason']}",
                    f"SUGGESTED_OPTION 2: {suggested_payload['options'][1]['title']} || {suggested_payload['options'][1]['pattern']} || {suggested_payload['options'][1]['vibration']} || {suggested_payload['options'][1]['key_digits']} || {suggested_payload['options'][1]['fills']} || {suggested_payload['options'][1]['reason']}",
                    f"SUGGESTED_OPTION 3: {suggested_payload['options'][2]['title']} || {suggested_payload['options'][2]['pattern']} || {suggested_payload['options'][2]['vibration']} || {suggested_payload['options'][2]['key_digits']} || {suggested_payload['options'][2]['fills']} || {suggested_payload['options'][2]['reason']}",
                    f"SUGGESTED_STEP 1: {suggested_payload['steps'][0]}",
                    f"SUGGESTED_STEP 2: {suggested_payload['steps'][1]}",
                    f"SUGGESTED_STEP 3: {suggested_payload['steps'][2]}",
                    f"SUGGESTED_STEP 4: {suggested_payload['steps'][3]}",
                    f"SUGGESTED_STEP 5: {suggested_payload['steps'][4]}",
                ],
            }
        )

    sections.extend(
        [
            {
                "order": 8,
                "key": "basic_charging_direction",
            "title": "8. Ã Â¤Å¡Ã Â¤Â¾Ã Â¤Â°Ã Â¥ÂÃ Â¤Å“Ã Â¤Â¿Ã Â¤â€šÃ Â¤â€” Ã Â¤Â¦Ã Â¤Â¿Ã Â¤Â¶Ã Â¤Â¾ | CHARGING YOUR MOBILE NUMBER",
            "subtitle": "Direction-day-time-method",
            "layout": "split_insight",
            "blocks": [
                    f"CHARGING_INTRO: {charging_payload['intro']}",
                    f"CHARGING_ROW 1: {charging_payload['direction_label']} | {charging_payload['direction_value']}",
                    f"CHARGING_ROW 2: {charging_payload['time_label']} | {charging_payload['time_value']}",
                    f"CHARGING_ROW 3: {charging_payload['how_label']} | {charging_payload['how_value']}",
                ],
            },
            {
                "order": 9,
                "key": "basic_remedies_table",
                "title": "9. Ã Â¤â€°Ã Â¤ÂªÃ Â¤Â¾Ã Â¤Â¯ | REMEDIES FOR YOUR CURRENT NUMBER",
                "subtitle": "Spiritual + Physical + Digital setup",
                "layout": "remedy_cards",
                "blocks": [
                    f"REMEDY_INTRO: {remedies_payload['intro']}",
                    f"REMEDY_SP_TITLE: {remedies_payload['spiritual_title']}",
                    *[
                        f"REMEDY_SP_ROW {idx}: {row['remedy']} || {row['action']} || {row['frequency']}"
                        for idx, row in enumerate(remedies_payload["spiritual_rows"], start=1)
                    ],
                    f"REMEDY_DG_TITLE: {remedies_payload['digital_title']}",
                    *[
                        f"REMEDY_DG_ROW {idx}: {row['remedy']} || {row['action']} || {row['why']}"
                        for idx, row in enumerate(remedies_payload["digital_rows"], start=1)
                    ],
                    f"REMEDY_SETUP_TITLE: {remedies_payload['setup_title']}",
                    *[
                        f"REMEDY_SETUP_ROW {idx}: {row['item']} || {row['recommendation']}"
                        for idx, row in enumerate(remedies_payload["setup_rows"], start=1)
                    ],
                    f"REMEDY_RESET_TITLE: {remedies_payload['reset_title']}",
                    *[
                        f"REMEDY_RESET_ROW {idx}: {row['week']} || {row['actions']}"
                        for idx, row in enumerate(remedies_payload["reset_rows"], start=1)
                    ],
                    f"REMEDY_CHECK_TITLE: {remedies_payload['check_title']}",
                    *[
                        f"REMEDY_CHECK {idx}: {line}"
                        for idx, line in enumerate(remedies_payload["checklist"], start=1)
                    ],
                    f"REMEDY_COMMENT: {ai_remedy or remedies_payload['comment'] or 'à¤‰à¤ªà¤¾à¤¯à¥‹à¤‚ à¤•à¥‹ à¤•à¤® à¤¸à¥‡ à¤•à¤® 21 à¤¦à¤¿à¤¨ à¤¨à¤¿à¤¯à¤®à¤¿à¤¤ à¤°à¥‚à¤ª à¤¸à¥‡ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤'}",
                ],
            },
            {
                "order": 10,
                "key": "basic_21_day_tracker",
                "title": "10. 21-Ã Â¤Â¦Ã Â¤Â¿Ã Â¤ÂµÃ Â¤Â¸Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Å¸Ã Â¥ÂÃ Â¤Â°Ã Â¥Ë†Ã Â¤â€¢Ã Â¤Â° | 21-DAY REMEDY TRACKER",
                "subtitle": "Week-wise plan",
                "layout": "timeline_strategy",
                "blocks": [
                    f"TRACKER_ROW 1: {tracker_payload['rows'][0]['week']} || {tracker_payload['rows'][0]['task']} || {tracker_payload['rows'][0]['status']}",
                    f"TRACKER_ROW 2: {tracker_payload['rows'][1]['week']} || {tracker_payload['rows'][1]['task']} || {tracker_payload['rows'][1]['status']}",
                    f"TRACKER_ROW 3: {tracker_payload['rows'][2]['week']} || {tracker_payload['rows'][2]['task']} || {tracker_payload['rows'][2]['status']}",
                ],
            },
            {
                "order": 11,
                "key": "basic_summary_table_v2",
                "title": "11. Ã Â¤Â¸Ã Â¤Â¾Ã Â¤Â°Ã Â¤Â¾Ã Â¤â€šÃ Â¤Â¶ | SUMMARY",
                "subtitle": "Current vs recommended",
                "layout": "four_card_grid",
                "blocks": [
                    f"SUMMARY_ROW 1: {summary_payload['rows'][0]['field']} || {summary_payload['rows'][0]['status']} || {summary_payload['rows'][0]['suggestion']}",
                    f"SUMMARY_ROW 2: {summary_payload['rows'][1]['field']} || {summary_payload['rows'][1]['status']} || {summary_payload['rows'][1]['suggestion']}",
                    f"SUMMARY_ROW 3: {summary_payload['rows'][2]['field']} || {summary_payload['rows'][2]['status']} || {summary_payload['rows'][2]['suggestion']}",
                    f"SUMMARY_ROW 4: {summary_payload['rows'][3]['field']} || {summary_payload['rows'][3]['status']} || {summary_payload['rows'][3]['suggestion']}",
                    f"SUMMARY_ROW 5: {summary_payload['rows'][4]['field']} || {summary_payload['rows'][4]['status']} || {summary_payload['rows'][4]['suggestion']}",
                    f"SUMMARY_ROW 6: {summary_payload['rows'][5]['field']} || {summary_payload['rows'][5]['status']} || {summary_payload['rows'][5]['suggestion']}",
                    f"SUMMARY_ROW 7: {summary_payload['rows'][6]['field']} || {summary_payload['rows'][6]['status']} || {summary_payload['rows'][6]['suggestion']}",
                ],
            },
            {
                "order": 12,
                "key": "basic_key_insight",
                "title": "12. Ã Â¤Â®Ã Â¥ÂÃ Â¤â€“Ã Â¥ÂÃ Â¤Â¯ Ã Â¤â€¦Ã Â¤â€šÃ Â¤Â¤Ã Â¤Â°Ã Â¥ÂÃ Â¤Â¦Ã Â¥Æ’Ã Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¿ | YOUR KEY INSIGHT",
                "subtitle": "One-line synthesis",
                "layout": "main_card_plus_strips",
                "blocks": [
                    f"KEY_INSIGHT_P1: {key_insight_payload['p1']}",
                    f"KEY_INSIGHT_P2: {key_insight_payload['p2']}",
                ],
            },
            {
                "order": 13,
                "key": "basic_upgrade_path",
                "title": "13. Ã Â¤â€¦Ã Â¤â€”Ã Â¤Â²Ã Â¥â€¡ Ã Â¤â€¢Ã Â¤Â¦Ã Â¤Â® | NEXT STEPS",
                "subtitle": "Upgrade path",
                "layout": "split_analysis",
                "blocks": [
                    f"NEXTSTEP_ROW 1: {next_steps_payload['rows'][0]['if_you_want']} || {next_steps_payload['rows'][0]['upgrade_to']}",
                    f"NEXTSTEP_ROW 2: {next_steps_payload['rows'][1]['if_you_want']} || {next_steps_payload['rows'][1]['upgrade_to']}",
                    f"NEXTSTEP_THANKS: {next_steps_payload['thanks']}",
                    f"NEXTSTEP_CONTEXT: {next_steps_payload['context']}",
                    f"NEXTSTEP_OPTION 1: {next_steps_payload['options'][0]}",
                    f"NEXTSTEP_OPTION 2: {next_steps_payload['options'][1]}",
                    f"NEXTSTEP_OPTION 3: {next_steps_payload['options'][2]}",
                    f"NEXTSTEP_CLOSING: {next_steps_payload['closing']}",
                    f"NEXTSTEP_FOOTER 1: {next_steps_payload['footer_lines'][0]}",
                    f"NEXTSTEP_FOOTER 2: {next_steps_payload['footer_lines'][1]}",
                    f"NEXTSTEP_FOOTER 3: {next_steps_payload['footer_lines'][2]}",
                ],
            },
            {
                "order": 14,
                "key": "basic_footer",
                "title": "14. Ã Â¤Â«Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â° | FOOTER",
                "subtitle": "Identity stamp",
                "layout": "closing_reflection",
                "blocks": [
                    footer_payload["report_type_line"],
                    footer_payload["generated_for_line"],
                    footer_payload["date_line"],
                    footer_payload["gratitude_line"],
                    footer_payload["tagline_line"],
                ],
            },
            {
                "order": 15,
                "key": "basic_upsell_page",
                "title": "Upgrade Page | Ã Â¤â€¦Ã Â¤ÂªÃ Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥â€¡Ã Â¤Â¡ Ã Â¤â€˜Ã Â¤Â«Ã Â¤Â°",
                "subtitle": "Grow from Basic to Standard/Premium",
                "layout": "center_feature",
                "blocks": [
                    "Standard Report: Name Numerology + Destiny + Soul Urge + Personality + Name Remedies",
                    "Premium Report: Complete Life Blueprint with 34 premium intelligence sections",
                    "Ã Â¤â€¢Ã Â¤Â¸Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â® Ã Â¤â€˜Ã Â¤Â«Ã Â¤Â°: Ã Â¤â€¦Ã Â¤Â­Ã Â¥â‚¬ Ã Â¤â€¦Ã Â¤ÂªÃ Â¤â€”Ã Â¥ÂÃ Â¤Â°Ã Â¥â€¡Ã Â¤Â¡ Ã Â¤â€¢Ã Â¤Â°Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€Ã Â¤Â° Ã Â¤â€¦Ã Â¤ÂªÃ Â¤Â¨Ã Â¥â‚¬ Ã Â¤Â°Ã Â¤Â£Ã Â¤Â¨Ã Â¥â‚¬Ã Â¤Â¤Ã Â¤Â¿Ã Â¤â€¢ Ã Â¤Â¸Ã Â¥ÂÃ Â¤ÂªÃ Â¤Â·Ã Â¥ÂÃ Â¤Å¸Ã Â¤Â¤Ã Â¤Â¾ Ã Â¤Â¬Ã Â¤Â¢Ã Â¤Â¼Ã Â¤Â¾Ã Â¤ÂÃ Â¤ÂÃ Â¥Â¤",
                ],
            },
        ]
    )

    ordered: List[Dict[str, Any]] = []
    for idx, section in enumerate(sections, start=1):
        cloned = dict(section)
        cloned["order"] = idx
        if cloned["key"] != "basic_upsell_page":
            title_text = str(cloned.get("title") or "")
            if ". " in title_text:
                cloned["title"] = f"{idx}. {title_text.split('. ', 1)[1]}"
        ordered.append(cloned)

    return _apply_basic_similarity_gate(
        sections=_fix_mojibake_text(ordered),
        core=core,
    )
def _index_ai_sections(ai_result: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    dropped: List[Dict[str, str]] = []
    for raw_section in ai_result.get("sections") or []:
        if not isinstance(raw_section, dict):
            dropped.append({"sectionKey": "unknown_section", "reason": "AI section is not an object"})
            continue

        section_key = str(raw_section.get("sectionKey") or "").strip()
        if not section_key:
            dropped.append({"sectionKey": "unknown_section", "reason": "AI section missing sectionKey"})
            continue

        if bool(raw_section.get("omitSection")):
            dropped.append(
                {
                    "sectionKey": section_key,
                    "reason": str(raw_section.get("reason") or "AI marked section to omit"),
                }
            )
            continue

        normalized = normalize_ai_section_shape(raw_section)
        if not normalized:
            dropped.append({"sectionKey": section_key, "reason": "AI section failed contract normalization"})
            continue

        indexed[section_key] = normalized
    return indexed, dropped


def _build_final_sections(
    *,
    enabled_sections: List[str],
    ai_sections: Dict[str, Dict[str, Any]],
    plan_key: str,
    language_preference: str,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
    deterministic_availability: Dict[str, bool],
    problem_profile: Dict[str, Any],
    allow_deterministic_fallback: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    final_sections: List[Dict[str, Any]] = []
    dropped_sections: List[Dict[str, str]] = []

    for section_key in enabled_sections:
        ai_candidate = ai_sections.get(section_key)

        if ai_candidate:
            if plan_key == "enterprise" and _needs_premium_fallback(ai_candidate):
                fallback_section = build_fallback_section(
                    section_key=section_key,
                    plan=plan_key,
                    normalized_input=canonical_normalized_input,
                    numerology_values=numerology_values,
                    derived_scores=derived_scores,
                    problem_profile=problem_profile,
                )
                final_sections.append(fallback_section)
            else:
                if plan_key == "enterprise":
                    fallback_section = build_fallback_section(
                        section_key=section_key,
                        plan=plan_key,
                        normalized_input=canonical_normalized_input,
                        numerology_values=numerology_values,
                        derived_scores=derived_scores,
                        problem_profile=problem_profile,
                    )
                    final_sections.append(
                        _sanitize_premium_section(
                            ai_candidate,
                            fallback=fallback_section,
                            force_summary_from_fallback=True,
                        )
                    )
                else:
                    final_sections.append(ai_candidate)
            continue

        if not allow_deterministic_fallback:
            dropped_sections.append(
                {
                    "sectionKey": section_key,
                    "reason": "AI section missing (deterministic fallback disabled)",
                }
            )
            continue

        # Always render a deterministic fallback when AI section is unavailable.
        fallback_section = build_fallback_section(
            section_key=section_key,
            plan=plan_key,
            normalized_input=canonical_normalized_input,
            numerology_values=numerology_values,
            derived_scores=derived_scores,
            problem_profile=problem_profile,
        )
        if plan_key == "enterprise":
            fallback_section = _sanitize_premium_section(fallback_section)
        final_sections.append(fallback_section)

    if plan_key == "enterprise":
        # Premium must preserve full 42-page structure; do not drop sections due to validation filters.
        validated_sections = final_sections
        validation_drops = []
    else:
        validated_sections, validation_drops = validate_sections_for_render(final_sections, language_preference)
        if validation_drops:
            dropped_sections.extend(
                {
                    "sectionKey": item.get("sectionKey", "unknown_section"),
                    "reason": f"Validation dropped section: {item.get('reason')}",
                }
                for item in validation_drops
            )

    replacement_sections: List[Dict[str, Any]] = []
    existing_keys = {section.get("sectionKey") for section in validated_sections}
    for dropped in validation_drops:
        key = str(dropped.get("sectionKey") or "").strip()
        if (
            not key
            or key in existing_keys
            or not deterministic_availability.get(key)
            or not allow_deterministic_fallback
        ):
            continue
        replacement = build_fallback_section(
            section_key=key,
            plan=plan_key,
            normalized_input=canonical_normalized_input,
            numerology_values=numerology_values,
            derived_scores=derived_scores,
            problem_profile=problem_profile,
        )
        replacement_sections.append(replacement)
        existing_keys.add(key)

    if replacement_sections:
        merged = validated_sections + replacement_sections
        validated_sections, replacement_drops = validate_sections_for_render(merged, language_preference)
        if replacement_drops:
            dropped_sections.extend(
                {
                    "sectionKey": item.get("sectionKey", "unknown_section"),
                    "reason": f"Replacement section dropped: {item.get('reason')}",
                }
                for item in replacement_drops
            )

    cap = PLAN_SECTION_CAPS.get(plan_key)
    if cap is not None and len(validated_sections) > cap:
        overflow = validated_sections[cap:]
        validated_sections = validated_sections[:cap]
        dropped_sections.extend(
            {
                "sectionKey": str(section.get("sectionKey") or "unknown_section"),
                "reason": f"dropped due to plan section cap ({cap})",
            }
            for section in overflow
        )

    return validated_sections, dropped_sections


def build_plan_aware_report(*, intake_data: Dict[str, Any], resolved_plan: str) -> Dict[str, Any]:
    plan_config = get_plan_config(resolved_plan)
    deterministic = run_deterministic_pipeline(intake_data=intake_data, plan_config=plan_config)
    basic_mobile_core: Dict[str, Any] = {}
    if plan_config.key == "basic" and not settings.AI_REPORT_FORCE_LLM_NARRATIVE:
        basic_mobile_core = _build_basic_mobile_deterministic_core_v2(
            canonical_normalized_input=deterministic.canonical_normalized_input,
            numerology_values=deterministic.numerology_values,
            problem_profile=deterministic.problem_profile,
        )
    _validate_required_fields(
        deterministic.normalized_input,
        plan_config.required_fields,
        plan_key=plan_config.key,
    )
    _validate_profile_identity(deterministic.canonical_normalized_input)
    ai_payload = build_ai_payload(
        plan_config=plan_config,
        deterministic=deterministic,
        basic_mobile_core=basic_mobile_core if plan_config.key == "basic" and not settings.AI_REPORT_FORCE_LLM_NARRATIVE else None,
    )

    logger.debug("Enabled sections for plan %s: %s", plan_config.key, plan_config.enabled_sections)
    logger.debug(
        "Deterministic availability for plan %s: %s",
        plan_config.key,
        deterministic.section_deterministic_availability,
    )

    language_pref = str(deterministic.canonical_normalized_input.get("language") or "").strip().lower()
    skip_basic_ai = (
        plan_config.key == "basic"
        and settings.AI_REPORT_SKIP_AZURE_FOR_BASIC
        and language_pref in {"", "hindi"}
        and not settings.AI_REPORT_FORCE_LLM_NARRATIVE
    )
    # Premium reports must remain deterministic; keep LLM off unless explicitly forced.
    disable_llm = plan_config.key == "enterprise" and not settings.AI_REPORT_FORCE_LLM_NARRATIVE
    if disable_llm or skip_basic_ai:
        ai_result = {
            "reportTitle": "Premium Numerology Report",
            "plan": plan_config.key.upper(),
            "sections": [],
            "profileSnapshot": {},
            "dashboard": {},
            "closingInsight": "Use your strongest insights deliberately and review progress weekly.",
            "narrativeQuality": {},
            "strategyBlueprint": {},
            "generationTrace": {
                "attempt": 0,
                "mode": "deterministic_only" if disable_llm else "deterministic_basic_fast_path",
                "rewriteTriggered": False,
            },
        }
    else:
        ai_result = generate_report_with_azure(
            ai_payload=ai_payload,
            max_retries=settings.AI_REPORT_AZURE_MAX_RETRIES,
            enable_targeted_rewrite=settings.AI_REPORT_AZURE_ENABLE_TARGETED_REWRITE,
        )
    if not isinstance(ai_result, dict):
        ai_result = {}
    ai_result.setdefault("sections", [])
    ai_result.setdefault("profileSnapshot", {})
    ai_result.setdefault("dashboard", {})
    ai_result.setdefault("narrativeQuality", {})
    ai_result.setdefault("strategyBlueprint", {})
    ai_result.setdefault("generationTrace", {})

    ai_indexed_sections, ai_dropped = _index_ai_sections(ai_result)
    if ai_dropped:
        logger.warning("AI parser dropped sections: %s", ai_dropped)
    else:
        logger.debug("AI parser accepted all section entries for plan %s", plan_config.key)

    if settings.AI_REPORT_FORCE_LLM_NARRATIVE:
        raw_sections = ai_result.get("sections") or []
        normalized_sections: List[Dict[str, Any]] = []
        dropped_sections: List[Dict[str, str]] = []
        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                continue
            normalized = normalize_ai_section_shape(raw_section)
            if normalized:
                normalized_sections.append(normalized)
            else:
                dropped_sections.append(
                    {
                        "sectionKey": str(raw_section.get("sectionKey") or "unknown_section"),
                        "reason": "AI section failed contract normalization",
                    }
                )

        validated_sections, validation_drops = validate_sections_for_render(normalized_sections, language_pref)
        final_sections = validated_sections
        final_dropped = dropped_sections + [
            {
                "sectionKey": item.get("sectionKey", "unknown_section"),
                "reason": f"Validation dropped section: {item.get('reason')}",
            }
            for item in validation_drops
        ]
    else:
        final_sections, final_dropped = _build_final_sections(
            enabled_sections=plan_config.enabled_sections,
            ai_sections=ai_indexed_sections,
            plan_key=plan_config.key,
            language_preference=language_pref,
            canonical_normalized_input=deterministic.canonical_normalized_input,
            numerology_values=deterministic.numerology_values,
            derived_scores=deterministic.derived_scores,
            deterministic_availability=deterministic.section_deterministic_availability,
            problem_profile=deterministic.problem_profile,
            allow_deterministic_fallback=not settings.AI_REPORT_FORCE_LLM_NARRATIVE,
        )

    if final_dropped:
        logger.warning("Sections dropped due to missing/invalid data: %s", final_dropped)

    if not final_sections:
        raise ValueError("No sections survived completeness validation for the selected plan.")

    logger.debug(
        "Final rendered sections for plan %s: %s",
        plan_config.key,
        [section.get("sectionKey") for section in final_sections],
    )
    ai_valid_sections = {
        section_key
        for section_key, section in ai_indexed_sections.items()
        if isinstance(section, dict)
    }
    fallback_sections = [
        section.get("sectionKey")
        for section in final_sections
        if section.get("sectionKey") not in ai_valid_sections
    ]
    summary_extra = {
        "plan": plan_config.key,
        "requested_sections": len(plan_config.enabled_sections),
        "rendered_sections": len(final_sections),
        "valid_ai_sections": len(ai_valid_sections),
        "fallback_sections": len(fallback_sections),
        "full_fallback": len(ai_valid_sections) == 0,
        "quality_tier": (ai_result.get("narrativeQuality") or {}).get("qualityTier"),
        "personalization_score": (ai_result.get("narrativeQuality") or {}).get("personalizationScore"),
        "avg_section_similarity": (ai_result.get("narrativeQuality") or {}).get("avgSectionSimilarity"),
    }
    if len(fallback_sections) >= settings.AI_FALLBACK_LOG_THRESHOLD:
        logger.warning("report_generation_summary", extra=summary_extra)
    else:
        logger.info("report_generation_summary", extra=summary_extra)

    generated_at = datetime.now(UTC).isoformat()
    merged_profile_snapshot = _merge_profile_snapshot(
        deterministic_profile_snapshot=deterministic.profile_snapshot,
        ai_profile_snapshot=ai_result.get("profileSnapshot"),
        canonical_normalized_input=deterministic.canonical_normalized_input,
    )
    if plan_config.key == "enterprise":
        merged_profile_snapshot = _sanitize_premium_profile_snapshot(merged_profile_snapshot)
    merged_dashboard = _merge_dashboard(
        deterministic_dashboard=deterministic.dashboard,
        ai_dashboard=ai_result.get("dashboard"),
    )
    legacy_input_normalized = _legacy_input_normalized_from_canonical(
        deterministic.canonical_normalized_input,
        current_problem=str(intake_data.get("current_problem") or "").strip(),
        plan_key=plan_config.key,
    )
    language_pref = (
        str(deterministic.canonical_normalized_input.get("language") or "").strip().lower()
        or "hindi"
    )

    final = {
        "meta": {
            "reportVersion": "7.1",
            "report_version": "7.1",
            "generatedAt": generated_at,
            "generated_at": generated_at,
            "plan": plan_config.key,
            "plan_tier": plan_config.key,
            "language": language_pref,
            "llm_only": bool(settings.AI_REPORT_FORCE_LLM_NARRATIVE),
            "enabledSections": plan_config.enabled_sections,
            "aiNarrativeDepth": plan_config.ai_narrative_depth,
            "deterministicSectionAvailability": deterministic.section_deterministic_availability,
            "droppedSections": ai_dropped + final_dropped,
            "finalRenderedSections": [section.get("sectionKey") for section in final_sections],
            "requestedSectionsCount": len(plan_config.enabled_sections),
            "renderedSectionsCount": len(final_sections),
            "validAiSectionsCount": len(ai_valid_sections),
            "fallbackSectionsCount": len(fallback_sections),
            "fullFallbackTriggered": len(ai_valid_sections) == 0,
            "narrativeQuality": ai_result.get("narrativeQuality") or {},
            "generationTrace": ai_result.get("generationTrace") or {},
            "strategyBlueprint": ai_result.get("strategyBlueprint") or {},
        },
        "reportTitle": ai_result.get("reportTitle", "Premium Numerology Report"),
        "plan": ai_result.get("plan", plan_config.key.upper()),
        "profileSnapshot": merged_profile_snapshot,
        "dashboard": merged_dashboard,
        "sections": final_sections,
        "closingInsight": ai_result.get(
            "closingInsight",
            "Use your strongest insights deliberately and review progress weekly.",
        ),
        "deterministic": {
            "normalizedInput": deterministic.canonical_normalized_input,
            "normalizedInputNested": deterministic.normalized_input,
            "normalizedInputCanonical": deterministic.canonical_normalized_input,
            "problemProfile": deterministic.problem_profile,
            "numerologyValues": deterministic.numerology_values,
            "basicMobileCore": basic_mobile_core if plan_config.key == "basic" else {},
            "derivedScores": deterministic.derived_scores,
            "sectionEligibility": deterministic.section_eligibility,
            "sectionDeterministicAvailability": deterministic.section_deterministic_availability,
            "sectionFactPacks": deterministic.section_fact_packs,
            "contradictionGuards": deterministic.contradiction_guards,
            "uniquenessFingerprint": deterministic.uniqueness_fingerprint,
        },
        "normalizedInput": deterministic.canonical_normalized_input,
        "input_normalized": legacy_input_normalized,
        # Keep cover/page-1 template unchanged and swap only BASIC content pages.
        "report_sections": (
            []
            if settings.AI_REPORT_FORCE_LLM_NARRATIVE
            else to_legacy_report_sections(final_sections)
        ),
    }

    return _strip_report_emoji_payload(_fix_mojibake_text(final))


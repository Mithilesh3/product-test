from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.modules.reports.blueprint import get_bilingual_section_heading, get_section_heading_pair
from app.modules.reports.metric_labels import to_metric_label
from app.modules.reports.plan_config import SECTIONS_REQUIRING_LOADED_ENERGIES
from app.modules.reports.presentation import display_label

FORBIDDEN_STRINGS = {
    "data not available",
    "no data available",
    "not available",
}

GENERIC_PLACEHOLDER_PATTERNS = {
    "lorem ipsum",
    "tbd",
    "to be added",
    "generic guidance",
    "placeholder",
}

RAW_INTERNAL_FIELDS = {
    "dharma_alignment_score",
    "financial_discipline_index",
    "confidence_score",
    "life_stability_index",
    "emotional_regulation_index",
    "karma_pressure_index",
    "data_completeness_score",
    "weakest_metric",
    "strongest_metric",
}

REQUIRED_SECTION_FIELDS = [
    "sectionKey",
    "summary",
    "keyStrength",
    "keyRisk",
    "practicalGuidance",
]

REQUIRED_TEXT_FIELDS = [
    "summary",
    "keyStrength",
    "keyRisk",
    "practicalGuidance",
]

SECTION_KEY_ALIASES = {
    "profile_overview": "profile",
    "profile_snapshot": "profile",
    "energy_dashboard": "dashboard",
    "personal_year_direction": "personal_year",
    "remedy_suggestions": "remedy",
}

DISPLAY_LABELS_HI = {
    "summary": display_label("summary", "सारांश"),
    "keyStrength": display_label("keyStrength", "मुख्य ताकत"),
    "keyRisk": display_label("keyRisk", "संभावित चुनौती"),
    "practicalGuidance": display_label("practicalGuidance", "व्यावहारिक सुझाव"),
    "energyIndicators": display_label("energy_indicators", "ऊर्जा संकेत"),
    "keyMetrics": display_label("key_metrics", "प्रमुख संकेतक"),
}

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")
HINDI_FALLBACK_TEXT = "यह भाग उपलब्ध इनपुट के आधार पर तैयार किया गया है।"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _contains_forbidden_text(value: str) -> bool:
    normalized = _clean_text(value).lower()
    return any(token in normalized for token in FORBIDDEN_STRINGS)


def _contains_generic_placeholder(value: str) -> bool:
    normalized = _clean_text(value).lower()
    return any(token in normalized for token in GENERIC_PLACEHOLDER_PATTERNS)


def _contains_raw_internal_field(value: str) -> bool:
    normalized = _clean_text(value).lower()
    return any(field in normalized for field in RAW_INTERNAL_FIELDS)


def _contains_devanagari(value: str) -> bool:
    return bool(DEVANAGARI_RE.search(_clean_text(value)))


def _contains_latin(value: str) -> bool:
    return bool(LATIN_RE.search(_clean_text(value)))


def _strip_latin(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    text = re.sub(r"[A-Za-z]", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"[|]{2,}", "|", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _extract_hindi_title(section: Dict[str, Any], fallback_key: str) -> str:
    title_hi = _clean_text(section.get("sectionTitleHindi"))
    if title_hi and _contains_devanagari(title_hi):
        return title_hi
    title_text = _clean_text(section.get("sectionTitle"))
    if title_text:
        parts = re.split(r"[|\n]+", title_text)
        for part in parts:
            if _contains_devanagari(part):
                return part.strip()
        cleaned = _strip_latin(title_text)
        if cleaned:
            return cleaned
    heading = get_section_heading_pair(fallback_key).get("hi") or ""
    return heading or "अनुभाग"


def _sanitize_hindi_text(value: str) -> str:
    cleaned = _strip_latin(value)
    return cleaned if cleaned else HINDI_FALLBACK_TEXT


def _is_hindi_dominant(value: str) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    devanagari_chars = len(DEVANAGARI_RE.findall(text))
    latin_chars = len(LATIN_RE.findall(text))
    if devanagari_chars == 0:
        return False
    if latin_chars == 0:
        return True
    return latin_chars <= max(12, devanagari_chars // 2)


def normalize_ai_section_shape(section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(section, dict):
        return None

    if bool(section.get("omitSection")):
        return None

    has_legacy_fields = any(field not in section for field in REQUIRED_SECTION_FIELDS) is False

    incoming_key = _clean_text(section.get("sectionKey"))
    normalized_key = SECTION_KEY_ALIASES.get(incoming_key, incoming_key)

    if has_legacy_fields:
        summary = _clean_text(section.get("summary"))
        key_strength = _clean_text(section.get("keyStrength"))
        key_risk = _clean_text(section.get("keyRisk"))
        practical_guidance = _clean_text(section.get("practicalGuidance"))
    else:
        content = _clean_text(section.get("content"))
        key_points = section.get("keyPoints") if isinstance(section.get("keyPoints"), list) else []
        key_points = [_clean_text(item) for item in key_points if _clean_text(item)]
        logical_reason = _clean_text(section.get("logicalReason"))

        summary = content or (key_points[0] if key_points else "")
        key_strength = key_points[0] if key_points else content
        key_risk = key_points[1] if len(key_points) > 1 else (key_points[0] if key_points else content)
        practical_guidance = logical_reason or (key_points[2] if len(key_points) > 2 else content)

    normalized = {
        "sectionKey": normalized_key,
        "sectionTitle": _clean_text(section.get("sectionTitle")) or get_bilingual_section_heading(normalized_key),
        "summary": summary,
        "keyStrength": key_strength,
        "keyRisk": key_risk,
        "practicalGuidance": practical_guidance,
        "loadedEnergies": [
            to_metric_label(_clean_text(item))
            for item in (section.get("loadedEnergies") or [])
            if _clean_text(item)
        ],
        "scoreHighlights": [
            {
                "label": to_metric_label(_clean_text(item.get("label"))),
                "value": _clean_text(item.get("value")),
            }
            for item in (section.get("scoreHighlights") or [])
            if isinstance(item, dict) and _clean_text(item.get("label")) and _clean_text(item.get("value"))
        ],
    }

    if isinstance(section.get("keyPoints"), list):
        normalized["keyPoints"] = [
            _clean_text(item) for item in (section.get("keyPoints") or []) if _clean_text(item)
        ]
    if _clean_text(section.get("logicalReason")):
        normalized["logicalReason"] = _clean_text(section.get("logicalReason"))
    if _clean_text(section.get("content")):
        normalized["content"] = _clean_text(section.get("content"))
    if _clean_text(section.get("sectionTitleHindi")):
        normalized["sectionTitleHindi"] = _clean_text(section.get("sectionTitleHindi"))
    if _clean_text(section.get("sectionTitleEnglish")):
        normalized["sectionTitleEnglish"] = _clean_text(section.get("sectionTitleEnglish"))

    if not normalized["sectionKey"]:
        return None
    if any(not _clean_text(normalized.get(field)) for field in REQUIRED_TEXT_FIELDS):
        return None
    return normalized


def validate_sections_for_render(
    sections: List[Dict[str, Any]],
    language_preference: str | None = "hindi",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    valid_sections: List[Dict[str, Any]] = []
    dropped_sections: List[Dict[str, str]] = []
    seen_summaries: set[str] = set()
    seen_summary_sentences: set[str] = set()
    language_mode = str(language_preference or "hindi").strip().lower()
    enforce_hindi_only = language_mode == "hindi"
    enforce_english_only = language_mode == "english"
    enforce_bilingual = language_mode == "bilingual"

    for section in sections:
        key = _clean_text(section.get("sectionKey")) or "unknown_section"

        if enforce_hindi_only:
            section["sectionTitle"] = _extract_hindi_title(section, key)
            if key != "basic_details":
                for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance"):
                    section[field] = _sanitize_hindi_text(_clean_text(section.get(field)))
        missing_fields = [
            field
            for field in REQUIRED_TEXT_FIELDS
            if not _clean_text(section.get(field))
        ]
        if missing_fields:
            dropped_sections.append(
                {
                    "sectionKey": key,
                    "reason": f"missing required fields: {', '.join(missing_fields)}",
                }
            )
            continue

        if not _clean_text(section.get("sectionTitle")):
            dropped_sections.append({"sectionKey": key, "reason": "missing required fields: sectionTitle"})
            continue

        summary = _clean_text(section.get("summary"))

        if any(
            _contains_forbidden_text(_clean_text(section.get(field)))
            for field in ("sectionTitle", "summary", "keyStrength", "keyRisk", "practicalGuidance")
        ):
            dropped_sections.append({"sectionKey": key, "reason": "contains forbidden placeholder text"})
            continue

        if any(
            _contains_generic_placeholder(_clean_text(section.get(field)))
            for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance")
        ):
            dropped_sections.append({"sectionKey": key, "reason": "contains generic placeholder narrative"})
            continue

        if any(
            _contains_raw_internal_field(_clean_text(section.get(field)))
            for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance")
        ):
            dropped_sections.append({"sectionKey": key, "reason": "contains raw internal field names"})
            continue

        if enforce_hindi_only and key != "basic_details" and any(
            not _is_hindi_dominant(_clean_text(section.get(field)))
            for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance")
        ):
            # Keep section count stable for Hindi reports: sanitize instead of dropping.
            for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance"):
                sanitized = _sanitize_hindi_text(_clean_text(section.get(field)))
                if not _is_hindi_dominant(sanitized):
                    sanitized = HINDI_FALLBACK_TEXT
                section[field] = sanitized

        if enforce_english_only and any(
            _contains_devanagari(_clean_text(section.get(field)))
            for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance", "sectionTitle")
        ):
            dropped_sections.append({"sectionKey": key, "reason": "contains Hindi characters in English mode"})
            continue

        if enforce_bilingual:
            title_text = _clean_text(section.get("sectionTitle"))
            title_hi = _clean_text(section.get("sectionTitleHindi"))
            title_en = _clean_text(section.get("sectionTitleEnglish"))
            if not _contains_devanagari(" ".join([title_text, title_hi, section.get("summary") or ""])):
                dropped_sections.append({"sectionKey": key, "reason": "missing Hindi content in bilingual mode"})
                continue
            if "|" not in title_text and not (title_hi and title_en):
                dropped_sections.append({"sectionKey": key, "reason": "missing bilingual title format"})
                continue

        summary_fingerprint = " ".join(summary.lower().split())
        if summary_fingerprint in seen_summaries:
            dropped_sections.append({"sectionKey": key, "reason": "repeated summary across sections"})
            continue
        seen_summaries.add(summary_fingerprint)

        sentence_fingerprints = {
            " ".join(chunk.strip().lower().split())
            for chunk in summary.replace("?", ".").replace("!", ".").split(".")
            if chunk.strip()
        }
        reused_sentences = [
            sentence for sentence in sentence_fingerprints if sentence in seen_summary_sentences
        ]
        if reused_sentences:
            dropped_sections.append(
                {"sectionKey": key, "reason": "summary reuses sentence patterns from another section"}
            )
            continue
        seen_summary_sentences.update(sentence_fingerprints)

        loaded = section.get("loadedEnergies") or []
        if key in SECTIONS_REQUIRING_LOADED_ENERGIES and not loaded:
            dropped_sections.append({"sectionKey": key, "reason": "missing loaded energies"})
            continue

        valid_sections.append(section)

    return valid_sections, dropped_sections


def to_legacy_report_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    legacy_sections: List[Dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        score_lines = [
            f"{DISPLAY_LABELS_HI['keyMetrics']}: {item.get('label')} - {item.get('value')}"
            for item in (section.get("scoreHighlights") or [])
            if _clean_text(item.get("label")) and _clean_text(item.get("value"))
        ]
        summary_text = _clean_text(section.get("summary"))
        strength_text = _clean_text(section.get("keyStrength"))
        risk_text = _clean_text(section.get("keyRisk"))
        guidance_text = _clean_text(section.get("practicalGuidance"))

        if section.get("sectionKey") == "lucky_numbers_unlucky_numbers_neutral_numbers":
            blocks = [
                f"{DISPLAY_LABELS_HI['summary']}: {summary_text}",
                f"शुभ अंक: {strength_text}",
                f"अशुभ अंक: {risk_text}",
                f"तटस्थ अंक: {guidance_text}",
            ]
        elif section.get("sectionKey") == "health_wealth_relationship_insight":
            blocks = [
                f"{DISPLAY_LABELS_HI['summary']}: {summary_text}",
                f"स्वास्थ्य संकेत: {strength_text}",
                f"धन संकेत: {risk_text}",
                f"संबंध संकेत: {guidance_text}",
            ]
        elif section.get("sectionKey") == "remedies":
            color_text = guidance_text
            mantra_text = ""
            if "||" in guidance_text:
                parts = [part.strip() for part in guidance_text.split("||") if part.strip()]
                if len(parts) >= 6:
                    blocks = [
                        f"{DISPLAY_LABELS_HI['summary']}: {summary_text}",
                        f"नाम सुधार अनुशंसा: {strength_text}",
                        f"शुभ अंक उपयोग: {risk_text}",
                        f"मोबाइल नंबर अनुशंसा: {parts[0]}",
                        f"मोबाइल कवर रंग: {parts[1]}",
                        f"वॉलपेपर सुझाव: {parts[2]}",
                        f"चार्जिंग दिशा: {parts[3]}",
                        f"बेसिक क्रिस्टल सुझाव: {parts[4]}",
                        f"मंत्र अनुशंसा: {parts[5]}",
                    ]
                else:
                    color_text, mantra_text = [part.strip() for part in guidance_text.split("||", 1)]
                    blocks = [
                        f"{DISPLAY_LABELS_HI['summary']}: {summary_text}",
                        f"शुभ अंक उपयोग: {strength_text}",
                        f"मोबाइल नंबर सुझाव: {risk_text}",
                        f"मोबाइल कवर रंग: {color_text or guidance_text}",
                        f"मंत्र सुझाव: {mantra_text or guidance_text}",
                    ]
            else:
                blocks = [
                    f"{DISPLAY_LABELS_HI['summary']}: {summary_text}",
                    f"शुभ अंक उपयोग: {strength_text}",
                    f"मोबाइल नंबर सुझाव: {risk_text}",
                    f"मोबाइल कवर रंग: {color_text or guidance_text}",
                    f"मंत्र सुझाव: {mantra_text or guidance_text}",
                ]
        else:
            blocks = [
                f"{DISPLAY_LABELS_HI['summary']}: {summary_text}",
                f"{DISPLAY_LABELS_HI['keyStrength']}: {strength_text}",
                f"{DISPLAY_LABELS_HI['keyRisk']}: {risk_text}",
                f"{DISPLAY_LABELS_HI['practicalGuidance']}: {guidance_text}",
            ]
        if section.get("loadedEnergies"):
            blocks.append(f"{DISPLAY_LABELS_HI['energyIndicators']}: {', '.join(section.get('loadedEnergies') or [])}")
        blocks.extend(score_lines)

        legacy_sections.append(
            {
                "order": index,
                "key": section.get("sectionKey"),
                "title": _clean_text(section.get("sectionTitle"))
                or get_bilingual_section_heading(_clean_text(section.get("sectionKey"))),
                "subtitle": "",
                "layout": "premium_card",
                "blocks": [line for line in blocks if _clean_text(line)],
            }
        )
    return legacy_sections


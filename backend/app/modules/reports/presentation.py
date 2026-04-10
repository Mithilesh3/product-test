from __future__ import annotations

from typing import Dict

from app.modules.reports.blueprint import (
    SECTION_HEADING_MAP as BLUEPRINT_SECTION_HEADING_MAP,
    SECTION_KEY_TO_HEADING_KEY,
    get_bilingual_section_heading,
)

SECTION_HEADING_MAP: Dict[str, Dict[str, str]] = {
    key: {"en": value["en"], "hi": value["hi"]}
    for key, value in BLUEPRINT_SECTION_HEADING_MAP.items()
}

LEGACY_SECTION_KEY_MAP: Dict[str, str] = {
    "executive_numerology_summary": "executive_summary",
    "core_numbers_analysis": "core_numbers",
    "number_interaction_analysis": "number_interaction",
    "name_vibration_optimization": "name_numerology",
    "email_identity_intelligence": "email_numerology",
    "numerology_personality_profile": "personality_profile",
    "current_life_phase_insight": "focus_snapshot",
    "personal_year_forecast": "personal_year_direction",
    "lucky_numbers_favorable_dates": "lucky_dates",
    "remedies_lifestyle_adjustments": "remedy_suggestions",
    "closing_numerology_guidance": "closing_summary",
    "loshu_grid_interpretation": "lo_shu_grid",
    "missing_numbers_analysis": "missing_numbers",
    "repeating_numbers_impact": "repeating_numbers",
    "mobile_number_numerology": "mobile_numerology",
    "mobile_number_intelligence": "mobile_numerology",
    "mobile_life_number_compatibility": "mobile_life_compatibility",
    "business_name_intelligence": "business_numerology",
    "digital_discipline": "digital_numerology",
    "career_financial_tendencies": "career_financial",
    "health_tendencies_from_numbers": "health_tendencies",
    "decision_intelligence": "decision_style",
    "karmic_pattern_intelligence": "growth_blockers",
    "strategic_execution_roadmap": "action_plan_90_days",
    "life_cycle_timeline": "life_timeline",
    "closing_synthesis": "strategic_life_theme",
    "leadership_intelligence": "leadership_archetype",
    "wealth_energy_blueprint": "wealth_strategy",
    "strategic_timing_intelligence": "decision_timing",
}

DISPLAY_LABEL_MAP: Dict[str, str] = {
    "summary": "सारांश",
    "key_strength": "मुख्य ताकत",
    "keyStrength": "मुख्य ताकत",
    "key_risk": "संभावित चुनौती",
    "keyRisk": "संभावित चुनौती",
    "strategic_focus": "व्यावहारिक सुझाव",
    "practical_guidance": "व्यावहारिक सुझाव",
    "practicalGuidance": "व्यावहारिक सुझाव",
    "energy_indicators": "ऊर्जा संकेत",
    "key_metrics": "प्रमुख संकेतक",
    "confidence_score": "निर्णय स्पष्टता स्कोर",
    "dharma_alignment_score": "धर्म संरेखण स्कोर",
    "financial_discipline_index": "वित्त अनुशासन सूचकांक",
    "life_stability_index": "जीवन स्थिरता सूचकांक",
    "emotional_regulation_index": "भावनात्मक संतुलन सूचकांक",
    "karma_pressure_index": "कर्म दबाव सूचकांक",
    "data_completeness_score": "डेटा पूर्णता स्कोर",
    "general_alignment": "समग्र जीवन सामंजस्य",
    "career_growth": "करियर प्रगति",
    "finance_debt": "वित्त और ऋण संतुलन",
    "relationship": "संबंध संतुलन",
    "health_stability": "स्वास्थ्य स्थिरता",
    "emotional_confusion": "भावनात्मक स्पष्टता",
    "business_decision": "व्यावसायिक निर्णय",
    "job": "नौकरी",
    "business": "व्यवसाय",
    "hybrid": "नौकरी + व्यवसाय",
    "single": "अविवाहित",
    "married": "विवाहित",
    "fast": "त्वरित",
    "research": "विश्लेषण-आधारित",
    "advice": "परामर्श-आधारित",
    "emotional": "भावनात्मक",
    "balanced": "संतुलित",
    "overthink": "अधिक-विचार",
    "impulsive": "आवेगपूर्ण",
    "withdraw": "संकोची प्रतिक्रिया",
    "take_control": "नियंत्रित प्रतिक्रिया",
    "discipline": "अनुशासन",
    "patience": "धैर्य",
    "confidence": "आत्मविश्वास",
    "focus": "केंद्रितता",
}


def canonical_section_key(section_key: str) -> str:
    raw = str(section_key or "").strip()
    if not raw:
        return ""
    legacy_normalized = LEGACY_SECTION_KEY_MAP.get(raw, raw)
    return SECTION_KEY_TO_HEADING_KEY.get(legacy_normalized, legacy_normalized)


def display_label(raw_key: str, default: str = "") -> str:
    key = str(raw_key or "").strip()
    if not key:
        return default
    return DISPLAY_LABEL_MAP.get(key, default or key)


def display_value(raw_value: str, default: str = "") -> str:
    text = str(raw_value or "").strip()
    if not text:
        return default
    normalized = text.lower().replace("-", "_").replace(" ", "_")
    return DISPLAY_LABEL_MAP.get(normalized, text)


def bilingual_heading(section_key: str, fallback_title: str = "") -> str:
    canonical = canonical_section_key(section_key)
    if canonical:
        return get_bilingual_section_heading(canonical)

    title = str(fallback_title or "").strip()
    if "\n" in title:
        return title
    if "|" in title:
        left, right = [part.strip() for part in title.split("|", 1)]
        if left and right:
            return f"{right}\n{left}"
    cleaned = title.replace("_", " ").strip() or "Section"
    return f"{cleaned}\n{cleaned}"

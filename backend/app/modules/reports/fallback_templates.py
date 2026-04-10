from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.modules.reports.blueprint import get_bilingual_section_heading
from app.modules.reports.metric_labels import to_metric_label
from app.modules.reports.pipeline_types import ReportSection
from app.modules.reports.presentation import display_value
from app.modules.numerology.chaldean import calculate_name_number

SECTION_TITLES: Dict[str, str] = {
    "plan_overview": "योजना अवलोकन",
    "required_inputs": "आवश्यक इनपुट",
    "core_purpose": "मुख्य उद्देश्य",
    "primary_focus": "मुख्य फोकस",
    "deterministic_engine": "निर्धारित इंजन",
    "ai_generation_layer": "AI निर्माण परत",
    "recommendation_logic": "सिफारिश तर्क",
    "narration_style": "वर्णन शैली",
    "ai_narration_role": "AI वर्णन भूमिका",
    "deterministic_role": "निर्धारित भूमिका",
    "ai_should_not_do": "AI क्या न करे",
    "ai_should_do": "AI क्या करे",
    "basic_details": "मूल विवरण",
    "mulank_analysis": "मूलांक विश्लेषण",
    "bhagyank_analysis": "भाग्यांक विश्लेषण",
    "mobile_number_total": "मोबाइल नंबर कुल योग",
    "mobile_digit_analysis": "मोबाइल अंकों का विश्लेषण",
    "mobile_energy_description": "मोबाइल ऊर्जा विवरण",
    "dob_mobile_alignment": "जन्मतिथि और मोबाइल सामंजस्य",
    "mulank_connection": "मूलांक कनेक्शन",
    "bhagyank_connection": "भाग्यांक कनेक्शन",
    "combo_analysis": "संयुक्त विश्लेषण",
    "lucky_numbers_unlucky_numbers_neutral_numbers": "शुभ, अशुभ और तटस्थ अंक",
    "lucky_numbers": "शुभ अंक",
    "unlucky_numbers": "अशुभ अंक",
    "neutral_numbers": "तटस्थ अंक",
    "color_recommendation": "रंग सुझाव",
    "health_wealth_relationship_insight": "स्वास्थ्य, धन और संबंध संकेत",
    "health_insight": "स्वास्थ्य अंतर्दृष्टि",
    "wealth_insight": "धन अंतर्दृष्टि",
    "relationship_insight": "संबंध अंतर्दृष्टि",
    "remedies": "उपाय",
    "remedies_logic": "उपाय तर्क",
    "lucky_number_usage": "शुभ अंक उपयोग",
    "mobile_recommendation": "मोबाइल अनुशंसा",
    "mobile_cover_color": "मोबाइल कवर रंग",
    "mantra_recommendation": "मंत्र अनुशंसा",
    "final_outcome": "अंतिम परिणाम",
    "name_analysis_type": "नाम विश्लेषण प्रकार",
    "name_correction": "नाम सुधार",
    "prefix_suffix_suggestion": "प्रिफिक्स/सुफिक्स सुझाव",
    "name_correction_basis": "नाम सुधार आधार",
    "dob_name_alignment": "जन्मतिथि + नाम संरेखण",
    "wallpaper_suggestion": "वॉलपेपर सुझाव",
    "charging_direction": "चार्जिंग दिशा",
    "bracelet_crystal_suggestion": "कंगन/क्रिस्टल सुझाव",
    "gemstone_recommendation": "रत्न अनुशंसा",
    "monthly_cycle_analysis": "मासिक/चक्र विश्लेषण",
    "astrology_integration": "ज्योतिष एकीकरण",
    "vedic_logic_integration": "वैदिक तर्क एकीकरण",
    "planetary_support_mapping": "ग्रह समर्थन मैपिंग",
    "business_brand_naming": "व्यवसाय/ब्रांड नाम",
    "signature_analysis": "हस्ताक्षर विश्लेषण",
    "space_direction_guidance": "स्थान/दिशा मार्गदर्शन",
    "ongoing_guidance": "निरंतर मार्गदर्शन",
    "profile": "प्रोफाइल अवलोकन",
    "dashboard": "ऊर्जा डैशबोर्ड",
    "executive_summary": "कार्यकारी सार",
    "core_numbers": "मुख्य अंक",
    "number_interaction": "अंक अंतःक्रिया",
    "name_numerology": "नाम अंक विश्लेषण",
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
    "name_analysis": "नाम विश्लेषण",
    "name_number_total": "नाम नंबर कुल योग",
    "name_correction_options": "नाम सुधार विकल्प",
    "prefix_suffix_suggestions": "प्रिफिक्स / सुफिक्स सुझाव",
    "name_correction_logic_explanation": "नाम सुधार तर्क",
    "name_mobile_alignment": "नाम और मोबाइल सामंजस्य",
    "mobile_name_combo_recommendation": "मोबाइल-नाम संयोजन सुझाव",
    "summary_and_priority_actions": "सारांश और प्राथमिक कार्य",
    "email_numerology": "ईमेल अंक विश्लेषण",
    "personality_profile": "व्यक्तित्व प्रोफाइल",
    "focus_snapshot": "फोकस स्नैपशॉट",
    "personal_year": "व्यक्तिगत वर्ष दिशा",
    "lucky_dates": "शुभ तिथियाँ",
    "color_alignment": "रंग सामंजस्य",
    "remedy": "उपाय सुझाव",
    "closing_summary": "समापन सार",
    "lo_shu_grid": "लो-शू ग्रिड",
    "missing_numbers": "अनुपस्थित अंक",
    "repeating_numbers": "दोहराते अंक",
    "mobile_numerology": "मोबाइल अंक विश्लेषण",
    "mobile_life_compatibility": "मोबाइल-जीवन संगतता",
    "business_numerology": "व्यवसाय अंक विश्लेषण",
    "digital_numerology": "डिजिटल अंक विश्लेषण",
    "career_financial": "करियर और वित्त",
    "relationship_patterns": "संबंध पैटर्न",
    "health_tendencies": "स्वास्थ्य प्रवृत्तियाँ",
    "action_plan_90_days": "90-दिवसीय कार्य योजना",
    "growth_blockers": "विकास अवरोध",
    "decision_style": "निर्णय शैली",
    "life_timeline": "जीवन समयरेखा",
    "strategic_life_theme": "रणनीतिक जीवन थीम",
    "leadership_archetype": "लीडरशिप आर्केटाइप",
    "wealth_strategy": "वेल्थ रणनीति",
    "opportunity_windows": "अवसर विंडो",
    "decision_timing": "निर्णय समय",
    "roadmap_12_months": "12-महीने रोडमैप",
    "outlook_3_years": "3-वर्षीय दृष्टिकोण",
    "life_alignment_scorecard": "लाइफ एलाइनमेंट स्कोरकार्ड",
    "strategic_correction": "रणनीतिक सुधार",
    "growth_blueprint": "ग्रोथ ब्लूप्रिंट",

    "mobile_digit_pattern": "मोबाइल अंक पैटर्न",
    "life_area_impact": "जीवन क्षेत्र प्रभाव",
    "name_vibration_optimization": "नाम कंपन अनुकूलन",
    "name_mobile_combo": "नाम + मोबाइल संयोजन",
    "numerology_architecture": "अंक वास्तुकला",
    "planetary_influence": "ग्रह प्रभाव",
    "vedic_remedy": "वैदिक उपाय",
    "karmic_pattern_intelligence": "कर्मिक पैटर्न बुद्धि",
    "pinnacle_challenge_cycle_intelligence": "पिनैकल व चैलेंज चक्र",
    "signature_intelligence": "हस्ताक्षर बुद्धि",
    "business_name_intelligence": "व्यवसाय / ब्रांड नाम",
    "environment_alignment": "स्थान / दिशा संरेखण",
    "strategic_execution_roadmap": "रणनीतिक निष्पादन रोडमैप",
}

SECTION_METRICS: Dict[str, List[str]] = {
    "plan_overview": ["confidence_score", "life_stability_index"],
    "required_inputs": ["data_completeness_score", "confidence_score"],
    "core_purpose": ["dharma_alignment_score", "confidence_score"],
    "primary_focus": ["confidence_score", "life_stability_index"],
    "deterministic_engine": ["confidence_score", "life_stability_index"],
    "ai_generation_layer": ["data_completeness_score", "confidence_score"],
    "recommendation_logic": ["confidence_score", "karma_pressure_index"],
    "narration_style": ["confidence_score"],
    "ai_narration_role": ["confidence_score", "dharma_alignment_score"],
    "deterministic_role": ["life_stability_index", "confidence_score"],
    "ai_should_not_do": ["karma_pressure_index"],
    "ai_should_do": ["confidence_score", "dharma_alignment_score"],
    "basic_details": ["confidence_score", "life_stability_index"],
    "mulank_analysis": ["confidence_score", "life_stability_index"],
    "bhagyank_analysis": ["confidence_score", "life_stability_index"],
    "mobile_number_total": ["confidence_score", "financial_discipline_index"],
    "mobile_digit_analysis": ["life_stability_index", "confidence_score"],
    "mobile_energy_description": ["dharma_alignment_score", "emotional_regulation_index"],
    "dob_mobile_alignment": ["confidence_score", "dharma_alignment_score"],
    "mulank_connection": ["confidence_score", "emotional_regulation_index"],
    "bhagyank_connection": ["confidence_score", "life_stability_index"],
    "combo_analysis": ["confidence_score", "dharma_alignment_score"],
    "lucky_numbers_unlucky_numbers_neutral_numbers": ["confidence_score", "life_stability_index"],
    "lucky_numbers": ["confidence_score"],
    "unlucky_numbers": ["karma_pressure_index"],
    "neutral_numbers": ["life_stability_index"],
    "color_recommendation": ["dharma_alignment_score"],
    "health_wealth_relationship_insight": [
        "emotional_regulation_index",
        "financial_discipline_index",
        "life_stability_index",
    ],
    "health_insight": ["emotional_regulation_index"],
    "wealth_insight": ["financial_discipline_index"],
    "relationship_insight": ["emotional_regulation_index"],
    "remedies": ["karma_pressure_index", "dharma_alignment_score"],
    "remedies_logic": ["karma_pressure_index"],
    "lucky_number_usage": ["confidence_score"],
    "mobile_recommendation": ["life_stability_index", "confidence_score"],
    "mobile_cover_color": ["dharma_alignment_score"],
    "mantra_recommendation": ["dharma_alignment_score"],
    "final_outcome": ["confidence_score", "life_stability_index"],
    "name_analysis_type": ["confidence_score", "dharma_alignment_score"],
    "name_correction": ["confidence_score"],
    "prefix_suffix_suggestion": ["confidence_score"],
    "name_correction_basis": ["dharma_alignment_score"],
    "dob_name_alignment": ["confidence_score"],
    "wallpaper_suggestion": ["dharma_alignment_score"],
    "charging_direction": ["life_stability_index"],
    "bracelet_crystal_suggestion": ["dharma_alignment_score"],
    "gemstone_recommendation": ["dharma_alignment_score"],
    "monthly_cycle_analysis": ["confidence_score", "life_stability_index"],
    "astrology_integration": ["dharma_alignment_score"],
    "vedic_logic_integration": ["dharma_alignment_score"],
    "planetary_support_mapping": ["dharma_alignment_score", "life_stability_index"],
    "business_brand_naming": ["financial_discipline_index"],
    "signature_analysis": ["confidence_score"],
    "space_direction_guidance": ["life_stability_index"],
    "ongoing_guidance": ["confidence_score", "karma_pressure_index"],
    "profile": ["confidence_score", "life_stability_index"],
    "dashboard": ["confidence_score", "karma_pressure_index", "dharma_alignment_score"],
    "executive_summary": ["confidence_score", "life_stability_index", "financial_discipline_index"],
    "core_numbers": ["confidence_score", "dharma_alignment_score"],
    "number_interaction": ["confidence_score", "emotional_regulation_index"],
    "personality_profile": ["emotional_regulation_index", "confidence_score"],
    "focus_snapshot": ["dharma_alignment_score", "confidence_score"],
    "personal_year": ["confidence_score", "life_stability_index"],
    "lucky_dates": ["life_stability_index", "dharma_alignment_score"],
    "color_alignment": ["dharma_alignment_score", "emotional_regulation_index"],
    "remedy": ["karma_pressure_index", "confidence_score"],
    "closing_summary": ["confidence_score", "financial_discipline_index", "life_stability_index"],
    "lo_shu_grid": ["life_stability_index", "confidence_score"],
    "missing_numbers": ["karma_pressure_index", "life_stability_index"],
    "repeating_numbers": ["karma_pressure_index", "emotional_regulation_index"],
    "mobile_numerology": ["confidence_score", "financial_discipline_index"],
    "mobile_life_compatibility": ["dharma_alignment_score", "confidence_score"],
    "career_financial": ["financial_discipline_index", "confidence_score", "life_stability_index"],
    "relationship_patterns": ["emotional_regulation_index", "dharma_alignment_score"],
    "health_tendencies": ["emotional_regulation_index", "life_stability_index"],
    "action_plan_90_days": ["weakest_metric_score", "confidence_score"],
    "growth_blockers": ["karma_pressure_index", "weakest_metric_score"],
    "decision_style": ["confidence_score", "emotional_regulation_index"],
    "life_timeline": ["life_stability_index", "confidence_score"],
    "strategic_life_theme": ["dharma_alignment_score", "confidence_score"],
    "leadership_archetype": ["confidence_score", "emotional_regulation_index"],
    "wealth_strategy": ["financial_discipline_index", "life_stability_index", "confidence_score"],
    "opportunity_windows": ["confidence_score", "dharma_alignment_score"],
    "decision_timing": ["confidence_score", "emotional_regulation_index"],
    "roadmap_12_months": ["confidence_score", "financial_discipline_index"],
    "outlook_3_years": ["life_stability_index", "dharma_alignment_score"],
    "life_alignment_scorecard": [
        "dharma_alignment_score",
        "life_stability_index",
        "emotional_regulation_index",
        "financial_discipline_index",
    ],
    "strategic_correction": ["karma_pressure_index", "weakest_metric_score", "confidence_score"],
    "growth_blueprint": ["confidence_score", "dharma_alignment_score", "financial_discipline_index"],

    "mobile_digit_pattern": ["life_stability_index", "confidence_score"],
    "life_area_impact": ["life_stability_index", "financial_discipline_index", "emotional_regulation_index"],
    "name_vibration_optimization": ["confidence_score", "dharma_alignment_score"],
    "name_mobile_combo": ["confidence_score", "dharma_alignment_score"],
    "numerology_architecture": ["confidence_score", "dharma_alignment_score"],
    "planetary_influence": ["dharma_alignment_score", "emotional_regulation_index"],
    "vedic_remedy": ["karma_pressure_index", "emotional_regulation_index"],
    "karmic_pattern_intelligence": ["karma_pressure_index", "confidence_score"],
    "pinnacle_challenge_cycle_intelligence": ["life_stability_index", "confidence_score"],
    "signature_intelligence": ["confidence_score", "dharma_alignment_score"],
    "business_name_intelligence": ["financial_discipline_index", "confidence_score"],
    "environment_alignment": ["life_stability_index", "emotional_regulation_index"],
    "strategic_execution_roadmap": ["confidence_score", "financial_discipline_index"],
}

# Premium-only metric mapping to reduce repeated trait labels across pages.
# Keeps scoring logic unchanged and only varies which existing scores are surfaced.
PREMIUM_SECTION_METRICS: Dict[str, List[str]] = {
    "full_identity_profile": ["confidence_score", "dharma_alignment_score"],
    "core_numbers": ["confidence_score", "life_stability_index"],
    "advanced_name_numerology": ["confidence_score", "dharma_alignment_score"],
    "karmic_name_analysis": ["karma_pressure_index", "dharma_alignment_score"],
    "planetary_name_support_mapping": ["dharma_alignment_score", "confidence_score"],
    "multi_name_correction_options": ["confidence_score", "karma_pressure_index"],
    "name_optimization_scoring": ["confidence_score", "dharma_alignment_score"],
    "prefix_suffix_advanced_logic": ["dharma_alignment_score", "confidence_score"],
    "mobile_numerology_advanced": ["emotional_regulation_index", "financial_discipline_index"],
    "mobile_digit_micro_analysis": ["emotional_regulation_index", "life_stability_index"],
    "mobile_energy_forecasting": ["emotional_regulation_index", "dharma_alignment_score"],
    "name_mobile_alignment": ["dharma_alignment_score", "emotional_regulation_index"],
    "dob_name_alignment": ["dharma_alignment_score", "confidence_score"],
    "dob_mobile_alignment": ["emotional_regulation_index", "dharma_alignment_score"],
    "full_system_alignment_score": ["dharma_alignment_score", "confidence_score"],
    "strength_vs_risk_matrix": ["confidence_score", "karma_pressure_index"],
    "life_area_scores": ["financial_discipline_index", "emotional_regulation_index"],
    "mulank_deep_analysis": ["confidence_score", "life_stability_index"],
    "bhagyank_destiny_roadmap": ["dharma_alignment_score", "life_stability_index"],
    "lo_shu_grid_advanced": ["life_stability_index", "karma_pressure_index"],
    "planetary_influence_mapping": ["dharma_alignment_score", "confidence_score"],
    "current_planetary_phase": ["dharma_alignment_score", "life_stability_index"],
    "upcoming_transit_highlights": ["life_stability_index", "dharma_alignment_score"],
    "personal_year_analysis": ["life_stability_index", "confidence_score"],
    "monthly_cycle_analysis": ["life_stability_index", "confidence_score"],
    "critical_decision_windows": ["confidence_score", "dharma_alignment_score"],
    "wealth_cycle_analysis": ["financial_discipline_index", "confidence_score"],
    "career_growth_timeline": ["financial_discipline_index", "confidence_score"],
    "relationship_timing_patterns": ["emotional_regulation_index", "dharma_alignment_score"],
    "dynamic_lucky_numbers": ["confidence_score", "dharma_alignment_score"],
    "situational_caution_numbers": ["karma_pressure_index", "dharma_alignment_score"],
    "neutral_number_strategy_usage": ["life_stability_index", "confidence_score"],
    "color_strategy": ["dharma_alignment_score", "life_stability_index"],
    "energy_objects_recommendation": ["emotional_regulation_index", "life_stability_index"],
    "advanced_remedies_engine": ["karma_pressure_index", "life_stability_index"],
    "business_brand_naming": ["financial_discipline_index", "confidence_score"],
    "signature_energy_analysis": ["confidence_score", "dharma_alignment_score"],
    "mobile_optimization_strategy": ["emotional_regulation_index", "life_stability_index"],
    "life_strategy_recommendations": ["confidence_score", "dharma_alignment_score"],
    "priority_action_plan": ["confidence_score", "karma_pressure_index"],
    "risk_alerts_and_mitigation": ["karma_pressure_index", "life_stability_index"],
    "premium_summary_narrative": ["confidence_score", "dharma_alignment_score"],
}

SECTION_KEY_ALIASES: Dict[str, str] = {
    "prefix_suffix_suggestions": "prefix_suffix_suggestion",
    "mobile_number_recommendation": "mobile_recommendation",
    "basic_crystal_suggestion": "bracelet_crystal_suggestion",
    "name_mobile_alignment_scored": "name_mobile_combo",
    "dob_name_alignment_deep": "dob_name_alignment",
    "dob_mobile_alignment_timing_logic": "dob_mobile_alignment",
}

COLOR_MAP = {
    1: ["स्वर्ण", "क्रीमी सफेद"],
    2: ["मोती सफेद", "चांदी"],
    3: ["पीला", "केसरिया"],
    4: ["स्टील ग्रे", "नीला"],
    5: ["हरा", "टील"],
    6: ["गुलाबी", "हल्का नीला"],
    7: ["इंडिगो", "ऑफ व्हाइट"],
    8: ["नेवी", "चारकोल"],
    9: ["लाल", "गहरा मरून"],
}

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _display(raw_value: Any, default: str) -> str:
    text = _safe_text(raw_value)
    if not text:
        return default
    return display_value(text, default) or default


def _hindi_context(raw_value: Any, default: str) -> str:
    text = _safe_text(raw_value)
    if not text:
        return default
    normalized = text.lower()
    if normalized in {"not provided", "na", "n/a", "none", "null", "unknown"}:
        return default
    return text


def _sanitize_identity_value(raw_value: Any) -> str:
    text = _safe_text(raw_value)
    if not text:
        return ""
    text = re.sub(r"\s*->\s*\d+\s*", " ", text)
    text = re.sub(r"\|\s*\|", " ", text)
    text = re.sub(r"[|]{2,}", " ", text)
    text = re.sub(r"@\.|\.@", "", text)
    text = re.sub(r"\s*,\s*", ", ", text).strip()
    text = text.strip(", ")
    text = re.sub(r"\s{2,}", " ", text).strip()
    if not text or re.fullmatch(r"[\s|.@।-]+", text):
        return ""
    return text


def _is_valid_email_token(value: str) -> bool:
    if "@" not in value:
        return True
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))




PREMIUM_NUMBER_TRAITS: Dict[int, Tuple[str, str, str]] = {
    1: ("नेतृत्व", "एकतरफा निर्णय", "सहयोगी योजना"),
    2: ("संतुलन", "अनिर्णय", "सीमाएँ स्पष्ट"),
    3: ("संचार", "ध्यान भटकना", "लिखित योजना"),
    4: ("अनुशासन", "जड़ता", "लचीलापन"),
    5: ("अनुकूलन", "अस्थिरता", "दिनचर्या"),
    6: ("जिम्मेदारी", "अति-चिंता", "प्राथमिकता"),
    7: ("विश्लेषण", "अति-शंका", "व्यवहारिक सत्यापन"),
    8: ("प्रबंधन", "कठोरता", "न्याय-संतुलन"),
    9: ("दृष्टि", "अति-भावनात्मकता", "ग्राउंडिंग"),
}


def _premium_number_trait(num: int | None) -> Tuple[str, str, str]:
    if isinstance(num, int) and num in PREMIUM_NUMBER_TRAITS:
        return PREMIUM_NUMBER_TRAITS[num]
    return ("संतुलन", "अनिश्चितता", "स्थिर रुटीन")


def _alignment_label_premium(name_num: int | None, mobile_num: int | None) -> str:
    if not isinstance(name_num, int) or not isinstance(mobile_num, int):
        return "मध्यम सामंजस्य"
    diff = abs(name_num - mobile_num)
    if diff == 0:
        return "उच्च सामंजस्य"
    if diff <= 2:
        return "मध्यम सामंजस्य"
    return "मिश्रित सामंजस्य"


def _premium_dynamic_traits(
    section_key: str,
    numerology_values: Dict[str, Any],
    normalized_input: Dict[str, Any],
    derived_scores: Dict[str, Any],
) -> Tuple[str, str, str]:
    pyth = numerology_values.get("pythagorean") or {}
    chaldean = numerology_values.get("chaldean") or {}
    mobile = numerology_values.get("mobile_analysis") or {}
    birth = pyth.get("birth_number")
    life_path = pyth.get("life_path_number")
    name_num = chaldean.get("name_number")
    mobile_num = mobile.get("mobile_vibration")

    label = "संयोजन"
    num = birth
    key_lower = section_key.lower()
    if "mulank" in key_lower:
        label, num = "मूलांक", birth
    elif "bhagyank" in key_lower or "destiny" in key_lower:
        label, num = "भाग्यांक", life_path
    elif "name" in key_lower or "signature" in key_lower or "brand" in key_lower:
        label, num = "नाम अंक", name_num
    elif "mobile" in key_lower:
        label, num = "मोबाइल कंपन", mobile_num

    strength_trait, risk_trait, action_trait = _premium_number_trait(num if isinstance(num, int) else None)
    focus = _safe_text(normalized_input.get("currentProblem") or normalized_input.get("focusArea") or "निष्पादन")

    templates = [
        (
            f"{label} {num or ''} की ऊर्जा {strength_trait} को मजबूत करती है।",
            f"{risk_trait} बढ़ने पर {focus} में असंतुलन आ सकता है।",
            f"{action_trait} अधारित 21-दिवसीय रुटीन रखें और साप्ताहिक रिव्यू करें।",
        ),
        (
            f"{label} {num or ''} आपके चरित्र में {strength_trait} का स्थिर सहारा देता है।",
            f"यदि {risk_trait} बढे, तो निर्णय लय विखर सकता है।",
            f"{focus} के लिए {action_trait} के 2 छोटे कदम तैय करके रोजाना निभाएँ।",
        ),
        (
            f"{label} {num or ''} प्रोफ़ाइल में {strength_trait} आपका प्रमुख लीवर है।",
            f"{risk_trait} के कारण समय-बध्द कार्य प्रभावित हो सकते हैं।",
            f"{action_trait} के साथ स्पष्ट टास्क स्लॉट बनाकर {focus} को ट्रैक करें।",
        ),
    ]

    if "alignment" in key_lower or "score" in key_lower or "matrix" in key_lower:
        label_text = _alignment_label_premium(name_num if isinstance(name_num, int) else None, mobile_num if isinstance(mobile_num, int) else None)
        strength = f"नाम अंक {name_num or '-'} और मोबाइल कंपन {mobile_num or '-'} में {label_text} दिखता है।"
        risk = "अलग-अलग उपयोग रिदम से सामंजस्य कमजोर पड़ सकता है।"
        action = "पहचान और संचार की टाइमिंग एक जैसी रखकर सामंजस्य बढ़ाएँ।"
        return strength, risk, action

    index = sum(ord(ch) for ch in section_key) % len(templates)
    return templates[index]


def _premium_section_summary(
    section_key: str,
    numerology_values: Dict[str, Any],
    normalized_input: Dict[str, Any],
) -> str:
    pyth = numerology_values.get("pythagorean") or {}
    chaldean = numerology_values.get("chaldean") or {}
    mobile = numerology_values.get("mobile_analysis") or {}
    birth = pyth.get("birth_number")
    life_path = pyth.get("life_path_number")
    name_num = chaldean.get("name_number")
    mobile_num = mobile.get("mobile_vibration")
    focus = _safe_text(normalized_input.get("currentProblem") or normalized_input.get("focusArea") or "सुधार")

    key_lower = section_key.lower()
    if "mulank" in key_lower:
        return f"मूलांक {birth or '-'} का गहन अध्ययन आपके स्वभाव की मूल दिशा को स्पष्ट करता है।"
    if "bhagyank" in key_lower or "destiny" in key_lower:
        return f"भाग्यांक {life_path or '-'} आपकी दीर्घकालिक प्रगति और निर्णय गति को सेट करता है।"
    if "full_identity_profile" in key_lower:
        return "पूर्ण पहचान प्रोफ़ाइल आपके मूल विवरण और व्यक्तिगत संदर्भ को स्पष्ट करता है।"
    if "core_numbers" in key_lower:
        return "मुख्य अंक आपके आधार-ऊर्जा चक्र की प्राथमिक दिशा दिखाते हैं।"
    if "advanced_name_numerology" in key_lower or "name_analysis" in key_lower or "name" in key_lower:
        return f"नाम अंक {name_num or '-'} आपकी पहचान और सार्वजनिक प्रभाव की दिशा तय करता है।"
    if "mobile" in key_lower and "alignment" not in key_lower:
        return f"मोबाइल कंपन {mobile_num or '-'} आपके व्यवहार और निर्णय-लय पर सीधा असर दिखाता है।"
    if "planetary_name_support_mapping" in key_lower:
        return "ग्रह-आधारित नाम समर्थन मैपिंग नाम ऊर्जा के सहायक प्रभाव को दर्शाती है।"
    if "multi_name_correction_options" in key_lower:
        return "बहु-नाम सुधार विकल्प पहचान संतुलन के व्यावहारिक मार्ग दिखाते हैं।"
    if "name_optimization_scoring" in key_lower:
        return "नाम अनुकूलन स्कोर वर्तमान नाम ऊर्जा की गुणवत्ता मापता है।"
    if "prefix_suffix_advanced_logic" in key_lower:
        return "उन्नत प्रिफिक्स/सुफिक्स तर्क सुधार दिशा का कारण स्पष्ट करता है।"
    if "mobile_digit_micro_analysis" in key_lower:
        return "मोबाइल अंकों का सूक्ष्म विश्लेषण दोहराव और कमी के प्रभाव दिखाता है।"
    if "mobile_energy_forecasting" in key_lower:
        return "मोबाइल ऊर्जा पूर्वानुमान अगले चरण की प्रतिक्रिया-लय को बताता है।"
    if "alignment" in key_lower:
        alignment = _alignment_label_premium(
            name_num if isinstance(name_num, int) else None,
            mobile_num if isinstance(mobile_num, int) else None,
        )
        return f"नाम {name_num or '-'} और मोबाइल {mobile_num or '-'} में {alignment} का संकेत मिलता है।"
    if "monthly_cycle" in key_lower:
        return "मासिक चक्र विश्लेषण आने वाले 30 दिनों की ऊर्जा-लय को दर्शाता है।"
    if "personal_year" in key_lower:
        return "व्यक्तिगत वर्ष विश्लेषण इस वर्ष की थीम और प्राथमिक दिशा स्पष्ट करता है।"
    if "critical_decision_windows" in key_lower:
        return "महत्वपूर्ण निर्णय समय-खिड़कियाँ सही टाइमिंग पर निर्णय लेने में मदद देती हैं।"
    if "upcoming_transit_highlights" in key_lower:
        return "आगामी गोचर संकेत अगले चरण में ऊर्जा-परिवर्तन की दिशा दिखाते हैं।"
    if "career_growth_timeline" in key_lower:
        return "करियर विकास टाइमलाइन आपके प्रगति चरणों को क्रमबद्ध रूप से दिखाती है।"
    if "wealth_cycle_analysis" in key_lower:
        return "धन चक्र विश्लेषण आय-व्यवहार की स्थिरता और जोखिम स्तर बताता है।"
    if "relationship_timing_patterns" in key_lower:
        return "संबंध समय-पैटर्न भावनात्मक तालमेल और प्रतिक्रिया चक्र को स्पष्ट करता है।"
    if "strength_vs_risk_matrix" in key_lower:
        return "ताकत बनाम जोखिम मैट्रिक्स आपके सबसे मजबूत और संवेदनशील क्षेत्रों को दिखाता है।"
    if "life_area_scores" in key_lower or "full_system_alignment_score" in key_lower:
        return "यह स्कोर प्रोफ़ाइल आपके समग्र संतुलन और सुधार प्राथमिकता को मापता है।"
    if "lo_shu_grid_advanced" in key_lower:
        return "उन्नत लो-शू ग्रिड कर्मिक खाली स्थान और सक्रिय पैटर्न दिखाता है।"
    if "planetary_influence_mapping" in key_lower:
        return "ग्रह प्रभाव मैपिंग निर्णय-शैली पर ग्रहों के संकेत बताती है।"
    if "current_planetary_phase" in key_lower:
        return "वर्तमान ग्रह चरण आपकी वर्तमान गति और दिशा की थीम दिखाता है।"
    if "dynamic_lucky_numbers" in key_lower:
        return "गतिशील शुभ अंक समय-चक्र के अनुसार आपकी गति को सपोर्ट करते हैं।"
    if "situational_caution_numbers" in key_lower:
        return "परिस्थितिजन्य सावधानी अंक निर्णयों में जोखिम कम करने का संकेत देते हैं।"
    if "neutral_number_strategy_usage" in key_lower:
        return "तटस्थ अंक उपयोग रणनीति बिना टकराव स्थिरता बनाए रखने में मदद करती है।"
    if "color_strategy" in key_lower:
        return "रंग रणनीति पहचान ऊर्जा को स्थिर रखने में सहायक होती है।"
    if "energy_objects_recommendation" in key_lower:
        return "ऊर्जा वस्तु सुझाव मनोबल और स्थिरता के लिए सहायक संकेत देता है।"
    if "advanced_remedies_engine" in key_lower or "remedies" in key_lower:
        return f"{focus} के लिए अनुशासन, दिशा और ऊर्जा-संतुलन पर आधारित उपाय दिए गए हैं।"
    if "business_brand_naming" in key_lower:
        return "व्यवसाय/ब्रांड नाम सुझाव बाज़ार प्रभाव को मजबूत बनाने में मदद करता है।"
    if "signature_energy_analysis" in key_lower:
        return "हस्ताक्षर ऊर्जा विश्लेषण आपकी पहचान की सूक्ष्म छाप दर्शाता है।"
    if "mobile_optimization_strategy" in key_lower:
        return "मोबाइल अनुकूलन रणनीति उपयोग-लय और निर्णय-समय को बेहतर बनाती है।"
    if "life_strategy_recommendations" in key_lower:
        return "जीवन रणनीति सुझाव अल्प-काल और दीर्घ-काल दोनों दिशाओं को संतुलित करते हैं।"
    if "priority_action_plan" in key_lower:
        return "प्राथमिक कार्य योजना आपके अगले कदमों को स्पष्ट क्रम में रखती है।"
    if "risk_alerts_and_mitigation" in key_lower:
        return "जोखिम चेतावनी और निवारण संभावित बाधाओं से पहले तैयार करता है।"
    if "premium_summary_narrative" in key_lower:
        return "प्रीमियम समापन सार आपके मुख्य बल, चुनौती और अगले कदम का समेकित निष्कर्ष है।"
    return f"{SECTION_TITLES.get(section_key, section_key)} का सार आपकी वर्तमान दिशा को स्पष्ट करता है।"



PREMIUM_TRAIT_EXCLUDE = {
    "full_identity_profile",
    "core_numbers",
    "dynamic_lucky_numbers",
    "situational_caution_numbers",
    "neutral_number_strategy_usage",
    "energy_objects_recommendation",
    "advanced_remedies_engine",
    "color_strategy",
}

def _premium_identity_value(raw_value: Any, default: str = "उपलब्ध नहीं") -> str:
    cleaned = _sanitize_identity_value(raw_value)
    if not cleaned:
        return default
    if not _is_valid_email_token(cleaned):
        return default
    normalized = cleaned.lower()
    if normalized in {"not provided", "na", "n/a", "none", "null", "unknown"}:
        return default
    return cleaned


def _premium_join_items(values: List[str], default: str) -> str:
    cleaned = [_sanitize_identity_value(item) for item in values]
    cleaned = [item for item in cleaned if item]
    return ", ".join(cleaned) if cleaned else default


def _join_items(values: List[str], default: str) -> str:
    cleaned = [_hindi_context(item, "") for item in values]
    cleaned = [item for item in cleaned if item]
    return ", ".join(cleaned) if cleaned else default


def _normalize_text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = [display_value(_safe_text(item), "") for item in value]
        return [item for item in items if item]
    text = display_value(_safe_text(value), "")
    if not text:
        return []
    if "," in text:
        chunks = [display_value(chunk.strip(), "") for chunk in text.split(",")]
        return [chunk for chunk in chunks if chunk]
    return [text]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _digits_from_text(value: Any) -> List[int]:
    return [int(ch) for ch in str(value or "") if str(ch).isdigit()]


def _reduce_number_steps(value: int) -> List[int]:
    steps: List[int] = [abs(int(value))]
    while steps[-1] > 9 and steps[-1] not in (11, 22, 33):
        steps.append(sum(int(digit) for digit in str(steps[-1])))
    return steps


def _mobile_sum_expression(mobile_number: str, total: int, vibration: int) -> str:
    digits = _digits_from_text(mobile_number)
    if not digits:
        return "अंक योग उपलब्ध नहीं है।"
    sum_expr = "+".join(str(digit) for digit in digits)
    steps = _reduce_number_steps(total)
    if len(steps) <= 1:
        return f"अंक योग: {sum_expr} = {total}; कंपन {vibration}"
    reduce_parts = " → ".join(
        f"{'+'.join(str(digit) for digit in str(step))}={step}" if idx > 0 else str(step)
        for idx, step in enumerate(steps)
    )
    return f"अंक योग: {sum_expr} = {total}; घटाकर {reduce_parts} ⇒ कंपन {vibration}"


def _format_number_list(values: List[Any], default: str = "कोई नहीं") -> str:
    cleaned = [str(_safe_int(value)) for value in values if _safe_int(value, -1) >= 0]
    return ", ".join(cleaned) if cleaned else default


def _normalize_color_list(values: List[str], fallback: List[str]) -> List[str]:
    if not values:
        return fallback
    if any(LATIN_RE.search(str(item)) for item in values):
        return fallback
    return values


def _derive_premium_lucky_numbers(
    numbers: Dict[str, Any],
    derived_scores: Dict[str, Any],
    numerology_values: Dict[str, Any],
) -> List[int]:
    base = [
        numbers.get("birthNumber"),
        numbers.get("lifePath"),
        numbers.get("nameNumber"),
        numbers.get("mobileVibration"),
        numbers.get("personalYear"),
    ]
    base = [int(value) for value in base if str(value).isdigit() and 1 <= int(value) <= 9]
    supportive = [
        int(value)
        for value in (numerology_values.get("supportive_numbers") or numerology_values.get("lucky_numbers") or [])
        if str(value).isdigit()
    ]
    candidates = [value for value in (supportive + base) if 1 <= int(value) <= 9]
    unique = []
    for value in candidates:
        if value not in unique:
            unique.append(value)
    if len(unique) < 3:
        for value in range(1, 10):
            if value not in unique:
                unique.append(value)
            if len(unique) >= 3:
                break
    return unique[:4]


def _derive_premium_caution_numbers(
    lucky_numbers: List[int],
    numbers: Dict[str, Any],
    derived_scores: Dict[str, Any],
) -> List[int]:
    avg = None
    scores = [
        derived_scores.get("confidence_score"),
        derived_scores.get("life_stability_index"),
    ]
    valid = [value for value in scores if isinstance(value, (int, float))]
    if valid:
        avg = sum(valid) / len(valid)
    count = 2 if avg is not None and avg >= 70 else 3
    avoid = set(lucky_numbers)
    core = {numbers.get("birthNumber"), numbers.get("lifePath")}
    pool = [value for value in range(1, 10) if value not in avoid and value not in core]
    if len(pool) < count:
        pool = [value for value in range(1, 10) if value not in avoid]
    return pool[:count]


def _derive_premium_neutral_numbers(lucky_numbers: List[int], caution_numbers: List[int]) -> List[int]:
    avoid = set(lucky_numbers) | set(caution_numbers)
    neutral = [value for value in range(1, 10) if value not in avoid]
    if not neutral:
        neutral = [value for value in range(1, 10) if value not in set(lucky_numbers)]
    return neutral[:3]


def _alignment_label(status: str) -> str:
    normalized = _safe_text(status).lower()
    if normalized in {"high", "strong"}:
        return "उच्च सामंजस्य"
    if normalized in {"supportive", "moderate"}:
        return "सहायक सामंजस्य"
    if normalized in {"challenging", "low"}:
        return "चुनौतीपूर्ण सामंजस्य"
    return "तटस्थ सामंजस्य"


NUMBER_TONE_MAP: Dict[int, Dict[str, str]] = {
    1: {"nature": "नेतृत्व और दिशा", "strength": "स्पष्ट निर्णय क्षमता", "risk": "जल्दबाज़ निर्णय", "action": "निर्णय से पहले एक लिखित पुष्टि नियम रखें"},
    2: {"nature": "संवेदनशीलता और संतुलन", "strength": "सहयोगी दृष्टि", "risk": "भावनात्मक उतार-चढ़ाव", "action": "प्रतिक्रिया से पहले 3 गहरी श्वास लें"},
    3: {"nature": "रचनात्मकता और अभिव्यक्ति", "strength": "स्पष्ट संचार", "risk": "ध्यान बिखरना", "action": "एक समय पर एक कार्य पूरा करने का नियम बनाएं"},
    4: {"nature": "संरचना और अनुशासन", "strength": "स्थिरता और मेहनत", "risk": "अति-कठोरता", "action": "हर सप्ताह एक लचीलापन स्लॉट रखें"},
    5: {"nature": "गति और अनुकूलन", "strength": "तेज़ सीख और बदलाव", "risk": "रूटीन टूटना", "action": "रोज़ एक स्थिर समय-ब्लॉक लॉक करें"},
    6: {"nature": "सामंजस्य और जिम्मेदारी", "strength": "विश्वसनीयता", "risk": "अधिक जिम्मेदारी का दबाव", "action": "सीमाएँ तय करें और मदद माँगना सीखें"},
    7: {"nature": "विश्लेषण और गहराई", "strength": "इनसाइट और योजना", "risk": "अति-विश्लेषण", "action": "निर्णय की समय-सीमा तय करें"},
    8: {"nature": "परिश्रम और अधिकार", "strength": "लक्ष्य अनुशासन", "risk": "कठोर दबाव", "action": "काम और विश्राम के अनुपात को लिखित रखें"},
    9: {"nature": "ऊर्जा और साहस", "strength": "त्वरित क्रियान्वयन", "risk": "अति-प्रतिक्रिया", "action": "बड़े निर्णय से पहले 10 सेकंड ठहरें"},
}


def _number_traits(number: Any) -> Dict[str, str]:
    value = _safe_int(number, 0)
    return NUMBER_TONE_MAP.get(value, NUMBER_TONE_MAP[5])


def _challenge_bucket(value: Any) -> str:
    return _problem_bucket_from_text(value)


def _challenge_action(bucket: str) -> str:
    mapping = {
        "consistency": "हर दिन एक फिक्स्ड समय पर सबसे महत्वपूर्ण काम पूरा करें और सप्ताह में एक समीक्षा रखें।",
        "confidence": "छोटे निर्णयों की सूची बनाकर रोज़ 1 निर्णय पूरा करें।",
        "finance": "हर सप्ताह खर्च और बचत की एक संक्षिप्त समीक्षा करें।",
        "career": "सप्ताह के 3 आउटपुट लक्ष्य लिखें और उन्हें ट्रैक करें।",
        "business": "साप्ताहिक बिक्री/राजस्व संकेतक तय कर उसी पर फोकस करें।",
        "relationship": "हर सप्ताह एक स्पष्ट संवाद स्लॉट तय करें।",
        "health": "नींद और पानी के लिए रोज़ दो अनिवार्य चेकपॉइंट रखें।",
    }
    return mapping.get(bucket, "रोज़ एक प्राथमिक लक्ष्य तय करें और शाम को प्रगति जांचें।")


def _score_band_label(score: Any) -> str:
    value = _safe_int(score, 0)
    if value >= 75:
        return "मजबूत"
    if value >= 55:
        return "मध्यम"
    return "संवेदनशील"


PLANET_HI_MAP = {
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


ELEMENT_HI_MAP = {
    "Fire": "अग्नि",
    "Water": "जल",
    "Air": "वायु",
    "Earth": "पृथ्वी",
}


MANTRA_HI_MAP = {
    1: "ॐ सूर्याय नमः",
    2: "ॐ सोमाय नमः",
    3: "ॐ गुरवे नमः",
    4: "ॐ राहवे नमः",
    5: "ॐ बुधाय नमः",
    6: "ॐ शुक्राय नमः",
    7: "ॐ केतवे नमः",
    8: "ॐ शनैश्चराय नमः",
    9: "ॐ भौमाय नमः",
}


ENERGY_OBJECT_MAP: Dict[int, Tuple[str, str, str]] = {
    1: ("सनस्टोन", "आत्मविश्वास और नेतृत्व स्थिर करता है", "दाहिने हाथ में या कार्य-डेस्क पर रखें"),
    2: ("मूनस्टोन", "भावनात्मक संतुलन और सहजता बढ़ाता है", "सोते समय पास रखें"),
    3: ("सिट्रीन", "रचनात्मकता और स्पष्ट संवाद को समर्थन देता है", "वर्क-स्टेशन पर रखें"),
    4: ("हेमाटाइट", "ग्राउंडिंग और अनुशासन को मजबूत करता है", "कलाई में या जेब में रखें"),
    5: ("ग्रीन एवेंचुरिन", "लचीलापन और निर्णय-संतुलन बढ़ाता है", "दैनिक उपयोग के बैग में रखें"),
    6: ("रोज़ क्वार्ट्ज", "सामंजस्य और जिम्मेदारी ऊर्जा को संतुलित करता है", "बेडसाइड पर रखें"),
    7: ("अमेथिस्ट", "फोकस और मानसिक स्थिरता देता है", "ध्यान के समय पास रखें"),
    8: ("टाइगर आइ", "लक्ष्य अनुशासन और दृढ़ता बढ़ाता है", "दाहिने हाथ में रखें"),
    9: ("कार्नेलियन", "ऊर्जा और कार्यवाही क्षमता बढ़ाता है", "सुबह के समय उपयोग करें"),
}

DIRECTION_MAP: Dict[int, str] = {
    1: "पूर्व",
    2: "उत्तर-पश्चिम",
    3: "उत्तर",
    4: "दक्षिण-पश्चिम",
    5: "उत्तर-पूर्व",
    6: "पश्चिम",
    7: "दक्षिण",
    8: "दक्षिण-पश्चिम",
    9: "उत्तर-पूर्व",
}

SPACE_ALIGNMENT_MAP: Dict[int, str] = {
    1: "कार्य-क्षेत्र को व्यवस्थित रखें और एक स्पष्ट विज़न बोर्ड लगाएं।",
    2: "शांत कोना बनाएं जहां संवाद और विचार स्पष्ट रहें।",
    3: "रचनात्मक कोना रखें जहां नोट्स/आइडिया आसानी से दिखें।",
    4: "स्टोरेज और फाइलिंग को व्यवस्थित करके अव्यवस्था घटाएं।",
    5: "मोबाइल/डेस्क को हल्का रखें ताकि गति और फोकस बना रहे।",
    6: "घर/ऑफिस में संतुलित रंग और साफ-सुथरा वातावरण बनाएं।",
    7: "ध्यान/पढ़ाई का शांत स्थान तय करें।",
    8: "टू-डू बोर्ड और साप्ताहिक लक्ष्य दृश्य में रखें।",
    9: "एक्शन-ट्रिगर स्पेस बनाएं जिससे तुरंत शुरू करने की आदत बने।",
}


def _premium_name_correction_hint(name_number: int) -> str:
    if name_number in (4, 8):
        return "स्वर जोड़कर नाम की कठोरता नरम करें और उच्चारण सरल रखें।"
    if name_number in (3, 5):
        return "अक्षर-संतुलन बढ़ाकर स्थिरता और अनुशासन जोड़ें।"
    if name_number in (7, 9):
        return "संक्षिप्त और स्पष्ट नाम-रूप अपनाएं ताकि पहचान स्थिर रहे।"
    return "नाम में उच्चारण-संगति और एकरूपता बनाए रखें।"



def _extract_label(value: Any, *, fallback: str) -> str:
    if isinstance(value, dict):
        for key in ("name", "label", "value", "text", "gemstone", "mantra", "title"):
            text = display_value(_safe_text(value.get(key)), "")
            if text:
                return text
    if isinstance(value, list):
        values = _normalize_text_list(value)
        if values:
            return ", ".join(values)
    text = display_value(_safe_text(value), "")
    return text or fallback


def _metric_value(scores: Dict[str, Any], key: str) -> Optional[Any]:
    value = scores.get(key)
    return value if value is not None else None


def _highlights(scores: Dict[str, Any], keys: List[str]) -> List[Dict[str, str]]:
    values: List[Dict[str, str]] = []
    for key in keys:
        value = _metric_value(scores, key)
        if value is None:
            continue
        values.append({"label": to_metric_label(key), "value": str(value)})
    return values


def _top_metrics(scores: Dict[str, Any]) -> Tuple[str, str]:
    strongest = to_metric_label(_safe_text(scores.get("strongest_metric")) or "confidence_score")
    weakest = to_metric_label(_safe_text(scores.get("weakest_metric")) or "karma_pressure_index")
    return strongest, weakest


def _problem_bucket_from_text(raw_problem: Any) -> str:
    text = _safe_text(raw_problem).lower()
    if not text:
        return "general"
    if any(token in text for token in ("debt", "loan", "emi", "finance", "money", "cash", "कर्ज", "ऋण", "वित्त")):
        return "finance"
    if any(token in text for token in ("career", "job", "work", "promotion", "interview", "करियर", "नौकरी", "काम")):
        return "career"
    if any(token in text for token in ("business", "startup", "sales", "revenue", "व्यवसाय", "राजस्व")):
        return "business"
    if any(token in text for token in ("confidence", "hesitation", "visibility", "self", "आत्मविश्वास", "हिचक")):
        return "confidence"
    if any(token in text for token in ("consistency", "routine", "discipline", "focus", "निरंतरता", "दिनचर्या", "अनुशासन")):
        return "consistency"
    if any(token in text for token in ("relationship", "partner", "marriage", "रिश्ता", "संबंध", "विवाह")):
        return "relationship"
    if any(token in text for token in ("health", "sleep", "stress", "anxiety", "स्वास्थ्य", "नींद", "तनाव")):
        return "health"
    if any(token in text for token in ("study", "exam", "education", "learning", "पढ़ाई", "परीक्षा", "शिक्षा")):
        return "education"
    return "general"


def _localized_problem_anchor(raw_problem: Any, bucket: str) -> str:
    text = _safe_text(raw_problem)
    if not text:
        return "वर्तमान समस्या"
    if DEVANAGARI_RE.search(text):
        return text

    bucket_hint = {
        "finance": "वित्त चुनौती",
        "career": "करियर चुनौती",
        "business": "व्यवसाय चुनौती",
        "confidence": "आत्मविश्वास चुनौती",
        "consistency": "अनुशासन चुनौती",
        "relationship": "संबंध चुनौती",
        "health": "स्वास्थ्य चुनौती",
        "education": "शिक्षा चुनौती",
        "general": "मुख्य चुनौती",
    }.get(bucket, "मुख्य चुनौती")
    compact = " ".join(text.split())[:64]
    return f"{bucket_hint} ({compact})"


def _extract_numbers(numerology_values: Dict[str, Any]) -> Dict[str, int]:
    pyth = numerology_values.get("pythagorean") or {}
    chaldean = numerology_values.get("chaldean") or {}
    mobile = numerology_values.get("mobile_analysis") or {}
    return {
        "lifePath": int(pyth.get("life_path_number") or 0),
        "destiny": int(pyth.get("destiny_number") or 0),
        "expression": int(pyth.get("expression_number") or 0),
        "nameNumber": int(chaldean.get("name_number") or 0),
        "mobileVibration": int(mobile.get("mobile_vibration") or 0),
        "birthNumber": int(pyth.get("birth_number") or 0),
        "personalYear": int(pyth.get("personal_year") or 0),
    }


def _guidance_profile(numerology_values: Dict[str, Any]) -> Dict[str, Any]:
    return numerology_values.get("guidance_profile") or {}


def _dominant_planet(numerology_values: Dict[str, Any]) -> Dict[str, Any]:
    return numerology_values.get("dominant_planet") or {}


def _mobile_analysis(numerology_values: Dict[str, Any]) -> Dict[str, Any]:
    return numerology_values.get("mobile_analysis") or {}


def _name_variation_lines(normalized_input: Dict[str, Any]) -> List[str]:
    variations = normalized_input.get("nameVariations") or []
    cleaned = [_safe_text(item) for item in variations if _safe_text(item)]
    if not cleaned:
        return []
    lines: List[str] = []
    for item in cleaned[:5]:
        try:
            number = calculate_name_number(item)
        except Exception:
            number = None
        if number:
            lines.append(f"{item} -> {number}")
        else:
            lines.append(item)
    return lines


def _section_text(
    *,
    section_key: str,
    plan: str,
    normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
    problem_profile: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, str, str]:
    focus = _display(normalized_input.get("focusArea") or "general_alignment", "समग्र जीवन सामंजस्य")
    industry = _hindi_context(normalized_input.get("industry") or normalized_input.get("occupation"), "सामान्य क्षेत्र")
    occupation = _hindi_context(normalized_input.get("occupation") or normalized_input.get("industry"), "वर्तमान भूमिका")
    relationship_status = _display(normalized_input.get("relationshipStatus") or "single", "अविवाहित")
    stress_level = _safe_text(normalized_input.get("stressLevel") or "मध्यम")
    raw_current_problem = _safe_text(normalized_input.get("currentProblem"))
    current_problem = _hindi_context(raw_current_problem, "जीवन दिशा")
    profile_category = _safe_text((problem_profile or {}).get("category")).lower()
    if profile_category in {
        "finance",
        "career",
        "business",
        "confidence",
        "consistency",
        "relationship",
        "health",
        "education",
        "general",
    }:
        problem_bucket = profile_category
    else:
        problem_bucket = _problem_bucket_from_text(raw_current_problem or current_problem)
    problem_anchor = _localized_problem_anchor(raw_current_problem or current_problem, problem_bucket)
    work_mode = _display(normalized_input.get("workMode") or "job", "नौकरी")
    income = _safe_text(normalized_input.get("incomeRangeMonthly") or "घोषित नहीं")
    debt = _safe_text(normalized_input.get("debtRange") or "घोषित नहीं")
    report_emphasis = _display(normalized_input.get("reportEmphasis") or "balanced", "संतुलित")
    goals = [_safe_text(item) for item in (normalized_input.get("goals") or []) if _safe_text(item)]
    challenges = [_safe_text(item) for item in (normalized_input.get("challenges") or []) if _safe_text(item)]
    numbers = _extract_numbers(numerology_values)
    plan_key = _safe_text(plan).lower()
    guidance = _guidance_profile(numerology_values)
    dominant = _dominant_planet(numerology_values)
    mobile = _mobile_analysis(numerology_values)
    supportive_numbers = _normalize_text_list(
        guidance.get("supportiveNumbers") or mobile.get("supportive_number_energies")
    )
    caution_numbers = _normalize_text_list(guidance.get("cautionNumbers"))
    guidance_colors = _normalize_text_list(guidance.get("colors"))
    guidance_direction = _extract_label(guidance.get("direction"), fallback="पूर्व")
    guidance_day = _extract_label(guidance.get("day"), fallback="सोमवार")
    guidance_mantra = _extract_label(guidance.get("mantra"), fallback="ॐ नमः शिवाय")
    guidance_gemstone = _extract_label(guidance.get("gemstone"), fallback="रत्न")
    dominant_planet = _extract_label(dominant.get("planet") or guidance.get("planet"), fallback="मंगल")
    dominant_element = _extract_label(dominant.get("element") or guidance.get("element"), fallback="अग्नि")
    dominant_qualities = _normalize_text_list(dominant.get("qualities") or guidance.get("qualities"))
    strongest, weakest = _top_metrics(derived_scores)
    risk_band = _safe_text(derived_scores.get("risk_band") or "सुधार योग्य")
    full_name = _safe_text(normalized_input.get("fullName") or "उपयोगकर्ता")

    if section_key == "required_inputs":
        if plan_key == "basic":
            return (
                "आवश्यक इनपुट: नाम, जन्मतिथि और मोबाइल नंबर।",
                "इन तीनों से मोबाइल ऊर्जा और मूलांक/भाग्यांक का आधार बनता है।",
                "इनपुट अधूरे होने पर सुधार सलाह कमजोर हो सकती है।",
                "रिपोर्ट शुरू करने से पहले नाम और मोबाइल की सटीकता सुनिश्चित करें।",
            )
        if plan_key == "standard":
            return (
                "आवश्यक इनपुट: नाम, जन्मतिथि, मोबाइल नंबर और नाम विकल्प (Name Variations)।",
                "नाम विकल्पों से कंपन तुलना और सुधार दिशा स्पष्ट होती है।",
                "नाम विकल्प अधूरे होने पर सुधार सीमित हो सकता है।",
                "कम से कम 2–3 नाम विकल्प दें ताकि तुलना मजबूत हो।",
            )
        return (
            "आवश्यक इनपुट: नाम, जन्मतिथि, मोबाइल नंबर, नाम विकल्प, लक्ष्य, जन्म समय/स्थान।",
            "प्रीमियम लेयर में टाइमिंग और ग्रह-समर्थन का प्रभाव इन इनपुट पर निर्भर है।",
            "जन्म समय/स्थान अधूरा होने पर टाइमिंग सलाह सीमित होगी।",
            "जन्म विवरण और लक्ष्य स्पष्ट देकर रणनीति को सटीक बनाएं।",
        )

    if section_key == "core_purpose":
        if plan_key == "basic":
            return (
                "मुख्य उद्देश्य: बाहरी मोबाइल ऊर्जा में सुधार और स्थिरता लाना।",
                "यह मोबाइल कंपन को व्यवहार और दिनचर्या से जोड़ता है।",
                "यदि सुधार को व्यवहार में नहीं उतारा तो परिणाम धीमे रहेंगे।",
                "मोबाइल ऊर्जा को दैनिक प्राथमिकता से जोड़ें।",
            )
        if plan_key == "standard":
            return (
                "मुख्य उद्देश्य: व्यक्तिगत पहचान ऊर्जा को नाम + मोबाइल संयोजन से संरेखित करना।",
                "नाम सुधार और मोबाइल कंपन के मिलान से स्थिर परिणाम मिलते हैं।",
                "बिना परीक्षण के नाम/मोबाइल बदलने से लाभ सीमित होता है।",
                "21 दिन के सुधार ट्रायल के बाद निर्णय लें।",
            )
        return (
            "मुख्य उद्देश्य: अंक + ज्योतिष + वैदिक तर्क से पूर्ण जीवन संरेखण।",
            "यह दीर्घकालिक टाइमिंग और निर्णय-गुणवत्ता को स्थिर करता है।",
            "यदि रणनीति में अनुशासन नहीं होगा तो परिणाम कमजोर होंगे।",
            "समय-चक्र और अनुशासन दोनों को साथ लागू करें।",
        )

    if section_key == "primary_focus":
        if plan_key == "basic":
            return (
                "प्राथमिक फोकस: मोबाइल अंक-विश्लेषण और उसकी ऊर्जा का उपयोग।",
                "मोबाइल कंपन दैनिक निर्णय और संचार गति को प्रभावित करता है।",
                "यदि फोकस भटका तो ऊर्जा बिखर सकती है।",
                "एक स्पष्ट लक्ष्य के साथ मोबाइल ऊर्जा को संरेखित रखें।",
            )
        if plan_key == "standard":
            return (
                "प्राथमिक फोकस: नाम अंक + मोबाइल संयोजन का सुधार और मिलान।",
                "यह पहचान और व्यवहार में स्थिरता लाता है।",
                "अनुशासन के बिना नाम/मोबाइल सुधार अधूरा रहेगा।",
                "नाम और मोबाइल के संयोजन का साप्ताहिक ट्रैक रखें।",
            )
        return (
            "प्राथमिक फोकस: नाम + मोबाइल + जन्मतिथि + ग्रह टाइमिंग + जीवन चक्र।",
            "यह टाइमिंग-सेंसिटिव निर्णयों के लिए आधार बनाता है।",
            "बिना समय-लॉजिक के निर्णय अपेक्षित परिणाम नहीं देंगे।",
            "टाइमिंग विंडो को निर्णय प्रक्रिया में शामिल करें।",
        )

    if section_key == "deterministic_engine":
        if plan_key == "basic":
            return (
                "निर्धारित इंजन: मूलांक, भाग्यांक, मोबाइल योग और बेसिक मैपिंग।",
                "यह संख्याओं से स्थिर और दोहराने योग्य दिशा देता है।",
                "यदि इन नियमों से अलग निर्णय हुए तो परिणाम अस्थिर हो सकते हैं।",
                "निर्धारित संकेतों को रोज़मर्रा की योजना में जोड़ें।",
            )
        if plan_key == "standard":
            return (
                "निर्धारित इंजन: नाम अंक, सुधार लॉजिक, प्रिफिक्स/सुफिक्स और कॉम्बो मिलान।",
                "यह पहचान और व्यवहार के बीच स्पष्ट पुल बनाता है।",
                "बिना सुधार लॉजिक लागू किए परिणाम सतही रहेंगे।",
                "नाम विकल्पों की तुलना और कॉम्बो मिलान करें।",
            )
        return (
            "निर्धारित इंजन: पूर्ण अंक विज्ञान + ज्योतिष + वैदिक टाइमिंग + उपाय मैपिंग।",
            "यह गहरी रणनीतिक दिशा और समय-सटीक निर्णय देता है।",
            "यदि टाइमिंग और उपाय अलग चले तो ऊर्जा बिखर सकती है।",
            "निर्धारित टाइमिंग को कार्य योजना में लॉक करें।",
        )

    if section_key == "ai_generation_layer":
        if plan_key == "basic":
            return (
                "AI लेयर: संख्या प्रभाव का संक्षिप्त और स्पष्ट विवरण।",
                "यह सरल भाषा में सुधार दिशा बताता है।",
                "यदि इनपुट कम हों तो विवरण सीमित हो सकता है।",
                "संक्षिप्त सुझावों को अनुशासन से लागू करें।",
            )
        if plan_key == "standard":
            return (
                "AI लेयर: नाम/मोबाइल संरेखण का विस्तृत और व्यक्तिगत वर्णन।",
                "यह सुधार विकल्पों की तुलना और परिणाम बताती है।",
                "यदि तुलना नहीं की गई तो सर्वोत्तम विकल्प छूट सकता है।",
                "AI सुझावों को deterministic नियमों के साथ पढ़ें।",
            )
        return (
            "AI लेयर: गहरी व्याख्या, रणनीतिक मार्गदर्शन और प्रीमियम नैरेशन।",
            "यह सिस्टम कनेक्शन और निर्णय रणनीति स्पष्ट करता है।",
            "यदि रणनीति लागू नहीं हुई तो प्रभाव धीमा रहेगा।",
            "AI नैरेशन को कार्य योजना में बदलें।",
        )

    if section_key == "recommendation_logic":
        if plan_key == "basic":
            return (
                "सिफारिश तर्क: deterministic आउटपुट + सरल AI व्याख्या।",
                "यह सीधे लागू होने वाले कदम देता है।",
                "बिना अनुशासन के त्वरित लाभ नहीं मिलेगा।",
                "साप्ताहिक समीक्षा के साथ सुधार लागू करें।",
            )
        if plan_key == "standard":
            return (
                "सिफारिश तर्क: deterministic सुधार + AI आधारित शब्दांकन।",
                "नाम/मोबाइल सुधार के लिए स्पष्ट दिशा मिलती है।",
                "यदि सुधार को ट्रायल नहीं किया तो निष्कर्ष कमजोर होगा।",
                "21 दिन के बाद परिणाम मापकर निर्णय लें।",
            )
        return (
            "सिफारिश तर्क: मजबूत deterministic नियम + AI नेतृत्व वाली रणनीति।",
            "यह समय-चक्र, ग्रह संकेत और व्यवहारिक सुधार को जोड़ता है।",
            "यदि नियमों को अनदेखा किया गया तो परिणाम अस्थिर हो सकते हैं।",
            "निर्णय-टाइमिंग और उपाय को साथ लागू करें।",
        )

    if section_key == "narration_style":
        if plan_key == "basic":
            return (
                "वर्णन शैली: छोटी, स्पष्ट और सीधी।",
                "यह तेज़ समझ और त्वरित अनुप्रयोग के लिए बनी है।",
                "लंबा विवरण जोड़ने से फोकस कमजोर हो सकता है।",
                "संक्षिप्त दिशा पर भरोसा रखें।",
            )
        if plan_key == "standard":
            return (
                "वर्णन शैली: विस्तृत और व्यक्तिगत।",
                "यह नाम/मोबाइल सुधार को समझने में मदद करती है।",
                "यदि विवरण पढ़े बिना निर्णय लिया तो सुधार सीमित रहेगा।",
                "प्रत्येक पैराग्राफ को actionable कदम की तरह लें।",
            )
        return (
            "वर्णन शैली: गहरी, रणनीतिक और उच्च-मूल्य परामर्श जैसी।",
            "यह जटिल संकेतों को सरल निर्णय में बदलती है।",
            "यदि रणनीति को व्यवहार में नहीं उतारा तो प्रभाव कम होगा।",
            "एक-एक सुझाव को चरणबद्ध लागू करें।",
        )

    if section_key == "ai_narration_role":
        if plan_key == "basic":
            return (
                "AI भूमिका: परिणाम को सरल भाषा में समझाना।",
                "यह अंक प्रभाव को पढ़ने में मदद करता है।",
                "यदि AI को नियमों से अलग पढ़ा गया तो भ्रम हो सकता है।",
                "AI नैरेशन को deterministic संकेतों के साथ जोड़ें।",
            )
        if plan_key == "standard":
            return (
                "AI भूमिका: लॉजिक समझाना, विकल्प तुलना करना, आउटपुट व्यक्तिगत बनाना।",
                "यह सही नाम/मोबाइल सुधार चुनने में मदद करता है।",
                "बिना तुलना के निर्णय लेने से सुधार कमजोर होगा।",
                "AI द्वारा बताए गए कारणों को प्राथमिकता दें।",
            )
        return (
            "AI भूमिका: गहराई से व्याख्या, सिस्टम कनेक्शन और निर्णय मार्गदर्शन।",
            "यह जटिल लॉजिक को स्पष्ट रणनीति बनाता है।",
            "यदि AI निर्देशों को अनदेखा किया गया तो लाभ धीमा होगा।",
            "AI मार्गदर्शन को समय-योजना में बदलें।",
        )

    if section_key == "deterministic_role":
        if plan_key == "basic":
            return (
                "निर्धारित भूमिका: निश्चित अंक परिणाम बनाना।",
                "यह बेसिक ऊर्जा मार्गदर्शन देता है।",
                "यदि नियम टूटे तो परिणाम अस्थिर होंगे।",
                "निर्धारित नियमों के अनुसार व्यवहार तय करें।",
            )
        if plan_key == "standard":
            return (
                "निर्धारित भूमिका: नाम सुधार और कॉम्बो लॉजिक निकालना।",
                "यह पहचान ऊर्जा को स्थिर करता है।",
                "यदि सुधार लॉजिक लागू नहीं हुआ तो परिणाम सीमित होंगे।",
                "निर्धारित सुधार को ट्रैक करें।",
            )
        return (
            "निर्धारित भूमिका: उन्नत अंक + ज्योतिष + वैदिक आउटपुट तैयार करना।",
            "यह दीर्घकालिक रणनीति का आधार है।",
            "यदि टाइमिंग नियम न अपनाए गए तो रणनीति कमजोर होगी।",
            "निर्धारित आउटपुट को मासिक समीक्षा में शामिल करें।",
        )

    if section_key == "ai_should_not_do":
        if plan_key == "basic":
            return (
                "AI को संख्याएँ या उपाय invent नहीं करने चाहिए।",
                "कृत्रिम या अनुमानित संख्याएँ भ्रम पैदा करती हैं।",
                "यदि गलत सुझाव दिए गए तो ऊर्जा-अनुशासन टूट सकता है।",
                "हमेशा deterministic डेटा से ही निर्णय लें।",
            )
        if plan_key == "standard":
            return (
                "AI को सुधार लॉजिक को random तरीके से नहीं बदलना चाहिए।",
                "नाम सुधार नियम स्थिर होने चाहिए।",
                "यदि लॉजिक बदला गया तो तुलना टूट जाएगी।",
                "नाम विकल्प deterministic नियमों से ही तय करें।",
            )
        return (
            "AI को deterministic या astro नियम override नहीं करने चाहिए।",
            "ग्रह-समर्थन और टाइमिंग नियम स्थिर रहने चाहिए।",
            "यदि override हुआ तो रणनीति गलत हो सकती है।",
            "हमेशा नियम-आधारित व्याख्या रखें।",
        )

    if section_key == "ai_should_do":
        if plan_key == "basic":
            return (
                "AI को रिपोर्ट को सरल और पढ़ने योग्य बनाना चाहिए।",
                "यह actionable दिशा देने में मदद करता है।",
                "यदि भाषा जटिल हुई तो लाभ कम होगा।",
                "सरल और लागू होने वाले सुझावों पर ध्यान दें।",
            )
        if plan_key == "standard":
            return (
                "AI को समझाना चाहिए कि नाम/मोबाइल सुधार क्यों महत्वपूर्ण है।",
                "यह पहचान संरेखण को मजबूत करता है।",
                "यदि कारण स्पष्ट न हों तो निर्णय कमजोर होगा।",
                "AI की तुलना और कारण को प्राथमिकता दें।",
            )
        return (
            "AI को जटिल लॉजिक को प्रीमियम मार्गदर्शन में बदलना चाहिए।",
            "यह निर्णय-समर्थन और रणनीतिक दिशा देता है।",
            "यदि लॉजिक सरल न किया गया तो उपयोग कठिन होगा।",
            "AI को निर्णय-मैप बनाने में उपयोग करें।",
        )

    if section_key == "plan_overview":
        if plan_key == "basic":
            return (
                "यह बेसिक मोबाइल फोकस रिपोर्ट नाम, जन्मतिथि और मोबाइल के आधार पर बाहरी मोबाइल ऊर्जा सुधार पर केंद्रित है।",
                "निर्धारित मूलांक/भाग्यांक और मोबाइल योग से स्पष्ट दिशा मिलती है।",
                "यदि दैनिक अनुशासन न बना तो परिणाम बिखर सकते हैं।",
                "मोबाइल ऊर्जा को एक प्राथमिक लक्ष्य और साप्ताहिक समीक्षा से जोड़ें।",
            )
        if plan_key == "standard":
            return (
                "यह स्टैंडर्ड रिपोर्ट नाम और मोबाइल के संयोजन से पहचान ऊर्जा को सुधारने पर केंद्रित है।",
                "नाम सुधार, प्रिफिक्स/सुफिक्स और कॉम्बो मिलान से स्थिरता बढ़ती है।",
                "यदि नाम-सुधार को व्यवहार में नहीं जोड़ा गया तो लाभ सीमित रहेगा।",
                "नाम विकल्पों की तुलना करें और 21 दिनों का अनुशासित प्रयोग करें।",
            )
        return (
            "यह प्रीमियम रिपोर्ट अंक + ज्योतिष + वैदिक लॉजिक से पूर्ण जीवन संरेखण पर केंद्रित है।",
            "ग्रह-समर्थन, समय-चक्र और उपाय-मैपिंग से निर्णय स्पष्ट होते हैं।",
            "समय और अनुशासन के बिना गहरी रणनीति भी धीमी हो सकती है।",
            "जन्म समय/स्थान के साथ निर्णय-टाइमिंग लागू करें और मासिक समीक्षा रखें।",
        )

    if section_key == "basic_details":
        full_name = _hindi_context(normalized_input.get("fullName"), "नाम उपलब्ध नहीं")
        dob = _hindi_context(normalized_input.get("dateOfBirth"), "जन्मतिथि उपलब्ध नहीं")
        mobile_number = _hindi_context(normalized_input.get("mobileNumber"), "मोबाइल उपलब्ध नहीं")
        city = _hindi_context(normalized_input.get("city") or normalized_input.get("currentCity"), "शहर उपलब्ध नहीं")
        gender = _hindi_context(normalized_input.get("gender"), "लिंग उपलब्ध नहीं")
        email = _hindi_context(normalized_input.get("email"), "ईमेल उपलब्ध नहीं")
        focus_label = _hindi_context(normalized_input.get("currentProblem") or normalized_input.get("focusArea"), "मुख्य फोकस")
        name_number = numbers["nameNumber"] or 0
        mobile_vibration = numbers["mobileVibration"] or 0
        return (
            f"नाम: {full_name} | जन्मतिथि: {dob} | मोबाइल: {mobile_number} | शहर: {city} | लिंग: {gender} | ईमेल: {email} | फोकस: {focus_label}",
            f"यह विवरण नाम अंक {name_number} और मोबाइल कंपन {mobile_vibration} के साथ आपका मूल संदर्भ बनाता है।",
            "सटीक जानकारी से मूलांक/भाग्यांक की व्याख्या अधिक विश्वसनीय रहती है।",
            "यदि किसी फ़ील्ड में गलती हो तो आगे के निष्कर्ष प्रभावित हो सकते हैं, इसलिए पहले सत्यापित करें।",
        )

    if section_key == "mulank_analysis":
        mulank = numbers["birthNumber"]
        traits = _number_traits(mulank)
        return (
            f"मूलांक {mulank} आपकी व्यक्तित्व-धारा को दिशा देता है और {traits['nature']} का संकेत देता है।",
            f"ताकत: {traits['strength']} आपके काम करने के तरीके को स्थिर करता है।",
            f"जोखिम: {traits['risk']} बढ़ने पर निर्णय में असंगति आ सकती है।",
            f"क्रिया: {traits['action']} और {_challenge_action(problem_bucket)} लागू करें।",
        )

    if section_key == "bhagyank_analysis":
        bhagyank = numbers["lifePath"]
        traits = _number_traits(bhagyank)
        return (
            f"भाग्यांक {bhagyank} आपकी दीर्घकालिक दिशा और प्रगति की शैली तय करता है।",
            f"ताकत: {traits['strength']} से लक्ष्य पर टिके रहने की क्षमता बढ़ती है।",
            f"जोखिम: {traits['risk']} बढ़ने पर दिशा बदलने की प्रवृत्ति आ सकती है।",
            f"क्रिया: 90 दिनों के 3 लक्ष्य तय करें और {traits['action']} अपनाएँ।",
        )

    if section_key == "name_numerology":
        name_number = numbers["nameNumber"]
        return (
            f"नाम अंक {name_number} आपकी पहचान, छवि और संचार ऊर्जा को दर्शाता है।",
            "यह अंक आपको पेशेवर और व्यक्तिगत प्रभाव में स्थिरता देता है।",
            "यदि नाम-अंक असंतुलित हो तो निर्णय और संवाद कमजोर हो सकते हैं।",
            "नाम-अंक के अनुसार प्रोफाइल, हस्ताक्षर और प्राथमिकता स्थिर रखें।",
        )

    if section_key == "name_analysis":
        name_number = numbers["nameNumber"]
        traits = _number_traits(name_number)
        return (
            f"नाम {name_number} की ऊर्जा आपकी व्यवहार शैली और सार्वजनिक छवि पर सीधा प्रभाव डालती है।",
            f"ताकत: {traits['strength']} के कारण आपकी अभिव्यक्ति स्पष्ट रहती है।",
            f"जोखिम: {traits['risk']} बढ़ने पर प्रभाव कमजोर या अस्थिर हो सकता है।",
            f"क्रिया: {traits['action']} और नाम/हस्ताक्षर की एकरूपता रखें।",
        )

    if section_key == "name_number_total":
        full_name = _safe_text(normalized_input.get("fullName"))
        compound = numbers["nameNumber"] or calculate_name_number(full_name)
        compound_raw = numerology_values.get("name_compound") or compound
        if numerology_values.get("name_compound"):
            compound_raw = numerology_values.get("name_compound")
        else:
            try:
                from app.modules.numerology.chaldean import calculate_name_compound
                compound_raw = calculate_name_compound(full_name)
            except Exception:
                compound_raw = compound
        return (
            f"नाम \"{full_name or 'नाम'}\" के अक्षर-मूल्य जोड़ने पर कुल योग {compound_raw} आता है।",
            f"कुल योग घटाकर नाम अंक {compound} बनता है, जो आपकी पहचान ऊर्जा का आधार है।",
            "यदि नाम-वर्तनी में बदलाव हो तो यह योग बदल सकता है।",
            "आगे की सलाह इसी नाम अंक के आधार पर दी गई है।",
        )

    if section_key == "name_correction_options":
        variations = _name_variation_lines(normalized_input)
        variation_line = _join_items(variations, "विकल्प: स्वर जोड़ना, मध्य अक्षर नरम करना, या उच्चारण सरल रखना")
        name_number = numbers["nameNumber"]
        traits = _number_traits(name_number)
        return (
            f"नाम सुधार विकल्प आपके मौजूदा नाम अंक {name_number} को संतुलित करने हेतु दिए गए हैं।",
            f"ताकत: {traits['strength']} बनी रहे, इसलिए बदलाव छोटे और नियंत्रित रखें।",
            f"विकल्प: {variation_line}",
            "क्रिया: 2-3 विकल्प चुनकर 21 दिनों का व्यवहारिक परीक्षण करें।",
        )

    if section_key == "name_correction_logic_explanation":
        name_number = numbers["nameNumber"]
        mulank = numbers["birthNumber"]
        bhagyank = numbers["lifePath"]
        focus = _safe_text(normalized_input.get("currentProblem") or normalized_input.get("focusArea") or "स्थिरता")
        return (
            f"नाम सुधार तर्क: नाम अंक {name_number} को मूलांक {mulank} और भाग्यांक {bhagyank} के साथ संतुलित करना।",
            "संतुलन बनने पर पहचान ऊर्जा और निर्णय गति दोनों स्थिर रहती हैं।",
            f"यदि {focus} चुनौती बढ़ी हुई हो तो नाम सुधार उससे जुड़ी अस्थिरता घटाने में मदद करता है।",
            "इसलिए सुधार छोटे, स्पष्ट और परीक्षण-आधारित रखें।",
        )

    if section_key == "name_analysis_type":
        if plan_key == "enterprise":
            return (
                "प्रीमियम नाम विश्लेषण में नाम कंपन के साथ कर्मिक और ग्रह समर्थन विश्लेषण जोड़ा जाता है।",
                "यह विश्लेषण नाम की ऊर्जा को समय-चक्र से जोड़कर निर्णय स्पष्ट करता है।",
                "बिना समय-संदर्भ के नाम सुधार सीमित प्रभाव देता है।",
                "नाम और ग्रह-अनुरूपता दोनों का मिलान करके अंतिम विकल्प चुनें।",
            )
        return (
            "नाम विश्लेषण में नाम कंपन और व्यवहारिक प्रभाव का आकलन किया जाता है।",
            "यह पहचान ऊर्जा को स्थिर करने में मदद करता है।",
            "बिना तुलना किए नाम विकल्प बदलना लाभ कम कर सकता है।",
            "कम से कम 2-3 नाम विकल्पों का कंपन मिलान करें।",
        )

    if section_key == "name_correction":
        correction = numerology_values.get("name_correction") or {}
        current_number = correction.get("current_number")
        suggestion = _safe_text(correction.get("suggestion") or "")
        variations = _name_variation_lines(normalized_input)
        variation_line = _join_items(variations, "नाम विकल्प उपलब्ध नहीं")
        return (
            f"नाम सुधार संकेत: वर्तमान नाम अंक {current_number or numbers['nameNumber']}।",
            f"प्रस्तावित दिशा: {suggestion or 'नाम कंपन में संतुलन बनाना उपयोगी रहेगा।'}",
            f"नाम विकल्प: {variation_line}",
            "नाम सुधार को 21 दिनों के व्यवहारिक परीक्षण के साथ अपनाएँ।",
        )

    if section_key == "prefix_suffix_suggestion":
        name_number = numbers["nameNumber"]
        hint = "स्वर जोड़ने से ऊर्जा नरम हो सकती है।" if name_number in (4, 8) else "अधिक स्पष्ट ध्वनि वाले अक्षर सहायक हो सकते हैं।"
        return (
            "प्रिफिक्स/सुफिक्स सुझाव नाम कंपन को संतुलित करने के लिए दिए जाते हैं।",
            hint,
            "यदि नाम बहुत कठोर लगे तो नरम ध्वनि वाले अक्षर जोड़ना उचित है।",
            "परिवर्तन के बाद 21-दिन का प्रभाव ट्रैक करें।",
        )

    if section_key == "name_correction_basis":
        basis = "अंक-आधारित संतुलन" if plan_key != "enterprise" else "अंक + ग्रह + वैदिक समर्थन"
        return (
            f"नाम सुधार का आधार: {basis}।",
            "लक्ष्य यह है कि नाम कंपन और जीवन-पथ के बीच असंतुलन कम हो।",
            "यदि आधार स्पष्ट न हो तो सुधार स्थायी नहीं बनता।",
            "नाम सुधार को मोबाइल और जन्मतिथि के साथ मिलाकर अंतिम निर्णय लें।",
        )

    if section_key == "name_mobile_combo":
        return (
            f"नाम अंक {numbers['nameNumber']} और मोबाइल कंपन {numbers['mobileVibration']} का संयोजन आपके संचार और निर्णय पैटर्न को प्रभावित करता है।",
            "संतुलित कॉम्बो होने पर पहचान और परिणाम दोनों मजबूत होते हैं।",
            "अनुकूल कॉम्बो न होने पर प्रयास के बावजूद स्थिर परिणाम नहीं मिलते।",
            "कॉम्बो मिलान के बाद संचार शैली और ब्रांड इमेज को उसी अनुसार सेट करें।",
        )

    if section_key == "mobile_name_combo_recommendation":
        name_number = numbers["nameNumber"]
        vibration = numbers["mobileVibration"]
        status = _safe_text((numerology_values.get("mobile_analysis") or {}).get("compatibility_status") or "neutral")
        label = _alignment_label(status)
        focus = _safe_text(normalized_input.get("currentProblem") or normalized_input.get("focusArea") or "स्थिरता")
        return (
            f"नाम अंक {name_number} और मोबाइल कंपन {vibration} का संयोजन आपके लिए {label} दिखाता है।",
            "यह संयोजन आपके निर्णय, संवाद और दैनिक अनुशासन को एक ही दिशा देता है।",
            f"यदि असंतुलन रहे तो {focus} से जुड़ी चुनौती बढ़ सकती है।",
            "क्रिया: नाम/मोबाइल उपयोग का समय तय करें और हर सप्ताह 1 समीक्षा रखें।",
        )

    if section_key == "dob_name_alignment" and plan_key not in ("enterprise", "premium"):
        return (
            f"जन्मतिथि (मूलांक {numbers['birthNumber']}) और नाम अंक {numbers['nameNumber']} का संरेखण आपकी पहचान को स्थिर करता है।",
            "अच्छा संरेखण निर्णय क्षमता और आत्मविश्वास दोनों बढ़ाता है।",
            "यदि संरेखण कमजोर हो तो नाम-सुधार प्राथमिकता होना चाहिए।",
            "कम से कम दो नाम विकल्पों का जन्म-अंक के साथ मिलान करें।",
        )

    if section_key == "mobile_number_total":
        mobile_total = mobile.get("mobile_total")
        mobile_number = _safe_text(normalized_input.get("mobileNumber"))
        vibration = numbers["mobileVibration"]
        sum_line = _mobile_sum_expression(mobile_number, _safe_int(mobile_total), vibration)
        return (
            sum_line,
            f"यह कुल योग मोबाइल की आधार ऊर्जा है और कंपन {vibration} उसे दिशा देता है।",
            "जोखिम: जीवन-पथ के साथ तालमेल कमजोर होने पर गति बिखर सकती है।",
            "क्रिया: बड़े निर्णयों को स्थिर समय-खिड़की में रखें और संचार लय तय करें।",
        )

    if section_key == "mobile_digit_analysis":
        dominant_digits = mobile.get("dominant_digits") or []
        missing_digits = mobile.get("missing_digits") or []
        repeating_digits = mobile.get("repeating_digits") or []
        repeating_text = ", ".join(
            f"{item.get('digit')}({item.get('count')} बार)"
            for item in repeating_digits
            if isinstance(item, dict) and item.get("digit")
        )
        return (
            f"प्रमुख अंक: {_format_number_list(dominant_digits, 'उपलब्ध नहीं')} | अनुपस्थित अंक: {_format_number_list(missing_digits, 'कोई नहीं')} | दोहराव: {repeating_text or 'कोई प्रमुख दोहराव नहीं'}",
            "सार: प्रमुख अंक आपकी प्रतिक्रिया शैली, और अनुपस्थित अंक अभ्यास-क्षेत्र दिखाते हैं।",
            "जोखिम: अधिक दोहराव से एक ही पैटर्न पर निर्भरता बढ़ सकती है।",
            "क्रिया: हर अनुपस्थित अंक के लिए 1 सरल आदत तय करें और 21 दिन लगातार करें।",
        )

    if section_key == "mobile_energy_description":
        vibration = numbers["mobileVibration"]
        traits = _number_traits(vibration)
        planet_hi = PLANET_HI_MAP.get(str(dominant_planet), _safe_text(dominant_planet) or "ग्रह संकेत")
        element_hi = ELEMENT_HI_MAP.get(str(dominant_element), _safe_text(dominant_element) or "तत्व संकेत")
        return (
            f"मोबाइल कंपन {vibration} की ऊर्जा {traits['nature']} से जुड़ी है; ग्रह {planet_hi} और तत्व {element_hi} संकेत देते हैं।",
            f"ताकत: {traits['strength']} के कारण संवाद और निर्णय का टोन साफ़ रहता है।",
            f"जोखिम: {traits['risk']} बढ़ने पर प्रतिक्रिया तेज़ हो सकती है।",
            f"क्रिया: दैनिक उपयोग में {traits['action']} ताकि ऊर्जा संतुलित रहे।",
        )

    if section_key == "dob_mobile_alignment" and plan_key not in ("enterprise", "premium"):
        status = _safe_text(mobile.get("compatibility_status") or "neutral")
        label = _alignment_label(status)
        mulank = numbers["birthNumber"]
        bhagyank = numbers["lifePath"]
        vibration = numbers["mobileVibration"]
        return (
            f"जन्मतिथि (मूलांक {mulank}, भाग्यांक {bhagyank}) और मोबाइल कंपन {vibration} के बीच {label} दिखता है।",
            "ताकत: अच्छा संरेखण होने पर मानसिक स्पष्टता और फोकस बढ़ता है।",
            "जोखिम: चुनौतीपूर्ण संरेखण में निर्णय देरी या बिखराव हो सकता है।",
            "क्रिया: निर्णय से पहले 3-बिंदु लिखित जांच सूची रखें।",
        )

    if section_key == "mulank_connection":
        mulank = numbers["birthNumber"]
        vibration = numbers["mobileVibration"]
        traits = _number_traits(mulank)
        match = "मेल" if mulank == vibration else "अंतर"
        return (
            f"मूलांक {mulank} आपकी शैली है और मोबाइल कंपन {vibration} बाहरी संचार टोन तय करता है; दोनों में {match} दिखता है।",
            f"ताकत: अच्छा कनेक्शन होने पर {traits['strength']} स्थिर रहती है।",
            "जोखिम: गति अलग होने पर संदेश और क्रिया के बीच अंतर बढ़ सकता है।",
            "क्रिया: दिन की शुरुआत में 1 प्राथमिक कार्य तय करें और मोबाइल उपयोग उसी क्रम में रखें।",
        )

    if section_key == "bhagyank_connection":
        bhagyank = numbers["lifePath"]
        vibration = numbers["mobileVibration"]
        traits = _number_traits(bhagyank)
        return (
            f"भाग्यांक {bhagyank} दिशा तय करता है और मोबाइल कंपन {vibration} आपकी दैनिक गति को।",
            f"ताकत: तालमेल होने पर {traits['strength']} से परिणाम स्थिर रहते हैं।",
            "जोखिम: फॉलो-अप कमजोर होने पर दिशा बदलने की प्रवृत्ति बढ़ सकती है।",
            "क्रिया: लक्ष्य, समय-सीमा और साप्ताहिक समीक्षा को एक साथ लॉक करें।",
        )

    if section_key == "combo_analysis":
        mulank = numbers["birthNumber"]
        bhagyank = numbers["lifePath"]
        vibration = numbers["mobileVibration"]
        if mulank == bhagyank == vibration:
            blend = "पूर्ण सामंजस्य"
        elif len({mulank, bhagyank, vibration}) == 2:
            blend = "आंशिक सामंजस्य"
        else:
            blend = "मिश्रित ऊर्जा"
        return (
            f"मूलांक {mulank}, भाग्यांक {bhagyank}, मोबाइल कंपन {vibration} के बीच {blend} है।",
            "मुख्य प्रभाव: यह संयोजन निर्णय, लक्ष्य और संचार को एक साथ चलाता है।",
            "जोखिम: मिश्रित ऊर्जा में कई लक्ष्य साथ पकड़ने की प्रवृत्ति बढ़ सकती है।",
            "क्रिया: एक समय पर एक बड़ा लक्ष्य रखें, बाकी कार्यों को सहायक सूची में रखें।",
        )

    if section_key == "lucky_numbers_unlucky_numbers_neutral_numbers":
        supportive_set = {int(x) for x in supportive_numbers if str(x).isdigit()}
        if not supportive_set:
            fallback = [numbers["mobileVibration"], numbers["birthNumber"], numbers["lifePath"]]
            supportive_set = {value for value in fallback if value}
        all_numbers = set(range(1, 10))
        caution_set = {int(x) for x in caution_numbers if str(x).isdigit()}
        if not caution_set:
            caution_set = all_numbers - supportive_set
        neutral_set = all_numbers - supportive_set - caution_set
        if not neutral_set:
            core_set = {numbers["mobileVibration"], numbers["birthNumber"], numbers["lifePath"]}
            neutral_candidates = [
                num for num in sorted(all_numbers) if num not in supportive_set and num not in core_set
            ]
            neutral_set = set(neutral_candidates[:3])
        if not neutral_set:
            neutral_candidates = [num for num in sorted(all_numbers) if num not in supportive_set]
            neutral_set = set(neutral_candidates[:2])
        supported_text = _format_number_list(sorted(supportive_set), "उपलब्ध नहीं")
        caution_text = _format_number_list(sorted(caution_set), "उपलब्ध नहीं")
        neutral_text = _format_number_list(sorted(neutral_set), "उपलब्ध नहीं")
        return (
            "आपके नंबर पैटर्न के आधार पर शुभ, अशुभ और तटस्थ अंकों का विभाजन तय किया गया है।",
            supported_text,
            caution_text,
            f"{neutral_text} (इनका उपयोग सामान्य कार्यों के लिए करें)।",
        )

    if section_key == "lucky_numbers":
        supported = ", ".join(str(x) for x in supportive_numbers) if supportive_numbers else "1, 3, 5"
        cautions = ", ".join(str(x) for x in caution_numbers) if caution_numbers else "4, 8"
        if plan_key == "basic":
            return (
                f"संयुक्त अंक मार्गदर्शन: शुभ {supported} | सावधानी {cautions} | तटस्थ अंक बैकअप उपयोग हेतु रखें।",
                "क्यों: सही अंक-चयन निर्णय घर्षण घटाता है और परिणाम-स्थिरता बढ़ाता है।",
                "कैसे: तारीख, मीटिंग स्लॉट, महत्वपूर्ण लेनदेन में पहले शुभ अंक विंडो चुनें।",
                "सावधानी अंकों पर निर्णय लेते समय डबल-वेरिफिकेशन नियम और लिखित योजना रखें।",
            )
        return (
            f"शुभ अंक: {supported}।",
            "ये अंक आपके निर्णय और संचार ऊर्जा को समर्थन देते हैं।",
            "शुभ अंकों को अनदेखा करने पर लाभ की गति धीमी हो सकती है।",
            "महत्वपूर्ण निर्णय और तारीखों में इन अंकों को प्राथमिकता दें।",
        )

    if section_key == "unlucky_numbers":
        cautions = ", ".join(str(x) for x in caution_numbers) if caution_numbers else "4, 8"
        return (
            f"अशुभ/सावधानी अंक: {cautions}।",
            "इन अंकों पर अतिरिक्त सावधानी रखने से जोखिम कम होता है।",
            "बिना तैयारी के इन अंकों से जुड़े निर्णय दबाव बढ़ा सकते हैं।",
            "यदि इन अंकों का उपयोग जरूरी हो तो सुरक्षा योजना साथ रखें।",
        )

    if section_key == "neutral_numbers":
        return (
            "तटस्थ अंक वे हैं जो न विशेष लाभ देते हैं और न नुकसान।",
            "इनका उपयोग व्यावहारिक निर्णयों में किया जा सकता है।",
            "अत्यधिक भरोसा करने से ऊर्जा प्रभाव कम हो सकता है।",
            "तटस्थ अंकों का उपयोग बैकअप विकल्प के रूप में करें।",
        )

    if section_key == "color_recommendation":
        vibration = numbers["mobileVibration"] or numbers["lifePath"] or 5
        fallback_colors = COLOR_MAP.get(vibration, ["हल्का पीला", "सफेद"])
        colors = _normalize_color_list(guidance_colors, fallback_colors)
        color_text = ", ".join(str(item) for item in colors) if colors else "हल्का पीला, सफेद"
        planet_hi = PLANET_HI_MAP.get(str(dominant_planet), "ग्रह")
        return (
            f"अनुशंसित रंग {color_text} हैं, जो आपके नंबर पैटर्न को स्थिर रखते हैं।",
            f"ताकत: {planet_hi} संकेत वाले रंग निर्णय स्पष्टता बढ़ाते हैं।",
            "जोखिम: रंग असंगत होने पर फोकस बिखर सकता है।",
            "क्रिया: कपड़े, कार्य-स्थान और मोबाइल कवर में यही टोन रखें।",
        )

    if section_key == "health_wealth_relationship_insight":
        health_score = derived_scores.get("emotional_regulation_index")
        wealth_score = derived_scores.get("financial_discipline_index")
        relationship_score = derived_scores.get("emotional_regulation_index")
        health_band = _score_band_label(health_score)
        wealth_band = _score_band_label(wealth_score)
        relationship_band = _score_band_label(relationship_score)
        health_value = health_score if health_score is not None else "निश्चित नहीं"
        wealth_value = wealth_score if wealth_score is not None else "निश्चित नहीं"
        relationship_value = relationship_score if relationship_score is not None else "निश्चित नहीं"
        return (
            "स्वास्थ्य, धन और संबंध संकेत आपके नंबर पैटर्न और स्कोर पर आधारित हैं।",
            f"स्कोर {health_value} ({health_band}); नींद की स्थिरता और हल्की गतिविधि से संतुलन बनेगा।",
            f"स्कोर {wealth_value} ({wealth_band}); खर्च की सीमा और साप्ताहिक समीक्षा आवश्यक है।",
            f"स्कोर {relationship_value} ({relationship_band}); स्पष्ट संवाद और तय समय से स्थिरता बढ़ेगी।",
        )

    if section_key == "health_insight":
        if plan_key == "basic":
            return (
                "जीवन अंतर्दृष्टि (स्वास्थ्य + धन + संबंध): अनुशासन टूटा तो तीनों क्षेत्रों में साथ दबाव बढ़ता है।",
                "क्यों: तनाव-प्रतिक्रिया, खर्च-व्यवहार और संवाद-गुणवत्ता एक ही ऊर्जा चक्र से प्रभावित होते हैं।",
                "कैसे: नींद-जल-गतिविधि, साप्ताहिक खर्च समीक्षा, और एक निश्चित संबंध संवाद-विंडो लॉक करें।",
                "7-दिवसीय ट्रैकर चलाएँ—नींद, खर्च, संवाद—तीनों का रोज़ 1-लाइन लॉग रखें।",
            )
        return (
            "स्वास्थ्य संकेत बताते हैं कि तनाव और अनुशासन का सीधा असर शरीर पर पड़ता है।",
            "नियमित नींद और जल-सेवन से ऊर्जा स्थिर रहती है।",
            "दिनचर्या टूटने पर स्वास्थ्य प्रभाव तेज़ हो सकते हैं।",
            "सप्ताह में 4 दिन हल्की गतिविधि और स्थिर समय-सीमा रखें।",
        )

    if section_key == "wealth_insight":
        return (
            "धन संकेत बताते हैं कि अनुशासन और खर्च नियंत्रण प्राथमिक आवश्यकता है।",
            "स्थिर कैश-फ्लो रखने पर धन वृद्धि की संभावना बढ़ती है।",
            "यदि खर्च आवेग में हो तो वित्तीय दबाव बढ़ता है।",
            "EMI/बचत को अलग करके ट्रैक करें और साप्ताहिक समीक्षा करें।",
        )

    if section_key == "relationship_insight":
        return (
            "संबंध संकेत बताते हैं कि संवाद की गुणवत्ता आपके निर्णय और ऊर्जा को प्रभावित करती है।",
            "नरम और स्पष्ट संवाद संबंधों में स्थिरता देता है।",
            "दबाव में भावनाएँ दबाने से तनाव बढ़ सकता है।",
            "साप्ताहिक संवाद समय तय करें और अपेक्षाएँ साफ रखें।",
        )

    if section_key == "remedies_logic":
        if plan_key == "basic":
            return (
                f"उपाय फ्रेम: ग्रह {dominant_planet}, मंत्र {guidance_mantra}, रत्न {guidance_gemstone}, दिशा {guidance_direction}।",
                "क्यों: उपाय तभी काम करते हैं जब उन्हें व्यवहार अनुशासन और समय-चक्र से जोड़ा जाए।",
                "कैसे: 21 दिन का नियम—सुबह मंत्र + स्वर-संतुलन श्वास + शाम 5 मिनट दिन-समापन समीक्षा।",
                "स्वर-संतुलन के अनुसार निर्णय लें: इड़ा में योजना, पिंगला में क्रिया करें।",
            )
        return (
            "उपाय तर्क का आधार अनुशासन, संतुलन और ऊर्जा सुधार है।",
            f"मुख्य मंत्र: {guidance_mantra}। रत्न: {guidance_gemstone}।",
            "यदि उपाय केवल प्रतीकात्मक हों तो परिणाम सीमित रहेंगे।",
            "21 दिनों का अनुशासित अभ्यास सबसे प्रभावी रहेगा।",
        )

    if section_key == "remedies":
        vibration = numbers["mobileVibration"] or numbers["lifePath"] or 5
        supportive_set = {int(x) for x in supportive_numbers if str(x).isdigit()}
        if not supportive_set:
            fallback = [numbers["mobileVibration"], numbers["birthNumber"], numbers["lifePath"]]
            supportive_set = {value for value in fallback if value}
        caution_set = {int(x) for x in caution_numbers if str(x).isdigit()}
        supported_text = _format_number_list(sorted(supportive_set), "उपलब्ध नहीं")
        caution_text = _format_number_list(sorted(caution_set), "कुछ अंक")
        colors = _normalize_color_list(guidance_colors, COLOR_MAP.get(vibration, ["हल्का पीला", "सफेद"]))
        color_text = ", ".join(str(item) for item in colors) if colors else "हल्का पीला, सफेद"
        mantra_text = MANTRA_HI_MAP.get(vibration, "ॐ शांति")
        if plan_key == "standard":
            name_suggestion = _safe_text((numerology_values.get("name_correction") or {}).get("suggestion") or "")
            if not name_suggestion:
                name_suggestion = "नाम में उच्चारण संतुलन रखें और छोटे सुधार से शुरुआत करें।"
            mobile_suggestion = _safe_text(mobile.get("correction_suggestion") or "")
            if not mobile_suggestion:
                mobile_suggestion = f"यदि संभव हो तो अंतिम अंकों में {supported_text} ऊर्जा रखें।"
            wallpaper_text = f"{color_text} टोन वाला वॉलपेपर रखें ताकि फोकस स्थिर रहे।"
            safe_direction = guidance_direction or "पूर्व/उत्तर"
            safe_day = guidance_day or "सोमवार"
            charging_text = f"{safe_direction} दिशा में चार्ज करें, दिन: {safe_day}।"
            crystal_text = guidance_gemstone or "सामान्य ऊर्जा हेतु एक हल्का क्रिस्टल/कंगन रखें।"
            return (
                "ये उपाय नाम, मोबाइल और मुख्य चुनौती को एक साथ संरेखित करने के लिए हैं।",
                name_suggestion,
                f"{supported_text} को तिथि, मीटिंग और महत्वपूर्ण कार्यों में प्राथमिकता दें।",
                " || ".join(
                    [
                        mobile_suggestion,
                        f"{color_text} मोबाइल कवर का उपयोग करें।",
                        wallpaper_text,
                        charging_text,
                        crystal_text,
                        mantra_text,
                    ]
                ),
            )
        return (
            "ये उपाय आपके नंबर पैटर्न और मुख्य चुनौती को व्यवहार में उतारने के लिए हैं।",
            f"{supported_text} को तिथि, मीटिंग और महत्वपूर्ण कार्यों में प्राथमिकता दें।",
            f"यदि बदलाव संभव हो तो मोबाइल नंबर के अंतिम अंकों में {supported_text} ऊर्जा रखें और {caution_text} सीमित रखें।",
            f"{color_text} || {mantra_text}",
        )

    if section_key == "lucky_number_usage":
        supported = ", ".join(str(x) for x in supportive_numbers) if supportive_numbers else "1, 3, 5"
        return (
            f"शुभ अंकों का उपयोग: {supported} को निर्णय, तिथि और नाम में प्राथमिकता दें।",
            "व्यावहारिक उपयोग से ऊर्जा स्थिर रहती है।",
            "अत्यधिक निर्भरता से लचीलापन कम हो सकता है।",
            "शुभ अंकों को केवल मुख्य निर्णयों में लागू करें।",
        )

    if section_key == "mobile_recommendation":
        suggestion = _safe_text(mobile.get("correction_suggestion") or "")
        if plan_key == "basic":
            return (
                "मोबाइल अनुशंसा: पहले व्यवहार-सुधार, फिर नंबर-परिवर्तन; केवल नंबर बदलना पर्याप्त नहीं।",
                suggestion or "यदि बदलना हो तो 4/6/8 आधारित स्थिर पैटर्न चुनें और 30-दिन ट्रांज़िशन रखें।",
                f"क्यों: ग्रह {dominant_planet} की असंतुलित अभिव्यक्ति प्रतिक्रिया-आधारित निर्णय बढ़ाती है।",
                "कैसे: 21 दिन अनुशासन प्रयोग + स्वर-जांच + निर्णय लॉग के बाद अंतिम नंबर निर्णय लें।",
            )
        return (
            "मोबाइल अनुशंसा में संख्या संतुलन और ऊर्जा स्थिरता प्राथमिक है।",
            suggestion or "यदि बदलना हो तो 4, 6, 8 जैसी स्थिर कंपन वाले विकल्प देखें।",
            "बिना व्यवहार सुधार के केवल नंबर बदलना पर्याप्त नहीं होगा।",
            "पहले 21 दिन अनुशासन प्रयोग करें, फिर निर्णय लें।",
        )

    if section_key == "mobile_cover_color":
        colors = _normalize_color_list(
            guidance_colors,
            COLOR_MAP.get(numbers["mobileVibration"] or numbers["lifePath"] or 5, ["हल्का पीला", "सफेद"]),
        )
        colors = ", ".join(str(item) for item in colors) if colors else "हल्का पीला, सफेद"
        return (
            f"मोबाइल कवर रंग सुझाव: {colors}।",
            "कवर रंग ऊर्जा को रिमाइंडर की तरह काम करता है।",
            "अनुशंसित रंग से बाहर जाना ऊर्जा को बिखेर सकता है।",
            "कम से कम 21 दिन एक ही रंग रखें।",
        )

    if section_key == "mantra_recommendation":
        return (
            f"मंत्र अनुशंसा: {guidance_mantra}।",
            "मंत्र का नियमित जप ऊर्जा स्थिरता बढ़ाता है।",
            "अनियमित जप से प्रभाव कम हो सकता है।",
            "दिन में दो बार 11 बार जप करें।",
        )

    if section_key == "summary_and_priority_actions":
        strongest = _safe_text(derived_scores.get("strongest_area") or "मुख्य ताकत")
        weakest = _safe_text(derived_scores.get("weakest_area") or "मुख्य सुधार")
        action_1 = "एक समय पर एक लक्ष्य, दैनिक 60 मिनट फोकस्ड निष्पादन"
        action_2 = "साप्ताहिक समीक्षा: निर्णय, खर्च और अनुशासन का 1-पेज लॉग"
        action_3 = "नाम + मोबाइल उपयोग में एकरूपता बनाए रखें"
        action_4 = "शुभ अंकों वाले निर्णय-समय चुनें"
        return (
            f"सारांश: {strongest} आपकी ताकत है और {weakest} प्राथमिक सुधार बिंदु है।",
            f"प्राथमिक कार्य: 1) {action_1} 2) {action_2} 3) {action_3} 4) {action_4}",
            "यदि साप्ताहिक समीक्षा छूटे तो सुधार की गति धीमी हो सकती है।",
            "अगले 21 दिनों तक यही 4 प्राथमिक कार्य लगातार लागू करें।",
        )

    if section_key == "final_outcome":
        if plan_key == "basic":
            return (
                f"अंतिम सार: {strongest} आपकी शक्ति है, {weakest} सुधार बिंदु है; 21 दिन अनुशासन से स्पष्ट बदलाव संभव है।",
                "क्यों: मूलांक-भाग्यांक-मोबाइल कॉम्बो संतुलित होने पर निर्णय, धन और संबंध तीनों में स्थिरता बढ़ती है।",
                "कैसे: 7-7 दिन के तीन चरण रखें—(1) दिनचर्या, (2) निर्णय अनुशासन, (3) समीक्षा और समायोजन।",
                "ग्रह-संरेखण, स्वर-संतुलन श्वास और मापनीय ट्रैकर को एक ही सिस्टम की तरह चलाएँ।",
            )
        return (
            f"अंतिम परिणाम: {strongest} को आधार बनाकर {weakest} पर सुधार लागू करें।",
            "संतुलित नाम, मोबाइल और दिनचर्या से ऊर्जा सुधरती है।",
            "यदि सुधार चरण छोड़े गए तो परिणाम अस्थिर रहेंगे।",
            "आज से 7 दिन के छोटे लक्ष्य तय करें और निष्पादन शुरू करें।",
        )

    if section_key == "wallpaper_suggestion":
        colors = _normalize_color_list(
            guidance_colors,
            COLOR_MAP.get(numbers["mobileVibration"] or numbers["lifePath"] or 5, ["नीला", "हल्का पीला"]),
        )
        colors = ", ".join(str(item) for item in colors) if colors else "नीला, हल्का पीला"
        return (
            f"वॉलपेपर सुझाव: {colors} टोन वाली छवि।",
            "दैनिक दृश्य संकेत ऊर्जा को केंद्रित रखने में मदद करता है।",
            "अव्यवस्थित दृश्य आपके फोकस को भटका सकते हैं।",
            "सुझाए गए रंगों को 21 दिन तक स्थिर रखें।",
        )

    if section_key == "charging_direction":
        return (
            f"चार्जिंग दिशा: {guidance_direction} की ओर रखें, दिन: {guidance_day}।",
            "नियमित दिशा-अनुशासन से ऊर्जा स्थिर होती है।",
            "दिशा का पालन न होने पर प्रभाव कमजोर हो सकता है।",
            "कम से कम 10 मिनट का चार्जिंग रिचुअल तय करें।",
        )

    if section_key == "bracelet_crystal_suggestion":
        return (
            f"कंगन/क्रिस्टल सुझाव: {guidance_gemstone} या इसके समान ऊर्जा वाला क्रिस्टल।",
            "यह मानसिक स्थिरता और अनुशासन को समर्थन देता है।",
            "गलत चयन प्रभाव को कमजोर कर सकता है।",
            "रोज़मर्रा में इसे एक ऊर्जा-रिमाइंडर की तरह रखें।",
        )

    if section_key == "gemstone_recommendation":
        return (
            f"रत्न अनुशंसा: {guidance_gemstone}।",
            "यह ग्रह-संतुलन और ऊर्जा स्थिरता में सहायक होता है।",
            "बिना नियमितता के रत्न का प्रभाव सीमित होगा।",
            "सप्ताह में कम से कम 4 दिन पहनना बेहतर रहेगा।",
        )

    if section_key == "monthly_cycle_analysis":
        return (
            f"मासिक/चक्र विश्लेषण बताता है कि व्यक्तिगत वर्ष {numbers['personalYear']} के अनुसार मासिक ऊर्जा बदलती रहती है।",
            "महीने की शुरुआत में लक्ष्य सेट करने से आउटपुट स्थिर रहता है।",
            "अंतिम सप्ताह में समीक्षा न होने पर चक्र टूटता है।",
            "हर महीने एक प्रमुख लक्ष्य और एक सुधार लक्ष्य तय करें।",
        )

    if plan_key in ("enterprise", "premium"):
        if section_key == "full_identity_profile":
            full_name = _premium_identity_value(normalized_input.get("fullName"), "उपलब्ध नहीं")
            dob = _premium_identity_value(normalized_input.get("dateOfBirth"), "उपलब्ध नहीं")
            mobile_number = _premium_identity_value(normalized_input.get("mobileNumber"), "उपलब्ध नहीं")
            city = _premium_identity_value(
                normalized_input.get("city") or normalized_input.get("currentCity"), "उपलब्ध नहीं"
            )
            gender = _premium_identity_value(normalized_input.get("gender"), "उपलब्ध नहीं")
            email = _premium_identity_value(normalized_input.get("email"), "उपलब्ध नहीं")
            focus_label = _premium_identity_value(
                normalized_input.get("currentProblem") or normalized_input.get("focusArea"), "उपलब्ध नहीं"
            )
            goals = _premium_join_items(normalized_input.get("goals") or [], "उपलब्ध नहीं")
            variations = _premium_join_items(_name_variation_lines(normalized_input), "उपलब्ध नहीं")
            return (
                f"प्रोफ़ाइल: नाम {full_name}, जन्मतिथि {dob}, मोबाइल {mobile_number}, शहर {city}, लिंग {gender}, ईमेल {email}।",
                f"फोकस/चुनौती: {focus_label} | लक्ष्य: {goals}",
                f"नाम विकल्प: {variations}",
                "इस पहचान प्रोफ़ाइल के आधार पर आगे का संरेखण और प्रीमियम मार्गदर्शन तैयार किया गया है।",
            )

        if section_key == "core_numbers":
            supportive_numbers = numerology_values.get("supportive_numbers") or numerology_values.get("lucky_numbers") or []
            fallback_support = [
                numbers["lifePath"],
                numbers["birthNumber"],
                numbers["nameNumber"],
                numbers["mobileVibration"],
            ]
            support_candidates = supportive_numbers or [value for value in fallback_support if value]
            support_text = _format_number_list(sorted(set(support_candidates)), "1, 3, 5")
            return (
                f"मुख्य अंक: मूलांक {numbers['birthNumber']}, भाग्यांक {numbers['lifePath']}, नाम अंक {numbers['nameNumber']}, मोबाइल कंपन {numbers['mobileVibration']}।",
                f"डेस्टिनी समर्थन अंक: {support_text}",
                "मुख्य अंकों का संतुलन निर्णय, अनुशासन और पहचान ऊर्जा को स्थिर रखता है।",
                "इन अंकों को निर्णय-समय, तारीख और संचार ताल में प्राथमिकता दें।",
            )

        if section_key == "advanced_name_numerology":
            name_number = numbers["nameNumber"]
            traits = _number_traits(name_number)
            return (
                f"उन्नत नाम अंक {name_number} आपकी पहचान, प्रभाव और सार्वजनिक छवि की दिशा तय करता है।",
                f"ताकत: {traits['strength']} के कारण अभिव्यक्ति गहरी और असरदार रहती है।",
                f"जोखिम: {traits['risk']} बढ़ने पर पहचान में अस्थिरता आ सकती है।",
                f"क्रिया: {traits['action']} और संचार/हस्ताक्षर में एकरूपता रखें।",
            )

        if section_key == "karmic_name_analysis":
            name_number = numbers["nameNumber"]
            weakest = _safe_text(derived_scores.get("weakest_area") or "अनुशासन")
            return (
                f"कर्मिक नाम विश्लेषण नाम अंक {name_number} के साथ आपकी सीखने की दिशा दिखाता है।",
                f"कर्मिक संकेत: {weakest} पर ध्यान देने से नाम ऊर्जा स्थिर होती है।",
                "असंतुलन रहने पर वही पैटर्न बार-बार दोहरता है।",
                "हर 7 दिनों में एक सुधार क्रिया तय कर उसका ट्रैक रखें।",
            )

        if section_key == "planetary_name_support_mapping":
            planet_hi = PLANET_HI_MAP.get(str(dominant_planet), _safe_text(dominant_planet) or "ग्रह संकेत")
            element_hi = ELEMENT_HI_MAP.get(str(dominant_element), _safe_text(dominant_element) or "तत्व संकेत")
            return (
                f"नाम ऊर्जा के लिए सहायक ग्रह {planet_hi} और तत्व {element_hi} प्रमुख माने जाते हैं।",
                "सही ग्रह-समर्थन नाम प्रभाव और निर्णय स्पष्टता बढ़ाता है।",
                "असंतुलन होने पर पहचान ऊर्जा बिखर सकती है।",
                "ग्रह-अनुरूप रंग और दिनचर्या को प्राथमिकता दें।",
            )

        if section_key == "multi_name_correction_options":
            variations = _name_variation_lines(normalized_input)
            variation_line = _join_items(variations, "स्वर जोड़ना / उच्चारण सरल करना / नाम की लंबाई संतुलित रखना")
            return (
                "बहु-नाम सुधार विकल्प पहचान ऊर्जा को स्थिर करने हेतु दिए गए हैं।",
                f"विकल्प: {variation_line}",
                "बड़े बदलाव से पहले छोटे परीक्षण करें।",
                "2-3 विकल्प चुनकर 21 दिन का व्यवहारिक ट्रायल करें।",
            )

        if section_key == "name_optimization_scoring":
            score = derived_scores.get("dharma_alignment_score")
            band = _score_band_label(score)
            score_text = score if score is not None else "निश्चित नहीं"
            return (
                f"नाम अनुकूलन स्कोर: {score_text} ({band})।",
                "उच्च स्कोर पहचान ऊर्जा को स्थिर और प्रभावी बनाता है।",
                "कम स्कोर में सुधार की प्राथमिकता बढ़ती है।",
                "स्कोर सुधार हेतु नाम-विकल्प और उपयोग-नियम साथ रखें।",
            )

        if section_key == "prefix_suffix_advanced_logic":
            name_number = numbers["nameNumber"]
            hint = "कठोर कंपन को नरम करने हेतु स्वरों का संयोजन उपयोगी रहता है।" if name_number in (4, 8) else "स्पष्ट उच्चारण अक्षर पहचान ऊर्जा मजबूत करते हैं।"
            return (
                "उन्नत प्रिफिक्स/सुफिक्स तर्क नाम ऊर्जा को सूक्ष्म स्तर पर संतुलित करता है।",
                hint,
                "गलत अक्षर जोड़ने से नाम ऊर्जा अस्थिर हो सकती है।",
                "छोटे अक्षर-समायोजन से शुरुआत करें और प्रभाव ट्रैक करें।",
            )

        if section_key == "mobile_numerology_advanced":
            mobile_total = mobile.get("mobile_total")
            dominant_digits = mobile.get("dominant_digits") or []
            dominant_text = _format_number_list(dominant_digits, "उपलब्ध नहीं")
            vibration = numbers["mobileVibration"]
            return (
                f"उन्नत मोबाइल विश्लेषण: कुल योग {mobile_total or 'निश्चित नहीं'}, कंपन {vibration}, प्रमुख अंक {dominant_text}।",
                "यह कंपन आपकी प्रतिक्रिया शैली और निर्णय लय तय करता है।",
                "अनुशासन कमजोर होने पर गति बिखर सकती है।",
                "मोबाइल उपयोग स्लॉट और निर्णय समय तय रखें।",
            )

        if section_key == "mobile_digit_micro_analysis":
            missing_digits = mobile.get("missing_digits") or []
            repeating_digits = mobile.get("repeating_digits") or []
            repeating_text = ", ".join(
                f"{item.get('digit')}({item.get('count')} बार)"
                for item in repeating_digits
                if isinstance(item, dict) and item.get("digit")
            )
            return (
                f"सूक्ष्म विश्लेषण: अनुपस्थित अंक {_format_number_list(missing_digits, 'कोई नहीं')} | दोहराव {repeating_text or 'कोई प्रमुख दोहराव नहीं'}।",
                "माइक्रो पैटर्न आपके छोटे निर्णयों पर असर डालते हैं।",
                "अनुपस्थित अंक संबंधित कौशल को कमजोर कर सकते हैं।",
                "हर अनुपस्थित अंक के लिए 1 सरल अभ्यास तय करें।",
            )

        if section_key == "mobile_energy_forecasting":
            vibration = numbers["mobileVibration"]
            personal_year = numbers.get("personalYear") or numerology_values.get("personal_year")
            return (
                f"मोबाइल ऊर्जा पूर्वानुमान: वर्तमान कंपन {vibration} से अगले चक्र की दिशा तय होती है।",
                f"व्यक्तिगत वर्ष {personal_year or 'निश्चित नहीं'} के साथ तालमेल रखने पर ऊर्जा स्थिर रहती है।",
                "असंतुलन से निर्णय गति और फोकस में उतार-चढ़ाव आ सकता है।",
                "हर माह के पहले सप्ताह में निर्णय योजना बनाएं।",
            )

        if section_key == "name_mobile_alignment":
            name_number = numbers["nameNumber"]
            vibration = numbers["mobileVibration"]
            label = "उच्च सामंजस्य" if name_number == vibration else "आंशिक सामंजस्य" if abs(name_number - vibration) <= 2 else "मिश्रित सामंजस्य"
            return (
                f"नाम अंक {name_number} और मोबाइल कंपन {vibration} के बीच {label} दिखता है।",
                "सामंजस्य होने पर पहचान और संचार दोनों स्थिर रहते हैं।",
                "मिश्रित सामंजस्य में प्रयास अधिक लगता है।",
                "मोबाइल उपयोग समय और नाम उपयोग में एकरूपता रखें।",
            )

        if section_key == "dob_name_alignment":
            return (
                f"जन्मतिथि (मूलांक {numbers['birthNumber']}, भाग्यांक {numbers['lifePath']}) और नाम अंक {numbers['nameNumber']} का गहरा संरेखण दिखता है।",
                "अच्छा संरेखण निर्णय और पहचान स्थिरता बढ़ाता है।",
                "कमज़ोर संरेखण होने पर नाम सुधार प्राथमिक बनता है।",
                "नाम विकल्पों का जन्म-अंक के साथ मिलान करें।",
            )

        if section_key == "dob_mobile_alignment":
            status = _safe_text((numerology_values.get("mobile_analysis") or {}).get("compatibility_status") or "neutral")
            label = _alignment_label(status)
            return (
                f"जन्मतिथि और मोबाइल कंपन के बीच {label} दिखता है।",
                "संतुलन होने पर निर्णय गति स्थिर रहती है।",
                "असंतुलन में प्रतिक्रिया-आधारित निर्णय बढ़ सकते हैं।",
                "महत्वपूर्ण निर्णय लिखित पुष्टि के साथ लें।",
            )

        if section_key == "full_system_alignment_score":
            scores = [
                derived_scores.get("life_stability_index"),
                derived_scores.get("confidence_score"),
                derived_scores.get("dharma_alignment_score"),
            ]
            avg = None
            valid_scores = [value for value in scores if isinstance(value, (int, float))]
            if valid_scores:
                avg = round(sum(valid_scores) / len(valid_scores))
            band = _score_band_label(avg)
            mulank = numbers["birthNumber"]
            bhagyank = numbers["lifePath"]
            name_number = numbers["nameNumber"]
            mobile = numbers["mobileVibration"]
            return (
                f"पूर्ण सिस्टम एलाइनमेंट स्कोर: {avg if avg is not None else 'निर्धारित नहीं'} ({band})।",
                f"मूलांक {mulank}, भाग्यांक {bhagyank}, नाम अंक {name_number} और मोबाइल कंपन {mobile} का संयुक्त संतुलन यह स्कोर बनाता है।",
                "उच्च स्कोर निर्णय-लय और पहचान-ऊर्जा में स्थिरता को दर्शाता है।",
                "यदि स्कोर मध्यम/कम है तो दिनचर्या और निर्णय अनुशासन के लिखित नियम अपनाएं।",
            )

        if section_key == "strength_vs_risk_matrix":
            strongest = _safe_text(derived_scores.get("strongest_area") or "मुख्य ताकत")
            weakest = _safe_text(derived_scores.get("weakest_area") or "मुख्य जोखिम")
            mulank = numbers["birthNumber"]
            bhagyank = numbers["lifePath"]
            return (
                f"ताकत बनाम जोखिम: ताकत {strongest}, जोखिम {weakest}।",
                f"ताकत {strongest} को मूलांक {mulank} की ऊर्जा समर्थन देती है।",
                f"जोखिम {weakest} भाग्यांक {bhagyank} के दबाव में बढ़ सकता है।",
                "साप्ताहिक समीक्षा में ताकत-जोखिम का 1-पेज ट्रैक रखें।",
            )

        if section_key == "life_area_scores":
            health = derived_scores.get("emotional_regulation_index")
            wealth = derived_scores.get("financial_discipline_index")
            stability = derived_scores.get("life_stability_index")
            confidence = derived_scores.get("confidence_score")
            return (
                "जीवन-क्षेत्र स्कोर वर्तमान ऊर्जा संतुलन का स्पष्ट संकेत देते हैं।",
                f"स्वास्थ्य: {health if health is not None else 'निश्चित नहीं'} | धन: {wealth if wealth is not None else 'निश्चित नहीं'}",
                f"स्थिरता: {stability if stability is not None else 'निश्चित नहीं'} | आत्मविश्वास: {confidence if confidence is not None else 'निश्चित नहीं'}",
                "कम स्कोर वाले क्षेत्र पर प्राथमिक सुधार लागू करें।",
            )

        if section_key == "mulank_deep_analysis":
            traits = _number_traits(numbers["birthNumber"])
            return (
                f"मूलांक {numbers['birthNumber']} का गहन विश्लेषण आपकी कर्मिक शैली दिखाता है।",
                f"ताकत: {traits['strength']} आपके कार्य-तरीके को स्थिर करती है।",
                f"जोखिम: {traits['risk']} बढ़ने पर निर्णय असंगति बढ़ती है।",
                f"क्रिया: {traits['action']} और अनुशासन नियम तय करें।",
            )

        if section_key == "bhagyank_destiny_roadmap":
            traits = _number_traits(numbers["lifePath"])
            return (
                f"भाग्यांक {numbers['lifePath']} डेस्टिनी रोडमैप आपकी दीर्घ दिशा तय करता है।",
                f"ताकत: {traits['strength']} से लक्ष्य पर टिके रहना आसान होता है।",
                f"जोखिम: {traits['risk']} बढ़ने पर दिशा बदल सकती है।",
                f"क्रिया: {traits['action']} और त्रैमासिक समीक्षा रखें।",
            )

        if section_key == "lo_shu_grid_advanced":
            lo_shu = numerology_values.get("loshu_grid") or {}
            missing = lo_shu.get("missing_numbers") or []
            grid_counts = lo_shu.get("grid_counts") or {}
            repeating = [num for num, count in grid_counts.items() if int(count or 0) > 1]
            return (
                f"उन्नत लो-शू: अनुपस्थित {_format_number_list(missing, 'कोई नहीं')} | दोहराव {_format_number_list(repeating, 'कोई नहीं')}।",
                "यह ग्रिड कर्मिक गैप और सक्रिय ऊर्जा दोनों दिखाता है।",
                "अनुपस्थित अंक संबंधित क्षेत्र में धीमापन ला सकते हैं।",
                "लक्षित अभ्यास और अनुशासन से गैप भरें।",
            )

        if section_key == "planetary_influence_mapping":
            planet_hi = PLANET_HI_MAP.get(str(dominant_planet), _safe_text(dominant_planet) or "ग्रह संकेत")
            element_hi = ELEMENT_HI_MAP.get(str(dominant_element), _safe_text(dominant_element) or "तत्व संकेत")
            return (
                f"ग्रह प्रभाव: {planet_hi} और तत्व {element_hi} का प्रभुत्व दिखता है।",
                "यह प्रभाव निर्णय, अनुशासन और भावनात्मक टोन पर असर डालता है।",
                "असंतुलन होने पर प्रतिक्रिया तेज़ हो सकती है।",
                "ग्रह-अनुरूप दिनचर्या और रंग अपनाएँ।",
            )

        if section_key == "current_planetary_phase":
            phases = ["स्थिरता चरण", "विकास चरण", "समीक्षा चरण", "पुनर्संरचना चरण"]
            idx = (numbers["lifePath"] + numbers["nameNumber"]) % len(phases)
            return (
                f"वर्तमान ग्रह चरण: {phases[idx]}।",
                "यह चरण निर्णय गति और ऊर्जा-प्रवाह को परिभाषित करता है।",
                "गलत चरण में आक्रामक निर्णय जोखिम बढ़ाते हैं।",
                "चरण के अनुसार छोटे लक्ष्य तय करें।",
            )

        if section_key == "upcoming_transit_highlights":
            supportive_numbers = numerology_values.get("supportive_numbers") or numerology_values.get("lucky_numbers") or []
            support_text = _format_number_list(supportive_numbers, "उपलब्ध नहीं")
            return (
                "आगामी गोचर संकेत अगले कुछ चक्रों में अवसर की दिशा बताते हैं।",
                f"शुभ अंक {support_text} वाले समय-खिड़की में निर्णय बेहतर रहते हैं।",
                "बिना तैयारी के तेज़ निर्णय जोखिम बढ़ा सकते हैं।",
                "हर माह 2 निर्णय-खिड़कियाँ पहले से तय करें।",
            )

        if section_key == "personal_year_analysis":
            personal_year = numbers.get("personalYear") or numerology_values.get("personal_year")
            return (
                f"व्यक्तिगत वर्ष विश्लेषण: वर्तमान वर्ष {personal_year or 'निश्चित नहीं'} आपकी सीखने की दिशा तय करता है।",
                "सही प्राथमिकता रखने पर ऊर्जा स्थिर रहती है।",
                "अधिक लक्ष्य लेने पर लाभ बिखर सकता है।",
                "वर्ष के लिए 3 प्राथमिक लक्ष्य तय करें।",
            )

        if section_key == "monthly_cycle_analysis":
            return (
                "मासिक चक्र विश्लेषण महीने-दर-महीने ऊर्जा बदलाव दिखाता है।",
                "हर महीने की शुरुआत में प्राथमिक कार्य तय करें।",
                "अंतिम सप्ताह में समीक्षा न होने पर चक्र टूटता है।",
                "मासिक समीक्षा को स्थायी नियम बनाएं।",
            )

        if section_key == "critical_decision_windows":
            supportive_numbers = numerology_values.get("supportive_numbers") or numerology_values.get("lucky_numbers") or []
            support_text = _format_number_list(supportive_numbers, "उपलब्ध नहीं")
            return (
                "महत्वपूर्ण निर्णय समय-खिड़कियाँ आपके नंबर पैटर्न पर आधारित हैं।",
                f"शुभ अंक {support_text} वाली तिथियों को प्राथमिकता दें।",
                "जल्दबाज़ी में निर्णय जोखिम बढ़ा सकती है।",
                "निर्णय से पहले 1-पेज योजना अनिवार्य रखें।",
            )

        if section_key == "wealth_cycle_analysis":
            wealth = derived_scores.get("financial_discipline_index")
            band = _score_band_label(wealth)
            return (
                f"धन चक्र विश्लेषण: स्कोर {wealth if wealth is not None else 'निश्चित नहीं'} ({band})।",
                "सही चक्र में निवेश और बचत स्थिर रहती है।",
                "अनुशासन कमजोर होने पर दबाव बढ़ता है।",
                "हर सप्ताह बजट समीक्षा रखें।",
            )

        if section_key == "career_growth_timeline":
            confidence = derived_scores.get("confidence_score")
            band = _score_band_label(confidence)
            return (
                f"करियर विकास टाइमलाइन: आत्मविश्वास स्कोर {confidence if confidence is not None else 'निश्चित नहीं'} ({band})।",
                "स्थिर आत्मविश्वास से प्रगति गति बढ़ती है।",
                "अनिश्चितता में दिशा बार-बार बदल सकती है।",
                "प्रत्येक तिमाही में 1 मुख्य करियर लक्ष्य तय करें।",
            )

        if section_key == "relationship_timing_patterns":
            rel = derived_scores.get("emotional_regulation_index")
            band = _score_band_label(rel)
            return (
                f"संबंध समय-पैटर्न: भावनात्मक संतुलन स्कोर {rel if rel is not None else 'निश्चित नहीं'} ({band})।",
                "सही संवाद समय संबंध स्थिरता बढ़ाता है।",
                "दबाव में संवाद टालने से दूरी बढ़ सकती है।",
                "साप्ताहिक संवाद समय तय करें।",
            )

        if section_key == "dynamic_lucky_numbers":
            derived_lucky = _derive_premium_lucky_numbers(numbers, derived_scores, numerology_values)
            support_text = _format_number_list(derived_lucky, "1, 3, 5")
            return (
                f"गतिशील शुभ अंक: {support_text}।",
                "ये अंक मूलांक, भाग्यांक, नाम और मोबाइल कंपन के संयुक्त संकेत पर आधारित हैं।",
                "इनका उपयोग मीटिंग, लॉंच या निर्णय-समय में प्राथमिकता से करें।",
                "अति-निर्भरता से बचें और संदर्भ अनुसार चुनें।",
            )

        if section_key == "situational_caution_numbers":
            lucky = _derive_premium_lucky_numbers(numbers, derived_scores, numerology_values)
            cautions = _derive_premium_caution_numbers(lucky, numbers, derived_scores)
            caution_text = _format_number_list(cautions, "4, 8")
            status = _safe_text(derived_scores.get("risk_band") or "सुधार योग्य")
            return (
                f"परिस्थितिजन्य सावधानी अंक: {caution_text}।",
                f"कारण: वर्तमान जोखिम बैंड {status} है, इसलिए इन अंकों पर अतिरिक्त जांच रखें।",
                "बिना तैयारी के उपयोग निर्णय दबाव बढ़ा सकता है।",
                "दोहरा सत्यापन और समय-सीमा नियम अपनाएं।",
            )

        if section_key == "neutral_number_strategy_usage":
            lucky = _derive_premium_lucky_numbers(numbers, derived_scores, numerology_values)
            cautions = _derive_premium_caution_numbers(lucky, numbers, derived_scores)
            neutral_numbers = _derive_premium_neutral_numbers(lucky, cautions)
            neutral_text = _format_number_list(neutral_numbers, "2, 6")
            return (
                f"तटस्थ अंक रणनीति: {neutral_text}।",
                "ये अंक सामान्य कार्यों और बैकअप निर्णयों में सुरक्षित रहते हैं।",
                "लंबी अवधि में इन्हें स्थिरता बनाए रखने के लिए उपयोग करें।",
                "विशेष अवसरों पर प्राथमिकता शुभ अंकों को दें।",
            )

        if section_key == "color_strategy":
            colors = _normalize_color_list(guidance_colors, COLOR_MAP.get(numbers["mobileVibration"] or 5, ["हल्का पीला", "सफेद"]))
            color_text = ", ".join(str(item) for item in colors) if colors else "हल्का पीला, सफेद"
            return (
                f"रंग रणनीति: {color_text} आपके ग्रह और संख्या पैटर्न के अनुरूप हैं।",
                "सही रंग फोकस और निर्णय स्पष्टता बढ़ाते हैं।",
                "असंगत रंग ऊर्जा बिखेर सकते हैं।",
                "कपड़े, कार्य-स्थान और मोबाइल में यही रंग रखें।",
            )

        if section_key == "energy_objects_recommendation":
            base_number = numbers.get("nameNumber") or numbers.get("lifePath") or numbers.get("mobileVibration") or 5
            obj_name, obj_reason, obj_usage = ENERGY_OBJECT_MAP.get(int(base_number), ENERGY_OBJECT_MAP[5])
            return (
                f"ऊर्जा वस्तु सुझाव: {obj_name}।",
                f"कारण: {obj_reason}।",
                f"उपयोग: {obj_usage}।",
                "नियमित उपयोग से प्रभाव अधिक स्थिर रहता है।",
            )

        if section_key == "advanced_remedies_engine":
            base_number = numbers.get("nameNumber") or numbers.get("lifePath") or numbers.get("mobileVibration") or 5
            name_hint = _premium_name_correction_hint(int(base_number))
            lucky = _derive_premium_lucky_numbers(numbers, derived_scores, numerology_values)
            lucky_text = _format_number_list(lucky, "1, 3, 5")
            mantra = MANTRA_HI_MAP.get(int(base_number), "ॐ शांति")
            direction = DIRECTION_MAP.get(int(base_number), "पूर्व")
            space_hint = SPACE_ALIGNMENT_MAP.get(int(base_number), "कार्य-स्थान को सरल और साफ रखें।")
            return (
                "उन्नत उपाय इंजन पहचान, नंबर और ग्रह-संतुलन को एक सिस्टम की तरह जोड़ता है।",
                f"नाम सुधार: {name_hint}",
                f"नंबर उपयोग रणनीति: शुभ अंक {lucky_text} को समय/तारीख/निर्णय में प्राथमिकता दें।",
                f"मंत्र (अंक + ग्रह): {mantra} | दिशा मार्गदर्शन: {direction} | स्पेस एलाइनमेंट: {space_hint}",
            )

        if section_key == "business_brand_naming":
            return (
                "व्यवसाय/ब्रांड नाम सुझाव पहचान और बाज़ार प्रभाव को स्थिर करते हैं।",
                "नाम में स्पष्ट उच्चारण और संतुलित कंपन प्राथमिक रखें।",
                "अत्यधिक जटिल नाम प्रभाव कम कर सकते हैं।",
                "2-3 नाम विकल्पों का तुलनात्मक मिलान करें।",
            )

        if section_key == "signature_energy_analysis":
            return (
                "हस्ताक्षर ऊर्जा विश्लेषण पहचान और निर्णय टोन को स्थिर करता है।",
                "स्थिर हस्ताक्षर से भरोसा और स्पष्टता बढ़ती है।",
                "बार-बार बदलाव से प्रभाव कम होता है।",
                "एक समान हस्ताक्षर शैली बनाए रखें।",
            )

        if section_key == "mobile_optimization_strategy":
            return (
                "मोबाइल अनुकूलन रणनीति नंबर और उपयोग अनुशासन को जोड़ती है।",
                "सही कंपन के साथ समय-सीमा तय होने पर परिणाम स्थिर रहते हैं।",
                "अनियमित उपयोग से ऊर्जा बिखर सकती है।",
                "दैनिक दो उपयोग विंडो और साप्ताहिक समीक्षा रखें।",
            )

        if section_key == "life_strategy_recommendations":
            return (
                "जीवन रणनीति सुझाव में शॉर्ट-टर्म, मिड-टर्म और लॉन्ग-टर्म दिशा शामिल है।",
                "शॉर्ट-टर्म: दिनचर्या स्थिर करें और फोकस नियम रखें।",
                "मिड-टर्म: तिमाही लक्ष्य और समीक्षा लागू करें।",
                "लॉन्ग-टर्म: पहचान और निर्णय प्रणाली को स्थायी बनाएं।",
            )

        if section_key == "priority_action_plan":
            return (
                "प्राथमिक कार्य योजना क्रमबद्ध सुधार के लिए है।",
                "1) दिनचर्या स्थिर करें  2) साप्ताहिक समीक्षा रखें  3) निर्णय समय तय करें",
                "अधूरी योजना से गति धीमी पड़ सकती है।",
                "21 दिनों तक यह प्राथमिक क्रम लागू रखें।",
            )

        if section_key == "risk_alerts_and_mitigation":
            return (
                "जोखिम चेतावनी और निवारण आपके कमजोर क्षेत्र पर आधारित है।",
                "जोखिम: अनुशासन टूटना, निर्णय विलंब, और संचार बिखराव।",
                "निवारण: लिखित योजना, समय-ब्लॉक, और साप्ताहिक समीक्षा।",
                "प्रत्येक जोखिम के लिए 1 कार्रवाई तय करें।",
            )

        if section_key == "premium_summary_narrative":
            strongest = _safe_text(derived_scores.get("strongest_area") or "मुख्य ताकत")
            weakest = _safe_text(derived_scores.get("weakest_area") or "मुख्य सुधार")
            mulank = numbers["birthNumber"]
            bhagyank = numbers["lifePath"]
            name_number = numbers["nameNumber"]
            mobile = numbers["mobileVibration"]
            return (
                f"प्रीमियम समापन: मूलांक {mulank}, भाग्यांक {bhagyank}, नाम अंक {name_number} और मोबाइल कंपन {mobile} आपके निर्णय पैटर्न को तय करते हैं।",
                f"मुख्य ताकत {strongest} है; सुधार का प्राथमिक बिंदु {weakest} है।",
                "नाम-उपयोग और मोबाइल-अनुशासन एक साथ रखें तो परिणाम स्थिर रहते हैं।",
                "अगले 21 दिनों में एक प्राथमिक सुधार क्रिया लगातार लागू करें।",
            )

    if section_key == "executive_summary":
        return (
            f"कार्यकारी निष्कर्ष: {strongest} आपका लाभ क्षेत्र है, {weakest} सुधार क्षेत्र है, और अनुशासित समीक्षा से समय-निर्णय बेहतर होता है।",
            f"{strongest} को दैनिक क्रिया में बदला जाए तो वृद्धि तेज होती है।",
            f"{weakest} पर निगरानी छूटने से कार्यान्वयन जोखिम बढ़ता है।",
            "एक समय में तीन लक्ष्य रखें और एक पूरा करके ही नया लक्ष्य जोड़ें।",
        )
    if section_key == "core_numbers":
        return (
            f"मुख्य अंक: लाइफ पाथ {numbers['lifePath']}, डेस्टिनी {numbers['destiny']}, एक्सप्रेशन {numbers['expression']}, नेम नंबर {numbers['nameNumber']}।",
            "ये अंक पहचान, दिशा, अभिव्यक्ति और प्रभाव का मूल ढांचा बनाते हैं।",
            "अंक आधारित दिशा से अलग निर्णय लेने पर परिणाम अस्थिर हो सकते हैं।",
            "मासिक समीक्षा में इन चार अंकों के संदर्भ में अपने निर्णय मिलान करें।",
        )
    if section_key == "number_interaction":
        return (
            f"लाइफ पाथ {numbers['lifePath']} और डेस्टिनी {numbers['destiny']} का संयोजन बताता है कि आपकी ऊर्जा परिणामों से कैसे जुड़ती है।",
            "संतुलित गति होने पर यह संयोजन तेज और स्थिर प्रगति देता है।",
            "बिना समीक्षा की जल्दीबाज़ी से निर्णय गुणवत्ता गिरती है।",
            "हर बड़े निर्णय से पहले अल्पकालिक और दीर्घकालिक दोनों प्रभाव जाँचें।",
        )
    if section_key == "personality_profile":
        return (
            f"व्यक्तित्व प्रोफाइल में {strongest} आधारित स्थिरता और {weakest} आधारित ब्लाइंड-स्पॉट दोनों स्पष्ट हैं।",
            "आपकी ताकत लक्ष्य स्पष्ट होने पर निरंतर कार्यान्वयन में दिखती है।",
            "दबाव में प्रतिक्रिया तेज होने से सुधार देर से लागू हो सकता है।",
            "निर्णय से पहले संक्षिप्त लिखित स्पष्टता रखने की आदत बनाएं।",
        )
    if section_key == "focus_snapshot":
        return (
            f"वर्तमान फोकस क्षेत्र {focus} है और यह आपकी समस्या '{problem_anchor}' से सीधे जुड़ा है।",
            "संकीर्ण और मापनीय फोकस पर यह प्रोफाइल बेहतर परिणाम देती है।",
            "एक साथ कई प्राथमिकताएँ लेने से प्रगति की गति घटती है।",
            "अगले 30 दिनों के लिए एक प्राथमिक परिणाम तय करें और दैनिक क्रिया उसी से जोड़ें।",
        )
    if section_key == "personal_year":
        return (
            "व्यक्तिगत वर्ष दिशा बताती है कि यह चरण स्थिर अनुशासन और क्रमिक प्रगति का है।",
            "नियमित दिनचर्या के साथ अवसरों का लाभ तेज मिलता है।",
            "ध्यान बिखरने पर प्रयास अधिक और परिणाम कम होता है।",
            "रोज़ का पहला 30 मिनट उच्च-प्रभाव कार्य पर दें।",
        )
    if section_key == "lucky_dates":
        base_numbers = [n for n in [numbers["lifePath"], numbers["destiny"], numbers["nameNumber"]] if n > 0]
        favorable = [str(n) for n in sorted({n for n in base_numbers})][:3]
        return (
            f"अनुकूल अंक: {', '.join(favorable) if favorable else '5, 6, 9'}। मासिक अनुकूल तिथियाँ: 3, 9, 18, 27।",
            "समय-चयन सही होने पर निर्णय गुणवत्ता और परिणाम दोनों सुधरते हैं।",
            "तनाव में बिना समय-चयन निर्णय लेने से त्रुटि का जोखिम बढ़ता है।",
            "महत्वपूर्ण वार्ता, खरीद और प्रतिबद्धता इन तिथि-विंडो में रखें।",
        )
    if section_key == "color_alignment":
        anchor = numbers["lifePath"] or numbers["destiny"] or 5
        colors = COLOR_MAP.get(anchor, ["हरा", "नीला"])
        return (
            f"अनुकूल रंग: {colors[0]} और {colors[1]}। यह चयन आपके मूल अंक स्पंदन से मेल खाता है।",
            f"{colors[0]} कार्य-एकाग्रता बढ़ाता है और {colors[1]} निर्णय के समय संतुलन देता है।",
            "असंगत रंग संयोजन उच्च दबाव में मानसिक घर्षण बढ़ा सकता है।",
            f"डेस्क, दस्तावेज़ और दैनिक एक्सेसरी में {colors[0]} तथा {colors[1]} का प्रयोग करें।",
        )
    if section_key == "remedy":
        bucket = problem_bucket
        category_label = {
            "finance": "वित्त",
            "career": "करियर",
            "business": "व्यवसाय",
            "confidence": "आत्मविश्वास",
            "consistency": "अनुशासन",
            "relationship": "संबंध",
            "health": "स्वास्थ्य",
            "education": "शिक्षा",
            "general": "जीवन",
        }
        remedy_actions = {
            "finance": "दैनिक खर्च सीमा + साप्ताहिक बजट समीक्षा + कर्ज/EMI ट्रैकिंग",
            "career": "टॉप-3 दैनिक निष्पादन कार्य + गहन कार्य ब्लॉक + साप्ताहिक आउटपुट समीक्षा",
            "business": "राजस्व गुणवत्ता समीक्षा + क्लाइंट फॉलो-अप अनुशासन + साप्ताहिक निर्णय लॉग",
            "confidence": "दैनिक दृश्य-उपस्थिति अभ्यास + निर्णय-पूर्व स्क्रिप्ट + चिंतन जर्नल",
            "consistency": "नियत-समय दिनचर्या + बिना-विराम ट्रैकर + साप्ताहिक रीसेट समीक्षा",
            "relationship": "नियत संवाद लय + शांत-प्रतिक्रिया नियम + साप्ताहिक संबंध समीक्षा",
            "health": "नियत नींद समय + तनाव-रीसेट ब्लॉक + दैनिक ऊर्जा ट्रैकर",
            "education": "नियत अध्ययन ब्लॉक + पुनरावृत्ति चेकपॉइंट + साप्ताहिक मॉक-परीक्षा समीक्षा",
            "general": "एक मुख्य समस्या पर दैनिक मापनीय क्रिया + साप्ताहिक समीक्षा",
        }
        remedy_risks = {
            "finance": "खर्च ट्रैकिंग टूटते ही नकद दबाव दोबारा बढ़ सकता है।",
            "career": "कार्यान्वयन अनुशासन टूटते ही आउटपुट गिर सकता है।",
            "business": "फॉलो-अप लय टूटते ही राजस्व पाइपलाइन कमजोर हो सकती है।",
            "confidence": "दैनिक visibility कदम रुकते ही हिचक बढ़ सकती है।",
            "consistency": "रूटीन टूटते ही सुधार गति रुक सकती है।",
            "relationship": "नियत संवाद न होने पर दूरी बढ़ सकती है।",
            "health": "नींद और तनाव-लय टूटते ही ऊर्जा गिर सकती है।",
            "education": "रिवीजन लय टूटते ही प्रदर्शन अस्थिर हो सकता है।",
            "general": "समीक्षा अनुशासन टूटने पर दिशा बिखर सकती है।",
        }
        action_line = remedy_actions.get(bucket, remedy_actions["general"])
        risk_line = remedy_risks.get(bucket, remedy_risks["general"])
        label = category_label.get(bucket, category_label["general"])
        return (
            f"शीर्ष 3 प्राथमिक क्रियाएँ ({label} समस्या '{problem_anchor}' के लिए): {action_line}।",
            "7-दिवसीय अनुपालन: रोज़ 20 मिनट प्राथमिक सुधार और सप्ताहांत स्थिति-समीक्षा।",
            f"मुख्य जोखिम: {risk_line}",
            "30-दिवसीय योजना + ट्रैकिंग: हर सप्ताह मापनीय स्कोरकार्ड रखें और महीने के अंत में आधार-रेखा तुलना करें।",
        )
    if section_key == "closing_summary":
        bucket = problem_bucket
        category_label = {
            "finance": "वित्त",
            "career": "करियर",
            "business": "व्यवसाय",
            "confidence": "आत्मविश्वास",
            "consistency": "अनुशासन",
            "relationship": "संबंध",
            "health": "स्वास्थ्य",
            "education": "शिक्षा",
            "general": "जीवन",
        }
        closing_focus = {
            "finance": "वित्त अनुशासन ढीला होने पर दबाव पुनः बढ़ सकता है।",
            "career": "करियर निष्पादन लय टूटने पर प्रगति धीमी हो सकती है।",
            "business": "व्यवसाय फॉलो-अप लय टूटने पर अवसर छूट सकते हैं।",
            "confidence": "आत्मविश्वास अभ्यास रुकने पर हिचक वापस बढ़ सकती है।",
            "consistency": "अनुशासन टूटते ही सुधार की गति रुक सकती है।",
            "relationship": "संबंध संवाद-लय टूटने पर दूरी बढ़ सकती है।",
            "health": "स्वास्थ्य दिनचर्या टूटने पर ऊर्जा अस्थिर हो सकती है।",
            "education": "शिक्षा रिवीजन लय टूटने पर प्रदर्शन गिर सकता है।",
            "general": "समीक्षा-लय टूटने पर दिशा बिखर सकती है।",
        }
        label = category_label.get(bucket, category_label["general"])
        return (
            f"समापन संकेत: जोखिम बैंड {risk_band}, प्रमुख ताकत {strongest}, और सुधार क्षेत्र {weakest}।",
            f"मुख्य चुनौती क्षेत्र: {label}। फोकस समस्या पर साप्ताहिक प्रगति-पत्रक बनाए रखें।",
            f"मुख्य जोखिम: {closing_focus.get(bucket, closing_focus['general'])}",
            "अगले 30 दिनों में साप्ताहिक समीक्षा के साथ अनुशासित क्रियान्वयन रखें।",
        )
    if section_key == "lo_shu_grid":
        lo_shu = numerology_values.get("loshu_grid") or {}
        missing = lo_shu.get("missing_numbers") or []
        grid_counts = lo_shu.get("grid_counts") or {}
        repeating = [num for num, count in grid_counts.items() if int(count or 0) > 1]
        return (
            f"लो-शू ग्रिड में अनुपस्थित अंक {_format_number_list(missing, 'कोई नहीं')} और दोहराए अंक {_format_number_list(repeating, 'कोई नहीं')} दिखाई देते हैं।",
            "उपस्थित अंक आपकी प्राकृतिक ताकत और स्थिर प्रवृत्ति दिखाते हैं।",
            "अनुपस्थित अंकों से कुछ जीवन-क्षेत्रों में कमजोरी महसूस हो सकती है।",
            "हर अनुपस्थित अंक के लिए एक लक्षित अभ्यास तय करें और दोहराव वाले अंकों पर संयम रखें।",
        )
    if section_key == "missing_numbers":
        lo_shu = numerology_values.get("loshu_grid") or {}
        missing = lo_shu.get("missing_numbers") or []
        return (
            f"अनुपस्थित अंक: {missing if missing else 'कोई महत्वपूर्ण रिक्ति नहीं'}। यह विकास के कमजोर आयाम दिखाते हैं।",
            "इन रिक्तियों पर लक्षित कार्य करने से सुधार की गति बढ़ती है।",
            "रिक्ति अनदेखी होने पर वही चुनौती दोहराती रहती है।",
            "हर अनुपस्थित अंक के लिए एक साप्ताहिक सुधार कार्य तय करें।",
        )
    if section_key == "repeating_numbers":
        lo_shu = numerology_values.get("loshu_grid") or {}
        grid_counts = lo_shu.get("grid_counts") or {}
        repeating = [num for num, count in grid_counts.items() if int(count or 0) > 1]
        return (
            f"दोहराते अंक: {repeating if repeating else 'कोई प्रमुख दोहराव नहीं'}। यह कुछ प्रवृत्तियों को बहुत सक्रिय करते हैं।",
            "सही दिशा मिलने पर यही प्रवृत्ति तेज उपलब्धि देती है।",
            "तनाव में यही प्रवृत्ति कठोरता या प्रतिक्रिया बढ़ा सकती है।",
            "बड़े निर्णय से पहले ठहरें, जाँचें और फिर निर्णय लें।",
        )
    if section_key == "mobile_numerology":
        mobile_total = mobile.get("mobile_total")
        dominant_digits = mobile.get("dominant_digits") or []
        dominant_text = _format_number_list(dominant_digits, "उपलब्ध नहीं")
        vibration = numbers["mobileVibration"] or 0
        traits = _number_traits(vibration)
        return (
            f"मोबाइल नंबर का कुल योग {mobile_total or 'निश्चित नहीं'} है और कंपन {vibration} बनता है; प्रमुख अंक {dominant_text} हैं।",
            f"ताकत: यह कंपन {traits['nature']} को सक्रिय करता है और संचार टोन स्पष्ट रखता है।",
            f"जोखिम: {traits['risk']} बढ़ने पर संवाद बिखर सकता है।",
            "क्रिया: दिन में दो तय संचार स्लॉट रखें ताकि गति और अनुशासन संतुलित रहें।",
        )
    if section_key == "mobile_life_compatibility":
        mobile = numerology_values.get("mobile_analysis") or {}
        compatibility = _safe_text(mobile.get("compatibility_status") or "संतुलित")
        return (
            f"मोबाइल-जीवन संगतता वर्तमान में {compatibility} श्रेणी में है।",
            "उच्च संगतता से दिनचर्या और संवाद दोनों में सहजता आती है।",
            "कम संगतता होने पर प्रतिक्रिया-आधारित निर्णय बढ़ सकते हैं।",
            "महत्वपूर्ण निर्णय लिखित पुष्टि के साथ लें और त्वरित उत्तर कम करें।",
        )
    if section_key == "career_financial":
        if plan.lower() == "enterprise":
            return (
                f"रणनीतिक परिप्रेक्ष्य में उद्योग ({industry}), भूमिका ({occupation}), आय ({income}), ऋण ({debt}) और कार्य शैली ({work_mode}) मुख्य कारक हैं।",
                f"मुख्य अवसर: {_join_items(goals[:2], 'रणनीतिक लक्ष्य')} पर अनुशासित कार्यान्वयन।",
                f"मुख्य जोखिम: {_join_items(challenges[:2], 'वर्तमान अवरोध')} के साथ नकद अनुशासन में देरी।",
                "मासिक संचालन समीक्षा में नकद, माइलस्टोन और जोखिम सीमाएँ साथ जाँचें।",
            )
        return (
            f"करियर-वित्त संकेत भूमिका ({occupation}), आय ({income}) और कार्य शैली ({work_mode}) से जुड़े हैं।",
            "भूमिका स्पष्टता और धन अनुशासन साथ हों तो प्रगति स्थिर रहती है।",
            "बजट अनुशासन कमजोर होने पर आय के बावजूद दबाव बना रह सकता है।",
            "हर महीने एक करियर माइलस्टोन और एक बचत/ऋण चेकपॉइंट रखें।",
        )
    if section_key == "relationship_patterns":
        return (
            f"संबंध पैटर्न वर्तमान स्थिति ({relationship_status}) के आधार पर आकार ले रहे हैं।",
            "नियमित और स्पष्ट संवाद इस क्षेत्र का सबसे बड़ा स्थिरकारी तत्व है।",
            "काम और वित्त का तनाव संबंध गुणवत्ता पर सीधा असर डालता है।",
            "सप्ताह में एक स्पष्टता वार्ता रखें जिसमें अपेक्षा और समय-सीमा दोनों तय हों।",
        )
    if section_key == "health_tendencies":
        return (
            f"स्वास्थ्य प्रवृत्ति वर्तमान तनाव स्तर ({stress_level}) और रिकवरी अनुशासन से प्रभावित है।",
            "नींद, पानी और हल्की गतिविधि की नियमितता भावनात्मक संतुलन बनाए रखती है।",
            "अनियमित दिनचर्या से निर्णय स्पष्टता कम होती है।",
            "निश्चित नींद विंडो और रोज़ 20 मिनट गतिविधि को अनिवार्य नियम बनाएं।",
        )
    if section_key == "action_plan_90_days":
        if plan.lower() == "enterprise":
            return (
                f"महीना 1: संचालन स्थिरता। महीना 2: {_join_items(goals[:3], 'प्राथमिक लक्ष्य')} पर क्रिया। महीना 3: {_join_items(challenges[:3], 'मुख्य अवरोध')} नियंत्रित रखते हुए विस्तार।",
                "यह योजना रणनीति और संचालन को एक ही ताल में रखती है।",
                "मासिक समीक्षा छूटने पर छिपे जोखिम जमा होते हैं।",
                "हर माह अंत में मेट्रिक, जोखिम और अगले माह फोकस तय करें।",
            )
        return (
            "महीना 1: दिनचर्या स्थिर करें। महीना 2: काम और वित्त लय सुधारें। महीना 3: प्रगति को स्थिर कर एक प्राथमिक लक्ष्य पर विस्तार करें।",
            "मापनीय मासिक चरण इस योजना की मुख्य ताकत हैं।",
            "समीक्षा छूटने पर निरंतरता और लाभ दोनों घटते हैं।",
            "तीन माह-अंत समीक्षा पहले से तय करें और हर महीने एक KPI ट्रैक करें।",
        )
    if section_key == "growth_blockers":
        return (
            f"मुख्य अवरोध: तनाव में {to_metric_label('karma_pressure_index')} बढ़ना, {weakest} कमजोर होने पर सुधार देर से करना, और साप्ताहिक लय टूटना।",
            "अवरोध स्पष्ट होने पर सुधार व्यवहारिक और मापनीय बनता है।",
            "अनट्रैक्ड अवरोध बार-बार वही बाधा पैदा करते हैं।",
            "हर अवरोध के लिए एक प्रतिकार तय करें और 12 सप्ताह साप्ताहिक समीक्षा करें।",
        )
    if section_key == "decision_style":
        if plan.lower() == "enterprise":
            return (
                f"निर्णय शैली {report_emphasis} झुकाव और {work_mode} कार्य-पैटर्न में दिखती है; संदर्भ समस्या: {current_problem}।",
                "सर्वश्रेष्ठ परिणाम तब मिलते हैं जब निर्णय प्रमाण, जोखिम-सीमा और समय-विंडो के साथ चरणबद्ध हों।",
                "तत्कालता के कारण संरचित समीक्षा छूटने पर जोखिम तेज बढ़ता है।",
                "निर्णय गेट लागू करें: लक्ष्य-मिलान, जोखिम बजट, और 30/90-दिवसीय व्यवहार्यता।",
            )
        return (
            f"निर्णय प्रवृत्ति {report_emphasis} उन्मुख है और {work_mode} संदर्भ में समस्या '{current_problem}' से प्रभावित है।",
            "इनपुट पहले व्यवस्थित होने पर निर्णय गुणवत्ता स्पष्ट बढ़ती है।",
            "दबाव में कमजोर फ़िल्टरिंग से निर्णय वापस लेने की स्थिति बनती है।",
            "हर बड़े निर्णय से पहले लक्ष्य, डाउनसाइड और समय की तीन जाँच करें।",
        )
    if section_key == "life_timeline":
        return (
            "जीवन समयरेखा संकेत देती है कि यह संचय से संरचित विस्तार की ओर जाने वाला चरण है।",
            "मासिक समीक्षा निरंतर रहने पर मध्यम अवधि की दिशा मजबूत होती है।",
            "रिएक्टिव निर्णय समयरेखा क्रम को तोड़ते हैं।",
            "अगली 4 तिमाहियों में हर तिमाही एक रणनीतिक उद्देश्य और एक माइलस्टोन लिखें।",
        )
    if section_key == "strategic_life_theme":
        return (
            f"रणनीतिक जीवन थीम का केंद्र {focus} है, जो समस्या '{current_problem}' और लक्ष्य {_join_items(goals[:2], 'प्राथमिक लक्ष्य')} से संचालित है।",
            "थीम स्पष्ट होने पर निर्णय आत्मविश्वास और ऊर्जा-दक्षता दोनों बढ़ते हैं।",
            "पुराने माइलस्टोन बंद किए बिना नए लक्ष्य जोड़ने से थीम कमजोर होती है।",
            "अगले 90 दिनों में केवल वही पहल लें जो इस थीम को सीधे समर्थन दे।",
        )
    if section_key == "leadership_archetype":
        return (
            f"लीडरशिप प्रोफाइल में {strongest} आपका प्रमुख लाभ है और निर्णय क्षमता स्पष्ट है।",
            "स्पष्ट प्राथमिकता, जिम्मेदारी और समय-सीमा पर आपका नेतृत्व सर्वश्रेष्ठ काम करता है।",
            f"उच्च दबाव में {weakest} की निगरानी न होने पर नेतृत्व जोखिम बढ़ता है।",
            "साप्ताहिक नेतृत्व समीक्षा करें: निर्णय गुणवत्ता, टीम संरेखण और जोखिम-संशोधन।",
        )
    if section_key == "wealth_strategy":
        return (
            f"वेल्थ रणनीति उद्योग ({industry}), आय ({income}), ऋण ({debt}) और निर्णय-झुकाव ({report_emphasis}) से तय होती है।",
            "पूंजी आवंटन और जोखिम बफर की मासिक समीक्षा से वित्त अनुशासन मजबूत होता है।",
            "विस्तार और देनदारियों की गति असंतुलित होने पर नकदी प्रवाह दबाव बढ़ता है।",
            "तीन-बकेट मॉडल अपनाएँ: संचालन बफर, वृद्धि निवेश और ऋण घटाव।",
        )
    if section_key == "opportunity_windows":
        return (
            "अवसर-विंडो तब प्रभावी होती हैं जब आत्मविश्वास और समय-अनुशासन साथ काम करें।",
            "तैयार विंडो में कार्रवाई करने से परिणाम गुणवत्ता बेहतर रहती है।",
            "संकेत तैयार होने के बाद निर्णय देर से लेने पर अवसर निकल सकता है।",
            "हर महीने निवेश और साझेदारी के लिए दो पूर्व-निर्धारित निर्णय-विंडो रखें।",
        )
    if section_key == "decision_timing":
        return (
            f"निर्णय समय-निर्धारण में {report_emphasis} प्रवृत्ति को संतुलित रखते हुए चरणबद्ध जाँच जरूरी है।",
            "डेटा, डाउनसाइड और क्रियान्वयन क्षमता क्रम से जाँचने पर टाइमिंग बेहतर होती है।",
            "गलत टाइमिंग अक्सर जल्दीबाज़ी पक्षपात से पैदा होती है।",
            "टाइमिंग प्रोटोकॉल रखें: मसौदा, 24 घंटे समीक्षा, फिर 30/90-दिवसीय फॉलो-अप।",
        )
    if section_key == "roadmap_12_months":
        return (
            f"12-महीने रोडमैप में लक्ष्य {_join_items(goals[:3], 'प्राथमिक लक्ष्य')} और जोखिम {_join_items(challenges[:2], 'प्राथमिक जोखिम')} को चार तिमाहियों में क्रम दें।",
            "हर तिमाही एक प्रमुख मेट्रिक और एक जोखिम-गार्डरेल रोडमैप को व्यवहारिक बनाते हैं।",
            "क्लोजर मानदंड बिना प्राथमिकता बदलना प्रगति को कमजोर करता है।",
            "हर तिमाही अंत में साक्ष्य-आधारित निर्णय लें: जारी रखें, रोकें या पुनःपरिभाषित करें।",
        )
    if section_key == "outlook_3_years":
        return (
            f"3-वर्षीय दृष्टिकोण बताता है कि {_join_items(goals[:2], 'दीर्घकालिक प्राथमिकताएँ')} को अनुशासित गति से चलाने पर कंपाउंडिंग संभव है।",
            "वार्षिक उद्देश्यों को तिमाही माइलस्टोन से जोड़ने पर दीर्घकालिक स्थिरता बढ़ती है।",
            "अल्पकालिक उतार-चढ़ाव से दिशा बार-बार बदलने पर दीर्घ योजना टूटती है।",
            "तीन वर्षों के लिए वार्षिक थीम तय करें और हर 6 माह सुधार ट्रिगर के साथ समीक्षा करें।",
        )
    if section_key == "life_alignment_scorecard":
        return (
            "लाइफ एलाइनमेंट स्कोरकार्ड जीवन स्थिरता, निर्णय स्पष्टता, भावनात्मक संतुलन और वित्त अनुशासन का संयुक्त दृश्य देता है।",
            "यह गिरावट दिखने से पहले चेतावनी संकेत देता है।",
            "कमज़ोर आयामों की अनदेखी से कार्यान्वयन गुणवत्ता धीरे-धीरे कम होती है।",
            "हर माह स्कोरकार्ड ट्रैक करें और सबसे कम स्कोर वाले आयाम पर सुधार लागू करें।",
        )
    if section_key == "strategic_correction":
        return (
            f"रणनीतिक सुधार की प्राथमिकता: {strongest} को सुरक्षित रखते हुए {weakest} का घर्षण घटाना। तत्काल दबाव: {_join_items(challenges[:2], 'कार्यान्वयन विचलन')}।",
            "फोकस्ड सुधार बिना पूरी योजना बदले दिशा को सुरक्षित रखता है।",
            "एक साथ बहुत बदलाव करने से सुधार अस्थिर हो जाता है।",
            "एक-चक्र-एक-सुधार नियम अपनाएँ: एक बदलाव, प्रभाव मापन, फिर अगला कदम।",
        )
    if section_key == "growth_blueprint":
        return (
            f"ग्रोथ ब्लूप्रिंट में लक्ष्य {_join_items(goals[:2], 'मुख्य लक्ष्य')}, सीमाएँ {_join_items(challenges[:2], 'वर्तमान सीमाएँ')} और उद्योग {industry} को एक ढांचे में जोड़ा गया है।",
            "ब्लूप्रिंट की ताकत स्पष्ट प्राथमिकता, स्थिर लय और मापनीय परिणाम में है।",
            "परिचालन अनुशासन से तेज महत्वाकांक्षा बढ़ने पर ग्रोथ जोखिम बढ़ता है।",
            "अगला चक्र तीन ट्रैक पर चलाएँ: राजस्व-गुणवत्ता क्रिया, जोखिम नियंत्रण और क्षमता उन्नयन।",
        )

    return (
        f"{SECTION_TITLES.get(section_key, section_key)} के लिए निर्धारक संकेत उपलब्ध हैं।",
        "मुख्य ताकत तभी परिणाम देती है जब कार्यान्वयन संरचित रहे।",
        "समीक्षा अनुशासन टूटने पर जोखिम बढ़ता है।",
        "साप्ताहिक एक सुधार क्रिया तय करें और निरंतरता ट्रैक करें।",
    )


def build_fallback_section(
    *,
    section_key: str,
    plan: str,
    normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
    problem_profile: Optional[Dict[str, Any]] = None,
) -> ReportSection:
    canonical_section_key = SECTION_KEY_ALIASES.get(section_key, section_key)
    summary, key_strength, key_risk, practical_guidance = _section_text(
        section_key=canonical_section_key,
        plan=plan,
        normalized_input=normalized_input,
        numerology_values=numerology_values,
        derived_scores=derived_scores,
        problem_profile=problem_profile,
    )

    # premium_trait_override
    plan_key = _safe_text(plan).lower()
    if plan_key == "enterprise":
        premium_summary = _premium_section_summary(
            section_key=canonical_section_key,
            numerology_values=numerology_values,
            normalized_input=normalized_input,
        )
        if premium_summary:
            summary = premium_summary
    if plan_key == "enterprise" and section_key not in PREMIUM_TRAIT_EXCLUDE:
        premium_strength, premium_risk, premium_action = _premium_dynamic_traits(
            section_key=canonical_section_key,
            numerology_values=numerology_values,
            normalized_input=normalized_input,
            derived_scores=derived_scores,
        )
        if premium_strength and premium_risk and premium_action:
            key_strength = premium_strength
            key_risk = premium_risk
            practical_guidance = premium_action
    if plan_key == "enterprise":
        metric_keys = PREMIUM_SECTION_METRICS.get(
            canonical_section_key,
            SECTION_METRICS.get(canonical_section_key, ["confidence_score", "life_stability_index"]),
        )
    else:
        metric_keys = SECTION_METRICS.get(canonical_section_key, ["confidence_score", "life_stability_index"])
    score_highlights = _highlights(derived_scores, metric_keys)
    loaded_energies = [item["label"] for item in score_highlights]
    return {
        "sectionKey": section_key,
        "sectionTitle": SECTION_TITLES.get(section_key, get_bilingual_section_heading(section_key))
        if str(plan or "").strip().lower() in ("standard", "pro", "premium", "enterprise")
        else get_bilingual_section_heading(section_key),
        "summary": summary,
        "keyStrength": key_strength,
        "keyRisk": key_risk,
        "practicalGuidance": practical_guidance,
        "loadedEnergies": loaded_energies,
        "scoreHighlights": score_highlights,
    }


def build_fallback_report(
    *,
    ai_payload: Dict[str, Any],
    section_keys: Optional[List[str]] = None,
    deterministic_availability: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    deterministic = ai_payload.get("deterministic", {})
    normalized_input = deterministic.get("normalizedInput") or {}
    numerology_values = deterministic.get("numerologyValues") or {}
    scores = deterministic.get("derivedScores") or {}
    problem_profile = deterministic.get("problemProfile") or {}
    plan = str(ai_payload.get("plan", "BASIC"))
    enabled_sections = section_keys or list(ai_payload.get("enabledSections", []))
    deterministic_map = deterministic_availability or {}

    sections: List[ReportSection] = []
    for section_key in enabled_sections:
        if deterministic_map and not deterministic_map.get(section_key, False):
            continue
        sections.append(
            build_fallback_section(
                section_key=section_key,
                plan=plan,
                normalized_input=normalized_input,
                numerology_values=numerology_values,
                derived_scores=scores,
                problem_profile=problem_profile if isinstance(problem_profile, dict) else None,
            )
        )

    return {
        "reportTitle": "Premium Numerology Report",
        "plan": plan,
        "profileSnapshot": ai_payload.get("profileSnapshot", {}),
        "dashboard": ai_payload.get("dashboard", {}),
        "sections": sections,
        "closingInsight": "मुख्य ताकत को वृद्धि का आधार बनाएं और मुख्य चुनौती पर साप्ताहिक सुधार लागू करें।",
    }


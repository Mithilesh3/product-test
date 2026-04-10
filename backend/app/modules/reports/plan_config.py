from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal

PlanKey = Literal["basic", "standard", "enterprise"]


@dataclass(frozen=True)
class PlanConfig:
    key: PlanKey
    required_fields: List[str]
    optional_fields: List[str]
    enabled_sections: List[str]
    visible_loaded_energy_metrics: List[str]
    ai_narrative_depth: Literal["light", "medium", "deep"]


FULL_FOUNDATION_SECTIONS = [
    "required_inputs",
    "core_purpose",
    "primary_focus",
    "deterministic_engine",
    "ai_generation_layer",
    "recommendation_logic",
    "narration_style",
    "ai_narration_role",
    "deterministic_role",
    "ai_should_not_do",
    "ai_should_do",
    "basic_details",
    "mulank_analysis",
    "bhagyank_analysis",
    "mobile_numerology",
    "mobile_number_total",
    "mobile_digit_analysis",
    "mobile_energy_description",
    "dob_mobile_alignment",
    "mulank_connection",
    "bhagyank_connection",
    "combo_analysis",
    "lo_shu_grid",
    "lucky_numbers_unlucky_numbers_neutral_numbers",
    "lucky_numbers",
    "unlucky_numbers",
    "neutral_numbers",
    "color_recommendation",
    "health_wealth_relationship_insight",
    "health_insight",
    "wealth_insight",
    "relationship_insight",
    "remedies",
    "remedies_logic",
    "lucky_number_usage",
    "mobile_recommendation",
    "mobile_cover_color",
    "mantra_recommendation",
    "final_outcome",
]

BASIC_SECTIONS = [
    "basic_details",
    "mulank_analysis",
    "bhagyank_analysis",
    "mobile_numerology",
    "mobile_number_total",
    "mobile_digit_analysis",
    "mobile_energy_description",
    "dob_mobile_alignment",
    "mulank_connection",
    "bhagyank_connection",
    "combo_analysis",
    "lo_shu_grid",
    "lucky_numbers_unlucky_numbers_neutral_numbers",
    "color_recommendation",
    "health_wealth_relationship_insight",
    "remedies",
]

STANDARD_ADDITIONAL_SECTIONS = [
    "name_numerology",
    "name_analysis_type",
    "name_correction",
    "prefix_suffix_suggestion",
    "name_correction_basis",
    "name_mobile_combo",
    "dob_name_alignment",
    "wallpaper_suggestion",
    "charging_direction",
    "bracelet_crystal_suggestion",
    "gemstone_recommendation",
]

ENTERPRISE_ADDITIONAL_SECTIONS = [
    "personal_year",
    "monthly_cycle_analysis",
    "decision_timing",
    "astrology_integration",
    "vedic_logic_integration",
    "planetary_support_mapping",
    "business_brand_naming",
    "signature_analysis",
    "space_direction_guidance",
    "ongoing_guidance",
]

STANDARD_SECTIONS = [
    "basic_details",
    "mulank_analysis",
    "bhagyank_analysis",
    "name_numerology",
    "name_analysis",
    "name_number_total",
    "name_correction_options",
    "prefix_suffix_suggestions",
    "name_correction_logic_explanation",
    "mobile_numerology",
    "mobile_number_total",
    "mobile_digit_analysis",
    "mobile_energy_description",
    "name_mobile_alignment",
    "dob_name_alignment",
    "dob_mobile_alignment",
    "mulank_connection",
    "bhagyank_connection",
    "combo_analysis",
    "lo_shu_grid",
    "lucky_numbers",
    "unlucky_numbers",
    "neutral_numbers",
    "color_recommendation",
    "health_insight",
    "wealth_insight",
    "relationship_insight",
    "remedies",
    "mobile_name_combo_recommendation",
    "summary_and_priority_actions",
]
ENTERPRISE_SECTIONS = [
    "full_identity_profile",
    "core_numbers",
    "advanced_name_numerology",
    "karmic_name_analysis",
    "planetary_name_support_mapping",
    "multi_name_correction_options",
    "name_optimization_scoring",
    "prefix_suffix_advanced_logic",
    "mobile_numerology_advanced",
    "mobile_digit_micro_analysis",
    "mobile_energy_forecasting",
    "name_mobile_alignment",
    "dob_name_alignment",
    "dob_mobile_alignment",
    "full_system_alignment_score",
    "strength_vs_risk_matrix",
    "life_area_scores",
    "mulank_deep_analysis",
    "bhagyank_destiny_roadmap",
    "lo_shu_grid_advanced",
    "planetary_influence_mapping",
    "current_planetary_phase",
    "upcoming_transit_highlights",
    "personal_year_analysis",
    "monthly_cycle_analysis",
    "critical_decision_windows",
    "wealth_cycle_analysis",
    "career_growth_timeline",
    "relationship_timing_patterns",
    "dynamic_lucky_numbers",
    "situational_caution_numbers",
    "neutral_number_strategy_usage",
    "color_strategy",
    "energy_objects_recommendation",
    "advanced_remedies_engine",
    "business_brand_naming",
    "signature_energy_analysis",
    "mobile_optimization_strategy",
    "life_strategy_recommendations",
    "priority_action_plan",
    "risk_alerts_and_mitigation",
    "premium_summary_narrative",
]

SECTIONS_REQUIRING_LOADED_ENERGIES = {
    "dashboard",
    "executive_summary",
    "career_financial",
    "growth_blockers",
    "closing_summary",
    "wealth_strategy",
    "life_alignment_scorecard",
    "growth_blueprint",
}

SECTION_SUPPORT_PATHS: Dict[str, List[str]] = {
    "required_inputs": [
        "normalized_input.identity.full_name",
        "normalized_input.birth_details.date_of_birth",
        "normalized_input.contact.mobile_number",
        "normalized_input.identity.name_variations",
        "normalized_input.preferences.primary_goal",
    ],
    "core_purpose": [
        "normalized_input.focus.life_focus",
        "normalized_input.current_problem",
    ],
    "primary_focus": [
        "normalized_input.focus.life_focus",
        "normalized_input.current_problem",
    ],
    "deterministic_engine": [
        "numerology_values.pythagorean.life_path_number",
        "numerology_values.pythagorean.birth_number",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "ai_generation_layer": [
        "derived_scores.confidence_score",
        "derived_scores.data_completeness_score",
    ],
    "recommendation_logic": [
        "derived_scores.weakest_metric",
        "derived_scores.strongest_metric",
    ],
    "narration_style": [
        "normalized_input.preferences.language_preference",
    ],
    "ai_narration_role": [
        "derived_scores.confidence_score",
    ],
    "deterministic_role": [
        "numerology_values.pythagorean.life_path_number",
    ],
    "ai_should_not_do": [
        "derived_scores.confidence_score",
    ],
    "ai_should_do": [
        "derived_scores.strongest_metric",
    ],
    "basic_details": [
        "normalized_input.identity.full_name",
        "normalized_input.birth_details.date_of_birth",
        "normalized_input.contact.mobile_number",
        "numerology_values.chaldean.name_number",
    ],
    "mulank_analysis": [
        "numerology_values.pythagorean.birth_number",
    ],
    "bhagyank_analysis": [
        "numerology_values.pythagorean.life_path_number",
    ],
    "profile": [
        "normalized_input.identity.full_name",
        "normalized_input.birth_details.date_of_birth",
    ],
    "dashboard": [
        "derived_scores.confidence_score",
        "derived_scores.risk_band",
    ],
    "executive_summary": [
        "normalized_input.current_problem",
        "derived_scores.risk_band",
    ],
    "core_numbers": [
        "numerology_values.pythagorean.life_path_number",
        "numerology_values.chaldean.name_number",
    ],
    "number_interaction": [
        "numerology_values.pythagorean.destiny_number",
        "numerology_values.pythagorean.expression_number",
    ],
    "name_numerology": [
        "numerology_values.chaldean.name_number",
        "normalized_input.identity.full_name",
    ],
    "name_analysis": [
        "numerology_values.chaldean.name_number",
        "normalized_input.identity.full_name",
    ],
    "name_number_total": [
        "numerology_values.chaldean.name_number",
    ],
    "email_numerology": [
        "numerology_values.email_analysis.email_number",
        "normalized_input.identity.email",
    ],
    "personality_profile": [
        "numerology_values.pythagorean.destiny_number",
        "normalized_input.identity.gender",
    ],
    "focus_snapshot": [
        "normalized_input.focus.life_focus",
        "normalized_input.current_problem",
    ],
    "personal_year": [
        "derived_scores.confidence_score",
        "numerology_values.pythagorean.life_path_number",
    ],
    "lucky_dates": [
        "numerology_values.pythagorean.life_path_number",
    ],
    "color_alignment": [
        "derived_scores.dharma_alignment_score",
    ],
    "remedy": [
        "derived_scores.weakest_metric",
        "derived_scores.karma_pressure_index",
    ],
    "closing_summary": [
        "derived_scores.strongest_metric",
        "derived_scores.risk_band",
    ],
    "lo_shu_grid": [
        "numerology_values.loshu_grid.grid_counts",
        "numerology_values.loshu_grid.missing_numbers",
    ],
    "missing_numbers": [
        "numerology_values.loshu_grid.missing_numbers",
    ],
    "repeating_numbers": [
        "numerology_values.loshu_grid.grid_counts",
    ],
    "mobile_numerology": [
        "normalized_input.contact.mobile_number",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "mobile_number_total": [
        "numerology_values.mobile_analysis.mobile_total",
    ],
    "mobile_digit_analysis": [
        "numerology_values.mobile_analysis.digit_frequency",
    ],
    "mobile_energy_description": [
        "numerology_values.dominant_planet",
    ],
    "mobile_digit_pattern": [
        "numerology_values.mobile_analysis.digit_frequency",
        "numerology_values.mobile_analysis.dominant_digits",
    ],
    "mobile_life_compatibility": [
        "numerology_values.mobile_analysis.compatibility_status",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "dob_mobile_alignment": [
        "numerology_values.mobile_analysis.compatibility_status",
    ],
    "mulank_connection": [
        "numerology_values.pythagorean.birth_number",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "bhagyank_connection": [
        "numerology_values.pythagorean.life_path_number",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "combo_analysis": [
        "numerology_values.pythagorean.life_path_number",
        "numerology_values.chaldean.name_number",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "lucky_numbers_unlucky_numbers_neutral_numbers": [
        "numerology_values.guidance_profile.supportiveNumbers",
        "numerology_values.guidance_profile.cautionNumbers",
        "numerology_values.mobile_analysis.supportive_number_energies",
    ],
    "lucky_numbers": [
        "numerology_values.guidance_profile.supportiveNumbers",
    ],
    "unlucky_numbers": [
        "numerology_values.guidance_profile.cautionNumbers",
    ],
    "neutral_numbers": [
        "numerology_values.guidance_profile.supportiveNumbers",
    ],
    "color_recommendation": [
        "numerology_values.guidance_profile.colors",
    ],
    "health_wealth_relationship_insight": [
        "derived_scores.emotional_regulation_index",
        "derived_scores.financial_discipline_index",
        "derived_scores.life_stability_index",
    ],
    "health_insight": [
        "derived_scores.emotional_regulation_index",
    ],
    "wealth_insight": [
        "derived_scores.financial_discipline_index",
    ],
    "relationship_insight": [
        "derived_scores.emotional_regulation_index",
    ],
    "remedies_logic": [
        "numerology_values.guidance_profile.mantra",
        "numerology_values.guidance_profile.gemstone",
    ],
    "remedies": [
        "numerology_values.guidance_profile.mantra",
        "numerology_values.guidance_profile.colors",
        "numerology_values.mobile_analysis.correction_suggestion",
        "numerology_values.guidance_profile.supportiveNumbers",
    ],
    "lucky_number_usage": [
        "numerology_values.guidance_profile.supportiveNumbers",
    ],
    "mobile_recommendation": [
        "numerology_values.mobile_analysis.correction_suggestion",
    ],
    "mobile_number_recommendation": [
        "numerology_values.mobile_analysis.correction_suggestion",
    ],
    "mobile_cover_color": [
        "numerology_values.guidance_profile.colors",
    ],
    "wallpaper_suggestion": [
        "numerology_values.guidance_profile.wallpaperTheme",
    ],
    "charging_direction": [
        "numerology_values.guidance_profile.direction",
    ],
    "basic_crystal_suggestion": [
        "numerology_values.guidance_profile.gemstone",
    ],
    "mantra_recommendation": [
        "numerology_values.guidance_profile.mantra",
    ],
    "final_outcome": [
        "derived_scores.strongest_metric",
        "derived_scores.weakest_metric",
    ],
    "summary_and_priority_actions": [
        "derived_scores.strongest_metric",
        "derived_scores.weakest_metric",
        "normalized_input.current_problem",
    ],
    "life_area_impact": [
        "derived_scores.life_stability_index",
        "derived_scores.financial_discipline_index",
        "derived_scores.emotional_regulation_index",
    ],
    "name_analysis_type": [
        "numerology_values.chaldean.name_number",
    ],
    "name_correction": [
        "numerology_values.name_correction.current_number",
    ],
    "name_correction_options": [
        "numerology_values.name_correction.current_number",
        "numerology_values.name_correction.suggestion",
    ],
    "prefix_suffix_suggestion": [
        "numerology_values.name_correction.current_number",
    ],
    "prefix_suffix_suggestions": [
        "numerology_values.name_correction.current_number",
    ],
    "name_correction_basis": [
        "numerology_values.chaldean.name_number",
        "numerology_values.dominant_planet",
    ],
    "name_correction_logic_explanation": [
        "numerology_values.chaldean.name_number",
        "numerology_values.dominant_planet",
    ],
    "name_vibration_optimization": [
        "numerology_values.name_correction.current_number",
        "numerology_values.name_correction.suggestion",
    ],
    "name_mobile_combo": [
        "numerology_values.chaldean.name_number",
        "numerology_values.mobile_analysis.mobile_vibration",
        "numerology_values.pythagorean.life_path_number",
    ],
    "name_mobile_alignment": [
        "numerology_values.chaldean.name_number",
        "numerology_values.mobile_analysis.mobile_vibration",
        "numerology_values.pythagorean.life_path_number",
    ],
    "mobile_name_combo_recommendation": [
        "numerology_values.chaldean.name_number",
        "numerology_values.mobile_analysis.mobile_vibration",
        "numerology_values.mobile_analysis.correction_suggestion",
    ],
    "business_numerology": [
        "numerology_values.business_analysis.business_number",
        "numerology_values.business_analysis.brand_vibration",
    ],
    "digital_numerology": [
        "numerology_values.digital_analysis.digital_vibration",
        "numerology_values.digital_analysis.profile_signal",
    ],
    "dob_name_alignment": [
        "numerology_values.pythagorean.birth_number",
        "numerology_values.chaldean.name_number",
    ],
    "career_financial": [
        "normalized_input.career.industry",
        "normalized_input.financial.monthly_income",
    ],
    "relationship_patterns": [
        "normalized_input.preferences.relationship_status",
        "normalized_input.identity.partner_name",
    ],
    "health_tendencies": [
        "normalized_input.career.stress_level",
        "normalized_input.health.exercise_frequency_per_week",
    ],
    "action_plan_90_days": [
        "derived_scores.weakest_metric",
        "derived_scores.confidence_score",
    ],
    "growth_blockers": [
        "derived_scores.karma_pressure_index",
        "derived_scores.weakest_metric",
    ],
    "decision_style": [
        "normalized_input.calibration.decision_style",
        "derived_scores.confidence_score",
    ],
    "life_timeline": [
        "normalized_input.birth_details.date_of_birth",
        "numerology_values.pythagorean.life_path_number",
    ],
    "strategic_life_theme": [
        "normalized_input.focus.life_focus",
        "derived_scores.dharma_alignment_score",
    ],
    "leadership_archetype": [
        "numerology_values.pythagorean.destiny_number",
        "numerology_values.pythagorean.expression_number",
    ],
    "wealth_strategy": [
        "normalized_input.financial.monthly_income",
        "normalized_input.financial.debt_ratio",
    ],
    "opportunity_windows": [
        "numerology_values.pythagorean.life_path_number",
        "derived_scores.confidence_score",
    ],
    "decision_timing": [
        "normalized_input.calibration.decision_style",
        "derived_scores.confidence_score",
    ],
    "personal_year": [
        "numerology_values.pythagorean.personal_year",
    ],
    "monthly_cycle_analysis": [
        "numerology_values.pythagorean.personal_year",
        "normalized_input.birth_details.date_of_birth",
    ],
    "astrology_integration": [
        "numerology_values.dominant_planet",
        "normalized_input.birth_details.time_of_birth",
    ],
    "vedic_logic_integration": [
        "numerology_values.guidance_profile.mantra",
        "numerology_values.guidance_profile.gemstone",
    ],
    "planetary_support_mapping": [
        "numerology_values.dominant_planet",
    ],
    "business_brand_naming": [
        "normalized_input.identity.business_name",
        "numerology_values.business_analysis.business_number",
    ],
    "signature_analysis": [
        "normalized_input.identity.signature_style",
    ],
    "space_direction_guidance": [
        "numerology_values.guidance_profile.direction",
        "numerology_values.guidance_profile.colors",
    ],
    "ongoing_guidance": [
        "derived_scores.confidence_score",
        "derived_scores.weakest_metric",
    ],
    "roadmap_12_months": [
        "normalized_input.preferences.primary_goal",
        "derived_scores.weakest_metric",
    ],
    "outlook_3_years": [
        "normalized_input.preferences.primary_goal",
        "derived_scores.risk_band",
    ],
    "life_alignment_scorecard": [
        "derived_scores.dharma_alignment_score",
        "derived_scores.life_stability_index",
    ],
    "strategic_correction": [
        "derived_scores.weakest_metric",
        "derived_scores.karma_pressure_index",
    ],
    "growth_blueprint": [
        "normalized_input.current_problem",
        "derived_scores.strongest_metric",
    ],
    "numerology_architecture": [
        "numerology_values.pythagorean.life_path_number",
        "numerology_values.pythagorean.destiny_number",
        "numerology_values.pythagorean.expression_number",
        "numerology_values.chaldean.name_number",
    ],
    "planetary_influence": [
        "numerology_values.dominant_planet",
    ],
    "vedic_remedy": [
        "numerology_values.guidance_profile.mantra",
        "numerology_values.guidance_profile.gemstone",
    ],
    "karmic_pattern_intelligence": [
        "numerology_values.loshu_grid.missing_numbers",
        "numerology_values.pythagorean.life_path_number",
    ],
    "pinnacle_challenge_cycle_intelligence": [
        "normalized_input.birth_details.date_of_birth",
    ],
    "signature_intelligence": [
        "normalized_input.identity.signature_style",
        "numerology_values.chaldean.name_number",
    ],
    "business_name_intelligence": [
        "numerology_values.business_analysis.business_number",
        "normalized_input.identity.business_name",
    ],
    "environment_alignment": [
        "numerology_values.guidance_profile.direction",
        "numerology_values.guidance_profile.colors",
    ],
    "strategic_execution_roadmap": [
        "derived_scores.weakest_metric",
        "derived_scores.confidence_score",
    ],
    "full_identity_profile": [
        "normalized_input.identity.full_name",
        "normalized_input.birth_details.date_of_birth",
        "normalized_input.contact.mobile_number",
        "normalized_input.identity.name_variations",
        "normalized_input.birth_details.time_of_birth",
        "normalized_input.preferences.primary_goal",
    ],
    "advanced_name_numerology": [
        "numerology_values.chaldean.name_number",
        "normalized_input.identity.full_name",
    ],
    "karmic_name_analysis": [
        "numerology_values.chaldean.name_number",
        "numerology_values.loshu_grid.missing_numbers",
    ],
    "planetary_name_support_mapping": [
        "numerology_values.dominant_planet",
    ],
    "multi_name_correction_options": [
        "numerology_values.name_correction.current_number",
        "numerology_values.name_correction.suggestion",
    ],
    "name_optimization_scoring": [
        "numerology_values.name_correction.current_number",
        "derived_scores.confidence_score",
    ],
    "prefix_suffix_advanced_logic": [
        "numerology_values.name_correction.current_number",
    ],
    "mobile_numerology_advanced": [
        "normalized_input.contact.mobile_number",
        "numerology_values.mobile_analysis.mobile_vibration",
    ],
    "mobile_digit_micro_analysis": [
        "numerology_values.mobile_analysis.digit_frequency",
        "numerology_values.mobile_analysis.dominant_digits",
    ],
    "mobile_energy_forecasting": [
        "numerology_values.dominant_planet",
        "derived_scores.life_stability_index",
    ],
    "name_mobile_alignment_scored": [
        "numerology_values.chaldean.name_number",
        "numerology_values.mobile_analysis.mobile_vibration",
        "derived_scores.confidence_score",
    ],
    "dob_name_alignment_deep": [
        "numerology_values.pythagorean.birth_number",
        "numerology_values.chaldean.name_number",
    ],
    "dob_mobile_alignment_timing_logic": [
        "numerology_values.mobile_analysis.compatibility_status",
        "numerology_values.pythagorean.personal_year",
    ],
    "full_system_alignment_score": [
        "derived_scores.dharma_alignment_score",
        "derived_scores.life_stability_index",
        "derived_scores.confidence_score",
    ],
    "strength_vs_risk_matrix": [
        "derived_scores.strongest_metric",
        "derived_scores.weakest_metric",
        "derived_scores.karma_pressure_index",
    ],
    "life_area_scores": [
        "derived_scores.life_stability_index",
        "derived_scores.financial_discipline_index",
        "derived_scores.emotional_regulation_index",
    ],
    "mulank_deep_analysis": [
        "numerology_values.pythagorean.birth_number",
        "numerology_values.number_profiles",
    ],
    "bhagyank_destiny_roadmap": [
        "numerology_values.pythagorean.life_path_number",
        "numerology_values.pythagorean.personal_year",
    ],
    "lo_shu_grid_advanced": [
        "numerology_values.loshu_grid.grid_counts",
        "numerology_values.loshu_grid.missing_numbers",
    ],
    "planetary_influence_mapping": [
        "numerology_values.dominant_planet",
    ],
    "current_planetary_phase": [
        "numerology_values.dominant_planet",
        "numerology_values.pythagorean.personal_year",
    ],
    "upcoming_transit_highlights": [
        "numerology_values.pythagorean.personal_year",
        "derived_scores.confidence_score",
    ],
    "personal_year_analysis": [
        "numerology_values.pythagorean.personal_year",
    ],
    "critical_decision_windows": [
        "normalized_input.calibration.decision_style",
        "derived_scores.confidence_score",
    ],
    "wealth_cycle_analysis": [
        "normalized_input.financial.monthly_income",
        "normalized_input.financial.debt_ratio",
    ],
    "career_growth_timeline": [
        "normalized_input.career.industry",
        "derived_scores.life_stability_index",
    ],
    "relationship_timing_patterns": [
        "normalized_input.preferences.relationship_status",
        "derived_scores.emotional_regulation_index",
    ],
    "dynamic_lucky_numbers": [
        "numerology_values.guidance_profile.supportiveNumbers",
        "numerology_values.pythagorean.personal_year",
    ],
    "situational_caution_numbers": [
        "numerology_values.guidance_profile.cautionNumbers",
    ],
    "neutral_number_strategy_usage": [
        "numerology_values.guidance_profile.supportiveNumbers",
    ],
    "color_strategy": [
        "numerology_values.guidance_profile.colors",
        "numerology_values.dominant_planet",
    ],
    "energy_objects_recommendation": [
        "numerology_values.guidance_profile.gemstone",
        "numerology_values.guidance_profile.direction",
    ],
    "advanced_remedies_engine": [
        "numerology_values.guidance_profile.mantra",
        "numerology_values.guidance_profile.gemstone",
        "numerology_values.guidance_profile.direction",
    ],
    "signature_energy_analysis": [
        "normalized_input.identity.signature_style",
        "numerology_values.chaldean.name_number",
    ],
    "mobile_optimization_strategy": [
        "numerology_values.mobile_analysis.correction_suggestion",
        "numerology_values.pythagorean.personal_year",
    ],
    "life_strategy_recommendations": [
        "normalized_input.current_problem",
        "derived_scores.strongest_metric",
        "derived_scores.weakest_metric",
    ],
    "priority_action_plan": [
        "derived_scores.weakest_metric",
        "derived_scores.confidence_score",
    ],
    "risk_alerts_and_mitigation": [
        "derived_scores.karma_pressure_index",
        "derived_scores.weakest_metric",
    ],
    "premium_summary_narrative": [
        "derived_scores.strongest_metric",
        "derived_scores.risk_band",
    ],
}

PLAN_CONFIGS: Dict[PlanKey, PlanConfig] = {
    "basic": PlanConfig(
        key="basic",
        required_fields=[
            "identity.full_name",
            "birth_details.date_of_birth",
            "contact.mobile_number",
        ],
        optional_fields=[
            "focus.life_focus",
            "current_problem",
            "preferences.language_preference",
            "preferences.willingness_to_change",
            "identity.email",
            "birth_details.birthplace_city",
            "birth_details.birthplace_country",
        ],
        enabled_sections=BASIC_SECTIONS,
        visible_loaded_energy_metrics=[
            "life_stability_index",
            "confidence_score",
            "dharma_alignment_score",
            "emotional_regulation_index",
            "financial_discipline_index",
        ],
        ai_narrative_depth="light",
    ),
    "standard": PlanConfig(
        key="standard",
        required_fields=[
            "identity.full_name",
            "identity.name_variations",
            "birth_details.date_of_birth",
            "contact.mobile_number",
        ],
        optional_fields=[
            "focus.life_focus",
            "current_problem",
            "preferences.language_preference",
            "preferences.willingness_to_change",
            "identity.email",
            "identity.business_name",
            "identity.signature_style",
            "career.industry",
            "preferences.relationship_status",
            "financial.monthly_income",
            "career.stress_level",
            "financial.savings_ratio",
            "financial.debt_ratio",
            "financial.risk_tolerance",
            "emotional.anxiety_level",
            "emotional.decision_confusion",
            "birth_details.birthplace_city",
            "birth_details.birthplace_country",
            "birth_details.time_of_birth",
            "contact.social_handle",
            "contact.domain_handle",
            "contact.residence_number",
            "contact.vehicle_number",
        ],
        enabled_sections=STANDARD_SECTIONS,
        visible_loaded_energy_metrics=[
            "life_stability_index",
            "confidence_score",
            "dharma_alignment_score",
            "emotional_regulation_index",
            "financial_discipline_index",
            "karma_pressure_index",
            "data_completeness_score",
        ],
        ai_narrative_depth="medium",
    ),
    "enterprise": PlanConfig(
        key="enterprise",
        required_fields=[
            "identity.full_name",
            "identity.name_variations",
            "birth_details.date_of_birth",
            "birth_details.time_of_birth",
            "birth_details.birthplace_city",
            "birth_details.birthplace_country",
            "contact.mobile_number",
            "preferences.primary_goal",
        ],
        optional_fields=[
            "current_problem",
            "preferences.language_preference",
            "preferences.willingness_to_change",
            "identity.email",
            "identity.business_name",
            "identity.signature_style",
            "career.industry",
            "preferences.relationship_status",
            "career.role",
            "financial.monthly_income",
            "career.stress_level",
            "financial.debt_ratio",
            "contact.social_handle",
            "contact.domain_handle",
            "contact.residence_number",
            "contact.vehicle_number",
            "business_history.major_investments",
            "business_history.major_losses",
            "business_history.risk_mistakes_count",
            "calibration.stress_response",
            "calibration.money_decision_style",
            "calibration.biggest_weakness",
            "calibration.life_preference",
            "calibration.decision_style",
            "birth_details.time_of_birth",
            "birth_details.birthplace_country",
        ],
        enabled_sections=ENTERPRISE_SECTIONS,
        visible_loaded_energy_metrics=[
            "life_stability_index",
            "confidence_score",
            "dharma_alignment_score",
            "emotional_regulation_index",
            "financial_discipline_index",
            "karma_pressure_index",
            "data_completeness_score",
        ],
        ai_narrative_depth="deep",
    ),
}


PLAN_ALIASES = {
    "basic": "basic",
    "pro": "standard",
    "premium": "enterprise",
    "standard": "standard",
    "enterprise": "enterprise",
}


def resolve_plan_key(raw: str) -> PlanKey:
    normalized = (raw or "").strip().lower()
    plan = PLAN_ALIASES.get(normalized, "basic")
    return plan  # type: ignore[return-value]


def get_plan_config(raw: str) -> PlanConfig:
    key = resolve_plan_key(raw)
    return PLAN_CONFIGS[key]

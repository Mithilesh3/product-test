from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from app.modules.numerology.core_engine import generate_numerology_profile
from app.modules.reports.ai_engine import flatten_input
from app.modules.reports.metric_labels import to_metric_label
from app.modules.reports.plan_config import PlanConfig, SECTION_SUPPORT_PATHS
from app.modules.reports.pipeline_types import DeterministicPipelineOutput
from app.modules.reports.problem_policy_config import (
    merge_category_fields,
    merge_priority_list,
    merge_token_map,
)
from app.modules.reports.scoring_engine import generate_score_summary


PROBLEM_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "finance": [
        "debt",
        "loan",
        "emi",
        "money",
        "finance",
        "financial",
        "cash",
        "income",
        "expense",
        "savings",
        "investment",
        "loss",
        "credit",
    ],
    "relationship": [
        "relationship",
        "marriage",
        "partner",
        "husband",
        "wife",
        "love",
        "breakup",
        "divorce",
        "compatibility",
    ],
    "health": [
        "health",
        "sleep",
        "weight",
        "fitness",
        "pain",
        "stress",
        "anxiety",
        "depression",
        "illness",
        "disease",
    ],
    "education": [
        "exam",
        "study",
        "education",
        "college",
        "school",
        "learning",
        "course",
        "grade",
    ],
    "business": [
        "business",
        "startup",
        "client",
        "revenue",
        "sales",
        "profit",
        "brand",
        "market",
        "entrepreneur",
    ],
    "career": [
        "career",
        "job",
        "work",
        "promotion",
        "office",
        "interview",
        "manager",
        "execution",
    ],
    "confidence": [
        "confidence",
        "self doubt",
        "self-doubt",
        "fear",
        "hesitation",
        "visibility",
        "public speaking",
        "communication",
    ],
    "consistency": [
        "consistency",
        "discipline",
        "routine",
        "habit",
        "focus",
        "procrastination",
        "follow through",
        "follow-through",
    ],
    "spiritual": [
        "spiritual",
        "mantra",
        "meditation",
        "peace",
        "purpose",
        "inner",
    ],
}

PROBLEM_FOCUS_METRIC: Dict[str, str] = {
    "finance": "financial_discipline_index",
    "career": "life_stability_index",
    "business": "life_stability_index",
    "relationship": "emotional_regulation_index",
    "health": "emotional_regulation_index",
    "education": "confidence_score",
    "confidence": "confidence_score",
    "consistency": "life_stability_index",
    "spiritual": "dharma_alignment_score",
}

WEAKEST_METRIC_ROOT_CAUSE: Dict[str, str] = {
    "financial_discipline_index": "Financial choices may be reacting to pressure instead of a fixed discipline rhythm.",
    "life_stability_index": "Execution rhythm is unstable, so effort does not consistently convert into outcomes.",
    "confidence_score": "Decision clarity is inconsistent, causing delays and second-guessing.",
    "emotional_regulation_index": "Emotional recovery cycle is stretched, reducing stable judgment quality.",
    "dharma_alignment_score": "Current actions may be misaligned with deeper purpose and value priorities.",
    "karma_pressure_index": "Compounding pressure from unresolved patterns is reducing strategic flexibility.",
}

PROBLEM_CATEGORY_DOMAIN_RULES: Dict[str, Dict[str, List[str]]] = {
    "finance": {
        "mustInclude": ["cash-protection discipline", "debt-reduction cadence", "weekly financial review"],
        "mustAvoid": [],
    },
    "career": {
        "mustInclude": ["execution priorities", "outcome-driven weekly review", "skill-output alignment"],
        "mustAvoid": ["debt-only remedy framing", "loan-first correction when challenge is not debt"],
    },
    "business": {
        "mustInclude": ["revenue-quality review", "decision discipline", "execution cadence"],
        "mustAvoid": ["debt-only remedy framing"],
    },
    "confidence": {
        "mustInclude": ["visibility reps", "decision-confidence loop", "small daily action protocol"],
        "mustAvoid": ["debt-only remedy framing", "finance-only corrective framing"],
    },
    "consistency": {
        "mustInclude": ["no-skip routine", "friction removal", "weekly reset checkpoint"],
        "mustAvoid": ["debt-only remedy framing", "finance-only corrective framing"],
    },
    "relationship": {
        "mustInclude": ["communication cadence", "emotional regulation protocol", "relationship clarity actions"],
        "mustAvoid": ["debt-only remedy framing"],
    },
    "health": {
        "mustInclude": ["stress-regulation routine", "daily rhythm correction", "energy-preserving decisions"],
        "mustAvoid": ["debt-only remedy framing"],
    },
    "education": {
        "mustInclude": ["study rhythm", "revision checkpoints", "performance tracking"],
        "mustAvoid": ["debt-only remedy framing"],
    },
    "spiritual": {
        "mustInclude": ["inner stability practice", "grounded ritual discipline", "reflection cadence"],
        "mustAvoid": ["debt-only remedy framing"],
    },
}


def _compact(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _compact(v) for k, v in data.items() if v not in (None, "", [], {})}
    if isinstance(data, list):
        return [_compact(item) for item in data if item not in (None, "", [], {})]
    return data


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


PYTHAGOREAN_MAP = {
    **{ch: 1 for ch in "AJSajs"},
    **{ch: 2 for ch in "BKTbkt"},
    **{ch: 3 for ch in "CLUclu"},
    **{ch: 4 for ch in "DMVdmv"},
    **{ch: 5 for ch in "ENWenw"},
    **{ch: 6 for ch in "FOXfox"},
    **{ch: 7 for ch in "GPYgpy"},
    **{ch: 8 for ch in "HQZhqz"},
    **{ch: 9 for ch in "IRir"},
}


def _reduce_to_single_digit(value: int) -> int:
    total = int(value)
    while total > 9:
        total = sum(int(digit) for digit in str(total))
    return total


def _pythagorean_email_number(email: str) -> int | None:
    text = _safe_text(email)
    if not text:
        return None
    local = text.split("@")[0]
    letters = [ch for ch in local if ch.isalpha()]
    if not letters:
        return None
    total = sum(PYTHAGOREAN_MAP.get(ch, 0) for ch in letters)
    if total <= 0:
        return None
    return _reduce_to_single_digit(total)


def _split_pipe_values(value: Any) -> List[str]:
    text = _safe_text(value)
    if not text:
        return []
    return [item.strip() for item in text.split("|") if item.strip()]


def _build_canonical_normalized_input(raw_input: Dict[str, Any], plan_key: str) -> Dict[str, Any]:
    identity = raw_input.get("identity") or {}
    birth = raw_input.get("birth_details") or {}
    contact = raw_input.get("contact") or {}
    focus = raw_input.get("focus") or {}
    preferences = raw_input.get("preferences") or {}
    career = raw_input.get("career") or {}
    financial = raw_input.get("financial") or {}
    emotional = raw_input.get("emotional") or {}
    calibration = raw_input.get("calibration") or {}
    health = raw_input.get("health") or {}

    career_role = _safe_text(career.get("role")).lower()
    career_type = _safe_text(preferences.get("career_type")).lower()
    if not career_type:
        career_type = "business" if career_role == "entrepreneur" else "job"

    return {
        "fullName": _safe_text(identity.get("full_name")),
        "nameVariations": _split_pipe_values(identity.get("name_variations")),
        "dateOfBirth": _safe_text(birth.get("date_of_birth")),
        "gender": _safe_text(identity.get("gender")),
        "partnerName": _safe_text(identity.get("partner_name")),
        "businessName": _safe_text(
            identity.get("business_name")
            or preferences.get("profession")
            or career.get("industry")
            or identity.get("full_name")
        ),
        "mobileNumber": _safe_text(contact.get("mobile_number") or identity.get("mobile_number")),
        "socialHandle": _safe_text(contact.get("social_handle")),
        "domainHandle": _safe_text(contact.get("domain_handle")),
        "email": _safe_text(identity.get("email")),
        "country": _safe_text(identity.get("country_of_residence") or birth.get("birthplace_country") or "India"),
        "city": _safe_text(birth.get("birthplace_city")),
        "currentCity": _safe_text(identity.get("current_city") or raw_input.get("current_city")),
        "focusArea": _safe_text(focus.get("life_focus") or "general_alignment"),
        "language": _safe_text(preferences.get("language_preference") or "hindi"),
        "willingnessToChange": _safe_text(preferences.get("willingness_to_change") or "undecided"),
        "currentProblem": _safe_text(raw_input.get("current_problem")),
        "occupation": _safe_text(preferences.get("profession") or career.get("industry")),
        "relationshipStatus": _safe_text(preferences.get("relationship_status")),
        "workMode": career_type,
        "industry": _safe_text(career.get("industry")),
        "employmentType": "entrepreneur" if career_role == "entrepreneur" else "employee",
        "incomeRangeMonthly": financial.get("monthly_income"),
        "incomeRangeAnnual": financial.get("annual_income"),
        "debtRange": financial.get("debt_ratio"),
        "stressLevel": career.get("stress_level"),
        "goals": _split_pipe_values(preferences.get("primary_goal")),
        "challenges": [
            value
            for value in [
                _safe_text(calibration.get("stress_response")),
                _safe_text(calibration.get("money_decision_style")),
                _safe_text(calibration.get("biggest_weakness")),
            ]
            if value
        ],
        "reportEmphasis": _safe_text(calibration.get("decision_style")),
        "spiritualPreference": _safe_text(raw_input.get("spiritual_preference")),
        "healthConcerns": _safe_text(health.get("health_concerns")),
        "anxietyLevel": emotional.get("anxiety_level"),
        "exerciseFrequencyPerWeek": health.get("exercise_frequency_per_week"),
        "plan": plan_key.upper(),
    }


def _build_nested_normalized_input(canonical: Dict[str, Any], raw_input: Dict[str, Any]) -> Dict[str, Any]:
    calibration = raw_input.get("calibration") or {}
    financial = raw_input.get("financial") or {}
    career = raw_input.get("career") or {}
    emotional = raw_input.get("emotional") or {}
    birth = raw_input.get("birth_details") or {}

    identity = {
        "full_name": canonical.get("fullName"),
        "name_variations": " | ".join(canonical.get("nameVariations") or []),
        "date_of_birth": canonical.get("dateOfBirth"),
        "gender": canonical.get("gender"),
        "partner_name": canonical.get("partnerName"),
        "business_name": canonical.get("businessName"),
        "country_of_residence": canonical.get("country"),
        "current_city": canonical.get("currentCity"),
        "email": canonical.get("email"),
        "mobile_number": canonical.get("mobileNumber"),
    }
    birth_details = {
        "date_of_birth": canonical.get("dateOfBirth"),
        "birthplace_city": canonical.get("city"),
        "birthplace_country": canonical.get("country"),
        "time_of_birth": birth.get("time_of_birth"),
    }
    contact = {
        "mobile_number": canonical.get("mobileNumber"),
        "social_handle": canonical.get("socialHandle"),
        "domain_handle": canonical.get("domainHandle"),
    }
    focus = {
        "life_focus": canonical.get("focusArea"),
    }
    preferences = {
        "language_preference": canonical.get("language"),
        "willingness_to_change": canonical.get("willingnessToChange"),
        "profession": canonical.get("occupation"),
        "relationship_status": canonical.get("relationshipStatus"),
        "career_type": canonical.get("workMode"),
        "primary_goal": " | ".join(canonical.get("goals") or []),
    }

    merged = {
        "identity": _compact(identity),
        "birth_details": _compact(birth_details),
        "contact": _compact(contact),
        "focus": _compact(focus),
        "preferences": _compact(preferences),
        "current_problem": canonical.get("currentProblem"),
        "career": _compact(
            {
                **career,
                "industry": canonical.get("industry") or career.get("industry"),
                "stress_level": canonical.get("stressLevel") if canonical.get("stressLevel") is not None else career.get("stress_level"),
            }
        ),
        "financial": _compact(
            {
                **financial,
                "monthly_income": canonical.get("incomeRangeMonthly")
                if canonical.get("incomeRangeMonthly") is not None
                else financial.get("monthly_income"),
                "annual_income": canonical.get("incomeRangeAnnual")
                if canonical.get("incomeRangeAnnual") is not None
                else financial.get("annual_income"),
                "debt_ratio": canonical.get("debtRange")
                if canonical.get("debtRange") is not None
                else financial.get("debt_ratio"),
            }
        ),
        "emotional": _compact(
            {
                **emotional,
                "anxiety_level": canonical.get("anxietyLevel")
                if canonical.get("anxietyLevel") is not None
                else emotional.get("anxiety_level"),
            }
        ),
        "calibration": _compact(
            {
                **calibration,
                "decision_style": canonical.get("reportEmphasis") or calibration.get("decision_style"),
            }
        ),
        "business_history": _compact(raw_input.get("business_history") or {}),
        "health": _compact(raw_input.get("health") or {}),
        "life_events": _compact(raw_input.get("life_events") or {}),
    }
    return _compact(merged)


def _build_profile_snapshot(canonical: Dict[str, Any], numerology_values: Dict[str, Any], plan_key: str) -> Dict[str, Any]:
    pyth = numerology_values.get("pythagorean") or {}
    chaldean = numerology_values.get("chaldean") or {}
    email = numerology_values.get("email_analysis") or {}
    business = numerology_values.get("business_analysis") or {}
    digital = numerology_values.get("digital_analysis") or {}
    mobile = numerology_values.get("mobile_analysis") or {}
    dominant_planet = numerology_values.get("dominant_planet") or {}
    guidance = numerology_values.get("guidance_profile") or {}
    return {
        "fullName": canonical.get("fullName", ""),
        "dateOfBirth": canonical.get("dateOfBirth", ""),
        "gender": canonical.get("gender", ""),
        "mobileNumber": canonical.get("mobileNumber", ""),
        "email": canonical.get("email", ""),
        "lifePath": pyth.get("life_path_number"),
        "destiny": pyth.get("destiny_number"),
        "expression": pyth.get("expression_number"),
        "birthNumber": pyth.get("birth_number"),
        "attitudeNumber": pyth.get("attitude_number"),
        "personalYear": pyth.get("personal_year"),
        "maturityNumber": pyth.get("maturity_number"),
        "soulUrge": pyth.get("soul_urge_number"),
        "personalityNumber": pyth.get("personality_number"),
        "nameNumber": chaldean.get("name_number"),
        "emailNumber": email.get("email_number"),
        "businessNumber": business.get("business_number"),
        "digitalVibration": digital.get("digital_vibration"),
        "mobileVibration": mobile.get("mobile_vibration"),
        "dominantPlanet": dominant_planet.get("planet"),
        "dominantElement": dominant_planet.get("element"),
        "guidancePrimary": guidance.get("primaryNumber"),
        "plan": plan_key.upper(),
    }


def _build_dashboard(scores: Dict[str, Any], plan_config: PlanConfig) -> Dict[str, Any]:
    highlights = []
    for metric in plan_config.visible_loaded_energy_metrics:
        raw_value = scores.get(metric)
        if raw_value is None:
            continue
        highlights.append({"label": to_metric_label(metric), "value": str(raw_value), "metricKey": metric})

    return {
        "riskBand": scores.get("risk_band", "Correctable"),
        "confidenceScore": scores.get("confidence_score", 0),
        "loadedEnergyMetrics": highlights,
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _keyword_hit_score(text: str, keywords: List[str]) -> int:
    score = 0
    for keyword in keywords:
        token = _safe_text(keyword).lower()
        if not token:
            continue
        if token in text:
            score += 2 if " " in token else 1
    return score


def _append_unique(items: List[str], value: str) -> None:
    text = _safe_text(value)
    if text and text not in items:
        items.append(text)


def _classify_problem_category(
    *,
    current_problem: str,
    focus_area: str,
    work_mode: str,
    industry: str,
) -> Dict[str, str]:
    problem_text = _safe_text(current_problem).lower()
    search_text = " ".join(part for part in [current_problem, focus_area, industry] if part).lower()
    default_ordered_categories = [
        "finance",
        "relationship",
        "education",
        "health",
        "business",
        "career",
        "confidence",
        "consistency",
        "spiritual",
    ]
    category_keywords = merge_token_map(
        defaults=PROBLEM_CATEGORY_KEYWORDS,
        config_key="problemCategoryKeywords",
    )
    ordered_categories = merge_priority_list(
        defaults=default_ordered_categories,
        config_key="problemCategoryPriority",
        known_categories=category_keywords.keys(),
    )

    category = "general"
    for candidate in ordered_categories:
        if _contains_any(problem_text, category_keywords.get(candidate, [])):
            category = candidate
            break

    if category == "general":
        for candidate in ordered_categories:
            if _contains_any(search_text, category_keywords.get(candidate, [])):
                category = candidate
                break

    normalized_work_mode = _safe_text(work_mode).lower()
    if category == "general" and normalized_work_mode == "business":
        category = "business"
    elif category == "general" and normalized_work_mode in {"job", "employee"} and current_problem:
        category = "career"

    subcategory = "general"
    for token in category_keywords.get(category, []):
        if token in problem_text or token in search_text:
            subcategory = token
            break

    return {
        "category": category,
        "subcategory": subcategory,
        "focusLabel": current_problem or focus_area or "general_alignment",
    }


def _problem_severity_score(category: str, derived_scores: Dict[str, Any]) -> int:
    positive_metric_keys = (
        "confidence_score",
        "life_stability_index",
        "financial_discipline_index",
        "dharma_alignment_score",
        "emotional_regulation_index",
    )
    pressures: List[int] = []
    for metric in positive_metric_keys:
        if derived_scores.get(metric) is None:
            continue
        score = max(0, min(_safe_int(derived_scores.get(metric)), 100))
        pressures.append(100 - score)

    karma_pressure_raw = derived_scores.get("karma_pressure_index")
    if karma_pressure_raw is not None:
        pressures.append(max(0, min(_safe_int(karma_pressure_raw), 100)))

    overall_pressure = int(round(sum(pressures) / len(pressures))) if pressures else 50

    focus_metric = PROBLEM_FOCUS_METRIC.get(category)
    focus_pressure = overall_pressure
    if focus_metric and derived_scores.get(focus_metric) is not None:
        focus_score = max(0, min(_safe_int(derived_scores.get(focus_metric)), 100))
        focus_pressure = focus_score if focus_metric == "karma_pressure_index" else (100 - focus_score)

    severity = int(round((0.65 * focus_pressure) + (0.35 * overall_pressure)))
    return max(0, min(severity, 100))


def _severity_label(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _time_horizon(score: int) -> str:
    if score >= 80:
        return "immediate_7_days"
    if score >= 65:
        return "short_term_30_days"
    if score >= 45:
        return "mid_term_90_days"
    return "long_term_6_months"


def _build_problem_root_causes(
    *,
    category: str,
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
) -> List[str]:
    causes: List[str] = []
    weakest_metric = _safe_text(derived_scores.get("weakest_metric"))
    if weakest_metric:
        _append_unique(
            causes,
            WEAKEST_METRIC_ROOT_CAUSE.get(
                weakest_metric,
                "The currently weakest deterministic metric needs explicit weekly correction.",
            ),
        )

    confidence_score = _safe_int(derived_scores.get("confidence_score"), default=50)
    stability_score = _safe_int(derived_scores.get("life_stability_index"), default=50)
    finance_score = _safe_int(derived_scores.get("financial_discipline_index"), default=50)
    emotional_score = _safe_int(derived_scores.get("emotional_regulation_index"), default=50)

    if category in {"career", "business", "consistency"} and stability_score <= 60:
        _append_unique(causes, "Execution consistency is weak, so plans lose momentum before measurable conversion.")
    if category == "finance" and finance_score <= 60:
        _append_unique(causes, "Financial decisions may be irregular, increasing avoidable pressure cycles.")
    if category in {"relationship", "health"} and emotional_score <= 60:
        _append_unique(causes, "Emotional regulation pressure is high, reducing clarity under stress.")
    if category in {"confidence", "education"} and confidence_score <= 60:
        _append_unique(causes, "Self-trust and decision confidence need structured rebuilding.")

    loshu = numerology_values.get("loshu_grid") or {}
    raw_missing = loshu.get("missing_numbers") or loshu.get("missing") or []
    missing_digits: List[int] = []
    if isinstance(raw_missing, list):
        for item in raw_missing:
            try:
                missing_digits.append(int(item))
            except (TypeError, ValueError):
                continue
    missing_set = set(missing_digits)
    if 4 in missing_set and category in {"career", "business", "consistency"}:
        _append_unique(causes, "Missing 4-pattern indicates structure and routine reinforcement is needed.")
    if 3 in missing_set and category in {"career", "confidence", "education"}:
        _append_unique(causes, "Missing 3-pattern can reduce expression confidence in high-pressure communication.")
    if 2 in missing_set and category == "relationship":
        _append_unique(causes, "Missing 2-pattern may weaken emotional reciprocity and listening balance.")

    if not causes:
        _append_unique(causes, "Primary gap appears to be execution consistency between intention and daily action.")
    return causes[:4]


def _build_problem_evidence(
    *,
    category: str,
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    focus_metric = PROBLEM_FOCUS_METRIC.get(category)
    if focus_metric and derived_scores.get(focus_metric) is not None:
        evidence.append(
            {
                "signalType": "focus_metric",
                "signalKey": focus_metric,
                "value": max(0, min(_safe_int(derived_scores.get(focus_metric)), 100)),
            }
        )

    weakest_metric = _safe_text(derived_scores.get("weakest_metric"))
    if weakest_metric:
        evidence.append({"signalType": "weakest_metric", "signalKey": weakest_metric})

    risk_band = _safe_text(derived_scores.get("risk_band"))
    if risk_band:
        evidence.append({"signalType": "risk_band", "signalKey": "risk_band", "value": risk_band})

    for metric in ("confidence_score", "life_stability_index", "financial_discipline_index", "emotional_regulation_index"):
        if derived_scores.get(metric) is None:
            continue
        evidence.append(
            {
                "signalType": "metric",
                "signalKey": metric,
                "value": max(0, min(_safe_int(derived_scores.get(metric)), 100)),
            }
        )

    loshu = numerology_values.get("loshu_grid") or {}
    raw_missing = loshu.get("missing_numbers") or loshu.get("missing") or []
    if isinstance(raw_missing, list) and raw_missing:
        numeric_missing: List[int] = []
        for item in raw_missing:
            try:
                numeric_missing.append(int(item))
            except (TypeError, ValueError):
                continue
        if numeric_missing:
            evidence.append(
                {
                    "signalType": "loshu_missing",
                    "signalKey": "missing_numbers",
                    "value": sorted(set(numeric_missing)),
                }
            )

    return evidence[:7]


def _build_problem_profile(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
) -> Dict[str, Any]:
    current_problem = _safe_text(canonical_normalized_input.get("currentProblem"))
    focus_area = _safe_text(canonical_normalized_input.get("focusArea"))
    work_mode = _safe_text(canonical_normalized_input.get("workMode"))
    industry = _safe_text(canonical_normalized_input.get("industry"))
    willingness = _safe_text(canonical_normalized_input.get("willingnessToChange")).lower()

    classification = _classify_problem_category(
        current_problem=current_problem,
        focus_area=focus_area,
        work_mode=work_mode,
        industry=industry,
    )
    category = classification.get("category", "general")
    severity_score = _problem_severity_score(category, derived_scores)
    evidence = _build_problem_evidence(
        category=category,
        numerology_values=numerology_values,
        derived_scores=derived_scores,
    )

    if current_problem and len(evidence) >= 3:
        profile_confidence = "high"
    elif current_problem or len(evidence) >= 2:
        profile_confidence = "medium"
    else:
        profile_confidence = "low"

    recommendation_mode = "stabilize_first" if severity_score >= 70 else "progressive_optimize"
    if willingness == "yes" and severity_score < 80:
        recommendation_mode = "fast_track_execution"
    elif willingness == "no":
        recommendation_mode = "low_resistance_adaptation"

    return _compact(
        {
            "category": category,
            "subcategory": classification.get("subcategory"),
            "focusLabel": classification.get("focusLabel"),
            "severityScore": severity_score,
            "severityLabel": _severity_label(severity_score),
            "timeHorizon": _time_horizon(severity_score),
            "confidence": profile_confidence,
            "recommendationMode": recommendation_mode,
            "rootCauses": _build_problem_root_causes(
                category=category,
                numerology_values=numerology_values,
                derived_scores=derived_scores,
            ),
            "evidence": evidence,
            "source": {
                "currentProblem": current_problem,
                "focusArea": focus_area,
                "workMode": work_mode,
                "industry": industry,
            },
        }
    )


def _read_path(context: Dict[str, Any], dotted_path: str) -> Any:
    cursor: Any = context
    for part in dotted_path.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return cursor


def _has_data(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _section_has_deterministic_support(section_key: str, context: Dict[str, Any]) -> bool:
    support_paths = SECTION_SUPPORT_PATHS.get(section_key, [])
    if not support_paths:
        return True
    return any(_has_data(_read_path(context, dotted_path)) for dotted_path in support_paths)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _build_uniqueness_fingerprint(
    *,
    canonical_normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
    plan_key: str,
) -> str:
    pyth = numerology_values.get("pythagorean") or {}
    chaldean = numerology_values.get("chaldean") or {}
    loshu = numerology_values.get("loshu_grid") or {}

    fingerprint_payload = {
        "plan": plan_key.upper(),
        "identity": {
            "fullName": canonical_normalized_input.get("fullName"),
            "dateOfBirth": canonical_normalized_input.get("dateOfBirth"),
            "mobileNumber": canonical_normalized_input.get("mobileNumber"),
            "email": canonical_normalized_input.get("email"),
            "businessName": canonical_normalized_input.get("businessName"),
            "socialHandle": canonical_normalized_input.get("socialHandle"),
            "domainHandle": canonical_normalized_input.get("domainHandle"),
            "focusArea": canonical_normalized_input.get("focusArea"),
            "currentProblem": canonical_normalized_input.get("currentProblem"),
            "industry": canonical_normalized_input.get("industry"),
            "workMode": canonical_normalized_input.get("workMode"),
            "healthConcerns": canonical_normalized_input.get("healthConcerns"),
            "willingnessToChange": canonical_normalized_input.get("willingnessToChange"),
        },
        "numerology": {
            "lifePath": pyth.get("life_path_number"),
            "destiny": pyth.get("destiny_number"),
            "expression": pyth.get("expression_number"),
            "nameNumber": chaldean.get("name_number"),
            "emailNumber": (numerology_values.get("email_analysis") or {}).get("email_number"),
            "businessNumber": (numerology_values.get("business_analysis") or {}).get("business_number"),
            "digitalVibration": (numerology_values.get("digital_analysis") or {}).get("digital_vibration"),
            "missingNumbers": loshu.get("missing_numbers"),
        },
        "scores": {
            "confidence_score": derived_scores.get("confidence_score"),
            "life_stability_index": derived_scores.get("life_stability_index"),
            "financial_discipline_index": derived_scores.get("financial_discipline_index"),
            "dharma_alignment_score": derived_scores.get("dharma_alignment_score"),
            "karma_pressure_index": derived_scores.get("karma_pressure_index"),
            "risk_band": derived_scores.get("risk_band"),
            "weakest_metric": derived_scores.get("weakest_metric"),
            "strongest_metric": derived_scores.get("strongest_metric"),
        },
    }
    canonical_json = json.dumps(_to_jsonable(fingerprint_payload), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:20]


def _build_contradiction_guards(
    *,
    canonical_normalized_input: Dict[str, Any],
    derived_scores: Dict[str, Any],
    problem_profile: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    guards: List[Dict[str, Any]] = []
    confidence_score = int(derived_scores.get("confidence_score") or 0)
    financial_score = int(derived_scores.get("financial_discipline_index") or 0)
    emotional_score = int(derived_scores.get("emotional_regulation_index") or 0)
    weakest_metric = _safe_text(derived_scores.get("weakest_metric"))
    current_problem = _safe_text(canonical_normalized_input.get("currentProblem"))

    if confidence_score <= 55:
        guards.append(
            {
                "guardId": "decision-clarity-low",
                "condition": {"metric": "confidence_score", "lte": 55},
                "mustAvoid": ["absolute certainty claims", "instant-outcome promises"],
                "mustInclude": ["stepwise decision protocol", "verification checkpoints"],
            }
        )
    if financial_score <= 55:
        guards.append(
            {
                "guardId": "financial-discipline-low",
                "condition": {"metric": "financial_discipline_index", "lte": 55},
                "mustAvoid": ["high-risk speculation advice"],
                "mustInclude": ["cash-protection discipline", "fixed review cadence"],
            }
        )
    if emotional_score <= 55:
        guards.append(
            {
                "guardId": "emotional-regulation-low",
                "condition": {"metric": "emotional_regulation_index", "lte": 55},
                "mustAvoid": ["emotionally charged urgency framing"],
                "mustInclude": ["regulation ritual before major decisions"],
            }
        )
    if weakest_metric:
        guards.append(
            {
                "guardId": "weakest-metric-priority",
                "condition": {"metric": weakest_metric, "priority": "highest"},
                "mustAvoid": ["ignoring weakest metric in action plan"],
                "mustInclude": ["explicit correction path for weakest metric"],
            }
        )
    if current_problem:
        guards.append(
            {
                "guardId": "user-problem-anchoring",
                "condition": {"field": "currentProblem", "present": True},
                "mustAvoid": ["detached generic narrative"],
                "mustInclude": [f"problem-specific guidance anchored to '{current_problem[:80]}'"],
            }
        )

    profile = problem_profile if isinstance(problem_profile, dict) else {}
    category = _safe_text(profile.get("category")).lower() or "general"
    category_domain_rules = merge_category_fields(
        defaults=PROBLEM_CATEGORY_DOMAIN_RULES,
        config_key="problemCategoryDomainRules",
        fields=("mustInclude", "mustAvoid"),
    )
    domain_rules = category_domain_rules.get(category) or {}
    domain_must_include = [item for item in (domain_rules.get("mustInclude") or []) if _safe_text(item)]
    domain_must_avoid = [item for item in (domain_rules.get("mustAvoid") or []) if _safe_text(item)]
    if domain_must_include or domain_must_avoid:
        guards.append(
            {
                "guardId": "problem-category-domain-consistency",
                "condition": {"problemCategory": category},
                "mustAvoid": domain_must_avoid,
                "mustInclude": domain_must_include,
            }
        )

    return guards


def _build_section_fact_packs(
    *,
    plan_config: PlanConfig,
    canonical_normalized_input: Dict[str, Any],
    normalized_input: Dict[str, Any],
    numerology_values: Dict[str, Any],
    derived_scores: Dict[str, Any],
    problem_profile: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    pyth = numerology_values.get("pythagorean") or {}
    chaldean = numerology_values.get("chaldean") or {}
    mobile = numerology_values.get("mobile_analysis") or {}
    email = numerology_values.get("email_analysis") or {}
    business = numerology_values.get("business_analysis") or {}
    digital = numerology_values.get("digital_analysis") or {}
    context = {
        "normalized_input": normalized_input,
        "numerology_values": numerology_values,
        "derived_scores": derived_scores,
    }
    base_identity = {
        "fullName": canonical_normalized_input.get("fullName"),
        "nameVariations": canonical_normalized_input.get("nameVariations"),
        "dateOfBirth": canonical_normalized_input.get("dateOfBirth"),
        "birthTime": (normalized_input.get("birth_details") or {}).get("time_of_birth"),
        "gender": canonical_normalized_input.get("gender"),
        "city": canonical_normalized_input.get("city"),
        "currentCity": canonical_normalized_input.get("currentCity"),
        "country": canonical_normalized_input.get("country"),
        "focusArea": canonical_normalized_input.get("focusArea"),
        "currentProblem": canonical_normalized_input.get("currentProblem"),
        "problemProfile": problem_profile,
        "willingnessToChange": canonical_normalized_input.get("willingnessToChange"),
        "workMode": canonical_normalized_input.get("workMode"),
        "industry": canonical_normalized_input.get("industry"),
        "businessName": canonical_normalized_input.get("businessName"),
        "socialHandle": canonical_normalized_input.get("socialHandle"),
        "domainHandle": canonical_normalized_input.get("domainHandle"),
        "goals": canonical_normalized_input.get("goals"),
        "challenges": canonical_normalized_input.get("challenges"),
    }
    base_numbers = {
        "lifePath": pyth.get("life_path_number"),
        "destiny": pyth.get("destiny_number"),
        "expression": pyth.get("expression_number"),
        "birthNumber": pyth.get("birth_number"),
        "attitudeNumber": pyth.get("attitude_number"),
        "personalYear": pyth.get("personal_year"),
        "maturityNumber": pyth.get("maturity_number"),
        "soulUrge": pyth.get("soul_urge_number"),
        "personalityNumber": pyth.get("personality_number"),
        "nameNumber": chaldean.get("name_number"),
        "nameCompound": chaldean.get("compound_number"),
        "emailVibration": email.get("email_number"),
        "mobileVibration": mobile.get("mobile_vibration"),
        "businessNumber": business.get("business_number"),
        "digitalVibration": digital.get("digital_vibration"),
        "mobileDigits": mobile.get("digits"),
        "mobilePresentDigits": mobile.get("present_digits"),
        "mobileMissingDigits": mobile.get("missing_digits"),
        "mobileRepeatingDigits": mobile.get("repeating_digits"),
        "mobileDominantDigits": mobile.get("dominant_digits"),
        "loShuGrid": numerology_values.get("loshu_grid"),
        "numberProfiles": numerology_values.get("number_profiles"),
        "dominantPlanet": numerology_values.get("dominant_planet"),
        "swarProfile": numerology_values.get("swar_profile"),
        "guidanceProfile": numerology_values.get("guidance_profile"),
    }
    base_scores = {
        "confidence_score": derived_scores.get("confidence_score"),
        "risk_band": derived_scores.get("risk_band"),
        "weakest_metric": derived_scores.get("weakest_metric"),
        "strongest_metric": derived_scores.get("strongest_metric"),
        "karma_pressure_index": derived_scores.get("karma_pressure_index"),
        "life_stability_index": derived_scores.get("life_stability_index"),
        "financial_discipline_index": derived_scores.get("financial_discipline_index"),
        "dharma_alignment_score": derived_scores.get("dharma_alignment_score"),
        "emotional_regulation_index": derived_scores.get("emotional_regulation_index"),
    }

    packs: Dict[str, Dict[str, Any]] = {}
    for section_key in plan_config.enabled_sections:
        support_paths = SECTION_SUPPORT_PATHS.get(section_key, [])
        support_values: Dict[str, Any] = {}
        for path in support_paths:
            value = _read_path(context, path)
            if _has_data(value):
                support_values[path] = value
        packs[section_key] = _compact(
            {
                "sectionKey": section_key,
                "supportPaths": support_paths,
                "supportValues": support_values,
                "identityContext": base_identity,
                "coreNumbers": base_numbers,
                "scoreSignals": base_scores,
            }
        )
    return packs


def run_deterministic_pipeline(*, intake_data: Dict[str, Any], plan_config: PlanConfig) -> DeterministicPipelineOutput:
    raw_input = _compact(intake_data or {})
    canonical_normalized_input = _build_canonical_normalized_input(raw_input, plan_config.key)
    normalized_input = _build_nested_normalized_input(canonical_normalized_input, raw_input)

    identity = dict(normalized_input.get("identity") or {})
    birth_details = dict(normalized_input.get("birth_details") or {})
    contact_layer = dict(normalized_input.get("contact") or {})
    if contact_layer.get("social_handle"):
        identity["social_handle"] = contact_layer.get("social_handle")
    if contact_layer.get("domain_handle"):
        identity["domain_handle"] = contact_layer.get("domain_handle")

    if settings.AI_REPORT_FORCE_LLM_NARRATIVE:
        numerology_values = {}
        derived_scores = {}
        problem_profile = _build_problem_profile(
            canonical_normalized_input=canonical_normalized_input,
            numerology_values=numerology_values,
            derived_scores=derived_scores,
        )
    else:
        numerology_values = generate_numerology_profile(
            identity=identity,
            birth_details=birth_details,
            plan_name=plan_config.key,
        ) or {}

        email_value = _safe_text(identity.get("email"))
        email_number = _pythagorean_email_number(email_value)
        if email_number is not None:
            email_analysis = dict(numerology_values.get("email_analysis") or {})
            email_analysis["email_number"] = email_number
            numerology_values["email_analysis"] = email_analysis

        flat_data = flatten_input(
            normalized_input,
            numerology_core=numerology_values,
            intake_context={
                "identity": identity,
                "birth_details": birth_details,
                "contact": normalized_input.get("contact") or {},
            },
        )
        derived_scores = generate_score_summary(flat_data, plan_name=plan_config.key) or {}
        problem_profile = _build_problem_profile(
            canonical_normalized_input=canonical_normalized_input,
            numerology_values=numerology_values,
            derived_scores=derived_scores,
        )

    support_context = {
        "normalized_input": normalized_input,
        "numerology_values": numerology_values,
        "derived_scores": derived_scores,
    }
    section_eligibility = {section: True for section in plan_config.enabled_sections}
    if settings.AI_REPORT_FORCE_LLM_NARRATIVE:
        section_deterministic_availability = {section: True for section in plan_config.enabled_sections}
        section_fact_packs = {}
        contradiction_guards = []
    else:
        section_deterministic_availability = {
            section: _section_has_deterministic_support(section, support_context)
            for section in plan_config.enabled_sections
        }
        section_fact_packs = _build_section_fact_packs(
            plan_config=plan_config,
            canonical_normalized_input=canonical_normalized_input,
            normalized_input=normalized_input,
            numerology_values=numerology_values,
            derived_scores=derived_scores,
            problem_profile=problem_profile,
        )
        contradiction_guards = _build_contradiction_guards(
            canonical_normalized_input=canonical_normalized_input,
            derived_scores=derived_scores,
            problem_profile=problem_profile,
        )
    uniqueness_fingerprint = _build_uniqueness_fingerprint(
        canonical_normalized_input=canonical_normalized_input,
        numerology_values=numerology_values,
        derived_scores=derived_scores,
        plan_key=plan_config.key,
    )

    profile_snapshot = _build_profile_snapshot(canonical_normalized_input, numerology_values, plan_config.key)
    dashboard = _build_dashboard(derived_scores, plan_config)

    return DeterministicPipelineOutput(
        normalized_input=normalized_input,
        canonical_normalized_input=canonical_normalized_input,
        numerology_values=numerology_values,
        derived_scores=derived_scores,
        section_eligibility=section_eligibility,
        section_deterministic_availability=section_deterministic_availability,
        profile_snapshot=profile_snapshot,
        dashboard=dashboard,
        problem_profile=problem_profile,
        section_fact_packs=section_fact_packs,
        contradiction_guards=contradiction_guards,
        uniqueness_fingerprint=uniqueness_fingerprint,
    )
from app.core.config import settings

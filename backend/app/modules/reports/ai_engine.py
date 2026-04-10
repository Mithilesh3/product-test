from typing import Dict, Any
from datetime import datetime
from app.core.time_utils import UTC
import re
import traceback

from app.modules.reports.interpretation_engine import build_interpretation_report
from app.modules.reports.scoring_engine import generate_score_summary
from app.modules.reports.llm_engine import generate_ai_narrative
from app.modules.numerology.core_engine import generate_numerology_profile

from app.modules.reports.remedy_engine import generate_remedy_protocol
from app.modules.reports.archetype_engine import generate_numerology_archetype

from app.modules.numerology.business_engine import analyze_business_name

from app.core.config import settings


# =====================================================
# PLAN CONFIGURATION
# =====================================================

PLAN_FEATURES = {
    "basic": {"token_multiplier": 0.7},
    "pro": {"token_multiplier": 0.9},
    "premium": {"token_multiplier": 1.1},
    "enterprise": {"token_multiplier": 1.3},
}

FOCUS_LABELS = {
    "finance_debt": "à¤µà¤¿à¤¤à¥à¤¤à¥€à¤¯ à¤¦à¤¬à¤¾à¤µ à¤”à¤° debt management",
    "career_growth": "à¤•à¤°à¤¿à¤¯à¤° à¤—à¥à¤°à¥‹à¤¥ à¤”à¤° positioning",
    "relationship": "à¤°à¤¿à¤²à¥‡à¤¶à¤¨à¤¶à¤¿à¤ª à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨ à¤”à¤° compatibility",
    "health_stability": "à¤¸à¥à¤µà¤¾à¤¸à¥à¤¥à¥à¤¯ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° sustainable routine",
    "emotional_confusion": "à¤­à¤¾à¤µà¤¨à¤¾à¤¤à¥à¤®à¤• à¤¸à¥à¤ªà¤·à¥à¤Ÿà¤¤à¤¾ à¤”à¤° inner stability",
    "business_decision": "à¤¬à¤¿à¤œà¤¼à¤¨à¥‡à¤¸ à¤¦à¤¿à¤¶à¤¾ à¤”à¤° strategic decisions",
    "general_alignment": "à¤¸à¤®à¤—à¥à¤° life alignment",
}

FOCUS_ACTIONS = {
    "finance_debt": "cash flow à¤•à¥‹ stabilize à¤•à¤°à¥‡à¤‚, debt discipline à¤®à¤œà¤¬à¥‚à¤¤ à¤•à¤°à¥‡à¤‚, à¤”à¤° repeatable savings habit à¤¬à¤¨à¤¾à¤à¤‚",
    "career_growth": "à¤à¤¸à¥‡ roles à¤”à¤° projects à¤šà¥à¤¨à¥‡à¤‚ à¤œà¥‹ credibility à¤•à¥‹ compound à¤•à¤°à¥‡à¤‚ à¤”à¤° energy à¤•à¥‹ scatter à¤¨ à¤¹à¥‹à¤¨à¥‡ à¤¦à¥‡à¤‚",
    "relationship": "close relationships à¤®à¥‡à¤‚ clarity, healthy boundaries, à¤”à¤° communication quality à¤¸à¥à¤§à¤¾à¤°à¥‡à¤‚",
    "health_stability": "sleep, routine, à¤”à¤° lower-stress decision cycles à¤¸à¥‡ energy à¤•à¥‹ protect à¤•à¤°à¥‡à¤‚",
    "emotional_confusion": "major choices à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ internal noise à¤•à¤® à¤•à¤°à¥‡à¤‚ à¤”à¤° steadier routines build à¤•à¤°à¥‡à¤‚",
    "business_decision": "reactive expansion à¤•à¥‡ à¤¬à¤œà¤¾à¤¯ disciplined execution à¤•à¥‹ priority à¤¦à¥‡à¤‚",
    "general_alignment": "priorities simplify à¤•à¤°à¤•à¥‡ daily action à¤•à¥‹ long-term direction à¤•à¥‡ à¤¸à¤¾à¤¥ align à¤•à¤°à¥‡à¤‚",
}

METRIC_LABELS = {
    "life_stability_index": "Life Stability",
    "financial_discipline_index": "Financial Discipline",
    "emotional_regulation_index": "Emotional Regulation",
    "dharma_alignment_score": "Dharma Alignment",
    "confidence_score": "Decision Clarity",
}

METRIC_STRENGTHS = {
    "life_stability_index": "à¤œà¤¬ priorities clear à¤¹à¥‹à¤‚ à¤¤à¤¬ structure create à¤•à¤°à¤¨à¥‡ à¤•à¥€ reliable capacity",
    "financial_discipline_index": "money aur risk ke around measured decisions lene ka instinct",
    "emotional_regulation_index": "pressure ke baad composed rehne aur recover karne ki capacity",
    "dharma_alignment_score": "effort, timing, aur purpose ke beech strong alignment",
    "confidence_score": "grounded decisions lene ke liye kaafi self-awareness aur momentum",
}

METRIC_RISKS = {
    "life_stability_index": "routine me inconsistency important moments par execution ko weak kar sakti hai",
    "financial_discipline_index": "strong budgeting structure ke bina money decisions drift kar sakte hain",
    "emotional_regulation_index": "agar recovery habits protected na hon to stress judgment ko distort kar sakta hai",
    "dharma_alignment_score": "energy un paths par spend ho sakti hai jo long-term progress me compound nahi karte",
    "confidence_score": "inputs unclear hone se precision kam ho rahi hai, isliye major decisions ko extra validation chahiye",
}


# =====================================================
# INTERNAL HELPERS
# =====================================================


def _clean_mapping(values: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(values, dict):
        return {}
    return {
        key: value
        for key, value in (values or {}).items()
        if value not in (None, "", [], {})
    }


def _prepare_identity(identity: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]:
    prepared = _clean_mapping(identity)
    date_of_birth = (birth_details or {}).get("date_of_birth")
    if date_of_birth and not prepared.get("date_of_birth"):
        prepared["date_of_birth"] = date_of_birth
    return prepared


def _build_intake_context(request_data: Dict[str, Any]) -> Dict[str, Any]:
    request_data = request_data or {}
    birth_details = request_data.get("birth_details") or {}
    contact = request_data.get("contact") or {}
    preferences = request_data.get("preferences") or {}
    identity = _prepare_identity(request_data.get("identity") or {}, birth_details)

    mobile_number = contact.get("mobile_number")
    if mobile_number and not identity.get("mobile_number"):
        identity["mobile_number"] = mobile_number

    return {
        "identity": identity,
        "birth_details": _clean_mapping(birth_details),
        "focus": _clean_mapping(request_data.get("focus") or {}),
        "financial": _clean_mapping(request_data.get("financial") or {}),
        "career": _clean_mapping(request_data.get("career") or {}),
        "emotional": _clean_mapping(request_data.get("emotional") or {}),
        "life_events": _clean_mapping(request_data.get("life_events") or {}),
        "calibration": _clean_mapping(request_data.get("calibration") or {}),
        "contact": _clean_mapping(contact),
        "preferences": _clean_mapping(preferences),
        "current_problem": (request_data.get("current_problem") or "").strip(),
    }


def _metric_extremes(scores: Dict[str, Any]) -> tuple[tuple[str, int], tuple[str, int]]:
    metric_pairs = []
    for key in METRIC_LABELS:
        raw_value = scores.get(key, 50)
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 50
        metric_pairs.append((key, value))

    strongest = max(metric_pairs, key=lambda item: item[1])
    weakest = min(metric_pairs, key=lambda item: item[1])
    return strongest, weakest


def _build_personalized_fallback(
    intake_context: Dict[str, Any],
    numerology_core: Dict[str, Any],
    scores: Dict[str, Any],
    current_problem: str,
) -> Dict[str, Any]:
    identity = intake_context.get("identity") or {}
    birth_details = intake_context.get("birth_details") or {}
    focus = intake_context.get("focus") or {}
    financial = intake_context.get("financial") or {}
    career = intake_context.get("career") or {}
    emotional = intake_context.get("emotional") or {}

    full_name = identity.get("full_name") or "User"
    first_name = full_name.split()[0] if full_name else "User"
    focus_key = focus.get("life_focus") or "general_alignment"
    focus_label = FOCUS_LABELS.get(focus_key, FOCUS_LABELS["general_alignment"])
    focus_action = FOCUS_ACTIONS.get(focus_key, FOCUS_ACTIONS["general_alignment"])

    pythagorean = numerology_core.get("pythagorean") or {}
    life_path = pythagorean.get("life_path_number")
    destiny_number = pythagorean.get("destiny_number")

    strongest, weakest = _metric_extremes(scores)
    strongest_label = METRIC_LABELS[strongest[0]]
    weakest_label = METRIC_LABELS[weakest[0]]
    strongest_message = METRIC_STRENGTHS[strongest[0]]
    weakest_message = METRIC_RISKS[weakest[0]]

    confidence = scores.get("confidence_score", 50)
    risk_band = scores.get("risk_band", "Correctable")
    monthly_income = financial.get("monthly_income")
    risk_tolerance = financial.get("risk_tolerance")
    industry = career.get("industry")
    role = career.get("role") or "professional"
    anxiety_level = emotional.get("anxiety_level")
    decision_confusion = emotional.get("decision_confusion")
    date_of_birth = birth_details.get("date_of_birth") or identity.get("date_of_birth")
    mobile_analysis = numerology_core.get("mobile_analysis") or {}
    mobile_vibration = mobile_analysis.get("mobile_vibration")

    problem_statement = current_problem or "à¤¸à¤®à¤—à¥à¤° à¤¦à¤¿à¤¶à¤¾ à¤”à¤° long-term stability"
    role_phrase = role.replace("_", " ")
    industry_phrase = f" ({industry})" if industry else ""
    income_phrase = f" à¤®à¤¾à¤¸à¤¿à¤• à¤†à¤¯ à¤²à¤—à¤­à¤— {monthly_income} à¤•à¤¾ à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¹à¥ˆà¥¤" if monthly_income else ""
    risk_phrase = f" Risk tolerance à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤®à¥‡à¤‚ {str(risk_tolerance).lower()} à¤¶à¥à¤°à¥‡à¤£à¥€ à¤®à¥‡à¤‚ à¤¹à¥ˆà¥¤" if risk_tolerance else ""
    anxiety_phrase = f" Reported anxiety level {anxiety_level}/10 à¤¹à¥ˆà¥¤" if anxiety_level is not None else ""
    confusion_phrase = (
        f" Decision confusion {decision_confusion}/10 à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤¬à¤¡à¤¼à¥‡ decisions à¤®à¥‡à¤‚ extra validation à¤‰à¤ªà¤¯à¥‹à¤—à¥€ à¤°à¤¹à¥‡à¤—à¤¾à¥¤"
        if decision_confusion is not None
        else ""
    )
    date_phrase = f" Date of birth input {date_of_birth} à¤¸à¥‡ numerology core derive à¤¹à¥à¤† à¤¹à¥ˆà¥¤" if date_of_birth else ""
    low_data_note = (
        " Behavioral intake limited à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤•à¥à¤› intelligence metrics neutral baseline à¤ªà¤° à¤°à¤¹ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤"
        if int(scores.get("data_completeness_score", 0) or 0) <= 35
        else ""
    )
    mobile_phrase = f" Mobile vibration {mobile_vibration} daily communication tone à¤•à¥‹ influence à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤" if mobile_vibration else ""

    business_signals = numerology_core.get("business_analysis") or {}
    business_strength = business_signals.get(
        "business_strength",
        f"{first_name} à¤•à¥€ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² à¤à¤¸à¥‡ strategic work à¤•à¥‹ support à¤•à¤°à¤¤à¥€ à¤¹à¥ˆ à¤œà¤¹à¤¾à¤ clarity, reputation, à¤”à¤° disciplined follow-through reward à¤®à¤¿à¤²à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    )
    business_risk = business_signals.get(
        "risk_factor",
        f"à¤®à¥à¤–à¥à¤¯ business risk à¤¯à¤¹ à¤¹à¥ˆ à¤•à¤¿ pressure à¤¬à¤¢à¤¼à¤¨à¥‡ à¤ªà¤° {weakest_label.lower()} execution à¤•à¥‹ slow à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    )
    compatible_industries = business_signals.get("compatible_industries") or []

    compatibility = numerology_core.get("compatibility") or {}
    compatibility_guidance = (
        f"Current compatibility signal {compatibility.get('compatibility_level', 'Moderate')} à¤¹à¥ˆ "
        f"à¤œà¤¿à¤¸à¤•à¤¾ score {compatibility.get('compatibility_score', 0)}/100 à¤¹à¥ˆà¥¤"
        if compatibility
        else f"{first_name} à¤•à¥‡ à¤²à¤¿à¤ à¤µà¥‡ relationships à¤¸à¤¬à¤¸à¥‡ à¤¬à¥‡à¤¹à¤¤à¤° à¤¹à¥ˆà¤‚ à¤œà¥‹ {strongest_label.lower()} à¤•à¥‹ reinforce à¤•à¤°à¥‡à¤‚ à¤”à¤° {weakest_label.lower()} à¤ªà¤° pressure à¤•à¤® à¤•à¤°à¥‡à¤‚à¥¤"
    )

    compatible_numbers = [number for number in [life_path, destiny_number] if isinstance(number, int)]
    challenging_numbers = []

    return {
        "_fallback_used": True,
        "executive_brief": {
            "summary": (
                f"{full_name} à¤•à¥€ report à¤•à¤¾ central focus {focus_label} à¤¹à¥ˆà¥¤ "
                f"Life Path {life_path or 'N/A'} à¤”à¤° Destiny {destiny_number or 'N/A'} à¤¸à¥‡ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ profile à¤®à¥‡à¤‚ {strongest_message} à¤®à¥Œà¤œà¥‚à¤¦ à¤¹à¥ˆ, "
                f"à¤œà¤¬à¤•à¤¿ current pressure point {weakest_message} à¤¹à¥ˆà¥¤ "
                f"Immediate concern {problem_statement} à¤¸à¥‡ à¤œà¥à¤¡à¤¼à¤¾ à¤¹à¥à¤† à¤¹à¥ˆà¥¤{date_phrase}{mobile_phrase}{low_data_note}"
            ),
            "key_strength": f"à¤†à¤ªà¤•à¤¾ strongest signal {strongest_label} à¤¹à¥ˆà¥¤ à¤‡à¤¸à¤•à¤¾ à¤¸à¥€à¤§à¤¾ à¤®à¤¤à¤²à¤¬ à¤¹à¥ˆ {strongest_message}à¥¤",
            "key_risk": f"à¤¸à¤¬à¤¸à¥‡ sensitive area {weakest_label} à¤¹à¥ˆ, à¤œà¥‹ à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ {weakest_message}à¥¤",
            "strategic_focus": (
                f"à¤…à¤­à¥€ à¤ªà¤¹à¤²à¥€ priority à¤¯à¤¹ à¤¹à¥‹à¤¨à¥€ à¤šà¤¾à¤¹à¤¿à¤ à¤•à¤¿ à¤†à¤ª {focus_action}à¥¤ à¤¹à¤° major decision à¤•à¥‹ stronger {weakest_label.lower()} routine à¤•à¥‡ through filter à¤•à¤°à¥‡à¤‚à¥¤"
            ),
        },
        "analysis_sections": {
            "career_analysis": (
                f"{first_name} à¤•à¥€ {role_phrase}{industry_phrase} profile à¤®à¥‡à¤‚ à¤à¤¸à¥‡ roles à¤¬à¥‡à¤¹à¤¤à¤° à¤°à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤œà¥‹ "
                f"{strongest_label.lower()} à¤•à¥‹ reward à¤•à¤°à¥‡à¤‚, à¤¨ à¤•à¤¿ constant reactive change à¤•à¥‹à¥¤ Dharma alignment {scores.get('dharma_alignment_score', 50)}/100 à¤¹à¥ˆ, "
                f"à¤‡à¤¸à¤²à¤¿à¤ work choices à¤•à¥‹ {focus_label} à¤•à¥‡ stated goal à¤•à¥‡ à¤ªà¤¾à¤¸ à¤°à¤–à¤¨à¤¾ à¤¬à¥‡à¤¹à¤¤à¤° à¤°à¤¹à¥‡à¤—à¤¾à¥¤"
            ),
            "decision_profile": (
                f"Current decision clarity {confidence}/100 à¤¹à¥ˆ à¤”à¤° overall risk band {risk_band} à¤¹à¥ˆà¥¤ "
                f"{confusion_phrase if confusion_phrase else 'Major choices à¤¬à¥‡à¤¹à¤¤à¤° à¤¹à¥‹à¤‚à¤—à¥‡ à¤œà¤¬ à¤†à¤ª decision speed à¤¥à¥‹à¤¡à¤¼à¥€ slow à¤•à¤°à¤•à¥‡ assumptions validate à¤•à¤°à¥‡à¤‚à¤—à¥‡à¥¤'}"
            ),
            "emotional_analysis": (
                f"Emotional regulation {scores.get('emotional_regulation_index', 50)}/100 à¤¹à¥ˆà¥¤{anxiety_phrase}"
                f" à¤¯à¤¹ signal à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ recovery routine à¤”à¤° lower-noise environment judgment quality à¤•à¥‹ à¤¸à¥€à¤§à¥‡ improve à¤•à¤°à¥‡à¤‚à¤—à¥‡à¥¤"
            ),
            "financial_analysis": (
                f"Financial discipline {scores.get('financial_discipline_index', 50)}/100 à¤¹à¥ˆà¥¤{income_phrase}"
                f"{risk_phrase} à¤…à¤­à¥€ à¤¸à¤¬à¤¸à¥‡ à¤‰à¤ªà¤¯à¥‹à¤—à¥€ à¤¬à¤¦à¤²à¤¾à¤µ à¤¯à¤¹ à¤¹à¥‹à¤—à¤¾ à¤•à¤¿ money decisions à¤•à¥‹ à¤…à¤§à¤¿à¤• structured à¤”à¤° à¤•à¤® reactive à¤¬à¤¨à¤¾à¤¯à¤¾ à¤œà¤¾à¤à¥¤"
            ),
        },
        "strategic_guidance": {
            "short_term": f"Short term à¤®à¥‡à¤‚ à¤ªà¤¹à¤²à¥‡ {weakest_label.lower()} à¤•à¥‹ stabilize à¤•à¤°à¥‡à¤‚ à¤”à¤° focus à¤•à¥‹ {focus_label} à¤ªà¤° centered à¤°à¤–à¥‡à¤‚à¥¤",
            "mid_term": f"Mid term à¤®à¥‡à¤‚ {strongest_label.lower()} à¤•à¥‹ repeatable weekly system à¤®à¥‡à¤‚ convert à¤•à¤°à¥‡à¤‚, à¤–à¤¾à¤¸à¤•à¤° work à¤”à¤° finance decisions à¤®à¥‡à¤‚à¥¤",
            "long_term": f"Life Path {life_path or 'N/A'} à¤•à¥‹ bigger moves à¤•à¥‡ guide à¤•à¥€ à¤¤à¤°à¤¹ use à¤•à¤°à¥‡à¤‚ à¤”à¤° scale à¤¤à¤­à¥€ à¤•à¤°à¥‡à¤‚ à¤œà¤¬ {weakest_label.lower()} recurring bottleneck à¤¨ à¤°à¤¹à¥‡à¥¤",
        },
        "growth_blueprint": {
            "phase_1": f"Noise à¤•à¤® à¤•à¤°à¤•à¥‡ {problem_statement} à¤•à¥‡ à¤†à¤¸à¤ªà¤¾à¤¸ stable base create à¤•à¤°à¥‡à¤‚à¥¤",
            "phase_2": f"{strongest_label.lower()} à¤•à¥‹ consistency, better filters, à¤”à¤° cleaner routines à¤¸à¥‡ visible advantage à¤¬à¤¨à¤¾à¤à¤‚à¥¤",
            "phase_3": f"Bigger opportunities à¤®à¥‡à¤‚ à¤¤à¤­à¥€ expand à¤•à¤°à¥‡à¤‚ à¤œà¤¬ {focus_label} stronger execution discipline à¤¸à¥‡ support à¤¹à¥‹à¥¤",
        },
        "business_block": {
            "business_strength": business_strength,
            "risk_factor": business_risk,
            "compatible_industries": compatible_industries,
        },
        "compatibility_block": {
            "compatible_numbers": compatible_numbers,
            "challenging_numbers": challenging_numbers,
            "relationship_guidance": compatibility_guidance,
        },
    }


# =====================================================
# INPUT FLATTENER
# =====================================================


def _reduce_number(value: int) -> int:
    while value > 9 and value not in (11, 22, 33):
        value = sum(int(char) for char in str(value))
    return value


def _derive_mulank(date_of_birth: str) -> int:
    text = str(date_of_birth or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return _reduce_number(parsed.day)
        except ValueError:
            continue
    return 0


def _derive_personal_year(date_of_birth: str) -> int:
    text = str(date_of_birth or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            total = parsed.day + parsed.month + sum(int(char) for char in str(datetime.now(UTC).year))
            return _reduce_number(total)
        except ValueError:
            continue
    return 0


def _extract_loshu_signals(numerology_core: Dict[str, Any]) -> Dict[str, Any]:
    loshu = (numerology_core or {}).get("loshu_grid") or {}
    grid_counts = loshu.get("grid_counts") if isinstance(loshu, dict) else {}
    if not isinstance(grid_counts, dict):
        grid_counts = {}

    present_digits = []
    missing_digits = []
    repeating_digits: Dict[int, int] = {}
    for digit in range(1, 10):
        raw_count = grid_counts.get(str(digit), grid_counts.get(digit, 0))
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            present_digits.append(digit)
            if count > 1:
                repeating_digits[digit] = count
        else:
            missing_digits.append(digit)

    explicit_missing = loshu.get("missing_numbers") if isinstance(loshu, dict) else None
    if isinstance(explicit_missing, list) and explicit_missing:
        normalized_missing = []
        for item in explicit_missing:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= number <= 9:
                normalized_missing.append(number)
        if normalized_missing:
            missing_digits = sorted(set(normalized_missing))
            present_digits = [digit for digit in range(1, 10) if digit not in missing_digits]

    return {
        "lo_shu_present_digits": present_digits,
        "lo_shu_missing_digits": missing_digits,
        "repeating_digits": repeating_digits,
    }


def flatten_input(
    data: Dict[str, Any],
    *,
    numerology_core: Dict[str, Any] | None = None,
    intake_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:

    data = data or {}
    numerology_core = numerology_core or {}
    intake_context = intake_context or {}

    financial = data.get("financial") or {}
    career = data.get("career") or {}
    emotional = data.get("emotional") or {}
    focus = data.get("focus") or {}
    life_events = data.get("life_events") or {}
    calibration = data.get("calibration") or {}
    identity = intake_context.get("identity") or data.get("identity") or {}
    birth_details = intake_context.get("birth_details") or data.get("birth_details") or {}
    contact = intake_context.get("contact") or data.get("contact") or {}

    date_of_birth = birth_details.get("date_of_birth") or identity.get("date_of_birth")
    pyth = numerology_core.get("pythagorean") or {}
    chaldean = numerology_core.get("chaldean") or {}
    mobile_analysis = numerology_core.get("mobile_analysis") or {}
    email_analysis = numerology_core.get("email_analysis") or {}
    loshu_signals = _extract_loshu_signals(numerology_core)

    mulank = _derive_mulank(date_of_birth)
    bhagyank = pyth.get("life_path_number")
    personal_year = _derive_personal_year(date_of_birth)

    decision_confusion = emotional.get("decision_confusion")
    impulse_control = emotional.get("impulse_control")

    decision_clarity = None
    if decision_confusion is not None:
        decision_clarity = max(1, min(10, 11 - int(decision_confusion)))

    impulse_spending = None
    if impulse_control is not None:
        impulse_spending = max(1, min(10, 11 - int(impulse_control)))

    setbacks = life_events.get("setback_events_years")
    major_setbacks = len(setbacks) if isinstance(setbacks, list) else None

    return {
        "full_name": identity.get("full_name"),
        "date_of_birth": date_of_birth,
        "gender": identity.get("gender"),
        "birthplace_city": birth_details.get("birthplace_city"),
        "mobile_number": contact.get("mobile_number") or identity.get("mobile_number"),
        "email": identity.get("email"),
        "current_problem": data.get("current_problem"),

        "monthly_income": financial.get("monthly_income"),
        "savings_ratio": financial.get("savings_ratio"),
        "debt_ratio": financial.get("debt_ratio"),
        "risk_tolerance": financial.get("risk_tolerance"),
        "impulse_spending": impulse_spending,

        "industry": career.get("industry"),
        "role": career.get("role"),
        "years_experience": career.get("years_experience"),
        "stress_level": career.get("stress_level"),

        "anxiety": emotional.get("anxiety_level"),
        "decision_confusion": decision_confusion,
        "decision_clarity": decision_clarity,
        "impulse_control": impulse_control,
        "emotional_stability": emotional.get("emotional_stability"),

        "life_focus": focus.get("life_focus"),
        "major_setbacks": major_setbacks,

        "stress_response": calibration.get("stress_response"),
        "money_decision_style": calibration.get("money_decision_style"),
        "biggest_weakness": calibration.get("biggest_weakness"),
        "life_preference": calibration.get("life_preference"),
        "decision_style": calibration.get("decision_style"),

        "mulank": mulank,
        "bhagyank": bhagyank,
        "life_path_number": bhagyank,
        "destiny_number": pyth.get("destiny_number"),
        "expression_number": pyth.get("expression_number"),
        "name_number": chaldean.get("name_number"),
        "personal_year": personal_year,
        "mobile_vibration": mobile_analysis.get("mobile_vibration") or mobile_analysis.get("mobile_number_vibration"),
        "email_vibration": email_analysis.get("email_number"),
        "lo_shu_present_digits": loshu_signals["lo_shu_present_digits"],
        "lo_shu_missing_digits": loshu_signals["lo_shu_missing_digits"],
        "repeating_digits": loshu_signals["repeating_digits"],
    }


# =====================================================
# AI QUALITY + MERGE HELPERS
# =====================================================


def _looks_usable_text(value: Any) -> bool:
    text = " ".join(str(value or "").split())
    if len(text) < 24:
        return False
    if any(token in text for token in ("{", "}", "ÃƒÂ Ã‚Â¤", "ÃƒÂ Ã‚Â¥", "Ã Â¤", "Ã Â¥", "ï¿½", "[]")):
        return False
    if re.search(r"(,\s*,)|(à¥¤\s*à¥¤)|(^[-,:;|]+$)", text):
        return False
    return True


def _merge_narrative(base: Any, override: Any) -> Any:
    if isinstance(base, dict):
        merged = dict(base)
        override = override if isinstance(override, dict) else {}
        for key, value in merged.items():
            merged[key] = _merge_narrative(value, override.get(key))
        for key, value in override.items():
            if key not in merged:
                if isinstance(value, str) and _looks_usable_text(value):
                    merged[key] = value
                elif isinstance(value, list) and value:
                    merged[key] = value
                elif isinstance(value, dict):
                    merged[key] = value
        return merged

    if isinstance(base, list):
        if isinstance(override, list) and override:
            cleaned = [item for item in override if not isinstance(item, str) or _looks_usable_text(item)]
            if cleaned:
                return cleaned
        return base

    if isinstance(base, str):
        if isinstance(override, str) and _looks_usable_text(override):
            return override
        return base

    return override if override not in (None, "", [], {}) else base


# =====================================================
# SAFE AI WRAPPER
# Guarantees structure even if LLM fails
# =====================================================


def safe_generate_ai_narrative(
    numerology_core,
    scores,
    current_problem,
    plan_name,
    token_multiplier,
    intake_context,
    interpretation_draft,
):
    baseline = interpretation_draft or _build_personalized_fallback(
        intake_context=intake_context,
        numerology_core=numerology_core,
        scores=scores,
        current_problem=current_problem,
    )

    try:
        ai_sections = generate_ai_narrative(
            numerology_core=numerology_core,
            scores=scores,
            current_problem=current_problem,
            plan_name=plan_name,
            token_multiplier=token_multiplier,
            intake_context=intake_context,
            interpretation_draft=baseline,
        )
        if isinstance(ai_sections, dict) and ai_sections:
            merged = _merge_narrative(baseline, ai_sections)
            merged["_fallback_used"] = False
            return merged
        raise ValueError("AI returned invalid structure")
    except Exception:
        traceback.print_exc()
        baseline["_fallback_used"] = True
        return baseline


# =====================================================
# MASTER REPORT GENERATOR
# =====================================================


def generate_life_signify_report(
    request_data: Dict[str, Any],
    plan_name: str = "basic",
) -> Dict[str, Any]:

    plan_name = (plan_name or "basic").lower()

    features = PLAN_FEATURES.get(plan_name, PLAN_FEATURES["basic"])

    intake_context = _build_intake_context(request_data)
    identity = intake_context.get("identity") or {}
    birth_details = intake_context.get("birth_details") or {}
    current_problem = intake_context.get("current_problem")

    # -------------------------------------------------
    # NUMEROLOGY CORE ENGINE
    # -------------------------------------------------

    numerology_core = generate_numerology_profile(
        identity=identity,
        birth_details=birth_details,
        plan_name=plan_name,
    ) or {}

    # -------------------------------------------------
    # BUSINESS NUMBER ENGINE
    # -------------------------------------------------

    try:
        business_signals = analyze_business_name(
            identity.get("business_name")
        )
    except Exception:
        traceback.print_exc()
        business_signals = {}

    numerology_core["business_analysis"] = business_signals

    # -------------------------------------------------
    # BEHAVIORAL SCORING ENGINE
    # -------------------------------------------------

    flat_data = flatten_input(
        request_data,
        numerology_core=numerology_core,
        intake_context=intake_context,
    )

    scores = generate_score_summary(flat_data, plan_name=plan_name) or {}

    # -------------------------------------------------
    # ARCHETYPE ENGINE
    # -------------------------------------------------

    archetype = generate_numerology_archetype(
        numerology_core,
        scores
    )

    # -------------------------------------------------
    # REMEDY ENGINE
    # -------------------------------------------------

    remedies = generate_remedy_protocol(
        numerology_core,
        scores=scores,
    )

    # -------------------------------------------------
    # INTERPRETATION ENGINE
    # -------------------------------------------------

    interpretation_draft = build_interpretation_report(
        intake_context=intake_context,
        numerology_core=numerology_core,
        scores=scores,
        archetype=archetype,
        remedies=remedies,
        plan_name=plan_name,
    )

    # -------------------------------------------------
    # AI NARRATIVE
    # -------------------------------------------------

    ai_sections = safe_generate_ai_narrative(
        numerology_core=numerology_core,
        scores=scores,
        current_problem=current_problem,
        plan_name=plan_name,
        token_multiplier=features["token_multiplier"],
        intake_context=intake_context,
        interpretation_draft=interpretation_draft,
    )

    # -------------------------------------------------
    # RADAR CHART DATA
    # -------------------------------------------------

    radar_chart_data = {
        "Life Stability": scores.get("life_stability_index", 50),
        "Decision Clarity": scores.get("confidence_score", 50),
        "Dharma Alignment": scores.get("dharma_alignment_score", 50),
        "Emotional Regulation": scores.get("emotional_regulation_index", 50),
        "Financial Discipline": scores.get("financial_discipline_index", 50),
        "Karma Pressure": scores.get("karma_pressure_index", 50),
    }

    # -------------------------------------------------
    # FINAL REPORT JSON
    # -------------------------------------------------

    report_output = {

        "meta": {
            "report_version": "6.0",
            "engine_version": settings.ENGINE_VERSION,
            "plan_tier": plan_name,
            "generated_at": datetime.now(UTC).isoformat(),
            "used_fallback_narrative": ai_sections.get("_fallback_used", False),
        },

        "identity": identity,

        "birth_details": birth_details,

        "focus": intake_context.get("focus") or {},

        "preferences": intake_context.get("preferences") or {},

        "current_problem": current_problem,

        "core_metrics": scores,

        "metric_explanations": ai_sections.get("metric_explanations"),

        "metrics_spine": ai_sections.get("metrics_spine"),

        "numerology_core": numerology_core,

        "executive_brief": ai_sections.get("executive_brief"),

        "analysis_sections": ai_sections.get("analysis_sections"),

        "primary_insight": ai_sections.get("primary_insight"),

        "numerology_architecture": ai_sections.get("numerology_architecture"),

        "archetype_intelligence": ai_sections.get("archetype_intelligence"),

        "loshu_diagnostic": ai_sections.get("loshu_diagnostic"),

        "planetary_mapping": ai_sections.get("planetary_mapping"),

        "structural_deficit_model": ai_sections.get("structural_deficit_model"),

        "circadian_alignment": ai_sections.get("circadian_alignment"),

        "environment_alignment": ai_sections.get("environment_alignment"),

        "vedic_remedy_protocol": ai_sections.get("vedic_remedy_protocol"),

        "execution_plan": ai_sections.get("execution_plan"),

        "strategic_guidance": ai_sections.get("strategic_guidance"),

        "growth_blueprint": ai_sections.get("growth_blueprint"),

        "personal_year_forecast": ai_sections.get("personal_year_forecast"),

        "name_vibration_optimization": ai_sections.get("name_vibration_optimization"),

        "mobile_number_intelligence": ai_sections.get("mobile_number_intelligence"),

        "email_identity_intelligence": ai_sections.get("email_identity_intelligence"),

        "signature_intelligence": ai_sections.get("signature_intelligence"),

        "business_name_intelligence": ai_sections.get("business_name_intelligence"),

        "brand_handle_optimization": ai_sections.get("brand_handle_optimization"),

        "residence_energy_intelligence": ai_sections.get("residence_energy_intelligence"),

        "vehicle_number_intelligence": ai_sections.get("vehicle_number_intelligence"),

        "correction_protocol_summary": ai_sections.get("correction_protocol_summary"),

        "karmic_pattern_intelligence": ai_sections.get("karmic_pattern_intelligence"),

        "hidden_talent_intelligence": ai_sections.get("hidden_talent_intelligence"),

        "pinnacle_challenge_cycle_intelligence": ai_sections.get("pinnacle_challenge_cycle_intelligence"),

        "life_cycle_timeline": ai_sections.get("life_cycle_timeline"),

        "strategic_timing_intelligence": ai_sections.get("strategic_timing_intelligence"),

        "wealth_energy_blueprint": ai_sections.get("wealth_energy_blueprint"),

        "leadership_intelligence": ai_sections.get("leadership_intelligence"),

        "decision_intelligence": ai_sections.get("decision_intelligence"),

        "emotional_intelligence": ai_sections.get("emotional_intelligence"),

        "digital_discipline": ai_sections.get("digital_discipline"),

        "lifestyle_alignment": ai_sections.get("lifestyle_alignment"),

        "vedic_remedy": ai_sections.get("vedic_remedy"),

        "closing_synthesis": ai_sections.get("closing_synthesis"),

        "business_block": ai_sections.get("business_block"),

        "compatibility_block": ai_sections.get("compatibility_block"),

        "radar_chart_data": radar_chart_data,

        "lifestyle_remedies": remedies.get("lifestyle_remedies"),

        "mobile_remedies": remedies.get("mobile_remedies"),

        "vedic_remedies": remedies.get("vedic_remedies"),

        "daily_energy_alignment": remedies.get("daily_energy_alignment"),

        "numerology_archetype": archetype,

        "section_payloads": ai_sections.get("section_payloads"),

        "disclaimer": {
            "framework": "Tiered Numerology Intelligence System",
            "confidence_score": scores.get("data_completeness_score", 0),
            "note": "Insights are probabilistic and strategic, not deterministic predictions.",
        },
    }

    return report_output






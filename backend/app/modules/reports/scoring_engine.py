"""
LIFE SIGNIFY NUMAI
Dynamic Numerology + Intake Scoring Engine
"""

from __future__ import annotations

from datetime import datetime
from app.core.time_utils import UTC
from typing import Any, Dict, List, Sequence


# ==========================================================
# CORE UTILITIES
# ==========================================================


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalize(value: Any, min_val: float, max_val: float) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if max_val == min_val:
        return None
    clipped = max(min_val, min(max_val, numeric))
    return (clipped - min_val) / (max_val - min_val)


def _inverse_normalize(value: Any, min_val: float, max_val: float) -> float | None:
    normalized = normalize(value, min_val, max_val)
    if normalized is None:
        return None
    return 1.0 - normalized


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_digit_list(value: Any) -> List[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        output: List[int] = []
        for item in value:
            item_int = _safe_int(item, 0)
            if 1 <= item_int <= 9:
                output.append(item_int)
        return sorted(set(output))
    if isinstance(value, str):
        values = []
        for token in value.replace(",", " ").split():
            token_int = _safe_int(token, 0)
            if 1 <= token_int <= 9:
                values.append(token_int)
        return sorted(set(values))
    return []


def _reduce_number(num: int) -> int:
    while num > 9 and num not in (11, 22, 33):
        num = sum(int(char) for char in str(num))
    return num


def _personal_year(date_of_birth: Any) -> int:
    text = str(date_of_birth or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            total = sum(int(ch) for ch in f"{dt.day:02d}{dt.month:02d}{datetime.now(UTC).year}")
            return _reduce_number(total)
        except ValueError:
            continue
    return 0


def weighted_score(components: Sequence[Dict[str, float | None]], fallback: float) -> int:
    valid = [item for item in components if item.get("value") is not None and item.get("weight")]
    if not valid:
        return int(round(_clamp(fallback) * 100))

    weighted_total = sum(float(item["value"]) * float(item["weight"]) for item in valid)
    total_weight = sum(float(item["weight"]) for item in valid)
    if total_weight <= 0:
        return int(round(_clamp(fallback) * 100))
    return int(round(_clamp(weighted_total / total_weight) * 100))


# ==========================================================
# NUMEROLOGY FEATURE EXTRACTION
# ==========================================================


NUMBER_ARCHETYPE: Dict[int, Dict[str, float]] = {
    1: {"stability": 0.68, "financial": 0.66, "emotional": 0.52, "dharma": 0.72, "clarity": 0.80},
    2: {"stability": 0.58, "financial": 0.52, "emotional": 0.70, "dharma": 0.62, "clarity": 0.56},
    3: {"stability": 0.54, "financial": 0.50, "emotional": 0.60, "dharma": 0.60, "clarity": 0.64},
    4: {"stability": 0.76, "financial": 0.78, "emotional": 0.50, "dharma": 0.66, "clarity": 0.72},
    5: {"stability": 0.52, "financial": 0.54, "emotional": 0.56, "dharma": 0.58, "clarity": 0.70},
    6: {"stability": 0.70, "financial": 0.64, "emotional": 0.76, "dharma": 0.72, "clarity": 0.62},
    7: {"stability": 0.60, "financial": 0.58, "emotional": 0.54, "dharma": 0.76, "clarity": 0.66},
    8: {"stability": 0.74, "financial": 0.80, "emotional": 0.46, "dharma": 0.70, "clarity": 0.74},
    9: {"stability": 0.62, "financial": 0.60, "emotional": 0.64, "dharma": 0.74, "clarity": 0.68},
    11: {"stability": 0.66, "financial": 0.62, "emotional": 0.72, "dharma": 0.82, "clarity": 0.74},
    22: {"stability": 0.80, "financial": 0.82, "emotional": 0.52, "dharma": 0.84, "clarity": 0.76},
    33: {"stability": 0.70, "financial": 0.64, "emotional": 0.80, "dharma": 0.86, "clarity": 0.68},
}

PERSONAL_YEAR_ENERGY: Dict[int, Dict[str, float]] = {
    1: {"stability": 0.62, "clarity": 0.76, "dharma": 0.72, "pressure": 0.46},
    2: {"stability": 0.66, "clarity": 0.58, "dharma": 0.62, "pressure": 0.42},
    3: {"stability": 0.56, "clarity": 0.66, "dharma": 0.60, "pressure": 0.48},
    4: {"stability": 0.74, "clarity": 0.72, "dharma": 0.64, "pressure": 0.58},
    5: {"stability": 0.52, "clarity": 0.62, "dharma": 0.58, "pressure": 0.54},
    6: {"stability": 0.70, "clarity": 0.60, "dharma": 0.72, "pressure": 0.44},
    7: {"stability": 0.58, "clarity": 0.56, "dharma": 0.76, "pressure": 0.52},
    8: {"stability": 0.68, "clarity": 0.70, "dharma": 0.66, "pressure": 0.64},
    9: {"stability": 0.60, "clarity": 0.64, "dharma": 0.74, "pressure": 0.56},
    11: {"stability": 0.68, "clarity": 0.70, "dharma": 0.82, "pressure": 0.50},
    22: {"stability": 0.76, "clarity": 0.74, "dharma": 0.84, "pressure": 0.60},
}

RISK_TOLERANCE_DISCIPLINE: Dict[str, float] = {"low": 0.78, "moderate": 0.64, "high": 0.48}

STRESS_RESPONSE_REGULATION: Dict[str, float] = {
    "take_control": 0.72,
    "withdraw": 0.58,
    "overthink": 0.50,
    "impulsive": 0.42,
}


def _harmony_score(numbers: Sequence[int]) -> float:
    valid = [value for value in numbers if value > 0]
    if len(valid) < 2:
        return 0.58
    gaps: List[float] = []
    for idx, left in enumerate(valid):
        for right in valid[idx + 1 :]:
            gaps.append(abs(left - right) / 8.0)
    avg_gap = sum(gaps) / len(gaps)
    exact_matches = sum(1 for idx, left in enumerate(valid) for right in valid[idx + 1 :] if left == right)
    match_bonus = min(0.12, exact_matches * 0.04)
    return _clamp((1.0 - avg_gap) + match_bonus)


def _archetype_signal(numbers: Sequence[int], key: str, default: float) -> float:
    values = [NUMBER_ARCHETYPE.get(number, {}).get(key) for number in numbers if NUMBER_ARCHETYPE.get(number, {}).get(key) is not None]
    if not values:
        return default
    return _clamp(sum(values) / len(values))


def _compatibility_strength(value: int, anchor: int) -> float | None:
    if value <= 0 or anchor <= 0:
        return None
    return _clamp(1.0 - (abs(value - anchor) / 8.0))


def _build_profile_features(data: Dict[str, Any]) -> Dict[str, Any]:
    mulank = _safe_int(data.get("mulank"), 0)
    bhagyank = _safe_int(data.get("bhagyank"), 0)
    destiny = _safe_int(data.get("destiny_number"), 0)
    expression = _safe_int(data.get("expression_number"), destiny)
    name_number = _safe_int(data.get("name_number"), 0)
    life_path = _safe_int(data.get("life_path_number"), bhagyank or mulank)
    personal_year = _safe_int(data.get("personal_year"), 0) or _personal_year(data.get("date_of_birth"))

    core_numbers = [value for value in [mulank, bhagyank, destiny, expression, name_number] if value > 0]
    harmony = _harmony_score(core_numbers)

    missing_digits = _as_digit_list(data.get("lo_shu_missing_digits"))
    present_digits = _as_digit_list(data.get("lo_shu_present_digits"))
    if not missing_digits and present_digits:
        missing_digits = [digit for digit in range(1, 10) if digit not in set(present_digits)]
    if not present_digits and missing_digits:
        present_digits = [digit for digit in range(1, 10) if digit not in set(missing_digits)]

    repeating_raw = data.get("repeating_digits")
    repeating_count = 0
    repeating_impulse = 0
    repeating_emotional = 0
    repeating_mental = 0

    if isinstance(repeating_raw, dict):
        for key, value in repeating_raw.items():
            digit = _safe_int(key, 0)
            count = max(0, _safe_int(value, 0))
            if count <= 1:
                continue
            extra = count - 1
            repeating_count += extra
            if digit in {3, 5, 8, 9}:
                repeating_impulse += extra
            if digit in {2, 6}:
                repeating_emotional += extra
            if digit in {1, 7}:
                repeating_mental += extra
    elif isinstance(repeating_raw, (list, tuple, set)):
        repeating_count = len(list(repeating_raw))
        repeating_impulse = sum(1 for item in repeating_raw if _safe_int(item, 0) in {3, 5, 8, 9})
        repeating_emotional = sum(1 for item in repeating_raw if _safe_int(item, 0) in {2, 6})
        repeating_mental = sum(1 for item in repeating_raw if _safe_int(item, 0) in {1, 7})

    lo_shu_balance = _clamp((9 - len(set(missing_digits))) / 9.0)
    structural_balance = _clamp(1.0 - (len({4, 8}.intersection(set(missing_digits))) / 2.0))
    emotional_balance = _clamp(1.0 - (len({2, 6}.intersection(set(missing_digits))) / 2.0))
    mental_balance = _clamp(len({1, 3, 7}.intersection(set(present_digits))) / 3.0)

    concern_text = str(data.get("current_problem") or "").lower()
    finance_concern = 1.0 if any(token in concern_text for token in ("finance", "money", "debt", "income", "loan", "cash")) else 0.0
    emotion_concern = 1.0 if any(token in concern_text for token in ("emotion", "stress", "anxiety", "relationship", "mental")) else 0.0
    decision_concern = 1.0 if any(token in concern_text for token in ("decision", "confusion", "clarity", "career", "study")) else 0.0

    year_energy = PERSONAL_YEAR_ENERGY.get(personal_year, {"stability": 0.60, "clarity": 0.62, "dharma": 0.64, "pressure": 0.52})
    mobile_vibration = _safe_int(data.get("mobile_vibration"), 0)
    email_vibration = _safe_int(data.get("email_vibration"), 0)
    anchor_number = life_path or bhagyank or mulank or destiny

    return {
        "mulank": mulank,
        "bhagyank": bhagyank or life_path,
        "destiny": destiny,
        "expression": expression,
        "name_number": name_number,
        "life_path": life_path or bhagyank,
        "personal_year": personal_year,
        "harmony": harmony,
        "lo_shu_balance": lo_shu_balance,
        "structural_balance": structural_balance,
        "emotional_balance": emotional_balance,
        "mental_balance": mental_balance,
        "missing_count": len(set(missing_digits)),
        "repeating_count": repeating_count,
        "repeating_impulse": repeating_impulse,
        "repeating_emotional": repeating_emotional,
        "repeating_mental": repeating_mental,
        "archetype_stability": _archetype_signal(core_numbers, "stability", 0.58),
        "archetype_financial": _archetype_signal(core_numbers, "financial", 0.56),
        "archetype_emotional": _archetype_signal(core_numbers, "emotional", 0.58),
        "archetype_dharma": _archetype_signal(core_numbers, "dharma", 0.62),
        "archetype_clarity": _archetype_signal(core_numbers, "clarity", 0.60),
        "year_stability": year_energy["stability"],
        "year_clarity": year_energy["clarity"],
        "year_dharma": year_energy["dharma"],
        "year_pressure": year_energy["pressure"],
        "mobile_alignment": _compatibility_strength(mobile_vibration, anchor_number),
        "email_alignment": _compatibility_strength(email_vibration, name_number or anchor_number),
        "finance_concern": finance_concern,
        "emotion_concern": emotion_concern,
        "decision_concern": decision_concern,
    }


# ==========================================================
# METRIC SCORERS
# ==========================================================


def life_stability_index(data: Dict[str, Any], profile: Dict[str, Any]) -> int:
    components = [
        {"value": normalize(data.get("emotional_stability"), 1, 10), "weight": 0.12},
        {"value": _inverse_normalize(data.get("stress_level"), 1, 10), "weight": 0.10},
        {"value": _inverse_normalize(data.get("debt_ratio"), 0, 100), "weight": 0.07},
        {"value": normalize(data.get("savings_ratio"), 0, 100), "weight": 0.06},
        {"value": _inverse_normalize(data.get("major_setbacks"), 0, 6), "weight": 0.06},
        {"value": profile["lo_shu_balance"], "weight": 0.22},
        {"value": profile["harmony"], "weight": 0.14},
        {"value": profile["archetype_stability"], "weight": 0.12},
        {"value": profile["year_stability"], "weight": 0.08},
        {"value": 1.0 - _clamp(profile["repeating_count"] / 8.0), "weight": 0.07},
        {"value": profile["mobile_alignment"], "weight": 0.04},
        {"value": profile["email_alignment"], "weight": 0.03},
    ]
    return weighted_score(components, fallback=profile["archetype_stability"])


def emotional_regulation_index(data: Dict[str, Any], profile: Dict[str, Any]) -> int:
    stress_response = str(data.get("stress_response") or "").strip().lower()
    components = [
        {"value": _inverse_normalize(data.get("anxiety"), 1, 10), "weight": 0.18},
        {"value": normalize(data.get("impulse_control"), 1, 10), "weight": 0.12},
        {"value": _inverse_normalize(data.get("decision_confusion"), 1, 10), "weight": 0.11},
        {"value": normalize(data.get("emotional_stability"), 1, 10), "weight": 0.16},
        {"value": profile["archetype_emotional"], "weight": 0.14},
        {"value": profile["emotional_balance"], "weight": 0.11},
        {"value": 1.0 - _clamp(profile["repeating_emotional"] / 4.0), "weight": 0.08},
        {"value": 1.0 - _clamp(profile["emotion_concern"] * 0.35), "weight": 0.05},
        {"value": STRESS_RESPONSE_REGULATION.get(stress_response), "weight": 0.05},
        {"value": 1.0 - profile["year_pressure"], "weight": 0.04},
    ]
    return weighted_score(components, fallback=profile["archetype_emotional"])


def financial_discipline_index(data: Dict[str, Any], profile: Dict[str, Any]) -> int:
    risk_tolerance = str(data.get("risk_tolerance") or "").strip().lower()
    components = [
        {"value": normalize(data.get("savings_ratio"), 0, 100), "weight": 0.17},
        {"value": _inverse_normalize(data.get("debt_ratio"), 0, 100), "weight": 0.17},
        {"value": normalize(data.get("impulse_control"), 1, 10), "weight": 0.10},
        {"value": _inverse_normalize(data.get("impulse_spending"), 1, 10), "weight": 0.08},
        {"value": RISK_TOLERANCE_DISCIPLINE.get(risk_tolerance), "weight": 0.06},
        {"value": profile["archetype_financial"], "weight": 0.14},
        {"value": profile["structural_balance"], "weight": 0.13},
        {"value": 1.0 - _clamp(profile["repeating_impulse"] / 5.0), "weight": 0.08},
        {"value": profile["mobile_alignment"], "weight": 0.03},
        {"value": profile["email_alignment"], "weight": 0.02},
        {"value": 1.0 - _clamp(profile["finance_concern"] * 0.30), "weight": 0.02},
    ]
    return weighted_score(components, fallback=profile["archetype_financial"])


def compute_decision_clarity_score(data: Dict[str, Any], profile: Dict[str, Any]) -> int:
    components = [
        {"value": normalize(data.get("decision_clarity"), 1, 10), "weight": 0.20},
        {"value": _inverse_normalize(data.get("decision_confusion"), 1, 10), "weight": 0.15},
        {"value": _inverse_normalize(data.get("stress_level"), 1, 10), "weight": 0.12},
        {"value": normalize(data.get("impulse_control"), 1, 10), "weight": 0.10},
        {"value": normalize(data.get("emotional_stability"), 1, 10), "weight": 0.08},
        {"value": profile["archetype_clarity"], "weight": 0.13},
        {"value": profile["mental_balance"], "weight": 0.10},
        {"value": profile["harmony"], "weight": 0.06},
        {"value": profile["year_clarity"], "weight": 0.04},
        {"value": 1.0 - _clamp(profile["repeating_mental"] / 4.0), "weight": 0.02},
    ]
    return weighted_score(components, fallback=profile["archetype_clarity"])


def dharma_alignment_score(data: Dict[str, Any], profile: Dict[str, Any], emotional_score: int, decision_clarity: int) -> int:
    focus_signal = 0.84 if _present(data.get("life_focus")) else 0.48
    concern_alignment = 1.0 - _clamp((profile["decision_concern"] + profile["finance_concern"] + profile["emotion_concern"]) / 6.0)
    components = [
        {"value": profile["harmony"], "weight": 0.20},
        {"value": profile["year_dharma"], "weight": 0.16},
        {"value": profile["archetype_dharma"], "weight": 0.16},
        {"value": focus_signal, "weight": 0.10},
        {"value": profile["lo_shu_balance"], "weight": 0.10},
        {"value": emotional_score / 100.0, "weight": 0.12},
        {"value": decision_clarity / 100.0, "weight": 0.10},
        {"value": concern_alignment, "weight": 0.06},
    ]
    return weighted_score(components, fallback=profile["archetype_dharma"])


def karma_pressure_index(data: Dict[str, Any], profile: Dict[str, Any]) -> int:
    components = [
        {"value": normalize(data.get("anxiety"), 1, 10), "weight": 0.17},
        {"value": normalize(data.get("debt_ratio"), 0, 100), "weight": 0.14},
        {"value": normalize(data.get("stress_level"), 1, 10), "weight": 0.16},
        {"value": normalize(data.get("major_setbacks"), 0, 6), "weight": 0.13},
        {"value": _clamp(profile["missing_count"] / 9.0), "weight": 0.14},
        {"value": _clamp(profile["repeating_count"] / 8.0), "weight": 0.08},
        {"value": 1.0 - profile["harmony"], "weight": 0.10},
        {"value": profile["year_pressure"], "weight": 0.08},
    ]
    return weighted_score(components, fallback=_clamp(1.0 - profile["harmony"]))


# ==========================================================
# INPUT COMPLETENESS
# ==========================================================


def compute_data_completeness_score(data: Dict[str, Any], plan_name: str = "basic") -> int:
    plan = str(plan_name or "basic").strip().lower()

    base_fields = [
        "full_name",
        "date_of_birth",
        "gender",
        "birthplace_city",
        "mobile_number",
        "email",
        "current_problem",
        "life_focus",
    ]
    behavior_fields = [
        "savings_ratio",
        "debt_ratio",
        "risk_tolerance",
        "stress_level",
        "years_experience",
        "anxiety",
        "decision_confusion",
        "impulse_control",
        "emotional_stability",
        "stress_response",
        "money_decision_style",
        "biggest_weakness",
        "life_preference",
        "decision_style",
        "major_setbacks",
    ]

    required = {
        "basic": base_fields + behavior_fields[:8],
        "standard": base_fields + behavior_fields,
        "pro": base_fields + behavior_fields,
        "enterprise": base_fields + behavior_fields + ["monthly_income", "industry", "role", "impulse_spending"],
        "premium": base_fields + behavior_fields,
    }.get(plan, base_fields + behavior_fields[:8])

    filled = sum(1 for field in required if _present(data.get(field)))
    ratio = filled / len(required) if required else 0.0
    return int(round(ratio * 100))


# ==========================================================
# RISK BAND
# ==========================================================


def risk_band(*, life_stability: int, emotional: int, financial: int, dharma: int, confidence: int, karma_pressure: int) -> str:
    operating_health = (life_stability + emotional + financial + dharma + confidence) / 5.0

    if operating_health >= 72 and karma_pressure <= 42:
        return "Stable"
    if operating_health >= 50 and karma_pressure <= 66:
        return "Correctable"
    return "Critical"


# ==========================================================
# MASTER SCORING FUNCTION
# ==========================================================


def generate_score_summary(data: Dict[str, Any], plan_name: str = "basic") -> Dict[str, Any]:
    profile = _build_profile_features(data)

    emotional = emotional_regulation_index(data, profile)
    financial = financial_discipline_index(data, profile)
    stability = life_stability_index(data, profile)
    confidence = compute_decision_clarity_score(data, profile)
    dharma = dharma_alignment_score(data, profile, emotional_score=emotional, decision_clarity=confidence)
    karma = karma_pressure_index(data, profile)
    completeness = compute_data_completeness_score(data, plan_name=plan_name)

    metrics = {
        "life_stability_index": stability,
        "emotional_regulation_index": emotional,
        "financial_discipline_index": financial,
        "dharma_alignment_score": dharma,
        "karma_pressure_index": karma,
        "confidence_score": confidence,
        "data_completeness_score": completeness,
    }

    ranking = sorted(
        [
            ("life_stability_index", stability),
            ("emotional_regulation_index", emotional),
            ("financial_discipline_index", financial),
            ("dharma_alignment_score", dharma),
            ("confidence_score", confidence),
        ],
        key=lambda item: item[1],
    )
    weakest_metric, weakest_score = ranking[0]
    strongest_metric, strongest_score = ranking[-1]

    metrics["weakest_metric"] = weakest_metric
    metrics["weakest_metric_score"] = weakest_score
    metrics["strongest_metric"] = strongest_metric
    metrics["strongest_metric_score"] = strongest_score
    metrics["risk_band"] = risk_band(
        life_stability=stability,
        emotional=emotional,
        financial=financial,
        dharma=dharma,
        confidence=confidence,
        karma_pressure=karma,
    )
    return metrics


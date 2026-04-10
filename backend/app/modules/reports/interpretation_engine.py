from __future__ import annotations

from datetime import datetime
from app.core.time_utils import UTC
import re
from typing import Any, Dict, List, Sequence, Tuple

from app.modules.reports.blueprint import SECTION_TITLES, get_tier_section_blueprint

PLANET_BY_NUMBER: Dict[int, str] = {
    1: "Surya",
    2: "Chandra",
    3: "Guru",
    4: "Rahu",
    5: "Budh",
    6: "Shukra",
    7: "Ketu",
    8: "Shani",
    9: "Mangal",
    11: "Moon-Jupiter",
    22: "Rahu-Saturn",
}

NUMBER_TRAITS: Dict[int, Dict[str, str]] = {
    1: {"strength": "initiative and leadership", "risk": "over-control", "protocol": "lead with review loops"},
    2: {"strength": "diplomacy and empathy", "risk": "indecision", "protocol": "enforce decision windows"},
    3: {"strength": "communication and creativity", "risk": "scattered execution", "protocol": "convert ideas into weekly outputs"},
    4: {"strength": "discipline and structure", "risk": "rigidity", "protocol": "blend process with flexibility"},
    5: {"strength": "adaptability and speed", "risk": "restless switching", "protocol": "protect freedom inside routine"},
    6: {"strength": "responsibility and trust", "risk": "over-burdening", "protocol": "set role boundaries"},
    7: {"strength": "analysis and insight", "risk": "overthinking", "protocol": "convert insight to checkpoints"},
    8: {"strength": "authority and material strategy", "risk": "pressure intensity", "protocol": "scale with governance"},
    9: {"strength": "vision and influence", "risk": "energy leakage", "protocol": "prioritize and close loops"},
}

COMPOUND_MEANINGS: Dict[int, str] = {
    13: "karmic discipline debt",
    14: "karmic freedom debt",
    16: "karmic ego correction",
    19: "karmic independence debt",
    22: "master builder field",
    33: "master service field",
}

SECTION_META: Dict[str, Dict[str, Any]] = {
    "default": {
        "purpose": "à¤¯à¤¹ à¤¸à¥‡à¤•à¥à¤¶à¤¨ à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤• diagnosis à¤”à¤° correction protocol à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        "key_inputs": ["numerology_core", "core_metrics", "intake_context"],
        "output_fields": ["cards", "bullets", "narrative"],
        "interpretation_logic": "Structural signals à¤•à¥‹ behavior impact à¤”à¤° protocol à¤®à¥‡à¤‚ map à¤•à¤¿à¤¯à¤¾ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        "tone_guidance": "Executive, premium, à¤”à¤° consultation-grade tone à¤¬à¤¨à¤¾à¤ à¤°à¤–à¥‡à¤‚à¥¤",
    },
    "intelligence_metrics": {
        "purpose": "Strength, deficit, à¤”à¤° intervention focus à¤•à¥‹ measurable format à¤®à¥‡à¤‚ quantify à¤•à¤°à¥‡à¤‚à¥¤",
        "key_inputs": ["core_metrics", "loshu_grid", "behavioral_intake"],
        "output_fields": ["primary_strength", "primary_deficit", "structural_cause", "intervention_focus", "risk_band"],
        "interpretation_logic": "Metric stack rank à¤•à¤°à¤•à¥‡ à¤‰à¤¸à¥‡ structural signals à¤¸à¥‡ à¤œà¥‹à¤¡à¤¼à¤¾ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        "tone_guidance": "Diagnostic, concise, à¤”à¤° high-authority guidance à¤¦à¥‡à¤‚à¥¤",
    },
}


def _safe_text(value: Any, default: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", [], {})]
    if value in (None, "", [], {}):
        return []
    return [value]


def _reduce_number(value: int) -> int:
    while value > 9 and value not in {11, 22, 33}:
        value = sum(int(char) for char in str(value))
    return value


def _alpha_sum(value: str) -> int:
    cleaned = "".join(char for char in value.lower() if char.isalpha())
    return sum(ord(char) - 96 for char in cleaned)


def _vibration_from_text(value: str) -> int:
    total = _alpha_sum(value)
    return _reduce_number(total) if total > 0 else 0


def _vibration_from_digits(value: str) -> int:
    digits = [int(char) for char in str(value or "") if char.isdigit()]
    return _reduce_number(sum(digits)) if digits else 0


def _metric_labels() -> Dict[str, str]:
    return {
        "life_stability_index": "Life Stability",
        "confidence_score": "Decision Clarity",
        "dharma_alignment_score": "Dharma Alignment",
        "emotional_regulation_index": "Emotional Regulation",
        "financial_discipline_index": "Financial Discipline",
        "karma_pressure_index": "Karma Pressure",
    }


def _metric_order(scores: Dict[str, Any]) -> List[Tuple[str, int]]:
    keys = [
        "life_stability_index",
        "confidence_score",
        "dharma_alignment_score",
        "emotional_regulation_index",
        "financial_discipline_index",
        "karma_pressure_index",
    ]
    return [(key, _safe_int(scores.get(key), 50)) for key in keys]


def _metric_status(score: int) -> str:
    if score >= 75:
        return "Strong"
    if score >= 55:
        return "Moderate"
    return "Sensitive"


def _risk_band(scores: Dict[str, Any]) -> str:
    confidence = _safe_int(scores.get("confidence_score"), 50)
    stability = _safe_int(scores.get("life_stability_index"), 50)
    emotional = _safe_int(scores.get("emotional_regulation_index"), 50)
    finance = _safe_int(scores.get("financial_discipline_index"), 50)
    karma = _safe_int(scores.get("karma_pressure_index"), 50)
    weakest = min(confidence, stability, emotional, finance)
    if karma >= 75 or weakest <= 35:
        return "High Risk | Structural Intervention Required"
    if karma >= 60 or weakest <= 49:
        return "Watch Zone | Guided Stabilization Required"
    if weakest >= 70 and karma <= 45:
        return "Strategic Growth Zone | Scale with Governance"
    return "Correctable Zone | Protocol-Driven Improvement"


def _dominant_planet(life_path: int, destiny: int, name_number: int) -> str:
    primary = life_path or destiny or name_number or 5
    return PLANET_BY_NUMBER.get(primary, "Budh")


def _parse_date(value: str) -> Tuple[int, int, int]:
    text = _safe_text(value)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(text, fmt)
            return (dt.day, dt.month, dt.year)
        except ValueError:
            continue
    return (1, 1, 2000)


def _personal_year(day: int, month: int) -> int:
    total = sum(int(char) for char in f"{day:02d}{month:02d}{datetime.now(UTC).year}")
    return _reduce_number(total)


def _lucky_dates(day: int, month: int, life_path: int, destiny: int) -> List[int]:
    anchors = {life_path, destiny, _reduce_number(day), _reduce_number(month)}
    anchors.discard(0)
    dates = sorted(value for value in anchors if value <= 31)
    return dates[:5] or [3, 5, 9]


def _karmic_numbers(day: int, name_compound: int, business_compound: int) -> List[int]:
    values = [day, name_compound, business_compound]
    return sorted(set(value for value in values if value in {13, 14, 16, 19}))


def _hidden_passion(loshu_grid: Dict[str, Any], full_name: str) -> Tuple[int, str]:
    counts = loshu_grid.get("grid_counts") if isinstance(loshu_grid, dict) else {}
    if isinstance(counts, dict) and counts:
        best_number = max(range(1, 10), key=lambda number: _safe_int(counts.get(str(number), counts.get(number, 0)), 0))
        return best_number, NUMBER_TRAITS.get(best_number, NUMBER_TRAITS[5])["strength"]
    vibration = _vibration_from_text(full_name) or 5
    return vibration, NUMBER_TRAITS.get(vibration, NUMBER_TRAITS[5])["strength"]


def _pinnacle_challenge(day: int, month: int, year: int) -> Dict[str, List[int]]:
    year_sum = _reduce_number(sum(int(char) for char in str(year)))
    day_root = _reduce_number(day)
    month_root = _reduce_number(month)
    p1 = _reduce_number(day_root + month_root)
    p2 = _reduce_number(day_root + year_sum)
    p3 = _reduce_number(p1 + p2)
    c1 = abs(day_root - month_root)
    c2 = abs(day_root - year_sum)
    c3 = abs(c1 - c2)
    return {"pinnacles": [p1, p2, p3], "challenges": [c1, c2, c3]}

def _name_options(full_name: str, target_numbers: Sequence[int]) -> List[Dict[str, Any]]:
    base = _safe_text(full_name)
    if not base:
        return []
    variants = [base, f"{base}a", f"{base}h", f"{base}aa", f"{base}y", f"{base}i"]
    options: List[Dict[str, Any]] = []
    seen = set()
    for variant in variants:
        key = variant.lower()
        if key in seen:
            continue
        seen.add(key)
        number = _vibration_from_text(variant)
        if number <= 0:
            continue
        if target_numbers and number not in target_numbers:
            continue
        options.append({"option": variant, "number": number, "logic": "aligns with target vibration"})
    return options[:3]


def _handle_patterns(base: str, target_numbers: Sequence[int]) -> List[str]:
    cleaned = "".join(char for char in base.lower() if char.isalnum()) or "strategicprofile"
    patterns: List[str] = []
    for number in target_numbers[:3] or [1, 3, 5]:
        patterns.append(f"{cleaned}.{number}")
        patterns.append(f"{cleaned}_{number}x")
    deduped: List[str] = []
    for item in patterns:
        if item not in deduped:
            deduped.append(item)
    return deduped[:4]


def _compound_meaning(value: int) -> str:
    return COMPOUND_MEANINGS.get(value, "composite growth-pressure cycle")


BASIC_NUMBER_MEANINGS: Dict[int, Dict[str, str]] = {
    1: {"signal": "leadership à¤”à¤° à¤†à¤°à¤‚à¤­", "risk": "à¤œà¤²à¥à¤¦à¤¬à¤¾à¤œà¤¼ à¤¨à¤¿à¤¯à¤‚à¤¤à¥à¤°à¤£"},
    2: {"signal": "à¤¸à¤¹à¤¯à¥‹à¤— à¤”à¤° à¤¸à¤‚à¤µà¥‡à¤¦à¤¨à¤¶à¥€à¤²à¤¤à¤¾", "risk": "à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤®à¥‡à¤‚ à¤¦à¥‡à¤°à¥€"},
    3: {"signal": "à¤…à¤­à¤¿à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤”à¤° à¤°à¤šà¤¨à¤¾à¤¤à¥à¤®à¤•à¤¤à¤¾", "risk": "à¤¬à¤¿à¤–à¤°à¤¾ à¤«à¥‹à¤•à¤¸"},
    4: {"signal": "à¤¸à¤‚à¤°à¤šà¤¨à¤¾ à¤”à¤° à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨", "risk": "à¤•à¤ à¥‹à¤°à¤¤à¤¾"},
    5: {"signal": "à¤…à¤¨à¥à¤•à¥‚à¤²à¤¨ à¤”à¤° à¤—à¤¤à¤¿", "risk": "à¤…à¤¸à¥à¤¥à¤¿à¤° à¤¸à¥à¤µà¤¿à¤šà¤¿à¤‚à¤—"},
    6: {"signal": "à¤œà¤¿à¤®à¥à¤®à¥‡à¤¦à¤¾à¤°à¥€ à¤”à¤° à¤­à¤°à¥‹à¤¸à¤¾", "risk": "à¤…à¤¤à¤¿-à¤­à¤¾à¤° à¤²à¥‡à¤¨à¤¾"},
    7: {"signal": "à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£ à¤”à¤° à¤—à¤¹à¤°à¤¾à¤ˆ", "risk": "à¤…à¤§à¤¿à¤• à¤¸à¥‹à¤š"},
    8: {"signal": "à¤ªà¥à¤°à¤¾à¤§à¤¿à¤•à¤°à¤£ à¤”à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤®", "risk": "à¤¦à¤¬à¤¾à¤µ à¤•à¥€ à¤¤à¥€à¤µà¥à¤°à¤¤à¤¾"},
    9: {"signal": "à¤¦à¥ƒà¤·à¥à¤Ÿà¤¿ à¤”à¤° à¤ªà¥à¤°à¤­à¤¾à¤µ", "risk": "à¤Šà¤°à¥à¤œà¤¾ à¤¬à¤¿à¤–à¤°à¤¨à¤¾"},
}

BASIC_MISSING_EFFECTS: Dict[int, Dict[str, str]] = {
    1: {"gap": "self-initiative à¤®à¥‡à¤‚ à¤à¤¿à¤à¤•", "fix": "daily first-action rule"},
    2: {"gap": "à¤­à¤¾à¤µà¤¨à¤¾à¤¤à¥à¤®à¤• à¤¸à¤®à¤¨à¥à¤µà¤¯ à¤®à¥‡à¤‚ friction", "fix": "response à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ 10-second pause"},
    3: {"gap": "communication clarity drop", "fix": "à¤¹à¤° à¤¦à¤¿à¤¨ concise message drill"},
    4: {"gap": "routine inconsistency", "fix": "fixed-time habit anchor"},
    5: {"gap": "adaptability imbalance", "fix": "weekly change-review"},
    6: {"gap": "responsibility boundaries blur", "fix": "clear role limits"},
    7: {"gap": "over-analysis loop", "fix": "decision deadline rule"},
    8: {"gap": "material discipline fluctuation", "fix": "money checkpoint cadence"},
    9: {"gap": "closure energy weak", "fix": "open-loop closure ritual"},
}

BASIC_REPEAT_EFFECTS: Dict[int, str] = {
    1: "assertive streak à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ",
    2: "emotional sensitivity amplify à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ",
    3: "expressive à¤Šà¤°à¥à¤œà¤¾ à¤¤à¥‡à¤œà¤¼ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ",
    4: "discipline demand à¤¸à¤–à¥à¤¤ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ",
    5: "change-seeking impulse à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ",
    6: "duty à¤”à¤° caretaking pressure à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ",
    7: "inner analysis à¤²à¤‚à¤¬à¤¾ à¤šà¤²à¤¤à¤¾ à¤¹à¥ˆ",
    8: "control à¤”à¤° performance drive à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ",
    9: "idealism à¤”à¤° emotional intensity à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ",
}


def _stable_seed(*parts: Any) -> int:
    joined = "|".join(_safe_text(part) for part in parts if _safe_text(part))
    if not joined:
        return 7
    return sum((index + 1) * ord(char) for index, char in enumerate(joined))


def _pick_variant(seed: int, section_key: str, slot: str, options: Sequence[str]) -> str:
    clean_options = [_safe_text(option) for option in options if _safe_text(option)]
    if not clean_options:
        return ""
    index = _stable_seed(seed, section_key, slot) % len(clean_options)
    return clean_options[index]


def _fit_box_text(value: Any, max_chars: int = 280) -> str:
    text = _safe_text(value)
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars].rsplit(" ", 1)[0]
    return f"{trimmed}â€¦"


PERSONAL_YEAR_THEMES: Dict[int, Dict[str, str]] = {
    1: {"theme": "à¤¨à¤¯à¤¾ à¤†à¤°à¤‚à¤­ à¤”à¤° à¤ªà¤¹à¤²", "strength_hook": "à¤¯à¤¹ à¤µà¤°à¥à¤· self-start decisions à¤•à¥‹ à¤¤à¥‡à¤œà¤¼ à¤¸à¤®à¤°à¥à¤¥à¤¨ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ", "pressure": "à¤œà¤²à¥à¤¦à¤¬à¤¾à¤œà¤¼ à¤µà¤¿à¤¸à¥à¤¤à¤¾à¤°", "protocol": "single-priority launch sprint"},
    2: {"theme": "à¤¸à¤¹à¤¯à¥‹à¤— à¤”à¤° à¤§à¥ˆà¤°à¥à¤¯", "strength_hook": "partnership-led progress à¤‡à¤¸ cycle à¤®à¥‡à¤‚ à¤¬à¥‡à¤¹à¤¤à¤° compound à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ", "pressure": "decision hesitation", "protocol": "response-pause + coordination review"},
    3: {"theme": "à¤…à¤­à¤¿à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤”à¤° visibility", "strength_hook": "communication clarity à¤•à¥‹ public outcomes à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¤¾ à¤†à¤¸à¤¾à¤¨ à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆ", "pressure": "scattered focus", "protocol": "message discipline + weekly publishing cadence"},
    4: {"theme": "à¤¸à¤‚à¤°à¤šà¤¨à¤¾ à¤”à¤° à¤ªà¥à¤°à¤£à¤¾à¤²à¥€", "strength_hook": "process rigor à¤•à¥‡ à¤¸à¤¾à¤¥ execution quality à¤œà¤²à¥à¤¦à¥€ à¤¸à¥à¤¥à¤¿à¤° à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ", "pressure": "rigidity loops", "protocol": "fixed routine + flexible review windows"},
    5: {"theme": "à¤ªà¤°à¤¿à¤µà¤°à¥à¤¤à¤¨ à¤”à¤° adaptation", "strength_hook": "adaptive actions à¤¸à¤¹à¥€ boundaries à¤®à¥‡à¤‚ à¤¬à¤¡à¤¼à¤¾ leverage à¤¦à¥‡à¤¤à¥‡ à¤¹à¥ˆà¤‚", "pressure": "context switching overload", "protocol": "bounded experimentation + closure checklist"},
    6: {"theme": "à¤œà¤¿à¤®à¥à¤®à¥‡à¤¦à¤¾à¤°à¥€ à¤”à¤° stability", "strength_hook": "trust-based commitments à¤‡à¤¸ à¤¸à¤®à¤¯ tangible growth à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¤à¥‡ à¤¹à¥ˆà¤‚", "pressure": "over-responsibility fatigue", "protocol": "role-boundary guardrails + recovery rhythm"},
    7: {"theme": "à¤—à¤¹à¤°à¤¾à¤ˆ à¤”à¤° introspection", "strength_hook": "analysis à¤•à¥‹ framework à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¥‡ à¤ªà¤° high-quality decisions à¤¨à¤¿à¤•à¤²à¤¤à¥‡ à¤¹à¥ˆà¤‚", "pressure": "analysis paralysis", "protocol": "insight-to-action checkpoint loop"},
    8: {"theme": "à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤”à¤° governance", "strength_hook": "authority à¤”à¤° disciplined scaling à¤•à¥‹ à¤®à¤œà¤¬à¥‚à¤¤ à¤¬à¥ˆà¤•à¤¿à¤‚à¤— à¤®à¤¿à¤²à¤¤à¥€ à¤¹à¥ˆ", "pressure": "control-heavy execution", "protocol": "governance board + pressure audit"},
    9: {"theme": "closure à¤”à¤° synthesis", "strength_hook": "unfinished loops à¤¬à¤‚à¤¦ à¤•à¤°à¤•à¥‡ à¤¬à¤¡à¤¼à¥€ clarity à¤®à¤¿à¤²à¤¤à¥€ à¤¹à¥ˆ", "pressure": "energy leakage", "protocol": "open-loop closure + selective commitments"},
    11: {"theme": "à¤‰à¤šà¥à¤š à¤…à¤‚à¤¤à¤°à¥à¤¦à¥ƒà¤·à¥à¤Ÿà¤¿ à¤”à¤° intuition", "strength_hook": "vision-led direction à¤•à¥‹ sharp execution à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¤¾ à¤¸à¤‚à¤­à¤µ à¤¹à¥ˆ", "pressure": "sensitivity overload", "protocol": "grounding rituals + decision filters"},
    22: {"theme": "à¤¨à¤¿à¤°à¥à¤®à¤¾à¤£ à¤”à¤° scale architecture", "strength_hook": "big systems build à¤•à¤°à¤¨à¥‡ à¤•à¥€ à¤•à¥à¤·à¤®à¤¤à¤¾ peak à¤ªà¤° à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆ", "pressure": "execution burden", "protocol": "macro blueprint + micro accountability"},
}

METRIC_STRENGTH_CONTEXT: Dict[str, str] = {
    "Life Stability": "à¤†à¤ª routine à¤¸à¥‡ outcome à¤¨à¤¿à¤•à¤¾à¤²à¤¨à¥‡ à¤•à¥€ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤°à¤–à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤”à¤° chaos à¤®à¥‡à¤‚ à¤­à¥€ base structure à¤¬à¤¨à¤¾ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
    "Decision Clarity": "à¤†à¤ª ambiguous inputs à¤•à¥‹ practical choices à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¥‡ à¤•à¤¾ skill-set à¤°à¤–à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
    "Dharma Alignment": "à¤†à¤ªà¤•à¥‡ goals à¤”à¤° effort à¤•à¥€ à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ alignment à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° output quality à¤¤à¥‡à¤œà¤¼à¥€ à¤¸à¥‡ improve à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
    "Emotional Regulation": "pressure windows à¤®à¥‡à¤‚ composure à¤¬à¤¨à¤¾à¤ à¤°à¤–à¤¨à¥‡ à¤¸à¥‡ à¤†à¤ªà¤•à¥€ performance advantage à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
    "Financial Discipline": "money decisions à¤®à¥‡à¤‚ structured thinking à¤†à¤ªà¤•à¥€ long-term stability à¤•à¥‹ support à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
    "Karma Pressure": "pressure signals à¤•à¥‹ à¤ªà¤¹à¤šà¤¾à¤¨à¤•à¤° à¤†à¤ª corrective action à¤œà¤²à¥à¤¦à¥€ activate à¤•à¤° à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
}

METRIC_RISK_CONTEXT: Dict[str, str] = {
    "Life Stability": "routine breaks à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° follow-through à¤Ÿà¥‚à¤Ÿà¤¤à¤¾ à¤¹à¥ˆ à¤”à¤° repeated restarts à¤¬à¤¢à¤¼à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
    "Decision Clarity": "high-noise phases à¤®à¥‡à¤‚ options à¤…à¤§à¤¿à¤• à¤”à¤° commitment à¤•à¤® à¤¹à¥‹à¤¨à¥‡ à¤•à¤¾ risk à¤¬à¤¢à¤¼ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    "Dharma Alignment": "effort à¤¸à¤¹à¥€ à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ à¤¨ à¤²à¤—à¤¨à¥‡ à¤ªà¤° busy à¤°à¤¹à¤¨à¥‡ à¤•à¥‡ à¤¬à¤¾à¤µà¤œà¥‚à¤¦ progress à¤§à¥€à¤®à¥€ à¤²à¤—à¤¤à¥€ à¤¹à¥ˆà¥¤",
    "Emotional Regulation": "stress spike phases à¤®à¥‡à¤‚ reaction quality à¤—à¤¿à¤°à¤¨à¥‡ à¤¸à¥‡ relationship à¤”à¤° decisions à¤¦à¥‹à¤¨à¥‹à¤‚ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
    "Financial Discipline": "untracked spending à¤”à¤° delayed checkpoints future flexibility à¤•à¥‹ à¤•à¤® à¤•à¤° à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
    "Karma Pressure": "old behavior loops activate à¤¹à¥‹à¤•à¤° correction momentum à¤•à¥‹ à¤ªà¥€à¤›à¥‡ à¤–à¥€à¤‚à¤š à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
}


def _alignment_signal(vibration: int, anchors: Sequence[int], label: str) -> Tuple[str, str]:
    clean_anchors = [value for value in anchors if isinstance(value, int) and value > 0]
    if _safe_int(vibration, 0) <= 0:
        return "data_limited", f"{label} signal à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹à¤¨à¥‡ à¤¸à¥‡ alignment reading à¤¸à¥€à¤®à¤¿à¤¤ à¤¹à¥ˆà¥¤"
    if not clean_anchors:
        return "neutral", f"{label} vibration {vibration} à¤•à¤¾ baseline à¤ªà¥à¤°à¤­à¤¾à¤µ neutral à¤®à¤¾à¤¨à¤¾ à¤œà¤¾à¤à¤—à¤¾à¥¤"

    min_gap = min(abs(vibration - anchor) for anchor in clean_anchors)
    if min_gap == 0:
        return "supportive", f"{label} vibration {vibration} core stack à¤•à¥‡ à¤¸à¤¾à¤¥ directly aligned à¤¹à¥ˆà¥¤"
    if min_gap == 1:
        return "near_supportive", f"{label} vibration {vibration} core stack à¤•à¥‡ à¤•à¤¾à¤«à¥€ à¤•à¤°à¥€à¤¬ à¤¹à¥ˆ à¤”à¤° partial support à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤"
    if min_gap >= 4:
        return "friction", f"{label} vibration {vibration} core stack à¤¸à¥‡ à¤¦à¥‚à¤° à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ communication rhythm à¤®à¥‡à¤‚ friction à¤¬à¤¨ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤"
    return "neutral", f"{label} vibration {vibration} mixed signal à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ; disciplined usage à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¯à¤¹ workable à¤¹à¥ˆà¥¤"


def _harmony_signal(mulank: int, bhagyank: int, name_number: int) -> Tuple[str, str]:
    name_anchor = name_number or bhagyank or mulank or 5
    gaps = [abs(mulank - bhagyank), abs(mulank - name_anchor), abs(bhagyank - name_anchor)]
    max_gap = max(gaps) if gaps else 0
    if max_gap <= 2:
        return "high_harmony", "core numbers à¤®à¥‡à¤‚ alignment à¤…à¤šà¥à¤›à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ intent à¤”à¤° execution à¤•à¤¾ à¤ªà¥à¤² à¤…à¤ªà¥‡à¤•à¥à¤·à¤¾à¤•à¥ƒà¤¤ à¤®à¤œà¤¬à¥‚à¤¤ à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆà¥¤"
    if max_gap <= 4:
        return "mixed_harmony", "core numbers à¤®à¥‡à¤‚ mixed harmony à¤¹à¥ˆ, à¤¯à¤¾à¤¨à¥€ à¤•à¥à¤› contexts à¤®à¥‡à¤‚ flow à¤”à¤° à¤•à¥à¤› à¤®à¥‡à¤‚ friction à¤‰à¤­à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤"
    return "friction_heavy", "core numbers à¤®à¥‡à¤‚ gap à¤…à¤§à¤¿à¤• à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ internal push-pull à¤”à¤° response drift à¤•à¤¾ à¤œà¥‹à¤–à¤¿à¤® à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤"


def _missing_severity_signal(loshu_missing: Sequence[int]) -> Tuple[str, str]:
    count = len(list(loshu_missing))
    if count >= 6:
        return "high_gap", f"Lo Shu à¤®à¥‡à¤‚ missing digits ({', '.join(str(v) for v in loshu_missing)}) à¤•à¤¾à¤«à¥€ à¤…à¤§à¤¿à¤• à¤¹à¥ˆà¤‚; behavioral support systems conscious à¤°à¥‚à¤ª à¤¸à¥‡ à¤¬à¤¨à¤¾à¤¨à¥€ à¤¹à¥‹à¤‚à¤—à¥€à¥¤"
    if count >= 4:
        return "medium_gap", f"Lo Shu missing set ({', '.join(str(v) for v in loshu_missing)}) moderate gap à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¥‡ routine correction à¤¸à¥‡ à¤­à¤°à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤"
    if count >= 2:
        return "light_gap", f"Lo Shu missing digits ({', '.join(str(v) for v in loshu_missing)}) à¤¸à¥€à¤®à¤¿à¤¤ à¤¹à¥ˆà¤‚; targeted habits à¤•à¤¾à¤«à¥€ à¤ªà¥à¤°à¤­à¤¾à¤µà¥€ à¤°à¤¹à¥‡à¤‚à¤—à¥€à¥¤"
    return "balanced", "Lo Shu distribution à¤…à¤ªà¥‡à¤•à¥à¤·à¤¾à¤•à¥ƒà¤¤ balanced à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ correction effort à¤…à¤§à¤¿à¤• focused à¤°à¤–à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤"


def _build_profile_driven_executive_brief(
    *,
    full_name: str,
    first_name: str,
    city_hint: str,
    focus_text: str,
    current_problem: str,
    mulank: int,
    bhagyank: int,
    life_path: int,
    destiny: int,
    expression: int,
    name_number: int,
    personal_year: int,
    loshu_missing: Sequence[int],
    repeating_numbers: Sequence[int],
    strongest_metric: str,
    strongest_score: int,
    weakest_metric: str,
    weakest_score: int,
    risk_band: str,
    mobile_vibration: int,
    mobile_classification: str,
    email_vibration: int,
    compatibility_level: str,
) -> Dict[str, str]:
    focus_hint = _safe_text(focus_text, "à¤œà¥€à¤µà¤¨ à¤¸à¤‚à¤¤à¥à¤²à¤¨").replace("_", " ")
    concern_hint = _safe_text(current_problem, "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤œà¥€à¤µà¤¨ à¤šà¥à¤¨à¥Œà¤¤à¥€")
    city_display = _safe_text(city_hint, "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¶à¤¹à¤°")
    name_number_text = str(name_number) if name_number else "-"
    risk_parts = [part.strip() for part in _safe_text(risk_band).split("|") if part.strip()]
    risk_primary = risk_parts[0] if risk_parts else _safe_text(risk_band, "Correctable Zone")
    risk_protocol = risk_parts[1] if len(risk_parts) > 1 else "protocol-led stabilization"
    repeating_text = ", ".join(str(value) for value in repeating_numbers[:3]) if repeating_numbers else "none"
    anchors = sorted(
        {
            value
            for value in [mulank, bhagyank, life_path, destiny, expression, name_number, personal_year]
            if isinstance(value, int) and value > 0
        }
    )

    harmony_state, harmony_note = _harmony_signal(mulank, bhagyank, name_number)
    harmony_brief = {
        "high_harmony": "core numbers à¤®à¥‡à¤‚ alignment à¤®à¤œà¤¬à¥‚à¤¤ à¤¹à¥ˆ",
        "mixed_harmony": "core numbers à¤®à¥‡à¤‚ mixed harmony à¤šà¤² à¤°à¤¹à¥€ à¤¹à¥ˆ",
        "friction_heavy": "core numbers à¤®à¥‡à¤‚ friction-heavy gap à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤¹à¥ˆ",
    }.get(harmony_state, "core numbers à¤®à¥‡à¤‚ mixed rhythm à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤¹à¥ˆ")
    missing_state, missing_note = _missing_severity_signal(loshu_missing)
    mobile_state, mobile_note = _alignment_signal(mobile_vibration, anchors, "Mobile")
    email_state, email_note = _alignment_signal(email_vibration, anchors, "Email")
    mobile_classification_hint = _safe_text(mobile_classification, mobile_state.replace("_", " "))

    year_key = personal_year if personal_year in PERSONAL_YEAR_THEMES else _reduce_number(personal_year or 0)
    year_theme = PERSONAL_YEAR_THEMES.get(year_key, PERSONAL_YEAR_THEMES[5])
    strength_core = METRIC_STRENGTH_CONTEXT.get(
        strongest_metric,
        "à¤†à¤ªà¤•à¥‡ profile à¤®à¥‡à¤‚ stable execution leverage à¤®à¥Œà¤œà¥‚à¤¦ à¤¹à¥ˆà¥¤",
    )
    risk_core = METRIC_RISK_CONTEXT.get(
        weakest_metric,
        "à¤¯à¤¹ axis à¤…à¤­à¥€ correction demand à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤",
    )
    compatibility_hint = _safe_text(compatibility_level, "moderate")
    seed = _stable_seed(
        full_name,
        concern_hint,
        focus_hint,
        mulank,
        bhagyank,
        name_number_text,
        personal_year,
        strongest_metric,
        weakest_metric,
        risk_primary,
    )

    summary_templates = [
        f"{first_name} à¤•à¥€ executive profile à¤®à¥‡à¤‚ {year_theme['theme']} phase à¤•à¥‡ à¤¸à¤¾à¤¥ {harmony_brief}à¥¤ à¤‡à¤¸à¤²à¤¿à¤ focus '{focus_hint}' à¤ªà¤° disciplined sequencing à¤‡à¤¸ à¤¸à¤®à¤¯ high-impact à¤°à¤¹à¥‡à¤—à¤¾à¥¤",
        f"Core stack {mulank}/{bhagyank}/{name_number_text} à¤”à¤° personal year {personal_year} à¤®à¤¿à¤²à¤•à¤° à¤¯à¤¹ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤•à¤¿ growth à¤¸à¤‚à¤­à¤µ à¤¹à¥ˆ, à¤²à¥‡à¤•à¤¿à¤¨ {weakest_metric.lower()} à¤•à¥‹ stabilize à¤•à¤¿à¤ à¤¬à¤¿à¤¨à¤¾ scale uneven à¤°à¤¹à¥‡à¤—à¤¾à¥¤",
        f"Risk context '{risk_primary}' à¤•à¥‡ à¤­à¥€à¤¤à¤° {strongest_metric.lower()} à¤†à¤ªà¤•à¤¾ leverage point à¤¹à¥ˆ, à¤œà¤¬à¤•à¤¿ {weakest_metric.lower()} à¤µà¤¹ axis à¤¹à¥ˆ à¤œà¤¹à¤¾à¤ drift à¤¸à¤¬à¤¸à¥‡ à¤¤à¥‡à¤œà¤¼ à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        f"{city_display} à¤œà¥ˆà¤¸à¥‡ real-world context à¤®à¥‡à¤‚ profile à¤•à¥€ à¤¸à¤«à¤²à¤¤à¤¾ à¤‡à¤¸ à¤¬à¤¾à¤¤ à¤ªà¤° à¤¨à¤¿à¤°à¥à¤­à¤° à¤•à¤°à¥‡à¤—à¥€ à¤•à¤¿ à¤†à¤ª {year_theme['pressure']} à¤•à¥‹ à¤•à¤¿à¤¤à¤¨à¥€ à¤œà¤²à¥à¤¦à¥€ control à¤•à¤° à¤ªà¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
    ]
    summary_tail = [
        f"{missing_note}",
        f"{mobile_note} {email_note} Mobile classification '{mobile_classification_hint}' à¤‡à¤¸ combined signal à¤•à¤¾ practical context à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        f"Repeating pattern ({repeating_text}) à¤”à¤° compatibility level '{compatibility_hint}' à¤•à¥‹ à¤¸à¤¾à¤¥ à¤ªà¤¢à¤¼à¤¨à¥‡ à¤ªà¤° correction order à¤”à¤° à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        f"Concern '{concern_hint}' à¤•à¥‹ measurable milestones à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¤¾ à¤‡à¤¸ report à¤•à¤¾ immediate execution pivot à¤¹à¥‹à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤à¥¤",
    ]
    profile_signature = (
        f"Profile marker: {first_name} | {city_display} | Core {mulank}/{bhagyank}/{name_number_text} "
        f"| PY {personal_year} | Mobile/Email {mobile_vibration}/{email_vibration} "
        f"| Focus {focus_hint} | Concern {concern_hint}."
    )
    summary = _fit_box_text(
        f"{profile_signature} "
        f"{_pick_variant(seed, 'executive_brief', 'summary', summary_templates)} "
        f"{_pick_variant(seed, 'executive_brief', 'summary_tail', summary_tail)}",
        max_chars=560,
    )

    strength_options = [
        f"{strongest_metric} ({strongest_score}/100) à¤‡à¤¸ profile à¤•à¤¾ strongest operational axis à¤¹à¥ˆà¥¤ {strength_core} {year_theme['strength_hook']}",
        f"à¤®à¥à¤–à¥à¤¯ strength signal {strongest_metric} à¤¹à¥ˆ à¤”à¤° à¤‡à¤¸à¤•à¥€ à¤µà¤œà¤¹ à¤¸à¥‡ high-noise phase à¤®à¥‡à¤‚ à¤­à¥€ à¤†à¤ª direction lock à¤•à¤°à¤¨à¥‡ à¤•à¥€ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤¦à¤¿à¤–à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤ {harmony_note}",
        f"{strongest_metric} score {strongest_score} à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ à¤¸à¤¹à¥€ system à¤®à¤¿à¤²à¤¨à¥‡ à¤ªà¤° à¤†à¤ªà¤•à¥€ execution quality à¤œà¤²à¥à¤¦à¥€ compound à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ, à¤–à¤¾à¤¸à¤•à¤° à¤œà¤¬ focus '{focus_hint}' à¤ªà¤° clear boundaries à¤¹à¥‹à¤‚à¥¤",
    ]
    if mobile_state in {"supportive", "near_supportive"}:
        strength_options.append(f"{mobile_note} à¤¯à¤¹ signal {strongest_metric.lower()} à¤•à¥‹ day-to-day communication à¤”à¤° follow-through à¤®à¥‡à¤‚ practical support à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤")
    key_strength = _fit_box_text(
        _pick_variant(seed, "executive_brief", "key_strength", strength_options),
        max_chars=420,
    )

    risk_options = [
        f"{weakest_metric} ({weakest_score}/100) profile à¤•à¤¾ current pressure-point à¤¹à¥ˆà¥¤ {risk_core} {missing_note}",
        f"Risk axis {weakest_metric.lower()} à¤®à¥‡à¤‚ drift à¤‡à¤¸à¤²à¤¿à¤ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ à¤•à¥à¤¯à¥‹à¤‚à¤•à¤¿ {harmony_state.replace('_', ' ')} pattern à¤”à¤° {year_theme['pressure']} à¤à¤• à¤¸à¤¾à¤¥ load à¤¬à¤¢à¤¼à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
        f"à¤¯à¤¦à¤¿ à¤‡à¤¸ axis à¤ªà¤° correction delay à¤¹à¥à¤† à¤¤à¥‹ {risk_primary} state à¤•à¥€ intensity à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ, à¤–à¤¾à¤¸à¤•à¤° concern '{concern_hint}' à¤”à¤° {missing_state.replace('_', ' ')} Lo Shu profile à¤•à¥‡ à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤®à¥‡à¤‚à¥¤",
    ]
    if mobile_state == "friction":
        risk_options.append(mobile_note)
    if email_state == "friction":
        risk_options.append(email_note)
    key_risk = _fit_box_text(
        _pick_variant(seed, "executive_brief", "key_risk", risk_options),
        max_chars=420,
    )

    correction_options = [
        f"Correction focus: à¤ªà¤¹à¤²à¥‡ {year_theme['protocol']} à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚, à¤«à¤¿à¤° {weakest_metric.lower()} à¤•à¥‡ à¤²à¤¿à¤ weekly scorecard à¤šà¤²à¤¾à¤à¤‚, à¤”à¤° concern '{concern_hint}' à¤•à¥‹ 3 measurable weekly outcomes à¤®à¥‡à¤‚ à¤¤à¥‹à¤¡à¤¼à¥‡à¤‚à¥¤",
        f"Execution order à¤°à¤–à¥‡à¤‚: (1) routine lock, (2) {weakest_metric.lower()} stabilization, (3) mobile/email identity alignment, (4) {strongest_metric.lower()} leverage scale-upà¥¤",
        f"{risk_protocol} à¤•à¥‹ daily action à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¥‡à¤‚: morning anchor, mid-week review, à¤”à¤° week-end proof log à¤•à¥‡ à¤¸à¤¾à¤¥ correction progress visible à¤°à¤–à¥‡à¤‚à¥¤",
    ]
    strategic_focus = _fit_box_text(
        _pick_variant(seed, "executive_brief", "strategic_focus", correction_options),
        max_chars=560,
    )

    structural_cause = _fit_box_text(
        f"Root cause stack: {mulank}/{bhagyank}/{name_number_text} à¤®à¥‡à¤‚ {harmony_state.replace('_', ' ')} signal, Lo Shu gap profile ({missing_state}), à¤”à¤° personal year {personal_year} à¤•à¤¾ {year_theme['pressure']} pressure à¤®à¤¿à¤²à¤•à¤° {weakest_metric.lower()} axis à¤ªà¤° drift à¤¬à¤¨à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
        max_chars=240,
    )
    intervention_focus = _fit_box_text(
        f"{risk_protocol}: {year_theme['protocol']} -> {weakest_metric.lower()} baseline stabilization -> concern '{concern_hint}' à¤ªà¤° weekly measurable correction proofà¥¤",
        max_chars=240,
    )

    return {
        "summary": summary,
        "key_strength": key_strength,
        "key_risk": key_risk,
        "strategic_focus": strategic_focus,
        "primary_strength": _fit_box_text(f"{strongest_metric} ({strongest_score}/100): {strength_core}", max_chars=200),
        "primary_deficit": _fit_box_text(f"{weakest_metric} ({weakest_score}/100): {risk_core}", max_chars=200),
        "structural_cause": structural_cause,
        "intervention_focus": intervention_focus,
        "short_term": _fit_box_text(f"Short term: {year_theme['protocol']} à¤•à¥‡ à¤¸à¤¾à¤¥ {weakest_metric.lower()} volatility à¤•à¥‹ stabilize à¤•à¤°à¥‡à¤‚à¥¤", max_chars=180),
        "mid_term": _fit_box_text(f"Mid term: Lo Shu missing à¤”à¤° repeating pattern ({repeating_text}) à¤ªà¤° behavior patches deploy à¤•à¤°à¥‡à¤‚à¥¤", max_chars=180),
        "long_term": _fit_box_text(f"Long term: {strongest_metric.lower()} leverage à¤•à¥‹ strategic decisions à¤”à¤° timing-fit execution à¤®à¥‡à¤‚ convert à¤•à¤°à¥‡à¤‚à¥¤", max_chars=180),
    }


CARD_LABELS_HI: Dict[str, str] = {
    "What is happening": "à¤•à¥à¤¯à¤¾ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆ",
    "Why it is happening": "à¤¯à¤¹ à¤•à¥à¤¯à¥‹à¤‚ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆ",
    "What it affects": "à¤‡à¤¸à¤•à¤¾ à¤ªà¥à¤°à¤­à¤¾à¤µ",
    "What to do about it": "à¤•à¥à¤¯à¤¾ à¤•à¤°à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤",
    "Current Number": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¸à¤‚à¤–à¥à¤¯à¤¾",
    "Current Name Number": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¨à¤¾à¤® à¤¸à¤‚à¤–à¥à¤¯à¤¾",
    "Target Numbers": "à¤²à¤•à¥à¤·à¥à¤¯ à¤¸à¤‚à¤–à¥à¤¯à¤¾à¤à¤‚",
    "Strength": "à¤®à¥à¤–à¥à¤¯ à¤¤à¤¾à¤•à¤¤",
    "Risk": "à¤®à¥à¤–à¥à¤¯ à¤œà¥‹à¤–à¤¿à¤®",
    "Current Mobile": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤®à¥‹à¤¬à¤¾à¤‡à¤²",
    "Target Vibrations": "à¤²à¤•à¥à¤·à¥à¤¯ à¤µà¤¾à¤‡à¤¬à¥à¤°à¥‡à¤¶à¤¨",
    "Ending Logic": "à¤…à¤‚à¤¤à¤¿à¤® à¤…à¤‚à¤• à¤²à¥‰à¤œà¤¿à¤•",
    "Current Email": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤ˆà¤®à¥‡à¤²",
    "Email Vibration": "à¤ˆà¤®à¥‡à¤² à¤µà¤¾à¤‡à¤¬à¥à¤°à¥‡à¤¶à¤¨",
    "Authority Signal": "à¤‘à¤¥à¥‹à¤°à¤¿à¤Ÿà¥€ à¤¸à¤¿à¤—à¥à¤¨à¤²",
    "Starting Stroke": "à¤¶à¥à¤°à¥à¤†à¤¤à¥€ à¤¸à¥à¤Ÿà¥à¤°à¥‹à¤•",
    "Ending Stroke": "à¤…à¤‚à¤¤à¤¿à¤® à¤¸à¥à¤Ÿà¥à¤°à¥‹à¤•",
    "Authority Alignment": "à¤‘à¤¥à¥‹à¤°à¤¿à¤Ÿà¥€ à¤à¤²à¤¾à¤‡à¤¨à¤®à¥‡à¤‚à¤Ÿ",
    "Business Name": "à¤¬à¤¿à¤œà¤¼à¤¨à¥‡à¤¸ à¤¨à¤¾à¤®",
    "Industry Fit": "à¤‡à¤‚à¤¡à¤¸à¥à¤Ÿà¥à¤°à¥€ à¤«à¤¿à¤Ÿ",
    "Social Handle": "à¤¸à¥‹à¤¶à¤² à¤¹à¥ˆà¤‚à¤¡à¤²",
    "Domain Handle": "à¤¡à¥‹à¤®à¥‡à¤¨ à¤¹à¥ˆà¤‚à¤¡à¤²",
    "Current Residence Number": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤°à¥‡à¤œà¤¿à¤¡à¥‡à¤‚à¤¸ à¤¨à¤‚à¤¬à¤°",
    "Residence Vibration": "à¤°à¥‡à¤œà¤¿à¤¡à¥‡à¤‚à¤¸ à¤µà¤¾à¤‡à¤¬à¥à¤°à¥‡à¤¶à¤¨",
    "Current Vehicle Number": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤µà¤¾à¤¹à¤¨ à¤¨à¤‚à¤¬à¤°",
    "Vehicle Vibration": "à¤µà¤¾à¤¹à¤¨ à¤µà¤¾à¤‡à¤¬à¥à¤°à¥‡à¤¶à¤¨",
    "Focus": "à¤«à¥‹à¤•à¤¸",
    "Code": "à¤•à¥‹à¤¡",
    "Parameter": "à¤ªà¥ˆà¤°à¤¾à¤®à¥€à¤Ÿà¤°",
    "Output": "à¤†à¤‰à¤Ÿà¤ªà¥à¤Ÿ",
    "Top Priority": "à¤Ÿà¥‰à¤ª à¤ªà¥à¤°à¤¾à¤¯à¥‹à¤°à¤¿à¤Ÿà¥€",
    "High-Impact Quick Fixes": "à¤¹à¤¾à¤ˆ-à¤‡à¤®à¥à¤ªà¥ˆà¤•à¥à¤Ÿ à¤•à¥à¤µà¤¿à¤• à¤«à¤¿à¤•à¥à¤¸",
    "Medium-Term Adjustments": "à¤®à¤¿à¤¡-à¤Ÿà¤°à¥à¤® à¤à¤¡à¤œà¤¸à¥à¤Ÿà¤®à¥‡à¤‚à¤Ÿ",
    "Premium Advisory": "à¤ªà¥à¤°à¥€à¤®à¤¿à¤¯à¤® à¤à¤¡à¤µà¤¾à¤‡à¤œà¤°à¥€",
    "Current Personal Year": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤ªà¤°à¥à¤¸à¤¨à¤² à¤ˆà¤¯à¤°",
    "Favorable Dates": "à¤…à¤¨à¥à¤•à¥‚à¤² à¤¤à¤¿à¤¥à¤¿à¤¯à¤¾à¤‚",
    "Lucky Numbers": "à¤¸à¤ªà¥‹à¤°à¥à¤Ÿà¤¿à¤µ à¤¨à¤‚à¤¬à¤°",
    "Risk Band": "à¤°à¤¿à¤¸à¥à¤• à¤¬à¥ˆà¤‚à¤¡",
    "Dominant Planet": "à¤¡à¥‰à¤®à¤¿à¤¨à¥‡à¤‚à¤Ÿ à¤—à¥à¤°à¤¹",
    "Summary": "à¤¸à¤¾à¤°à¤¾à¤‚à¤¶",
    "Key Strength": "à¤®à¥à¤–à¥à¤¯ à¤¤à¤¾à¤•à¤¤",
    "Key Risk": "à¤¸à¤‚à¤­à¤¾à¤µà¤¿à¤¤ à¤šà¥à¤¨à¥Œà¤¤à¥€",
    "Practical Guidance": "à¤µà¥à¤¯à¤¾à¤µà¤¹à¤¾à¤°à¤¿à¤• à¤¸à¥à¤à¤¾à¤µ",
    "Energy Indicators": "à¤Šà¤°à¥à¤œà¤¾ à¤¸à¤‚à¤•à¥‡à¤¤",
    "Key Metrics": "à¤ªà¥à¤°à¤®à¥à¤– à¤¸à¤‚à¤•à¥‡à¤¤à¤•",
    "confidence_score": "à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤¸à¥à¤ªà¤·à¥à¤Ÿà¤¤à¤¾ à¤¸à¥à¤•à¥‹à¤°",
    "dharma_alignment_score": "à¤§à¤°à¥à¤® à¤¸à¤‚à¤°à¥‡à¤–à¤£ à¤¸à¥à¤•à¥‹à¤°",
    "financial_discipline_index": "à¤µà¤¿à¤¤à¥à¤¤ à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤¸à¥‚à¤šà¤•à¤¾à¤‚à¤•",
    "life_stability_index": "à¤œà¥€à¤µà¤¨ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤¸à¥‚à¤šà¤•à¤¾à¤‚à¤•",
}

DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")
PLACEHOLDER_PATTERN = re.compile(r"\{[^{}]+\}")

PHRASE_REPLACEMENTS: Sequence[Tuple[str, str]] = [
    ("Deterministic structure", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤¸à¤‚à¤°à¤šà¤¨à¤¾"),
    ("deterministic structure", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤¸à¤‚à¤°à¤šà¤¨à¤¾"),
    ("Deterministic signal", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤¸à¤‚à¤•à¥‡à¤¤"),
    ("deterministic signal", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤¸à¤‚à¤•à¥‡à¤¤"),
    ("generated from deterministic profile synthesis", "à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² synthesis à¤¸à¥‡ à¤¤à¥ˆà¤¯à¤¾à¤°"),
    ("Not provided", "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"),
    ("Current cycle", "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤šà¤•à¥à¤°"),
    ("Current personal year", "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤ªà¤°à¥à¤¸à¤¨à¤² à¤ˆà¤¯à¤°"),
    ("Personal year", "à¤ªà¤°à¥à¤¸à¤¨à¤² à¤ˆà¤¯à¤°"),
    ("Risk band", "à¤°à¤¿à¤¸à¥à¤• à¤¬à¥ˆà¤‚à¤¡"),
    ("Primary deficit", "à¤®à¥à¤–à¥à¤¯ à¤•à¤®à¥€"),
    ("Primary strength", "à¤®à¥à¤–à¥à¤¯ à¤¤à¤¾à¤•à¤¤"),
    ("Current ", "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ "),
    ("Target ", "à¤²à¤•à¥à¤·à¥à¤¯ "),
    ("Option ", "à¤µà¤¿à¤•à¤²à¥à¤ª "),
]

WORD_REPLACEMENTS: Sequence[Tuple[str, str]] = [
    (r"\bprofile\b", "à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤²"),
    (r"\bstrategic\b", "à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤•"),
    (r"\banalysis\b", "à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£"),
    (r"\bstructure\b", "à¤¸à¤‚à¤°à¤šà¤¨à¤¾"),
    (r"\bindicates\b", "à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ"),
    (r"\bshows\b", "à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆ"),
    (r"\bsupports\b", "à¤¸à¤ªà¥‹à¤°à¥à¤Ÿ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ"),
    (r"\bimproves\b", "à¤¬à¥‡à¤¹à¤¤à¤° à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ"),
    (r"\bstabilize\b", "à¤¸à¥à¤¥à¤¿à¤° à¤•à¤°à¥‡à¤‚"),
    (r"\bconsistency\b", "à¤•à¤‚à¤¸à¤¿à¤¸à¥à¤Ÿà¥‡à¤‚à¤¸à¥€"),
    (r"\bdiscipline\b", "à¤¡à¤¿à¤¸à¤¿à¤ªà¥à¤²à¤¿à¤¨"),
    (r"\bstrategy\b", "à¤¸à¥à¤Ÿà¥à¤°à¥ˆà¤Ÿà¥‡à¤œà¥€"),
    (r"\brisk\b", "à¤œà¥‹à¤–à¤¿à¤®"),
    (r"\bstrength\b", "à¤¤à¤¾à¤•à¤¤"),
    (r"\bdeficit\b", "à¤•à¤®à¥€"),
    (r"\balignment\b", "à¤à¤²à¤¾à¤‡à¤¨à¤®à¥‡à¤‚à¤Ÿ"),
    (r"\bgrowth\b", "à¤—à¥à¤°à¥‹à¤¥"),
]


def _hindi_mix_text(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return text

    text = PLACEHOLDER_PATTERN.sub("", text)
    text = re.sub(r"(,\s*){2,}", ", ", text)
    text = re.sub(r"\s+[|]\s+", " | ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;|")

    if not text:
        return "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

    for source, target in PHRASE_REPLACEMENTS:
        text = text.replace(source, target)

    for pattern, replacement in WORD_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"([|,:;])\1+", r"\1", text)
    text = text.replace("à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤¸à¤‚à¤•à¥‡à¤¤: à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤¸à¤‚à¤•à¥‡à¤¤:", "à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤¸à¤‚à¤•à¥‡à¤¤:")
    text = text.replace("..", ".")

    latin_letters = sum(1 for ch in text if ("a" <= ch.lower() <= "z"))
    latin_ratio = latin_letters / max(len(text), 1)
    has_devanagari = bool(DEVANAGARI_PATTERN.search(text))

    if latin_ratio > 0.55 and not has_devanagari:
        text = f"à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤¸à¤‚à¤•à¥‡à¤¤: {text}. à¤‡à¤¸à¥‡ à¤¸à¥à¤§à¤¾à¤° à¤ªà¥à¤°à¥‹à¤Ÿà¥‹à¤•à¥‰à¤² à¤”à¤° disciplined execution à¤•à¥‡ à¤¸à¤¾à¤¥ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤"

    return text


def _localize_payloads(payloads: Dict[str, Any]) -> Dict[str, Any]:
    localized: Dict[str, Any] = {}
    for key, payload in (payloads or {}).items():
        if not isinstance(payload, dict):
            localized[key] = payload
            continue

        entry = dict(payload)

        entry["purpose"] = _hindi_mix_text(
            entry.get("purpose") or "à¤¯à¤¹ à¤¸à¥‡à¤•à¥à¤¶à¤¨ deterministic diagnosis à¤”à¤° correction protocol à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤"
        ) or "à¤¯à¤¹ à¤¸à¥‡à¤•à¥à¤¶à¤¨ deterministic diagnosis à¤”à¤° correction protocol à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤"
        entry["interpretation_logic"] = _hindi_mix_text(entry.get("interpretation_logic")) or "Structural signal à¤¸à¥‡ actionable insight à¤¨à¤¿à¤•à¤¾à¤²à¥€ à¤œà¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤"
        entry["tone_guidance"] = _hindi_mix_text(entry.get("tone_guidance")) or "Executive à¤”à¤° premium tone à¤°à¤–à¥‡à¤‚à¥¤"
        entry["narrative"] = _hindi_mix_text(entry.get("narrative")) or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

        cards = []
        for card in entry.get("cards") or []:
            if not isinstance(card, dict):
                continue
            label = _safe_text(card.get("label"))
            cards.append(
                {
                    "label": CARD_LABELS_HI.get(label, _hindi_mix_text(label)),
                    "value": _hindi_mix_text(card.get("value")) or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚",
                }
            )
        entry["cards"] = cards

        entry["bullets"] = [_hindi_mix_text(item) for item in (entry.get("bullets") or []) if _safe_text(item)]

        localized[key] = entry

    return localized


def _section_payload(
    section_key: str,
    narrative: str,
    what_happening: str,
    why_happening: str,
    impact: str,
    action: str,
    extra_cards: Sequence[Dict[str, str]] | None = None,
    bullets: Sequence[str] | None = None,
) -> Dict[str, Any]:
    meta = SECTION_META.get(section_key, SECTION_META["default"])
    cards = [
        {"label": "à¤•à¥à¤¯à¤¾ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆ", "value": what_happening},
        {"label": "à¤¯à¤¹ à¤•à¥à¤¯à¥‹à¤‚ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆ", "value": why_happening},
        {"label": "à¤‡à¤¸à¤•à¤¾ à¤ªà¥à¤°à¤­à¤¾à¤µ", "value": impact},
        {"label": "à¤•à¥à¤¯à¤¾ à¤•à¤°à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤", "value": action},
    ]
    if extra_cards:
        cards.extend(extra_cards)
    clean_bullets = [_safe_text(item) for item in (bullets or []) if _safe_text(item)]
    return {
        "section_key": section_key,
        "title": SECTION_TITLES.get(section_key, section_key.replace("_", " ").title()),
        "purpose": meta["purpose"],
        "key_inputs": meta["key_inputs"],
        "output_fields": meta["output_fields"],
        "interpretation_logic": meta["interpretation_logic"],
        "tone_guidance": meta["tone_guidance"],
        "cards": cards,
        "bullets": clean_bullets,
        "narrative": _safe_text(narrative),
    }


def _ensure_all_payloads(plan_name: str, payloads: Dict[str, Any]) -> Dict[str, Any]:
    for section in get_tier_section_blueprint(plan_name).get("sections", []):
        key = section.get("key")
        if key and key not in payloads:
            payloads[key] = _section_payload(
                key,
                narrative=f"{SECTION_TITLES.get(key, key)} à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² synthesis à¤¸à¥‡ à¤¤à¥ˆà¤¯à¤¾à¤° à¤•à¤¿à¤¯à¤¾ à¤—à¤¯à¤¾ à¤¹à¥ˆà¥¤",
                what_happening="à¤‡à¤¸ intelligence layer à¤®à¥‡à¤‚ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¤¿à¤– à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤",
                why_happening="à¤¯à¤¹ layer numerology core à¤”à¤° intake patterns à¤•à¥‡ à¤°à¤¿à¤¶à¥à¤¤à¥‡ à¤¸à¥‡ à¤¨à¤¿à¤•à¤²à¤¾ à¤¹à¥ˆà¥¤",
                impact="à¤¯à¤¹ correction-aware à¤¨à¤¿à¤°à¥à¤£à¤¯ lens à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤•à¤°à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
                action="à¤‡à¤¸ protocol à¤•à¥‹ integrated execution system à¤®à¥‡à¤‚ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤",
            )
    return payloads


def _personalize_basic_payloads(
    basic_payloads: Dict[str, Any],
    *,
    full_name: str,
    first_name: str,
    date_of_birth: str,
    current_problem: str,
    city_hint: str,
    focus_text: str,
    mulank: int,
    bhagyank: int,
    life_path: int,
    destiny: int,
    expression: int,
    name_number: int,
    name_compound: int,
    personal_year: int,
    strongest_metric: str,
    weakest_metric: str,
    risk_band: str,
    loshu_present: Sequence[int],
    loshu_missing: Sequence[int],
    repeating_numbers: Sequence[int],
    mobile_vibration: int,
    mobile_classification: str,
    mobile_value: str,
    email_value: str,
    email_vibration: int,
    compatibility_summary: str,
    compatibility_level: str,
    career_industry: str,
    lucky_dates: Sequence[int],
    name_targets: Sequence[int],
    favorable_colors: str,
    caution_colors: str,
    dominant_planet: str,
    vedic_code: str,
    vedic_parameter: str,
    lifestyle_protocol: str,
    name_options: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    mulank_signal = BASIC_NUMBER_MEANINGS.get(mulank, BASIC_NUMBER_MEANINGS[5])["signal"]
    bhagyank_signal = BASIC_NUMBER_MEANINGS.get(bhagyank, BASIC_NUMBER_MEANINGS[5])["signal"]
    name_signal = BASIC_NUMBER_MEANINGS.get(name_number or bhagyank or mulank or 5, BASIC_NUMBER_MEANINGS[5])["signal"]
    name_number_text = str(name_number) if name_number else "-"
    present_text = ", ".join(str(value) for value in loshu_present) or "none"
    missing_text = ", ".join(str(value) for value in loshu_missing) or "none"
    repeating_text = ", ".join(str(value) for value in repeating_numbers) if repeating_numbers else "à¤•à¥‹à¤ˆ à¤ªà¥à¤°à¤®à¥à¤– à¤ªà¥à¤¨à¤°à¤¾à¤µà¥ƒà¤¤à¥à¤¤à¤¿ à¤¨à¤¹à¥€à¤‚"
    lucky_text = ", ".join(str(value) for value in lucky_dates) or "3, 5, 9"
    target_text = ", ".join(str(value) for value in name_targets[:4]) or "3, 5, 9"

    missing_insights: List[str] = []
    for number in list(loshu_missing)[:4]:
        meta = BASIC_MISSING_EFFECTS.get(number, {"gap": "behavior gap", "fix": "daily correction"})
        missing_insights.append(f"{number}â†’{meta['gap']}")
    missing_insight_text = " | ".join(missing_insights) if missing_insights else "missing gaps limited à¤¹à¥ˆà¤‚"

    repeat_insights: List[str] = []
    for number in list(repeating_numbers)[:3]:
        repeat_insights.append(f"{number}â†’{BASIC_REPEAT_EFFECTS.get(number, 'trait intensity à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ')}")
    repeat_insight_text = " | ".join(repeat_insights) if repeat_insights else "repeat pressure à¤•à¤® à¤¹à¥ˆ"

    seed = _stable_seed(
        full_name,
        date_of_birth,
        current_problem,
        focus_text,
        mulank,
        bhagyank,
        name_number,
        personal_year,
        mobile_vibration,
        email_vibration,
        missing_text,
    )

    def _style_line(section_key: str, slot: str, statement: str) -> str:
        clean_statement = _safe_text(statement).rstrip("à¥¤.")
        lead = _pick_variant(
            seed,
            section_key,
            f"{slot}:lead",
            ["", "à¤…à¤‚à¤• à¤…à¤µà¤²à¥‹à¤•à¤¨:", "à¤ªà¥à¤°à¥‹à¤«à¤¼à¤¾à¤‡à¤² à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£:", "à¤¸à¤‚à¤°à¤šà¤¨à¤¾ à¤¸à¤‚à¤•à¥‡à¤¤:"],
        )
        tail = ""
        if slot == "why":
            tail = _pick_variant(
                seed,
                section_key,
                f"{slot}:tail",
                [
                    f"à¤•à¤¾à¤°à¤£ à¤®à¥‡à¤‚ Mulank {mulank}, Bhagyank {bhagyank}, Name {name_number_text} à¤”à¤° Personal Year {personal_year} à¤à¤• à¤¸à¤¾à¤¥ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤¹à¥ˆà¤‚à¥¤",
                    f"Lo Shu missing {missing_text} à¤”à¤° repeating pattern à¤‡à¤¸ à¤•à¤¾à¤°à¤£ à¤•à¥‹ à¤µà¥à¤¯à¤µà¤¹à¤¾à¤° à¤®à¥‡à¤‚ à¤¬à¤¾à¤°-à¤¬à¤¾à¤° trigger à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
                    f"Life Path {life_path} à¤”à¤° Destiny {destiny} à¤•à¥€ direction à¤‡à¤¸ à¤•à¤¾à¤°à¤£ à¤•à¥€ intensity à¤•à¥‹ context à¤•à¥‡ à¤¹à¤¿à¤¸à¤¾à¤¬ à¤¸à¥‡ à¤¬à¤¢à¤¼à¤¾à¤¤à¥€ à¤¯à¤¾ à¤˜à¤Ÿà¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤",
                ],
            )
        elif slot == "impact":
            tail = _pick_variant(
                seed,
                section_key,
                f"{slot}:tail",
                [
                    f"à¤‡à¤¸à¤•à¤¾ à¤…à¤¸à¤° à¤¸à¥€à¤§à¥‡ {weakest_metric} à¤”à¤° response consistency à¤•à¥€ quality à¤ªà¤° à¤†à¤¤à¤¾ à¤¹à¥ˆà¥¤",
                    f"à¤…à¤—à¤° à¤¯à¤¹ unchecked à¤°à¤¹à¤¾ à¤¤à¥‹ {risk_band} à¤•à¥€ à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ risk pressure à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
                    f"à¤¸à¤¹à¥€ handling à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° {strongest_metric} à¤•à¤¾ à¤²à¤¾à¤­ measurable output à¤®à¥‡à¤‚ à¤œà¤²à¥à¤¦à¥€ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆà¥¤",
                ],
            )
        elif slot == "action":
            tail = _pick_variant(
                seed,
                section_key,
                f"{slot}:tail",
                [
                    f"à¤‡à¤¸à¥‡ focus '{focus_text}' à¤”à¤° concern '{current_problem}' à¤¸à¥‡ à¤œà¥‹à¤¡à¤¼à¤•à¤° weekly measurable actions à¤®à¥‡à¤‚ à¤šà¤²à¤¾à¤à¤‚à¥¤",
                    f"{city_hint} à¤œà¥ˆà¤¸à¥‡ context à¤®à¥‡à¤‚ fixed routine, review slots à¤”à¤° low-noise decision windows à¤¬à¥‡à¤¹à¤¤à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¦à¥‡à¤‚à¤—à¥‡à¥¤",
                    f"21-day cycle, weekly proof-log à¤”à¤° monthly correction reset à¤¸à¤¾à¤¥ à¤°à¤–à¥‡à¤‚à¥¤",
                ],
            )

        text = clean_statement
        if lead:
            text = f"{lead} {text}"
        if tail:
            text = f"{text} {tail}"
        if not text.endswith(("à¥¤", ".")):
            text = f"{text}à¥¤"
        return _fit_box_text(text)

    section_facts: Dict[str, Dict[str, str]] = {
        "executive_numerology_summary": {
            "narrative": f"{full_name} à¤•à¥‡ à¤²à¤¿à¤ Mulank {mulank}, Bhagyank {bhagyank}, Name {name_number_text}, Personal Year {personal_year} à¤”à¤° focus '{focus_text}' à¤®à¤¿à¤²à¤•à¤° à¤®à¥à¤–à¥à¤¯ numerology profile à¤¬à¤¨à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤ Concern: {current_problem}.",
            "what": f"Mulank {mulank} response style à¤®à¥‡à¤‚ {mulank_signal} à¤•à¥‹ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": f"Bhagyank {bhagyank} à¤•à¥€ direction à¤”à¤° Name {name_number_text} à¤•à¥€ identity resonance à¤‡à¤¸à¤•à¤¾ à¤•à¤¾à¤°à¤£ à¤¹à¥ˆà¥¤",
            "impact": f"{strongest_metric} leverage à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ, à¤²à¥‡à¤•à¤¿à¤¨ {weakest_metric} à¤®à¥‡à¤‚ fluctuation friction à¤²à¤¾ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "21-day correction routine à¤”à¤° weekly review à¤¸à¥‡ core instability à¤•à¥‹ stabilize à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "core_numbers_analysis": {
            "narrative": f"Core stack: Mulank {mulank}, Bhagyank {bhagyank}, Destiny {destiny}, Expression {expression}, Name {name_number_text}.",
            "what": "à¤¯à¤¹ core numbers à¤†à¤ªà¤•à¥€ decision architecture à¤”à¤° response rhythm à¤¦à¤¿à¤–à¤¾à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "why": "DOB digit sum à¤”à¤° name vibration deterministic à¤°à¥‚à¤ª à¤¸à¥‡ à¤¯à¤¹ stack à¤¬à¤¨à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "impact": "Role-fit, communication tone à¤”à¤° discipline quality à¤ªà¤° à¤¸à¥€à¤§à¤¾ à¤…à¤¸à¤° à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "action": "à¤¹à¤° à¤¸à¤ªà¥à¤¤à¤¾à¤¹ core numbers à¤•à¥‡ à¤†à¤§à¤¾à¤° à¤ªà¤° 3 priority actions à¤²à¥‰à¤• à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "mulank_description": {
            "narrative": f"Mulank {mulank} à¤†à¤ªà¤•à¥€ instinctive personality à¤®à¥‡à¤‚ {mulank_signal} à¤•à¥‹ à¤ªà¥à¤°à¤®à¥à¤– à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "what": "First reaction pattern à¤®à¥‡à¤‚ Mulank energy à¤¤à¥‡à¤œà¥€ à¤¸à¥‡ à¤¦à¤¿à¤–à¤¾à¤ˆ à¤¦à¥‡à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "à¤œà¤¨à¥à¤®à¤¦à¤¿à¤¨ à¤•à¤¾ root vibration reflex behavior à¤•à¥‹ directly shape à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "Pressure phase à¤®à¥‡à¤‚ impulsive à¤¯à¤¾ rigid response pattern à¤‰à¤­à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "action": "Pause rule à¤”à¤° routine anchors à¤¸à¥‡ Mulank intensity à¤•à¥‹ balance à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "bhagyank_description": {
            "narrative": f"Bhagyank {bhagyank} long-term path à¤®à¥‡à¤‚ {bhagyank_signal} theme à¤•à¥‹ drive à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "what": "Bhagyank growth direction à¤”à¤° recurring lesson-cycle à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": "Life-path reduction à¤¸à¥‡ à¤¯à¤¹ destiny flow à¤²à¤—à¤¾à¤¤à¤¾à¤° activate à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "Timing mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° progress à¤§à¥€à¤®à¥€ à¤”à¤° effort heavy à¤®à¤¹à¤¸à¥‚à¤¸ à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Personal Year theme à¤•à¥‡ à¤¸à¤¾à¤¥ annual goals align à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "name_number_analysis": {
            "narrative": f"Name Number {name_number_text} à¤”à¤° compound {name_compound} à¤†à¤ªà¤•à¥€ social projection à¤®à¥‡à¤‚ {name_signal} signal à¤¬à¤¨à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "what": "à¤¨à¤¾à¤® vibration trust, recall à¤”à¤° communication tone à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "à¤…à¤•à¥à¤·à¤°-à¤µà¤¾à¤‡à¤¬à¥à¤°à¥‡à¤¶à¤¨ à¤•à¤¾ à¤¯à¥‹à¤— identity frequency à¤•à¥‹ encode à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "à¤¨à¤¾à¤® mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° clarity à¤”à¤° confidence à¤¦à¥‹à¤¨à¥‹à¤‚ dilute à¤¹à¥‹ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "action": "Consistent spelling use à¤•à¤°à¥‡à¤‚ à¤”à¤° practical à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° target-aligned variant à¤šà¥à¤¨à¥‡à¤‚à¥¤",
        },
        "number_interaction_analysis": {
            "narrative": f"Mulank {mulank}, Bhagyank {bhagyank}, Name {name_number_text} interaction profile à¤®à¥‡à¤‚ harmony-gap signal à¤¦à¤¿à¤– à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤",
            "what": "à¤‡à¤¨ numbers à¤•à¤¾ interaction execution style à¤”à¤° emotional pace à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": "Root-number distance à¤¬à¤¢à¤¼à¤¨à¥‡ à¤ªà¤° internal push-pull à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "Focus à¤”à¤° consistency à¤ªà¤° cycle-wise friction à¤¬à¤¨ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "One-habit-one-correction à¤®à¥‰à¤¡à¤² à¤¸à¥‡ interaction gap à¤•à¤® à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "loshu_grid_interpretation": {
            "narrative": f"Lo Shu present: {present_text} | missing: {missing_text}.",
            "what": "Grid present à¤¬à¤¨à¤¾à¤® missing energies à¤•à¤¾ practical map à¤¦à¥‡à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "à¤œà¤¨à¥à¤®à¤¤à¤¿à¤¥à¤¿ digit distribution à¤¸à¥‡ Lo Shu behavior matrix à¤¨à¤¿à¤•à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": f"Current grid à¤®à¥‡à¤‚ {missing_insight_text} à¤œà¥ˆà¤¸à¥‡ gaps à¤¦à¤¿à¤–à¤¾à¤ˆ à¤¦à¥‡à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "action": "Weekly tracker à¤¸à¥‡ missing themes à¤•à¤¾ progress validate à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "missing_numbers_analysis": {
            "narrative": f"Missing numbers: {missing_text}.",
            "what": "Missing digits behavioral blind zones à¤•à¤¾ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "why": "Absent digits à¤•à¥‡ à¤•à¤¾à¤°à¤£ à¤•à¥à¤› traits conscious effort à¤¸à¥‡ build à¤•à¤°à¤¨à¥€ à¤ªà¤¡à¤¼à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "impact": "Untreated gaps à¤¸à¥‡ repeated friction à¤”à¤° response fatigue à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "à¤¹à¤° missing digit à¤•à¥‡ à¤²à¤¿à¤ micro-habit correction à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "repeating_numbers_impact": {
            "narrative": f"Repeating numbers pattern: {repeating_text}. {repeat_insight_text}.",
            "what": "Repeated digits traits à¤•à¥‹ amplify à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "why": "à¤à¤• à¤¹à¥€ number à¤•à¥€ frequency à¤¬à¤¢à¤¼à¤¨à¥‡ à¤ªà¤° à¤µà¤¹à¥€ behavior loop à¤¬à¤¾à¤°-à¤¬à¤¾à¤° trigger à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "Over-amplification à¤¸à¥‡ rigidity, overthinking à¤¯à¤¾ impulsive response à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Amplified trait à¤•à¥‡ opposite balancing habit à¤œà¥‹à¤¡à¤¼à¥‡à¤‚à¥¤",
        },
        "mobile_number_numerology": {
            "narrative": f"Mobile vibration {mobile_vibration} à¤•à¤¾ classification {mobile_classification} à¤¹à¥ˆà¥¤",
            "what": "Phone-number vibration daily communication tone à¤•à¥‹ shape à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": f"Digit sum {mobile_vibration} core life numbers à¤•à¥‡ à¤¸à¤¾à¤¥ resonance à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¯à¤¾ à¤˜à¤Ÿà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "Mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° distraction à¤”à¤° decision clarity drop à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Supportive ending logic à¤”à¤° disciplined mobile usage à¤°à¤–à¥‡à¤‚à¥¤",
        },
        "mobile_life_number_compatibility": {
            "narrative": f"Mobile vibration {mobile_vibration} à¤¬à¤¨à¤¾à¤® life numbers {mulank}/{bhagyank}: {mobile_classification}.",
            "what": "à¤¯à¤¹ pairing communication smoothness à¤”à¤° response pace à¤•à¤¾ quick indicator à¤¹à¥ˆà¥¤",
            "why": "Mobile frequency à¤”à¤° life-number resonance day-to-day behavior tune à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Compatibility low à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° response delay à¤”à¤° fatigue à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Next number update à¤®à¥‡à¤‚ supportive digit logic prefer à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "email_numerology": {
            "narrative": (
                f"Email vibration {email_vibration or 0} digital identity signal à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤°à¤¹à¥€ à¤¹à¥ˆà¥¤"
                if email_value
                else "à¤ˆà¤®à¥‡à¤² à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆ; detailed email numerology à¤ˆà¤®à¥‡à¤² à¤®à¤¿à¤²à¤¨à¥‡ à¤ªà¤° auto-generate à¤¹à¥‹à¤—à¥€à¥¤"
            ),
            "what": "Email local-part authority à¤”à¤° trust perception à¤ªà¤° à¤…à¤¸à¤° à¤¡à¤¾à¤²à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": "Letter-frequency pattern à¤¡à¤¿à¤œà¤¿à¤Ÿà¤² first impression coding à¤¬à¤¨à¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Weak email signal response quality à¤”à¤° perceived credibility à¤˜à¤Ÿà¤¾ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Short, clear à¤”à¤° number-aligned email naming pattern à¤…à¤ªà¤¨à¤¾à¤à¤à¥¤",
        },
        "numerology_personality_profile": {
            "narrative": f"Personality profile à¤®à¥‡à¤‚ Mulank {mulank} à¤•à¥€ instinct, Bhagyank {bhagyank} à¤•à¥€ direction à¤”à¤° Name {name_number_text} à¤•à¥€ projection à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤°à¥‚à¤ª à¤¸à¥‡ active à¤¹à¥ˆà¤‚à¥¤",
            "what": "à¤¯à¤¹ profile social style, internal nature à¤”à¤° pressure response define à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "Core-number interaction à¤¸à¥‡ thought-action loop à¤•à¥€ default quality à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Blind spots unmanaged à¤°à¤¹à¤¨à¥‡ à¤ªà¤° relationships à¤”à¤° confidence à¤¦à¥‹à¤¨à¥‹à¤‚ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "action": "Strength-led tasks à¤¬à¤¢à¤¼à¤¾à¤à¤ à¤”à¤° blind-spot triggers à¤ªà¤° pause à¤°à¤–à¥‡à¤‚à¥¤",
        },
        "current_life_phase_insight": {
            "narrative": f"Current life phase à¤®à¥‡à¤‚ Personal Year {personal_year} à¤”à¤° risk band '{risk_band}' correction-priority define à¤•à¤° à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "what": "à¤¯à¤¹ à¤šà¤°à¤£ stabilization à¤”à¤° consistency build à¤•à¤°à¤¨à¥‡ à¤•à¤¾ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": "Year vibration à¤”à¤° weakest metric à¤•à¥€ pairing phase intensity à¤¤à¤¯ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "à¤—à¤²à¤¤ priorities à¤°à¤–à¤¨à¥‡ à¤ªà¤° effort high à¤”à¤° output low à¤°à¤¹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "action": "Limited priorities + weekly review cadence à¤¤à¥à¤°à¤‚à¤¤ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "career_financial_tendencies": {
            "narrative": f"Career orientation '{career_industry}' à¤”à¤° financial behavior pattern à¤®à¥‡à¤‚ structure-led growth à¤•à¥€ à¤œà¤°à¥‚à¤°à¤¤ à¤¦à¤¿à¤–à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "what": "Work style depth, accountability à¤”à¤° process-fit à¤®à¥‡à¤‚ à¤¬à¥‡à¤¹à¤¤à¤° à¤šà¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "Core numbers à¤”à¤° discipline signals earning-response loop à¤•à¥‹ shape à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "impact": "Reactive choices income consistency à¤”à¤° savings momentum à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "action": "Monthly finance checkpoints à¤”à¤° role-fit review routine à¤¬à¤¨à¤¾à¤à¤‚à¥¤",
        },
        "relationship_compatibility_patterns": {
            "narrative": f"{compatibility_summary} Current compatibility level: {compatibility_level}.",
            "what": "Relationship pattern communication pace à¤”à¤° emotional style à¤¸à¥‡ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "Core-number resonance expectation matching à¤¯à¤¾ mismatch à¤ªà¥ˆà¤¦à¤¾ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Mismatch phase à¤®à¥‡à¤‚ misunderstanding cycle à¤”à¤° trust fatigue à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Clear boundaries à¤”à¤° calm communication protocol à¤¬à¤¨à¤¾à¤ à¤°à¤–à¥‡à¤‚à¥¤",
        },
        "health_tendencies_from_numbers": {
            "narrative": f"Health tendency numerology view: stress rhythm à¤”à¤° recovery quality à¤¸à¤¬à¤¸à¥‡ à¤…à¤§à¤¿à¤• {weakest_metric} axis à¤¸à¥‡ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥ˆà¥¤",
            "what": "à¤¯à¤¹ wellness tendency layer à¤¹à¥ˆ, medical diagnosis à¤¨à¤¹à¥€à¤‚à¥¤",
            "why": "Number imbalance sleep, stress pace à¤”à¤° recovery discipline à¤ªà¤° à¤…à¤¸à¤° à¤¡à¤¾à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Fatigue build-up à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° clarity à¤”à¤° emotional steadiness à¤•à¤®à¤œà¥‹à¤° à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Breath reset, fixed sleep window à¤”à¤° low-noise shutdown routine à¤°à¤–à¥‡à¤‚à¥¤",
        },
        "personal_year_forecast": {
            "narrative": f"à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ Personal Year {personal_year} year-theme à¤”à¤° action timing à¤•à¥‹ à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤",
            "what": "à¤¯à¤¹ à¤µà¤°à¥à¤· correction-led consistency à¤”à¤° focused progress à¤•à¥‹ support à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": "Birth day/month à¤”à¤° current year à¤•à¥‡ à¤¯à¥‹à¤— à¤¸à¥‡ yearly vibration à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "à¤¸à¤¹à¥€ timing à¤ªà¤° effort à¤•à¤¾ output à¤¬à¥‡à¤¹à¤¤à¤° à¤”à¤° à¤¤à¥‡à¤œà¤¼ à¤®à¤¿à¤²à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "action": f"à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ launches à¤”à¤° decisions à¤•à¥‹ favorable dates ({lucky_text}) à¤®à¥‡à¤‚ à¤°à¤–à¥‡à¤‚à¥¤",
        },
        "lucky_numbers_favorable_dates": {
            "narrative": f"Supportive numbers: {target_text} | favorable dates: {lucky_text}.",
            "what": "à¤¯à¤¹ timing utility à¤¹à¥ˆ, blind superstition à¤¨à¤¹à¥€à¤‚à¥¤",
            "why": "Core-number resonance specific dates à¤ªà¤° action efficiency à¤¬à¤¢à¤¼à¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Aligned windows à¤®à¥‡à¤‚ response quality à¤”à¤° confidence à¤¬à¥‡à¤¹à¤¤à¤° à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "action": "Key meetings, outreach à¤”à¤° agreements date-fit check à¤•à¥‡ à¤¬à¤¾à¤¦ à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "color_alignment": {
            "narrative": f"Favorable colors: {favorable_colors}. Caution colors: {caution_colors}.",
            "what": "Color vibration focus à¤”à¤° mood-stability à¤ªà¤° subtle à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¡à¤¾à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "why": "Dominant number resonance à¤•à¥à¤› tones à¤•à¥‡ à¤¸à¤¾à¤¥ à¤¬à¥‡à¤¹à¤¤à¤° sync à¤¬à¤¨à¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "impact": "Mismatched palette à¤•à¤¾ overuse energy dull à¤¯à¤¾ reactive à¤¬à¤¨à¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "action": "Workspace à¤”à¤° wardrobe à¤®à¥‡à¤‚ favorable colors à¤•à¤¾ controlled à¤‰à¤ªà¤¯à¥‹à¤— à¤•à¤°à¥‡à¤‚à¥¤",
        },
        "remedies_lifestyle_adjustments": {
            "narrative": f"Correction layer: mantra + routine + lifestyle discipline. Dominant support planet: {dominant_planet}.",
            "what": "Practical remedies à¤•à¥‹ daily behavior system à¤¸à¥‡ à¤œà¥‹à¤¡à¤¼à¤¨à¤¾ à¤¸à¤¬à¤¸à¥‡ effective à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "why": "Consistency à¤•à¥‡ à¤¬à¤¿à¤¨à¤¾ corrective signal à¤²à¤‚à¤¬à¥‡ à¤¸à¤®à¤¯ à¤¤à¤• à¤Ÿà¤¿à¤•à¤¤à¤¾ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆà¥¤",
            "impact": "Regular practice à¤¸à¥‡ stability, clarity à¤”à¤° confidence steadily improve à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "action": "Daily short mantra, fixed routine à¤”à¤° weekly correction review à¤°à¤–à¥‡à¤‚à¥¤",
        },
        "closing_numerology_guidance": {
            "narrative": f"Closing synthesis: {full_name} à¤•à¥€ profile correction-ready à¤¹à¥ˆ; primary focus {weakest_metric} stabilization à¤”à¤° {strongest_metric} leverage à¤ªà¤° à¤°à¤¹à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤à¥¤",
            "what": "Profile fundamentally blocked à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆ; pattern workable à¤”à¤° improvable à¤¹à¥ˆà¥¤",
            "why": "Core numbers, Lo Shu gaps à¤”à¤° habits à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤ªà¥à¤°à¤­à¤¾à¤µ final outcomes à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "impact": "Correction ignore à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° repeat cycle à¤”à¤° confidence drift à¤²à¥Œà¤Ÿ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "action": f"Next step: 21-day correction routine, monthly review, à¤”à¤° {city_hint} context à¤®à¥‡à¤‚ practical consistencyà¥¤",
        },
    }

    for key, facts in section_facts.items():
        section = basic_payloads.get(key)
        if not isinstance(section, dict):
            continue

        section["narrative"] = _style_line(key, "narrative", facts["narrative"])
        cards = section.get("cards") or []
        if len(cards) >= 4:
            cards[0]["value"] = _style_line(key, "what", facts["what"])
            cards[1]["value"] = _style_line(key, "why", facts["why"])
            cards[2]["value"] = _style_line(key, "impact", facts["impact"])
            cards[3]["value"] = _style_line(key, "action", facts["action"])

    if isinstance(basic_payloads.get("name_number_analysis"), dict):
        basic_payloads["name_number_analysis"]["bullets"] = [
            f"à¤µà¤¿à¤•à¤²à¥à¤ª {index + 1}: {item.get('option', full_name)} -> {item.get('number', '-')}"
            for index, item in enumerate(name_options[:3])
        ] or [f"à¤µà¤¿à¤•à¤²à¥à¤ª 1: {full_name} -> {target_text.split(',')[0].strip()}"]

    if isinstance(basic_payloads.get("missing_numbers_analysis"), dict):
        basic_payloads["missing_numbers_analysis"]["bullets"] = [
            f"Missing {number}: {BASIC_MISSING_EFFECTS.get(number, {'fix': 'daily correction'})['fix']}"
            for number in list(loshu_missing)[:5]
        ]

    if isinstance(basic_payloads.get("mobile_number_numerology"), dict):
        cards = basic_payloads["mobile_number_numerology"].get("cards") or []
        if len(cards) >= 5:
            cards[4]["value"] = mobile_value or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

    if isinstance(basic_payloads.get("email_numerology"), dict):
        cards = basic_payloads["email_numerology"].get("cards") or []
        if len(cards) >= 5:
            cards[4]["value"] = email_value or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

    if isinstance(basic_payloads.get("personal_year_forecast"), dict):
        cards = basic_payloads["personal_year_forecast"].get("cards") or []
        if len(cards) >= 6:
            cards[4]["value"] = str(personal_year)
            cards[5]["value"] = lucky_text

    if isinstance(basic_payloads.get("lucky_numbers_favorable_dates"), dict):
        cards = basic_payloads["lucky_numbers_favorable_dates"].get("cards") or []
        if len(cards) >= 6:
            cards[4]["value"] = target_text
            cards[5]["value"] = lucky_text

    if isinstance(basic_payloads.get("remedies_lifestyle_adjustments"), dict):
        basic_payloads["remedies_lifestyle_adjustments"]["bullets"] = [
            f"Mantra: {vedic_code}",
            f"Practice: {vedic_parameter}",
            f"Lifestyle: {lifestyle_protocol}",
        ]

    return basic_payloads


def _enrich_basic_payloads(
    basic_payloads: Dict[str, Any],
    *,
    full_name: str,
    first_name: str,
    city_hint: str,
    focus_text: str,
    current_problem: str,
    mulank: int,
    bhagyank: int,
    life_path: int,
    destiny: int,
    expression: int,
    name_number: int,
    name_compound: int,
    loshu_present: Sequence[int],
    loshu_missing: Sequence[int],
    repeating_numbers: Sequence[int],
    mobile_vibration: int,
    mobile_classification: str,
    mobile_value: str,
    email_value: str,
    email_vibration: int,
    compatibility_summary: str,
    compatibility_level: str,
    personal_year: int,
    strongest_metric: str,
    weakest_metric: str,
    risk_band: str,
    lucky_dates: Sequence[int],
    target_numbers: Sequence[int],
    favorable_colors: str,
    caution_colors: str,
    dominant_planet: str,
    vedic_code: str,
    vedic_parameter: str,
    lifestyle_protocol: str,
) -> Dict[str, Any]:
    seed = _stable_seed(
        full_name,
        focus_text,
        current_problem,
        mulank,
        bhagyank,
        life_path,
        destiny,
        expression,
        name_number,
        personal_year,
        ",".join(str(v) for v in loshu_missing),
    )

    mulank_signal = BASIC_NUMBER_MEANINGS.get(mulank or 5, BASIC_NUMBER_MEANINGS[5])["signal"]
    bhagyank_signal = BASIC_NUMBER_MEANINGS.get(bhagyank or 5, BASIC_NUMBER_MEANINGS[5])["signal"]
    name_signal = BASIC_NUMBER_MEANINGS.get(name_number or bhagyank or mulank or 5, BASIC_NUMBER_MEANINGS[5])["signal"]
    risk_primary = _safe_text(risk_band).split("|")[0].strip()
    risk_protocol = _safe_text(risk_band).split("|")[1].strip() if "|" in _safe_text(risk_band) else "à¤¨à¤¿à¤¯à¤®à¤¿à¤¤ à¤¸à¥à¤§à¤¾à¤° à¤ªà¥à¤°à¤•à¥à¤°à¤¿à¤¯à¤¾ à¤œà¤¾à¤°à¥€ à¤°à¤–à¥‡à¤‚"

    present_text = ", ".join(str(v) for v in loshu_present) if loshu_present else "none"
    missing_text = ", ".join(str(v) for v in loshu_missing) if loshu_missing else "none"
    repeating_text = ", ".join(str(v) for v in repeating_numbers) if repeating_numbers else "none"
    lucky_text = ", ".join(str(v) for v in lucky_dates) if lucky_dates else "3, 5, 9"
    target_text = ", ".join(str(v) for v in target_numbers[:4]) if target_numbers else "3, 5, 9"
    focus_hint = _safe_text(focus_text, "à¤œà¥€à¤µà¤¨ à¤¸à¤‚à¤¤à¥à¤²à¤¨")
    concern_hint = _safe_text(current_problem, "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤œà¥€à¤µà¤¨ à¤šà¥à¤¨à¥Œà¤¤à¥€")
    city_display = _safe_text(city_hint, "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¶à¤¹à¤°")
    mobile_state = _safe_text(mobile_classification, "neutral")
    name_number_text = str(name_number) if name_number else "0"

    missing_descriptions = []
    for number in list(loshu_missing)[:4]:
        meta = BASIC_MISSING_EFFECTS.get(number, {"gap": "à¤µà¥à¤¯à¤µà¤¹à¤¾à¤°à¤¿à¤• à¤°à¤¿à¤•à¥à¤¤à¤¿", "fix": "à¤¦à¥ˆà¤¨à¤¿à¤• à¤¸à¥à¤§à¤¾à¤° à¤†à¤¦à¤¤"})
        missing_descriptions.append(f"{number} à¤®à¥‡à¤‚ {meta['gap']}")
    missing_line = " | ".join(missing_descriptions) if missing_descriptions else "à¤®à¥à¤–à¥à¤¯ missing digits à¤¸à¥€à¤®à¤¿à¤¤ à¤¹à¥ˆà¤‚"

    repeat_descriptions = []
    for number in list(repeating_numbers)[:3]:
        repeat_descriptions.append(f"{number} à¤•à¥‡ à¤¦à¥‹à¤¹à¤°à¤¾à¤µ à¤¸à¥‡ {BASIC_REPEAT_EFFECTS.get(number, 'à¤à¤• trait à¤•à¤¾ volume à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ')}")
    repeating_line = " | ".join(repeat_descriptions) if repeat_descriptions else "à¤•à¥‹à¤ˆ à¤¬à¤¡à¤¼à¤¾ à¤¦à¥‹à¤¹à¤°à¤¾à¤µ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆ"

    def _sent(text: str) -> str:
        clean = _safe_text(text)
        if not clean:
            return ""
        if clean.endswith(("à¥¤", ".")):
            return clean
        return f"{clean}à¥¤"

    def _fit_rich(value: str, max_chars: int = 700) -> str:
        text = _safe_text(value)
        if len(text) <= max_chars:
            return text
        window = text[:max_chars]
        end = max(window.rfind("à¥¤"), window.rfind("."))
        if end >= int(max_chars * 0.65):
            return window[: end + 1].strip()
        trimmed = window.rsplit(" ", 1)[0].strip()
        return trimmed if trimmed.endswith(("à¥¤", ".", "â€¦")) else f"{trimmed}â€¦"

    global_fillers: Dict[str, List[str]] = {
        "what": [
            f"à¤¯à¤¹ à¤¸à¤‚à¤•à¥‡à¤¤ {first_name} à¤•à¥‡ à¤°à¥‹à¤œà¤¼à¤®à¤°à¥à¤°à¤¾ à¤•à¥‡ à¤µà¥à¤¯à¤µà¤¹à¤¾à¤°, communication tone à¤”à¤° execution pace à¤®à¥‡à¤‚ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¤à¥Œà¤° à¤ªà¤° à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ",
            f"à¤«à¥‹à¤•à¤¸ '{focus_hint}' à¤”à¤° concern '{concern_hint}' à¤•à¥‡ à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤®à¥‡à¤‚ à¤¯à¤¹ pattern à¤…à¤­à¥€ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤¹à¥ˆ",
            f"{city_display} à¤œà¥ˆà¤¸à¥‡ à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤µà¤¾à¤¤à¤¾à¤µà¤°à¤£ à¤®à¥‡à¤‚ à¤­à¥€ à¤¯à¤¹à¥€ tendency à¤¬à¤¾à¤°-à¤¬à¤¾à¤° à¤‰à¤­à¤°à¤¤à¥€ à¤¹à¥ˆ",
        ],
        "why": [
            f"à¤•à¤¾à¤°à¤£ à¤à¤•à¤² à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆ; Mulank {mulank}, Bhagyank {bhagyank}, Name {name_number_text}, Personal Year {personal_year} à¤”à¤° Lo Shu pattern à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¬à¤¨ à¤°à¤¹à¤¾ à¤¹à¥ˆ",
            f"core stack à¤”à¤° missing digits à¤•à¥€ interaction intensity à¤¸à¥‡ behavior friction à¤•à¤¾ root à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ",
            f"à¤‡à¤¸à¥€ à¤µà¤œà¤¹ à¤¸à¥‡ pattern situational à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ repeatable numerology architecture à¤œà¥ˆà¤¸à¤¾ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ",
        ],
        "impact": [
            f"à¤‡à¤¸à¤•à¤¾ à¤…à¤¸à¤° {weakest_metric}, confidence rhythm à¤”à¤° decision consistency à¤ªà¤° compound à¤¤à¤°à¥€à¤•à¥‡ à¤¸à¥‡ à¤†à¤¤à¤¾ à¤¹à¥ˆ",
            f"à¤…à¤—à¤° corrective action à¤¨ à¤¹à¥‹ à¤¤à¥‹ {risk_primary} band à¤•à¥‡ à¤¸à¤‚à¤•à¥‡à¤¤ à¤”à¤° à¤—à¤¹à¤°à¥‡ à¤¹à¥‹ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            f"à¤¸à¤¹à¥€ handling à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° {strongest_metric} leverage à¤¹à¥‹à¤•à¤° overall stability à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ",
        ],
        "action": [
            "à¤‰à¤ªà¤¾à¤¯à¥‹à¤‚ à¤•à¥‹ 21-day discipline cycle, weekly review à¤”à¤° measurable tracking à¤•à¥‡ à¤¸à¤¾à¤¥ à¤²à¤¾à¤—à¥‚ à¤•à¤°à¤¨à¤¾ à¤œà¤°à¥‚à¤°à¥€ à¤¹à¥ˆ",
            f"weekly execution map à¤¬à¤¨à¤¾à¤•à¤° correction à¤•à¥‹ concern '{concern_hint}' à¤•à¥‡ measurable outcomes à¤¸à¥‡ à¤œà¥‹à¤¡à¤¼à¥‡à¤‚",
            f"à¤›à¥‹à¤Ÿà¥‡ à¤²à¥‡à¤•à¤¿à¤¨ à¤²à¤—à¤¾à¤¤à¤¾à¤° à¤•à¤¦à¤® à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ {weakest_metric} axis à¤®à¥‡à¤‚ durable à¤¸à¥à¤§à¤¾à¤° à¤¬à¤¨à¤¤à¤¾ à¤œà¤¾à¤",
        ],
    }

    dynamic_fillers: Dict[str, List[str]] = {
        "what": [
            f"Core stack {mulank}/{bhagyank}/{name_number_text} à¤”à¤° personal year {personal_year} à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨ à¤…à¤­à¥€ à¤®à¥à¤–à¥à¤¯ à¤¸à¤‚à¤šà¤¾à¤²à¤¨ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡ à¤°à¤¹à¤¾ à¤¹à¥ˆ",
            f"à¤«à¥‹à¤•à¤¸ '{focus_hint}' à¤”à¤° concern '{concern_hint}' à¤•à¥‡ à¤•à¤¾à¤°à¤£ à¤¯à¤¹ à¤¸à¤‚à¤•à¥‡à¤¤ à¤‡à¤¸ à¤¸à¤®à¤¯ à¤”à¤° à¤…à¤§à¤¿à¤• visible à¤¹à¥ˆ",
            f"{city_display} à¤œà¥ˆà¤¸à¥‡ à¤µà¤¾à¤¤à¤¾à¤µà¤°à¤£ à¤®à¥‡à¤‚ à¤­à¥€ à¤¯à¤¹à¥€ à¤ªà¥à¤°à¤µà¥ƒà¤¤à¥à¤¤à¤¿ à¤¦à¥‹à¤¹à¤°à¤•à¤° à¤¸à¤¾à¤®à¤¨à¥‡ à¤†à¤¤à¥€ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤‡à¤¸à¥‡ à¤¸à¥à¤¥à¤¾à¤¯à¥€ behavior signal à¤®à¤¾à¤¨à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
        ],
        "why": [
            f"current root à¤•à¤¾à¤°à¤£ à¤®à¥‡à¤‚ missing cluster ({missing_line}) à¤”à¤° repeating cluster ({repeating_line}) à¤¦à¥‹à¤¨à¥‹à¤‚ à¤•à¤¾ à¤ªà¤°à¤¸à¥à¤ªà¤° à¤¦à¤¬à¤¾à¤µ à¤¶à¤¾à¤®à¤¿à¤² à¤¹à¥ˆ",
            f"risk context '{risk_primary}' à¤¹à¥‹à¤¨à¥‡ à¤¸à¥‡ à¤µà¤¹à¥€ à¤•à¤¾à¤°à¤£ à¤¸à¤¾à¤®à¤¾à¤¨à¥à¤¯ à¤¦à¤¿à¤¨à¥‹à¤‚ à¤•à¥€ à¤¤à¥à¤²à¤¨à¤¾ à¤®à¥‡à¤‚ à¤…à¤§à¤¿à¤• à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¦à¤¿à¤–à¤¾à¤ˆ à¤¦à¥‡ à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚",
            f"stack {mulank}/{bhagyank}/{name_number_text} à¤”à¤° personal year {personal_year} à¤¸à¤¾à¤¥ à¤†à¤¨à¥‡ à¤ªà¤° à¤•à¤¾à¤°à¤£ à¤•à¥‡à¤µà¤² surface-level à¤¨à¤¹à¥€à¤‚ à¤°à¤¹à¤¤à¤¾",
        ],
        "impact": [
            f"à¤…à¤¸à¤° à¤•à¥€ à¤°à¥‡à¤‚à¤œ decision clarity à¤¸à¥‡ à¤²à¥‡à¤•à¤° relationship pacing à¤”à¤° money discipline à¤¤à¤• à¤œà¤¾à¤¤à¥€ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤‡à¤¸à¥‡ à¤à¤• single-issue à¤¨ à¤¸à¤®à¤à¥‡à¤‚",
            f"à¤¯à¤¦à¤¿ unchecked à¤°à¤¹à¤¾ à¤¤à¥‹ weekly output quality à¤˜à¤Ÿ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ à¤”à¤° long-term confidence curve flatter à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
            f"positive correction à¤•à¥€ à¤¸à¥à¤¥à¤¿à¤¤à¤¿ à¤®à¥‡à¤‚ {strongest_metric} à¤•à¥€ à¤Šà¤°à¥à¤œà¤¾ recovery accelerator à¤•à¤¾ à¤•à¤¾à¤® à¤•à¤° à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
        ],
        "action": [
            f"{city_display} à¤œà¥ˆà¤¸à¥‡ context à¤®à¥‡à¤‚ à¤­à¥€ routine discipline à¤²à¤¾à¤—à¥‚ à¤•à¤¿à¤¯à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ à¤¯à¤¦à¤¿ steps measurable à¤¹à¥‹à¤‚ à¤”à¤° review calendar-locked à¤¹à¥‹",
            f"daily correction à¤•à¥‹ identity consistency, communication drill à¤”à¤° timing alignment à¤•à¥‡ à¤¸à¤¾à¤¥ à¤œà¥‹à¤¡à¤¼à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤Ÿà¤¿à¤•à¤¾à¤Š à¤¬à¤¨à¥‡à¤‚",
            f"à¤¹à¤° à¤¸à¤ªà¥à¤¤à¤¾à¤¹ à¤à¤• improvement proof à¤²à¤¿à¤–à¥‡à¤‚, à¤¤à¤¾à¤•à¤¿ progress visible à¤°à¤¹à¥‡ à¤”à¤° motivation volatile à¤¨ à¤¬à¤¨à¥‡",
        ],
    }

    def _style_sentence(section_key: str, slot: str, sentence: str, idx: int) -> str:
        styled = _safe_text(sentence)
        style_modes: Sequence[Dict[str, str]] = (
            {},
            {
                "à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ": "à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ": "à¤¨à¤œà¤¼à¤° à¤†à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ": "à¤…à¤¸à¤° à¤¡à¤¾à¤²à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ": "à¤…à¤¸à¤° à¤®à¥‡à¤‚ à¤† à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤œà¤°à¥‚à¤°à¥€": "à¤…à¤¨à¤¿à¤µà¤¾à¤°à¥à¤¯",
                "à¤¸à¥à¤§à¤¾à¤°": "à¤¬à¥‡à¤¹à¤¤à¤° à¤¬à¤¦à¤²à¤¾à¤µ",
            },
            {
                "à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ": "à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ": "à¤‰à¤­à¤°à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ": "à¤—à¤¹à¤°à¤¾ à¤…à¤¸à¤° à¤¡à¤¾à¤²à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ": "à¤•à¤¾à¤«à¥€ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤œà¤°à¥‚à¤°à¥€": "à¤…à¤¤à¥à¤¯à¤¾à¤µà¤¶à¥à¤¯à¤•",
                "à¤¸à¥à¤§à¤¾à¤°": "à¤•à¤°à¥‡à¤•à¥à¤Ÿà¤¿à¤µ à¤¬à¤¦à¤²à¤¾à¤µ",
            },
        )
        style_mode = (_stable_seed(seed, section_key, slot) + idx) % len(style_modes)
        for source, target in style_modes[style_mode].items():
            styled = styled.replace(source, target)
        prefix_options = [
            "",
            "",
            "",
            "à¤¸à¤‚à¤–à¥à¤¯à¤¾à¤¤à¥à¤®à¤• à¤¦à¥ƒà¤·à¥à¤Ÿà¤¿ à¤¸à¥‡,",
            "à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¯à¤¹ à¤¹à¥ˆ à¤•à¤¿,",
            "à¤…à¤µà¤²à¥‹à¤•à¤¨ à¤¸à¥‡ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥ˆ à¤•à¤¿,",
        ]
        prefix_index = (_stable_seed(seed, section_key, slot) + idx) % len(prefix_options)
        prefix = _safe_text(prefix_options[prefix_index])
        if prefix:
            return _safe_text(f"{prefix} {styled}")
        return styled

    section_lines: Dict[str, Dict[str, List[str]]] = {
        "executive_numerology_summary": {
            "what": [
                f"à¤†à¤ªà¤•à¥€ à¤ªà¥à¤°à¥‹à¤«à¤¼à¤¾à¤‡à¤² à¤®à¥‡à¤‚ Mulank {mulank}, Bhagyank {bhagyank}, Name Number {name_number_text} à¤”à¤° Personal Year {personal_year} à¤à¤• à¤¸à¤¾à¤¥ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤¹à¥ˆà¤‚",
                f"à¤‡à¤¸ à¤¸à¤‚à¤¯à¥‹à¤œà¤¨ à¤¸à¥‡ {mulank_signal} à¤”à¤° {bhagyank_signal} à¤•à¥€ dual rhythm à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¤®à¥‡à¤‚ à¤—à¤¤à¤¿ à¤”à¤° à¤—à¤¹à¤°à¤¾à¤ˆ à¤¦à¥‹à¤¨à¥‹à¤‚ à¤¸à¤¾à¤¥ à¤šà¤²à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "why": [
                f"à¤œà¤¬ identity signal ({name_signal}) à¤”à¤° life direction ({bhagyank_signal}) à¤…à¤²à¤— à¤—à¤¤à¤¿ à¤¸à¥‡ à¤•à¤¾à¤® à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤¤à¥‹ à¤…à¤‚à¤¦à¤°-à¤¬à¤¾à¤¹à¤° à¤•à¥‡ à¤…à¤¨à¥à¤­à¤µ à¤®à¥‡à¤‚ à¤…à¤‚à¤¤à¤° à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ",
                f"Lo Shu missing pattern ({missing_text}) à¤‡à¤¸ à¤…à¤‚à¤¤à¤° à¤•à¥‹ à¤”à¤° à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ à¤•à¥à¤¯à¥‹à¤‚à¤•à¤¿ à¤•à¥à¤› behavioral supports à¤ªà¥à¤°à¤¾à¤•à¥ƒà¤¤à¤¿à¤• à¤°à¥‚à¤ª à¤¸à¥‡ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤°à¤¹à¤¤à¥‡",
            ],
            "impact": [
                f"à¤ªà¥à¤°à¤­à¤¾à¤µ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ à¤•à¤­à¥€ high clarity à¤”à¤° à¤•à¤­à¥€ hesitation à¤¦à¤¿à¤– à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¤¸à¥‡ {weakest_metric} à¤®à¥‡à¤‚ fluctuation à¤†à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤¯à¤¹ à¤‰à¤¤à¤¾à¤°-à¤šà¤¢à¤¼à¤¾à¤µ long-term confidence à¤”à¤° trust consistency à¤¦à¥‹à¤¨à¥‹à¤‚ à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "action": [
                "à¤ªà¤¹à¤²à¤¾ à¤•à¤¦à¤® profile simplification à¤¹à¥ˆ: à¤à¤• à¤¸à¤®à¤¯ à¤®à¥‡à¤‚ à¤•à¤® goals à¤²à¥‡à¤•à¤° à¤‰à¤¨à¥à¤¹à¥‡à¤‚ rigorously à¤ªà¥‚à¤°à¤¾ à¤•à¤°à¥‡à¤‚",
                f"à¤¦à¥‚à¤¸à¤°à¤¾ à¤•à¤¦à¤® weekly reflection à¤¹à¥ˆ à¤œà¤¿à¤¸à¤®à¥‡à¤‚ à¤†à¤ª à¤¦à¥‡à¤–à¥‡à¤‚ à¤•à¤¿ à¤•à¥Œà¤¨-à¤¸à¤¾ à¤µà¥à¤¯à¤µà¤¹à¤¾à¤° à¤†à¤ªà¤•à¥‡ à¤®à¥à¤–à¥à¤¯ focus '{focus_hint}' à¤•à¥‹ support à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆ",
            ],
        },
        "core_numbers_analysis": {
            "what": [
                f"Core stack à¤®à¥‡à¤‚ Mulank {mulank} instinct, Bhagyank {bhagyank} direction, Destiny {destiny} execution frame à¤”à¤° Expression {expression} communication style à¤•à¥‹ define à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ",
                f"Name Number {name_number_text} à¤‡à¤¸ architecture à¤®à¥‡à¤‚ public perception layer à¤œà¥‹à¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¤¸à¥‡ capability à¤•à¥€ social readability à¤¤à¤¯ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ",
            ],
            "why": [
                "à¤¯à¥‡ à¤¸à¤­à¥€ numbers à¤…à¤²à¤—-à¤…à¤²à¤— behavior layers à¤•à¥‹ à¤¨à¤¿à¤¯à¤‚à¤¤à¥à¤°à¤¿à¤¤ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤‡à¤¸à¤²à¤¿à¤ à¤‡à¤¨à¥à¤¹à¥‡à¤‚ à¤…à¤²à¤—-à¤…à¤²à¤— à¤ªà¤¢à¤¼à¤¨à¥‡ à¤•à¥‡ à¤¬à¤œà¤¾à¤¯ integrated à¤°à¥‚à¤ª à¤®à¥‡à¤‚ à¤¦à¥‡à¤–à¤¨à¤¾ à¤œà¤°à¥‚à¤°à¥€ à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤œà¤¬ à¤‡à¤¨ layers à¤®à¥‡à¤‚ alignment à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ à¤¤à¥‹ flow smooth à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆ, à¤”à¤° mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° start à¤”à¤° finish à¤•à¥‡ à¤¬à¥€à¤š gap à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "impact": [
                "à¤‡à¤¸ à¤¸à¤‚à¤°à¤šà¤¨à¤¾ à¤•à¤¾ à¤…à¤¸à¤° à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤•à¥€ à¤—à¤¤à¤¿, à¤¸à¤‚à¤šà¤¾à¤° à¤•à¥€ à¤¸à¥à¤ªà¤·à¥à¤Ÿà¤¤à¤¾, accountability à¤”à¤° à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤•à¥€ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤ªà¤° à¤¸à¥€à¤§à¥‡ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤¸à¤•à¥à¤·à¤® à¤¹à¥‹à¤¨à¥‡ à¤•à¥‡ à¤¬à¤¾à¤µà¤œà¥‚à¤¦ inconsistent à¤¦à¤¿à¤– à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ à¤¯à¤¦à¤¿ core layers à¤à¤• à¤¹à¥€ à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ synchronized à¤¨ à¤¹à¥‹à¤‚",
            ],
            "action": [
                "à¤¹à¤° à¤¸à¤ªà¥à¤¤à¤¾à¤¹ top-3 priorities à¤•à¥‹ core numbers à¤•à¥‡ à¤¹à¤¿à¤¸à¤¾à¤¬ à¤¸à¥‡ map à¤•à¤°à¥‡à¤‚: à¤•à¥Œà¤¨-à¤¸à¤¾ à¤•à¤¾à¤® instinct fit à¤¹à¥ˆ à¤”à¤° à¤•à¥Œà¤¨-à¤¸à¤¾ direction fit",
                "decision à¤•à¥‡ à¤¬à¤¾à¤¦ review loop à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ architecture-driven à¤¸à¥à¤§à¤¾à¤° à¤µà¥à¤¯à¤µà¤¹à¤¾à¤° à¤®à¥‡à¤‚ à¤‰à¤¤à¤° à¤¸à¤•à¥‡",
            ],
        },
        "mulank_description": {
            "what": [
                f"Mulank {mulank} à¤†à¤ªà¤•à¥‡ reflex behavior à¤•à¤¾ à¤®à¥à¤–à¥à¤¯ à¤Ÿà¥à¤°à¤¿à¤—à¤° à¤¹à¥ˆ à¤”à¤° à¤ªà¤¹à¤²à¥€ à¤ªà¥à¤°à¤¤à¤¿à¤•à¥à¤°à¤¿à¤¯à¤¾ à¤•à¥‡ à¤Ÿà¥‹à¤¨ à¤®à¥‡à¤‚ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤‡à¤¸ à¤…à¤‚à¤• à¤•à¥€ à¤µà¤œà¤¹ à¤¸à¥‡ à¤†à¤ªà¤•à¥€ natural style à¤®à¥‡à¤‚ {mulank_signal} à¤ªà¥à¤°à¤®à¥à¤– à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆ, à¤–à¤¾à¤¸à¤•à¤° à¤œà¤¬ à¤¸à¥à¤¥à¤¿à¤¤à¤¿ à¤¨à¤ˆ à¤¯à¤¾ urgent à¤¹à¥‹",
            ],
            "why": [
                "Mulank à¤œà¤¨à¥à¤®à¤¦à¤¿à¤¨ à¤•à¥€ à¤®à¥‚à¤² à¤†à¤µà¥ƒà¤¤à¥à¤¤à¤¿ à¤¸à¥‡ à¤¨à¤¿à¤•à¤²à¤¤à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤¯à¤¹ subconscious response pattern à¤ªà¤° à¤¸à¥€à¤§à¤¾ à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¡à¤¾à¤²à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤¯à¤¦à¤¿ Mulank à¤Šà¤°à¥à¤œà¤¾ à¤”à¤° Name Number {name_number_text} à¤•à¥€ à¤…à¤­à¤¿à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤®à¥‡à¤‚ à¤…à¤‚à¤¤à¤° à¤¹à¥‹ à¤¤à¥‹ à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤•à¥€ intent à¤”à¤° expression à¤…à¤²à¤— à¤¦à¤¿à¤–à¤¾à¤ˆ à¤¦à¥‡à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "impact": [
                "à¤‡à¤¸à¤¸à¥‡ impulsive jumps, delayed closure à¤¯à¤¾ mixed social signals à¤œà¥ˆà¤¸à¥‡ à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨ à¤¬à¤¨ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                "stress phase à¤®à¥‡à¤‚ à¤¯à¤¹à¥€ à¤ªà¥à¤°à¤µà¥ƒà¤¤à¥à¤¤à¤¿ confidence drift à¤”à¤° communication inconsistency à¤•à¥‹ à¤¬à¤¢à¤¼à¤¾ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
            ],
            "action": [
                "response-pause drill à¤…à¤ªà¤¨à¤¾à¤à¤‚: à¤¤à¥à¤°à¤‚à¤¤ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤µà¤¾à¤²à¥‡ à¤•à¥à¤·à¤£à¥‹à¤‚ à¤®à¥‡à¤‚ à¤›à¥‹à¤Ÿà¤¾ à¤µà¤¿à¤°à¤¾à¤®, à¤«à¤¿à¤° à¤²à¤¿à¤–à¤¿à¤¤ à¤¨à¤¿à¤°à¥à¤£à¤¯",
                "daily routine à¤®à¥‡à¤‚ à¤à¤• non-negotiable execution block à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ instinctive energy productive à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ à¤œà¤¾à¤",
            ],
        },
        "bhagyank_description": {
            "what": [
                f"Bhagyank {bhagyank} à¤†à¤ªà¤•à¥€ long-term à¤¦à¤¿à¤¶à¤¾, maturity pattern à¤”à¤° recurring life lessons à¤•à¤¾ à¤†à¤§à¤¾à¤° à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤‡à¤¸ à¤…à¤‚à¤• à¤•à¥€ à¤µà¤œà¤¹ à¤¸à¥‡ {bhagyank_signal} theme à¤¬à¤¾à¤°-à¤¬à¤¾à¤° à¤œà¥€à¤µà¤¨ à¤•à¥‡ à¤…à¤²à¤— à¤šà¤°à¤£à¥‹à¤‚ à¤®à¥‡à¤‚ à¤‰à¤­à¤°à¤¤à¥€ à¤¹à¥ˆ",
            ],
            "why": [
                "Bhagyank date-reduction à¤¸à¥‡ à¤¨à¤¿à¤•à¤²à¤•à¤° life-cycle pressure à¤•à¥‹ à¤¦à¤°à¥à¤¶à¤¾à¤¤à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤¯à¤¹ growth à¤•à¥€ à¤ªà¥à¤°à¤¾à¤•à¥ƒà¤¤à¤¿à¤• à¤²à¤¯ à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ",
                f"Life Path {life_path} à¤”à¤° Destiny {destiny} à¤•à¥‡ à¤¸à¤¾à¤¥ à¤‡à¤¸à¤•à¤¾ à¤®à¥‡à¤² à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ progress steady à¤¹à¥‹à¤—à¥€ à¤¯à¤¾ fragmented",
            ],
            "impact": [
                "alignment à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° à¤¦à¤¿à¤¶à¤¾ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆ, à¤²à¥‡à¤•à¤¿à¤¨ mismatch à¤®à¥‡à¤‚ à¤®à¥‡à¤¹à¤¨à¤¤ à¤¬à¤¢à¤¼à¤•à¤° à¤­à¥€ output à¤¤à¥à¤²à¤¨à¤¾à¤¤à¥à¤®à¤• à¤°à¥‚à¤ª à¤¸à¥‡ à¤•à¤® à¤¦à¤¿à¤– à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤—à¤²à¤¤ à¤¸à¤®à¤¯ à¤ªà¤° à¤¬à¤¡à¤¼à¥‡ commitments à¤²à¥‡à¤¨à¥‡ à¤¸à¥‡ frustration à¤”à¤° reset cycles à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "action": [
                "annual goals à¤•à¥‹ quarterly milestones à¤®à¥‡à¤‚ à¤¤à¥‹à¤¡à¤¼à¥‡à¤‚ à¤”à¤° à¤¹à¤° milestone à¤•à¥‹ personal-year theme à¤¸à¥‡ validate à¤•à¤°à¥‡à¤‚",
                "long-term decisions à¤®à¥‡à¤‚ readiness checklist à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ direction drift à¤¨ à¤¹à¥‹",
            ],
        },
        "name_number_analysis": {
            "what": [
                f"Name Number {name_number_text} à¤”à¤° compound {name_compound} à¤†à¤ªà¤•à¥€ public memory, trust signal à¤”à¤° communication impression à¤•à¥‹ shape à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                f"à¤¯à¤¹ layer à¤¬à¤¤à¤¾à¤¤à¥€ à¤¹à¥ˆ à¤•à¤¿ à¤²à¥‹à¤— à¤†à¤ªà¤•à¥€ presence à¤•à¥‹ structured, warm, assertive à¤¯à¤¾ reserved à¤•à¥ˆà¤¸à¥‡ à¤ªà¤¢à¤¼à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "why": [
                "à¤¨à¤¾à¤® à¤•à¥€ à¤…à¤•à¥à¤·à¤°-à¤†à¤µà¥ƒà¤¤à¥à¤¤à¤¿ identity frequency à¤¬à¤¨à¤¾à¤¤à¥€ à¤¹à¥ˆ; spelling consistency à¤”à¤° usage frequency à¤‡à¤¸à¤•à¥‡ à¤ªà¥à¤°à¤­à¤¾à¤µ à¤•à¥‹ à¤¬à¤¢à¤¼à¤¾à¤¤à¥€ à¤¹à¥ˆ",
                f"core stack à¤¸à¥‡ à¤‡à¤¸à¤•à¤¾ alignment à¤•à¤®à¤œà¥‹à¤° à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° perception gap à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¹à¤¾à¤‚ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤…à¤§à¤¿à¤• à¤ªà¤° projection à¤•à¤® à¤¦à¤¿à¤–à¤¤à¥€ à¤¹à¥ˆ",
            ],
            "impact": [
                "impact à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ clarity loss, social hesitation, delayed trust formation à¤”à¤° authority dilution à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤¯à¤¹ gap professional à¤”à¤° personal à¤¦à¥‹à¤¨à¥‹à¤‚ interactions à¤®à¥‡à¤‚ conversion quality à¤•à¥‹ à¤•à¤® à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "action": [
                "à¤à¤• standard spelling à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤•à¤°à¥‡à¤‚ à¤”à¤° à¤¸à¤­à¥€ public surfaces à¤ªà¤° à¤µà¤¹à¥€ à¤°à¤–à¥‡à¤‚",
                f"à¤œà¤¹à¤¾à¤‚ practical à¤¹à¥‹, target numbers ({target_text}) à¤•à¥€ à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ identity consistency test à¤•à¤°à¥‡à¤‚",
            ],
        },
        "number_interaction_analysis": {
            "what": [
                f"Mulank {mulank}, Bhagyank {bhagyank} à¤”à¤° Name Number {name_number_text} à¤•à¥‡ à¤¬à¥€à¤š interaction à¤†à¤ªà¤•à¥€ inner drive à¤”à¤° outer expression à¤•à¤¾ à¤¸à¤®à¤¨à¥à¤µà¤¯ à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤¯à¤¹à¥€ combination à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ à¤†à¤ª tension à¤®à¥‡à¤‚ integrated à¤¦à¤¿à¤–à¥‡à¤‚à¤—à¥‡ à¤¯à¤¾ fragmented",
            ],
            "why": [
                "à¤œà¤¬ reflex layer, direction layer à¤”à¤° identity layer à¤•à¥€ à¤—à¤¤à¤¿ à¤…à¤²à¤— à¤¹à¥‹ à¤œà¤¾à¤¤à¥€ à¤¹à¥ˆ à¤¤à¥‹ internal push-pull à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ",
                f"Lo Shu missing cluster ({missing_text}) à¤‡à¤¸ tension à¤•à¥‹ amplify à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ à¤•à¥à¤¯à¥‹à¤‚à¤•à¤¿ stabilizing supports à¤•à¤® à¤¹à¥‹ à¤œà¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "impact": [
                "à¤¯à¤¹ à¤¸à¥à¤¥à¤¿à¤¤à¤¿ decision reversals, communication mismatch à¤”à¤° execution fatigue à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ à¤¦à¤¿à¤–à¤¾à¤ˆ à¤¦à¥‡ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
                "à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ intent à¤¸à¥‡ committed à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ, à¤ªà¤° behavior rhythm inconsistent à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° outcome quality à¤—à¤¿à¤°à¤¤à¥€ à¤¹à¥ˆ",
            ],
            "action": [
                "interaction correction chart à¤¬à¤¨à¤¾à¤à¤‚: trigger, old response, corrected response, measurable result",
                "weekly à¤¦à¥‹ à¤˜à¤Ÿà¤¨à¤¾à¤à¤‚ à¤šà¥à¤¨à¤•à¤° à¤¦à¥‡à¤–à¥‡à¤‚ à¤•à¤¿ à¤†à¤ªà¤¨à¥‡ impulse à¤”à¤° direction à¤•à¥‹ à¤•à¤¿à¤¤à¤¨à¤¾ sync à¤•à¤¿à¤¯à¤¾",
            ],
        },
        "loshu_grid_interpretation": {
            "what": [
                f"Lo Shu layout à¤®à¥‡à¤‚ present digits ({present_text}) à¤†à¤ªà¤•à¥€ available strengths à¤¦à¤¿à¤–à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤”à¤° missing digits ({missing_text}) conscious correction zones à¤¬à¤¤à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                "à¤¯à¤¹ grid à¤•à¥‡à¤µà¤² à¤¸à¥‚à¤šà¥€ à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ behavior wiring à¤•à¤¾ practical map à¤¹à¥ˆ",
            ],
            "why": [
                "grid à¤œà¤¨à¥à¤®à¤¤à¤¿à¤¥à¤¿ à¤•à¥‡ digit distribution à¤¸à¥‡ à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤¯à¤¹ à¤®à¤¾à¤¨à¤¸à¤¿à¤• rhythm, routine discipline à¤”à¤° emotional handling à¤•à¤¾ à¤†à¤§à¤¾à¤° à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤†à¤ªà¤•à¥‡ pattern à¤®à¥‡à¤‚ {missing_line} à¤œà¥ˆà¤¸à¥‡ à¤¸à¤‚à¤•à¥‡à¤¤ combined à¤µà¥à¤¯à¤µà¤¹à¤¾à¤°à¤¿à¤• gaps à¤•à¥€ à¤“à¤° à¤‡à¤¶à¤¾à¤°à¤¾ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "impact": [
                "à¤…à¤¸à¤° à¤¯à¤¹ à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ à¤•à¥à¤› à¤•à¥à¤·à¥‡à¤¤à¥à¤°à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¤à¥‡à¤œà¤¼ à¤ªà¥à¤°à¤—à¤¤à¤¿ à¤”à¤° à¤•à¥à¤› à¤®à¥‡à¤‚ repeated friction à¤¸à¤¾à¤¥-à¤¸à¤¾à¤¥ à¤šà¤²à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                "à¤…à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ grid à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ planning à¤¤à¥‹ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ à¤ªà¤° sustained follow-through à¤Ÿà¥‚à¤Ÿ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "action": [
                "Lo Shu behavior tracker à¤¬à¤¨à¤¾à¤à¤‚: communication, routine, money, recovery, closure à¤ªà¤¾à¤‚à¤š axes à¤ªà¤° weekly score à¤°à¤–à¥‡à¤‚",
                "missing digits à¤•à¥‡ à¤²à¤¿à¤ micro-habit correction à¤°à¤–à¥‡à¤‚ à¤”à¤° 21-day cycles à¤®à¥‡à¤‚ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¦à¥‡à¤–à¥‡à¤‚",
            ],
        },
        "missing_numbers_analysis": {
            "what": [
                f"Missing digits ({missing_text}) à¤•à¤¾ à¤®à¤¤à¤²à¤¬ à¤¹à¥ˆ à¤•à¤¿ à¤•à¥à¤› behavioral muscles naturally strong à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆà¤‚ à¤”à¤° à¤‰à¤¨à¥à¤¹à¥‡à¤‚ consciously train à¤•à¤°à¤¨à¤¾ à¤¹à¥‹à¤—à¤¾",
                "à¤¯à¥‡ gaps isolated à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ combined pattern à¤¬à¤¨à¤¾à¤•à¤° daily behavior à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "why": [
                "à¤œà¤¬ à¤¸à¤‚à¤¬à¤‚à¤§à¤¿à¤¤ digits à¤œà¤¨à¥à¤® pattern à¤®à¥‡à¤‚ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹à¤¤à¥‡ à¤¤à¥‹ à¤‰à¤¨à¤•à¥‡ à¤—à¥à¤£ à¤¸à¥à¤µà¤¤à¤ƒ à¤¨à¤¹à¥€à¤‚ à¤†à¤¤à¥‡ à¤”à¤° à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ pressure à¤®à¥‡à¤‚ reactive mode à¤šà¥à¤¨à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤‡à¤¸ à¤µà¤œà¤¹ à¤¸à¥‡ à¤•à¥à¤› à¤•à¥à¤·à¥‡à¤¤à¥à¤°à¥‹à¤‚ à¤®à¥‡à¤‚ repeated strain à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ, à¤­à¤²à¥‡ core intent à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤”à¤° à¤¸à¤•à¤¾à¤°à¤¾à¤¤à¥à¤®à¤• à¤¹à¥‹",
            ],
            "impact": [
                "impact à¤®à¥‡à¤‚ communication breaks, delayed closure, habit inconsistency à¤”à¤° decision fatigue à¤¶à¤¾à¤®à¤¿à¤² à¤¹à¥‹ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                "à¤¦à¥€à¤°à¥à¤˜à¤•à¤¾à¤² à¤®à¥‡à¤‚ à¤¯à¤¹à¥€ gaps confidence à¤•à¥‹ à¤§à¥€à¤®à¥‡-à¤§à¥€à¤®à¥‡ à¤•à¤®à¤œà¥‹à¤° à¤•à¤° à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "action": [
                "à¤¹à¤° missing digit à¤•à¥‡ à¤²à¤¿à¤ à¤à¤• targeted corrective habit à¤¤à¤¯ à¤•à¤°à¥‡à¤‚ à¤”à¤° à¤‰à¤¸à¥‡ measurable outcome à¤¸à¥‡ à¤œà¥‹à¤¡à¤¼à¥‡à¤‚",
                "monthly review à¤®à¥‡à¤‚ à¤¦à¥‡à¤–à¥‡à¤‚ à¤•à¥Œà¤¨-à¤¸à¥‡ gaps à¤¸à¥à¤§à¤° à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚ à¤”à¤° à¤•à¤¿à¤¨à¥à¤¹à¥‡à¤‚ stronger intervention à¤•à¥€ à¤œà¤°à¥‚à¤°à¤¤ à¤¹à¥ˆ",
            ],
        },
        "repeating_numbers_impact": {
            "what": [
                f"Repeating pattern ({repeating_text}) à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ à¤†à¤ªà¤•à¥€ à¤•à¥à¤› traits amplified mode à¤®à¥‡à¤‚ à¤šà¤²à¤¤à¥€ à¤¹à¥ˆà¤‚ à¤”à¤° behavior volume à¤¸à¤¾à¤®à¤¾à¤¨à¥à¤¯ à¤¸à¥‡ à¤…à¤§à¤¿à¤• à¤¹à¥‹ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤†à¤ªà¤•à¥‡ case à¤®à¥‡à¤‚ {repeating_line} à¤œà¥ˆà¤¸à¥€ tendencies visible à¤¹à¥ˆà¤‚, à¤œà¤¿à¤¨à¥à¤¹à¥‡à¤‚ à¤¸à¤¹à¥€ channel à¤®à¤¿à¤²à¥‡ à¤¤à¥‹ à¤¯à¤¹ advantage à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¤‚",
            ],
            "why": [
                "à¤à¤• digit à¤•à¤¾ à¤¬à¤¾à¤°-à¤¬à¤¾à¤° à¤†à¤¨à¤¾ mind à¤•à¥‹ familiar response loop à¤®à¥‡à¤‚ à¤°à¤–à¤¤à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤µà¤¹à¥€ pattern à¤…à¤²à¤— contexts à¤®à¥‡à¤‚ à¤­à¥€ repeat à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤œà¤¬ amplification à¤”à¤° missing pattern à¤¸à¤¾à¤¥ à¤†à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤¤à¥‹ overuse à¤”à¤° underdevelopment à¤•à¤¾ à¤®à¤¿à¤¶à¥à¤°à¤¿à¤¤ imbalance à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "impact": [
                "à¤‡à¤¸à¤•à¤¾ à¤…à¤¸à¤° à¤¯à¤¾ à¤¤à¥‹ high performance spikes à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ à¤¯à¤¾ overthinking/rigidity à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚",
                "à¤¯à¤¦à¤¿ modulation à¤¨ à¤¹à¥‹ à¤¤à¥‹ à¤¸à¤‚à¤¬à¤‚à¤§à¥‹à¤‚ à¤”à¤° à¤•à¤¾à¤® à¤¦à¥‹à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ response quality uneven à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
            ],
            "action": [
                "à¤¹à¤° amplified trait à¤•à¥‡ à¤¸à¤¾à¤¥ opposite balancing habit à¤œà¥‹à¤¡à¤¼à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ behavior range à¤¨à¤¿à¤¯à¤‚à¤¤à¥à¤°à¤¿à¤¤ à¤°à¤¹à¥‡",
                "daily quick log à¤°à¤–à¥‡à¤‚: à¤†à¤œ amplification à¤¨à¥‡ à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾ à¤•à¥€ à¤¯à¤¾ friction à¤¬à¤¨à¤¾à¤¯à¤¾",
            ],
        },
        "mobile_number_numerology": {
            "what": [
                f"Mobile vibration {mobile_vibration} ({mobile_state}) à¤†à¤ªà¤•à¥€ daily communication energy, response style à¤”à¤° interaction clarity à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ",
                f"current number signal à¤¸à¥‡ message timing à¤”à¤° conversational tone à¤®à¥‡à¤‚ subtle pattern à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "why": [
                f"digit-sum resonance core life numbers à¤•à¥‡ à¤¸à¤¾à¤¥ sync à¤¯à¤¾ mismatch à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¤¸à¥‡ communication fatigue à¤•à¤¾ à¤¸à¥à¤¤à¤° à¤¬à¤¦à¤²à¤¤à¤¾ à¤¹à¥ˆ",
                f"à¤œà¤¬ mobile signal à¤”à¤° name identity à¤…à¤²à¤— à¤¦à¤¿à¤¶à¤¾ à¤®à¥‡à¤‚ à¤¹à¥‹à¤‚ à¤¤à¥‹ expression noise à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "impact": [
                "à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ delayed responses, unclear follow-ups à¤”à¤° mental distraction à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
                f"à¤¯à¤¹ pattern {weakest_metric} à¤”à¤° confidence consistency à¤•à¥‹ à¤­à¥€ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "action": [
                "phone hygiene protocol à¤…à¤ªà¤¨à¤¾à¤à¤‚: response windows, callback slots à¤”à¤° notification boundaries à¤¤à¤¯ à¤•à¤°à¥‡à¤‚",
                "à¤¯à¤¦à¤¿ future à¤®à¥‡à¤‚ number change à¤¹à¥‹ à¤¤à¥‹ target-compatible ending logic à¤ªà¤° à¤µà¤¿à¤šà¤¾à¤° à¤•à¤°à¥‡à¤‚",
            ],
        },
        "mobile_life_number_compatibility": {
            "what": [
                f"mobile vibration {mobile_vibration} à¤”à¤° life stack {mulank}/{bhagyank} à¤•à¤¾ compatibility signal à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ à¤°à¥‹à¤œà¤¼à¤®à¤°à¥à¤°à¤¾ à¤•à¤¾ response flow à¤•à¤¿à¤¤à¤¨à¤¾ smooth à¤°à¤¹à¥‡à¤—à¤¾",
                f"à¤…à¤­à¥€ à¤•à¤¾ classification ({mobile_state}) communication discipline à¤•à¥€ à¤†à¤µà¤¶à¥à¤¯à¤•à¤¤à¤¾ à¤•à¤¾ à¤¸à¥à¤¤à¤° à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "why": [
                "mobile frequency micro-decisions à¤ªà¤° à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¡à¤¾à¤²à¤¤à¥€ à¤¹à¥ˆ; life numbers à¤¸à¥‡ mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° cognitive switching load à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ",
                "à¤¯à¤¹à¥€ à¤•à¤¾à¤°à¤£ à¤¹à¥ˆ à¤•à¤¿ à¤•à¥à¤› à¤¦à¤¿à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ responsiveness à¤…à¤šà¥à¤›à¤¾ à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆ à¤”à¤° à¤•à¥à¤› à¤¦à¤¿à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ unplanned delays à¤†à¤¤à¥‡ à¤¹à¥ˆà¤‚",
            ],
            "impact": [
                "à¤ªà¥à¤°à¤­à¤¾à¤µ à¤®à¥‡à¤‚ inconsistent replies, conversation fatigue à¤”à¤° priority confusion à¤¶à¤¾à¤®à¤¿à¤² à¤¹à¥‹ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                "long-term à¤®à¥‡à¤‚ à¤¯à¤¹ à¤­à¤°à¥‹à¤¸à¤¾ à¤”à¤° relationship pacing à¤¦à¥‹à¤¨à¥‹à¤‚ à¤ªà¤° à¤…à¤¸à¤° à¤¡à¤¾à¤² à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
            ],
            "action": [
                "communication rules à¤²à¤¿à¤–à¤¿à¤¤ à¤•à¤°à¥‡à¤‚: urgent, important à¤”à¤° routine responses à¤•à¥‡ à¤²à¤¿à¤ à¤…à¤²à¤— windows à¤°à¤–à¥‡à¤‚",
                "à¤¸à¤ªà¥à¤¤à¤¾à¤¹ à¤®à¥‡à¤‚ à¤à¤• à¤¬à¤¾à¤° interaction audit à¤•à¤°à¥‡à¤‚ à¤”à¤° friction patterns à¤•à¥‹ à¤•à¤® à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ behavior tweaks à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚",
            ],
        },
    }

    section_lines.update(
        {
            "email_numerology": {
                "what": [
                    f"Email vibration {email_vibration or 0} à¤†à¤ªà¤•à¥€ digital identity readability, professionalism signal à¤”à¤° trust perception à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ",
                    "email handle à¤•à¤¾ tone à¤…à¤•à¥à¤¸à¤° first response à¤•à¥€ quality à¤”à¤° seriousness à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤¯à¤¹ identity à¤•à¤¾ functional à¤¹à¤¿à¤¸à¥à¤¸à¤¾ à¤¹à¥ˆ",
                ],
                "why": [
                    "email numerology à¤…à¤•à¥à¤·à¤°-à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨, naming clarity à¤”à¤° consistency à¤¸à¥‡ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆ; à¤¯à¤¹ à¤•à¥‡à¤µà¤² number à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ signal architecture à¤¹à¥ˆ",
                    f"Name Number {name_number_text} à¤”à¤° email vibration à¤®à¥‡à¤‚ à¤¤à¤¾à¤²à¤®à¥‡à¤² à¤°à¤¹à¤¨à¥‡ à¤ªà¤° public identity coherent à¤¦à¤¿à¤–à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "impact": [
                    "mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤¸à¤•à¥à¤·à¤® à¤¹à¥‹à¤¨à¥‡ à¤•à¥‡ à¤¬à¤¾à¤µà¤œà¥‚à¤¦ online communication à¤®à¥‡à¤‚ clarity loss à¤”à¤° delayed trust à¤•à¤¾ à¤¸à¤¾à¤®à¤¨à¤¾ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                    "career, outreach à¤”à¤° formal à¤¸à¤‚à¤¬à¤‚à¤§à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¯à¤¹ gap conversion quality à¤”à¤° credibility perception à¤•à¥‹ à¤•à¤®à¤œà¥‹à¤° à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "action": [
                    "email naming à¤•à¥‹ short, clear à¤”à¤° identity-consistent à¤°à¤–à¥‡à¤‚; random digits à¤”à¤° à¤…à¤¨à¤¾à¤µà¤¶à¥à¤¯à¤• separators à¤•à¤® à¤•à¤°à¥‡à¤‚",
                    "display name, signature à¤”à¤° profile naming à¤•à¥‹ à¤à¤•à¤°à¥‚à¤ª à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ trust signal stable à¤¬à¤¨à¥‡",
                ],
            },
            "numerology_personality_profile": {
                "what": [
                    f"à¤†à¤ªà¤•à¥€ personality profile à¤®à¥‡à¤‚ Mulank {mulank} à¤•à¥€ instinct, Bhagyank {bhagyank} à¤•à¥€ direction à¤”à¤° Name {name_number_text} à¤•à¥€ projection à¤à¤• à¤¸à¤¾à¤¥ à¤•à¤¾à¤® à¤•à¤°à¤¤à¥€ à¤¹à¥ˆ",
                    "à¤‡à¤¸ à¤¸à¤‚à¤¯à¥‹à¤œà¤¨ à¤¸à¥‡ à¤†à¤ª context-sensitive à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤¦à¤¿à¤–à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤œà¥‹ à¤•à¤­à¥€ à¤¬à¤¹à¥à¤¤ decisive à¤”à¤° à¤•à¤­à¥€ à¤¬à¤¹à¥à¤¤ reflective à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "why": [
                    "core numbers à¤…à¤²à¤—-à¤…à¤²à¤— behavioral layers à¤•à¥‹ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚; à¤‡à¤¨à¥à¤¹à¥€à¤‚ layers à¤•à¤¾ à¤¤à¤¾à¤²à¤®à¥‡à¤² à¤†à¤ªà¤•à¥€ social style à¤”à¤° internal processing à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ",
                    f"Lo Shu pattern ({present_text}/{missing_text}) à¤‡à¤¨ layers à¤•à¥‹ stabilize à¤¯à¤¾ disturb à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "à¤‡à¤¸à¤•à¤¾ à¤ªà¥à¤°à¤­à¤¾à¤µ social readability, self-confidence rhythm à¤”à¤° emotional boundary setting à¤ªà¤° à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆ",
                    "à¤œà¤¬ blind spots active à¤°à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤¤à¥‹ à¤µà¥à¤¯à¤•à¥à¤¤à¤¿ à¤•à¥€ strengths à¤¦à¤¿à¤–à¤¨à¥‡ à¤•à¥‡ à¤¬à¤¾à¤µà¤œà¥‚à¤¦ consistency perception à¤•à¤® à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "action": [
                    "trigger-based self-awareness sheet à¤¬à¤¨à¤¾à¤à¤‚ à¤”à¤° à¤¦à¥‡à¤–à¥‡à¤‚ à¤•à¤¿à¤¸ à¤¸à¥à¤¥à¤¿à¤¤à¤¿ à¤®à¥‡à¤‚ à¤†à¤ªà¤•à¤¾ à¤•à¥Œà¤¨-à¤¸à¤¾ mode activate à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ",
                    "strength-led scheduling à¤•à¤°à¥‡à¤‚: high-focus tasks clarity windows à¤®à¥‡à¤‚ à¤”à¤° high-emotion interactions regulated windows à¤®à¥‡à¤‚ à¤°à¤–à¥‡à¤‚",
                ],
            },
            "current_life_phase_insight": {
                "what": [
                    f"à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤šà¤°à¤£ Personal Year {personal_year} à¤¸à¥‡ à¤¸à¤‚à¤šà¤¾à¤²à¤¿à¤¤ à¤¹à¥ˆ à¤”à¤° à¤¯à¤¹ phase correction-led progress, structured reset à¤”à¤° priority refinement à¤®à¤¾à¤‚à¤—à¤¤à¤¾ à¤¹à¥ˆ",
                    f"à¤…à¤­à¥€ à¤•à¥€ à¤¸à¥à¤¥à¤¿à¤¤à¤¿ à¤®à¥‡à¤‚ {strongest_metric} support à¤¦à¥‡ à¤°à¤¹à¤¾ à¤¹à¥ˆ à¤œà¤¬à¤•à¤¿ {weakest_metric} à¤•à¥‹ stabilizing attention à¤šà¤¾à¤¹à¤¿à¤",
                ],
                "why": [
                    "personal year time-pressure map à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¤¸à¥‡ à¤ªà¤¤à¤¾ à¤šà¤²à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ à¤•à¤¿à¤¸ à¤ªà¥à¤°à¤•à¤¾à¤° à¤•à¥‡ à¤¨à¤¿à¤°à¥à¤£à¤¯ à¤…à¤­à¥€ à¤ªà¤°à¤¿à¤£à¤¾à¤®à¤•à¤¾à¤°à¥€ à¤¹à¥‹à¤‚à¤—à¥‡",
                    f"core stack à¤”à¤° concern '{concern_hint}' à¤•à¤¾ intersection à¤‡à¤¸ phase à¤•à¥€ urgency à¤”à¤° intervention depth à¤¤à¤¯ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "phase-aligned actions à¤¸à¥‡ progress compounding à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ, à¤œà¤¬à¤•à¤¿ scattered actions à¤¸à¥‡ effort leakage à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                    f"à¤¯à¤¦à¤¿ correction delay à¤¹à¥à¤† à¤¤à¥‹ {risk_primary} à¤¸à¤‚à¤•à¥‡à¤¤ decision fatigue à¤”à¤° confidence drift à¤®à¥‡à¤‚ à¤¬à¤¦à¤² à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                ],
                "action": [
                    "90-day phase board à¤¬à¤¨à¤¾à¤à¤‚: 3 focus outcomes, 3 weekly metrics à¤”à¤° 1 non-negotiable routine block",
                    "à¤¹à¤° à¤¸à¤ªà¥à¤¤à¤¾à¤¹ phase-fit review à¤•à¤°à¥‡à¤‚ à¤”à¤° low-value commitments à¤¹à¤Ÿà¤¾à¤•à¤° execution bandwidth à¤¬à¤šà¤¾à¤à¤‚",
                ],
            },
            "career_financial_tendencies": {
                "what": [
                    "career layer à¤®à¥‡à¤‚ à¤†à¤ªà¤•à¥€ tendency depth, accountability à¤”à¤° structured execution à¤•à¥€ à¤¤à¤°à¤« à¤¹à¥ˆ, à¤œà¤¹à¤¾à¤‚ role clarity à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° output à¤®à¤œà¤¬à¥‚à¤¤ à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆ",
                    "financial layer à¤®à¥‡à¤‚ discipline à¤”à¤° timing à¤¦à¥‹à¤¨à¥‹à¤‚ à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ à¤¹à¥ˆà¤‚; à¤•à¥‡à¤µà¤² income potential à¤ªà¤°à¥à¤¯à¤¾à¤ªà¥à¤¤ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹à¤¤à¤¾",
                ],
                "why": [
                    f"Mulank {mulank} action impulse à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ, Bhagyank {bhagyank} direction à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ à¤”à¤° Name {name_number_text} opportunity conversion signal à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ",
                    f"missing digits ({missing_text}) à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° money routine à¤®à¥‡à¤‚ inconsistency à¤”à¤° delayed follow-through à¤•à¤¾ à¤œà¥‹à¤–à¤¿à¤® à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "career side à¤ªà¤° role mismatch à¤¹à¥‹à¤¨à¥‡ à¤¸à¥‡ motivation drop à¤”à¤° decision confusion à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ",
                    "finance side à¤ªà¤° reactive choices savings continuity à¤”à¤° long-term stability à¤•à¥‹ à¤•à¤®à¤œà¥‹à¤° à¤•à¤° à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¤‚",
                ],
                "action": [
                    "monthly career review à¤°à¤–à¥‡à¤‚: role-fit, output quality, communication value à¤”à¤° growth direction à¤•à¤¾ à¤²à¥‡à¤–à¤¾ à¤¬à¤¨à¤¾à¤à¤‚",
                    "money checkpoint protocol à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚: essentials, reserves, growth allocation à¤”à¤° impulse guardrails à¤šà¤¾à¤°à¥‹à¤‚ à¤¤à¤¯ à¤•à¤°à¥‡à¤‚",
                ],
            },
            "relationship_compatibility_patterns": {
                "what": [
                    "à¤°à¤¿à¤¶à¥à¤¤à¥‹à¤‚ à¤®à¥‡à¤‚ à¤†à¤ªà¤•à¤¾ pattern à¤…à¤•à¥à¤¸à¤° emotional pace à¤”à¤° communication pace à¤•à¥‡ à¤¤à¤¾à¤²à¤®à¥‡à¤² à¤ªà¤° à¤¨à¤¿à¤°à¥à¤­à¤° à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ, à¤¨ à¤•à¤¿ à¤•à¥‡à¤µà¤² intent à¤ªà¤°",
                    "à¤œà¤¬ response timing à¤¸à¤¹à¥€ à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆ à¤¤à¥‹ à¤¸à¤‚à¤¬à¤‚à¤§ à¤œà¤²à¥à¤¦à¥€ à¤¸à¥à¤¥à¤¿à¤° à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚; timing à¤Ÿà¥‚à¤Ÿà¥‡ à¤¤à¥‹ misunderstanding à¤•à¤¾ loop à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "why": [
                    f"Mulank {mulank} à¤¤à¥à¤µà¤°à¤¿à¤¤ à¤ªà¥à¤°à¤¤à¤¿à¤•à¥à¤°à¤¿à¤¯à¤¾ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ à¤œà¤¬à¤•à¤¿ Bhagyank {bhagyank} à¤—à¤¹à¤°à¤¾à¤ˆ à¤¸à¥‡ à¤¸à¤®à¤ à¤šà¤¾à¤¹à¤¤à¤¾ à¤¹à¥ˆ; à¤¯à¤¹à¥€ à¤…à¤‚à¤¤à¤° relational friction à¤•à¤¾ à¤¸à¥à¤°à¥‹à¤¤ à¤¬à¤¨ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                    f"compatibility level ({_safe_text(compatibility_level, 'medium')}) à¤”à¤° summary ({_safe_text(compatibility_summary, 'balanced signal')}) à¤‡à¤¸ à¤ªà¥à¤°à¤µà¥ƒà¤¤à¥à¤¤à¤¿ à¤•à¤¾ à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤¦à¥‡à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                ],
                "impact": [
                    "à¤ªà¥à¤°à¤­à¤¾à¤µ à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ over-explaining, silence blocks, delayed repair à¤¯à¤¾ expectation mismatch à¤¦à¤¿à¤– à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                    "à¤¯à¤¦à¤¿ clarity protocols à¤¨ à¤¹à¥‹à¤‚ à¤¤à¥‹ trust building à¤•à¥€ à¤—à¤¤à¤¿ à¤§à¥€à¤®à¥€ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ à¤”à¤° emotional fatigue à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "action": [
                    "conflict protocol à¤¤à¤¯ à¤•à¤°à¥‡à¤‚: pause, clear statement, listening window, repair action à¤”à¤° closure check",
                    "à¤¸à¤¾à¤ªà¥à¤¤à¤¾à¤¹à¤¿à¤• relationship review à¤°à¤–à¥‡à¤‚ à¤œà¤¿à¤¸à¤®à¥‡à¤‚ unresolved points à¤”à¤° appreciation à¤¦à¥‹à¤¨à¥‹à¤‚ à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤ à¤°à¥‚à¤ª à¤¸à¥‡ à¤¦à¤°à¥à¤œ à¤¹à¥‹à¤‚",
                ],
            },
            "health_tendencies_from_numbers": {
                "what": [
                    "à¤¯à¤¹ health section non-medical wellness trend à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ: stress rhythm, sleep discipline, recovery quality à¤”à¤° emotional overload risk",
                    f"current profile à¤®à¥‡à¤‚ {weakest_metric} axis à¤¸à¤‚à¤µà¥‡à¤¦à¤¨à¤¶à¥€à¤² à¤¦à¤¿à¤– à¤°à¤¹à¤¾ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ recovery planning à¤•à¥€ à¤œà¤°à¥‚à¤°à¤¤ à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "why": [
                    f"Lo Shu gaps ({missing_text}) à¤”à¤° repeating traits ({repeating_text}) stress-processing à¤•à¥‹ uneven à¤¬à¤¨à¤¾ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                    "à¤œà¤¬ decision pressure à¤”à¤° emotional load à¤¸à¤¾à¤¥ à¤¬à¤¢à¤¼à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤¤à¥‹ nervous system à¤®à¥‡à¤‚ reset time à¤²à¤‚à¤¬à¤¾ à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "à¤‡à¤¸à¤•à¤¾ à¤…à¤¸à¤° fatigue build-up, attention drift, irritability spikes à¤”à¤° motivation inconsistency à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ à¤¦à¤¿à¤– à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                    "routine à¤Ÿà¥‚à¤Ÿà¤¨à¥‡ à¤ªà¤° performance à¤”à¤° emotional steadiness à¤¦à¥‹à¤¨à¥‹à¤‚ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                ],
                "action": [
                    "daily recovery protocol à¤°à¤–à¥‡à¤‚: breathing reset, movement block, digital shutdown à¤”à¤° fixed sleep window",
                    "peak-stress à¤¦à¤¿à¤¨à¥‹à¤‚ à¤•à¥‡ à¤²à¤¿à¤ backup plan à¤¬à¤¨à¤¾à¤à¤‚ à¤¤à¤¾à¤•à¤¿ overload à¤•à¥‹ à¤¤à¥à¤°à¤‚à¤¤ stabilize à¤•à¤¿à¤¯à¤¾ à¤œà¤¾ à¤¸à¤•à¥‡",
                ],
            },
            "personal_year_forecast": {
                "what": [
                    f"Personal Year {personal_year} à¤‡à¤¸ à¤µà¤°à¥à¤· à¤•à¥€ growth theme, decision timing à¤”à¤° correction priority à¤•à¥‹ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤•à¤° à¤°à¤¹à¤¾ à¤¹à¥ˆ",
                    "à¤¯à¤¹ à¤µà¤°à¥à¤· random expansion à¤•à¥€ à¤œà¤—à¤¹ disciplined progress à¤”à¤° structure-led gains à¤•à¥‡ à¤²à¤¿à¤ à¤‰à¤ªà¤¯à¥à¤•à¥à¤¤ à¤¹à¥ˆ",
                ],
                "why": [
                    "year vibration à¤œà¤¨à¥à¤®à¤¤à¤¿à¤¥à¤¿ à¤”à¤° à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤µà¤°à¥à¤· à¤•à¥‡ à¤—à¤£à¤¿à¤¤ à¤¸à¥‡ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤¯à¤¹ à¤¸à¤®à¤¯-à¤†à¤§à¤¾à¤°à¤¿à¤¤ behavioral pressure à¤•à¥‹ à¤µà¤¿à¤¶à¥à¤µà¤¸à¤¨à¥€à¤¯ à¤°à¥‚à¤ª à¤¸à¥‡ à¤¦à¤°à¥à¤¶à¤¾à¤¤à¥€ à¤¹à¥ˆ",
                    "à¤œà¤¬ actions year-theme aligned à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤¤à¥‹ effort-to-result ratio à¤¬à¥‡à¤¹à¤¤à¤° à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "aligned timing à¤®à¥‡à¤‚ launches à¤”à¤° commitments smoother à¤°à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚, misaligned timing à¤®à¥‡à¤‚ same effort à¤­à¤¾à¤°à¥€ à¤²à¤— à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                    "year awareness à¤¹à¥‹à¤¨à¥‡ à¤¸à¥‡ uncertainty à¤•à¤® à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ à¤”à¤° decision confidence à¤¸à¥à¤¥à¤¿à¤° à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "action": [
                    f"à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ à¤¨à¤¿à¤°à¥à¤£à¤¯à¥‹à¤‚ à¤•à¥‹ favorable dates ({lucky_text}) à¤ªà¤° schedule à¤•à¤°à¥‡à¤‚ à¤”à¤° à¤ªà¤¹à¤²à¥‡ readiness checklist à¤ªà¥‚à¤°à¥€ à¤•à¤°à¥‡à¤‚",
                    "à¤¹à¤° à¤®à¤¹à¥€à¤¨à¥‡ phase review à¤•à¤°à¤•à¥‡ non-aligned tasks à¤¹à¤Ÿà¤¾à¤à¤‚ à¤”à¤° aligned tasks à¤•à¥€ intensity à¤¬à¤¢à¤¼à¤¾à¤à¤‚",
                ],
            },
            "lucky_numbers_favorable_dates": {
                "what": [
                    f"Supportive numbers ({target_text}) à¤”à¤° favorable dates ({lucky_text}) à¤†à¤ªà¤•à¥€ profile à¤•à¥‡ à¤²à¤¿à¤ timing accelerators à¤•à¥€ à¤¤à¤°à¤¹ à¤•à¤¾à¤® à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                    "à¤‡à¤¨à¤•à¤¾ à¤‰à¤ªà¤¯à¥‹à¤— blind belief à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ structured planning utility à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ à¤•à¤°à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤",
                ],
                "why": [
                    "timing windows core stack à¤”à¤° year vibration à¤•à¥‡ resonance à¤¸à¥‡ à¤¨à¤¿à¤•à¤¾à¤²à¥‡ à¤œà¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤‡à¤¸à¤²à¤¿à¤ à¤¯à¥‡ contextual support à¤¦à¥‡à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                    "aligned dates à¤ªà¤° cognitive friction à¤•à¤® à¤¹à¥‹à¤¨à¥‡ à¤¸à¥‡ focus à¤”à¤° completion rate à¤¬à¥‡à¤¹à¤¤à¤° à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "impact": [
                    "à¤ªà¥à¤°à¤­à¤¾à¤µ à¤•à¥‡ à¤°à¥‚à¤ª à¤®à¥‡à¤‚ key actions à¤®à¥‡à¤‚ momentum, clarity à¤”à¤° stakeholder response quality à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
                    "à¤—à¤²à¤¤ timing à¤®à¥‡à¤‚ à¤µà¤¹à¥€ à¤•à¤¾à¤°à¥à¤¯ à¤…à¤§à¤¿à¤• rework à¤”à¤° delay à¤ªà¥ˆà¤¦à¤¾ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "action": [
                    "à¤¹à¤° à¤®à¤¹à¥€à¤¨à¥‡ top supportive dates à¤ªà¤¹à¤²à¥‡ à¤®à¤¾à¤°à¥à¤• à¤•à¤°à¥‡à¤‚ à¤”à¤° high-impact tasks à¤‰à¤¨à¥à¤¹à¥€à¤‚ windows à¤®à¥‡à¤‚ à¤°à¤–à¥‡à¤‚",
                    "date alignment à¤•à¥‡ à¤¸à¤¾à¤¥ preparation discipline à¤œà¥‹à¤¡à¤¼à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ timing à¤•à¤¾ à¤²à¤¾à¤­ à¤µà¤¾à¤¸à¥à¤¤à¤µà¤¿à¤• à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¥‡",
                ],
            },
            "color_alignment": {
                "what": [
                    "à¤°à¤‚à¤— à¤•à¥‡à¤µà¤² aesthetics à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ mood regulation, focus stability à¤”à¤° public projection à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¨à¥‡ à¤µà¤¾à¤²à¤¾ subtle behavioral lever à¤¹à¥ˆà¤‚",
                    f"favorable palette ({_safe_text(favorable_colors, 'neutral supportive tones')}) à¤†à¤ªà¤•à¥€ profile à¤•à¥‡ à¤²à¤¿à¤ balanced signal à¤¦à¥‡ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "why": [
                    f"core number resonance à¤”à¤° dominant planet ({dominant_planet}) color sensitivity à¤ªà¤° à¤…à¤¸à¤° à¤¡à¤¾à¤²à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                    f"caution palette ({_safe_text(caution_colors, 'high-intensity tones')}) à¤•à¤¾ overuse emotional tone à¤•à¥‹ reactive à¤¬à¤¨à¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "à¤¸à¤¹à¥€ à¤°à¤‚à¤— choices à¤¸à¥‡ communication presence à¤”à¤° confidence projection à¤¸à¥à¤§à¤°à¤¤à¥€ à¤¹à¥ˆ",
                    "à¤—à¤²à¤¤ color environment à¤®à¥‡à¤‚ fatigue, irritability à¤¯à¤¾ distracted mood à¤•à¥‡ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                ],
                "action": [
                    "workspace, wardrobe à¤”à¤° digital profile à¤®à¥‡à¤‚ consistent color strategy à¤°à¤–à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ identity tone coherent à¤°à¤¹à¥‡",
                    "high-pressure à¤¦à¤¿à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ calming-supportive palette à¤•à¥‹ à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾ à¤¦à¥‡à¤‚ à¤”à¤° extreme contrasts à¤¸à¥€à¤®à¤¿à¤¤ à¤°à¤–à¥‡à¤‚",
                ],
            },
            "remedies_lifestyle_adjustments": {
                "what": [
                    "à¤¯à¤¹ section practical correction protocol à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ à¤œà¤¿à¤¸à¤®à¥‡à¤‚ mantra, habit discipline à¤”à¤° lifestyle calibration à¤•à¥‹ à¤à¤• integrated system à¤•à¥€ à¤¤à¤°à¤¹ à¤²à¤¾à¤—à¥‚ à¤•à¤¿à¤¯à¤¾ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆ",
                    f"à¤®à¥à¤–à¥à¤¯ à¤‰à¤¦à¥à¤¦à¥‡à¤¶à¥à¤¯ {weakest_metric} stabilization à¤”à¤° behavior consistency à¤¬à¤¨à¤¾à¤¨à¤¾ à¤¹à¥ˆ, à¤¤à¤¾à¤•à¤¿ long-term drift à¤°à¥à¤•à¥‡",
                ],
                "why": [
                    "Remedies à¤¤à¤­à¥€ à¤ªà¥à¤°à¤­à¤¾à¤µà¥€ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¤‚ à¤œà¤¬ repetition, timing à¤”à¤° routine integration à¤•à¥‡ à¤¸à¤¾à¤¥ à¤•à¥€ à¤œà¤¾à¤à¤‚",
                    f"à¤†à¤ªà¤•à¥‡ pattern à¤®à¥‡à¤‚ missing cluster à¤”à¤° concern '{concern_hint}' à¤¦à¥‹à¤¨à¥‹à¤‚ sustained correction à¤®à¤¾à¤‚à¤—à¤¤à¥‡ à¤¹à¥ˆà¤‚",
                ],
                "impact": [
                    "consistent practice à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° clarity, emotional regulation à¤”à¤° decision steadiness à¤§à¥€à¤°à¥‡-à¤§à¥€à¤°à¥‡ à¤¸à¥à¤¥à¤¿à¤° à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ",
                    "à¤…à¤¨à¤¿à¤¯à¤®à¤¿à¤¤ à¤…à¤­à¥à¤¯à¤¾à¤¸ à¤®à¥‡à¤‚ à¤¶à¥à¤°à¥à¤†à¤¤à¥€ à¤²à¤¾à¤­ à¤Ÿà¤¿à¤•à¤¤à¥‡ à¤¨à¤¹à¥€à¤‚ à¤”à¤° à¤ªà¥à¤°à¤¾à¤¨à¤¾ behavior loop à¤²à¥Œà¤Ÿ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "action": [
                    f"Mantra routine: {vedic_code}; à¤‡à¤¸à¥‡ fixed time à¤ªà¤° short but daily discipline à¤•à¥‡ à¤¸à¤¾à¤¥ à¤•à¤°à¥‡à¤‚",
                    f"Practice stack: {vedic_parameter}; lifestyle anchor: {lifestyle_protocol}; weekly compliance review à¤…à¤¨à¤¿à¤µà¤¾à¤°à¥à¤¯ à¤°à¤–à¥‡à¤‚",
                ],
            },
            "closing_numerology_guidance": {
                "what": [
                    f"{full_name} à¤•à¥€ profile correction-ready à¤¹à¥ˆ; core potential à¤®à¥Œà¤œà¥‚à¤¦ à¤¹à¥ˆ à¤”à¤° growth path usable à¤¹à¥ˆ",
                    f"à¤®à¥à¤–à¥à¤¯ balance point {weakest_metric} stabilization à¤”à¤° {strongest_metric} leverage à¤•à¥‡ à¤¬à¥€à¤š disciplined coordination à¤¹à¥ˆ",
                ],
                "why": [
                    "à¤¸à¤®à¤—à¥à¤° à¤ªà¥ˆà¤Ÿà¤°à¥à¤¨ à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ issue à¤•à¥à¤·à¤®à¤¤à¤¾ à¤•à¥€ à¤•à¤®à¥€ à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ rhythm, timing à¤”à¤° consistency misalignment à¤•à¤¾ à¤¹à¥ˆ",
                    f"core stack, Lo Shu gaps à¤”à¤° yearly pressure à¤®à¤¿à¤²à¤•à¤° repeat cycles à¤¬à¤¨à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤œà¤¿à¤¨à¥à¤¹à¥‡à¤‚ process-driven correction à¤¸à¥‡ à¤¤à¥‹à¤¡à¤¼à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ",
                ],
                "impact": [
                    "à¤¸à¤¹à¥€ implementation à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° decision quality, communication trust à¤”à¤° execution continuity à¤¤à¥€à¤¨à¥‹à¤‚ à¤®à¥‡à¤‚ compound à¤¸à¥à¤§à¤¾à¤° à¤†à¤¤à¤¾ à¤¹à¥ˆ",
                    "à¤¯à¤¦à¤¿ correction postpone à¤•à¤¿à¤¯à¤¾ à¤œà¤¾à¤ à¤¤à¥‹ à¤µà¤¹à¥€ patterns à¤¬à¤¾à¤°-à¤¬à¤¾à¤° à¤²à¥Œà¤Ÿà¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤”à¤° effort efficiency à¤—à¤¿à¤°à¤¤à¥€ à¤¹à¥ˆ",
                ],
                "action": [
                    "à¤…à¤—à¤²à¥‡ 30 à¤¦à¤¿à¤¨à¥‹à¤‚ à¤•à¥‡ à¤²à¤¿à¤ compact execution plan à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚: daily anchors, weekly review à¤”à¤° monthly consolidation",
                    f"final focus: concern '{concern_hint}' à¤•à¥‹ measurable goals à¤®à¥‡à¤‚ à¤¤à¥‹à¤¡à¤¼à¥‡à¤‚ à¤”à¤° à¤¹à¤° à¤¸à¤ªà¥à¤¤à¤¾à¤¹ evidence-based progress validate à¤•à¤°à¥‡à¤‚",
                ],
            },
        }
    )

    def _compose_box(section_key: str, slot: str, seeds: Sequence[str]) -> str:
        seed_pool: List[str] = []
        for item in seeds:
            clean = _safe_text(item)
            if clean and clean not in seed_pool:
                seed_pool.append(clean)
        dynamic_pool: List[str] = []
        for item in global_fillers.get(slot, []) + dynamic_fillers.get(slot, []):
            clean = _safe_text(item)
            if clean and clean not in dynamic_pool:
                dynamic_pool.append(clean)
        sentences: List[str] = []
        used = set()

        ordered_seeds = sorted(seed_pool, key=lambda text: _stable_seed(seed, section_key, slot, "seed", text))
        for idx, base in enumerate(ordered_seeds):
            if len(sentences) >= 3:
                break
            pick = _sent(_style_sentence(section_key, slot, base, idx))
            if pick and pick not in used:
                sentences.append(pick)
                used.add(pick)

        ordered_fillers = sorted(dynamic_pool, key=lambda text: _stable_seed(seed, section_key, slot, "fill", text))
        for idx, filler in enumerate(ordered_fillers):
            if not ((len(sentences) < 5 or len(" ".join(sentences)) < 450) and len(sentences) < 7):
                break
            pick = _sent(_style_sentence(section_key, slot, filler, idx + 10))
            if pick and pick not in used:
                sentences.append(pick)
                used.add(pick)

        emergency_pool = ordered_fillers + ordered_seeds
        for idx, filler in enumerate(emergency_pool):
            if not ((len(sentences) < 4 or len(" ".join(sentences)) < 350) and len(sentences) < 7):
                break
            pick = _sent(_style_sentence(section_key, slot, filler, idx + 40))
            if pick and pick not in used:
                sentences.append(pick)
                used.add(pick)

        text = " ".join(sentences)
        return _fit_rich(text, max_chars=700)

    narrative_hooks: Dict[str, List[str]] = {
        "executive_numerology_summary": [
            f"Strength-risk ranking à¤®à¥‡à¤‚ {strongest_metric} leverage à¤”à¤° {weakest_metric} correction à¤¦à¥‹à¤¨à¥‹à¤‚ à¤¸à¤¾à¤¥ à¤šà¤²à¤¾à¤¨à¤¾ à¤‡à¤¸ profile à¤•à¥‡ à¤²à¤¿à¤ à¤…à¤¨à¤¿à¤µà¤¾à¤°à¥à¤¯ à¤°à¤¹à¥‡à¤—à¤¾à¥¤",
            f"Risk band '{risk_primary}' à¤•à¥‡ à¤­à¥€à¤¤à¤° concern '{concern_hint}' à¤•à¥‹ measurable protocol à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¨à¤¾ executive priority à¤¹à¥ˆà¥¤",
        ],
        "core_numbers_analysis": [
            f"Core architecture {mulank}/{bhagyank}/{name_number_text} à¤¤à¤­à¥€ productive à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆ à¤œà¤¬ decision rhythm à¤”à¤° closure rhythm à¤à¤• à¤¹à¥€ sequence à¤®à¥‡à¤‚ à¤šà¤²à¥‡à¤‚à¥¤",
            f"à¤¯à¤¹ stack à¤¯à¤¦à¤¿ aligned à¤°à¤–à¤¾ à¤œà¤¾à¤ à¤¤à¥‹ {strongest_metric.lower()} à¤•à¥‹ consistent growth asset à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        ],
        "name_number_analysis": [
            f"Identity projection layer à¤®à¥‡à¤‚ Name {name_number_text} à¤”à¤° compound {name_compound} à¤•à¥€ tuning social trust à¤”à¤° clarity à¤¦à¥‹à¤¨à¥‹à¤‚ à¤ªà¤° à¤…à¤¸à¤° à¤¡à¤¾à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            f"à¤¨à¤¾à¤® signal à¤•à¥€ consistency à¤¸à¥‡ public perception à¤”à¤° internal confidence à¤•à¥‡ à¤¬à¥€à¤š gap à¤•à¤® à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        ],
        "number_interaction_analysis": [
            f"Interaction layer à¤®à¥‡à¤‚ harmony-gap profile à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ intent à¤¬à¤¨à¤¾à¤® execution mismatch à¤•à¤¹à¤¾à¤ à¤¸à¥‡ à¤ªà¥ˆà¤¦à¤¾ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤",
            f"à¤¯à¤¹ section à¤µà¥à¤¯à¤µà¤¹à¤¾à¤°à¤¿à¤• friction à¤•à¥‡ root node à¤•à¥€ à¤ªà¤¹à¤šà¤¾à¤¨ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¿à¤¸à¤¸à¥‡ corrective sequencing à¤†à¤¸à¤¾à¤¨ à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆà¥¤",
        ],
        "remedies_lifestyle_adjustments": [
            f"Correction engine à¤¤à¤­à¥€ effective à¤¹à¥‹à¤—à¤¾ à¤œà¤¬ routine, mantra à¤”à¤° behavior audit à¤¤à¥€à¤¨à¥‹à¤‚ calendar-bound cadence à¤®à¥‡à¤‚ à¤šà¤²à¥‡à¤‚à¥¤",
            f"à¤¯à¤¹ section à¤•à¥‡à¤µà¤² à¤¸à¤²à¤¾à¤¹ à¤¨à¤¹à¥€à¤‚ à¤¬à¤²à¥à¤•à¤¿ daily/weekly execution protocol à¤•à¤¾ practical blueprint à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        ],
        "closing_numerology_guidance": [
            f"Final synthesis à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ profile à¤®à¥‡à¤‚ à¤•à¥à¤·à¤®à¤¤à¤¾ à¤®à¥Œà¤œà¥‚à¤¦ à¤¹à¥ˆ, bottleneck consistency architecture à¤®à¥‡à¤‚ à¤¹à¥ˆà¥¤",
            f"Next-step discipline à¤œà¤¿à¤¤à¤¨à¥€ measurable à¤¹à¥‹à¤—à¥€, à¤‰à¤¤à¤¨à¥€ à¤œà¤²à¥à¤¦à¥€ {risk_primary} pressure zone à¤¸à¥‡ à¤¬à¤¾à¤¹à¤° à¤¨à¤¿à¤•à¤²à¤¾ à¤œà¤¾ à¤¸à¤•à¥‡à¤—à¤¾à¥¤",
        ],
    }

    def _compose_narrative(section_key: str, slots: Dict[str, List[str]]) -> str:
        base_leads = [
            f"{first_name} à¤•à¥€ {section_key.replace('_', ' ')} reading à¤®à¥‡à¤‚ profile-specific à¤¸à¤‚à¤•à¥‡à¤¤ à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥ˆà¤‚à¥¤",
            f"{section_key.replace('_', ' ').title()} layer à¤®à¥‡à¤‚ core numbers, Lo Shu à¤”à¤° current cycle à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¦à¤¿à¤– à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤",
            f"à¤¯à¤¹ section {focus_hint} à¤”à¤° concern '{concern_hint}' à¤•à¥‡ à¤¸à¤‚à¤¦à¤°à¥à¤­ à¤®à¥‡à¤‚ actionable clarity à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
        ]
        selected_sentences: List[str] = []
        lead = _pick_variant(seed, section_key, "narrative:lead", base_leads)
        selected_sentences.append(_sent(_style_sentence(section_key, "what", lead, 70)))

        for slot_name in ("what", "why"):
            candidates = [item for item in slots.get(slot_name, []) if _safe_text(item)]
            if not candidates:
                continue
            idx = _stable_seed(seed, section_key, slot_name, "narrative") % len(candidates)
            selected_sentences.append(_sent(_style_sentence(section_key, slot_name, candidates[idx], idx + 80)))

        hooks = narrative_hooks.get(
            section_key,
            [
                f"Risk context '{risk_primary}' à¤”à¤° year theme {personal_year} à¤‡à¤¸ section à¤•à¥€ correction priority à¤•à¥‹ directly influence à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
                f"Focused implementation à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° {strongest_metric.lower()} leverage à¤”à¤° {weakest_metric.lower()} stabilization à¤¸à¤¾à¤¥ à¤®à¥‡à¤‚ à¤¸à¤‚à¤­à¤µ à¤¹à¥ˆà¥¤",
            ],
        )
        selected_sentences.append(_sent(_pick_variant(seed, section_key, "narrative:hook", hooks)))
        return _fit_rich(" ".join(item for item in selected_sentences if _safe_text(item)), max_chars=420)

    for section_key, slots in section_lines.items():
        section = basic_payloads.get(section_key)
        if not isinstance(section, dict):
            continue
        section["narrative"] = _compose_narrative(section_key, slots)
        cards = section.get("cards") or []
        if len(cards) < 4:
            continue
        cards[0]["value"] = _compose_box(section_key, "what", slots.get("what", []))
        cards[1]["value"] = _compose_box(section_key, "why", slots.get("why", []))
        cards[2]["value"] = _compose_box(section_key, "impact", slots.get("impact", []))
        cards[3]["value"] = _compose_box(section_key, "action", slots.get("action", []))

    if isinstance(basic_payloads.get("missing_numbers_analysis"), dict):
        basic_payloads["missing_numbers_analysis"]["bullets"] = [
            f"{number}: {BASIC_MISSING_EFFECTS.get(number, {'fix': 'à¤¦à¥ˆà¤¨à¤¿à¤• correction discipline'})['fix']}"
            for number in list(loshu_missing)[:5]
        ]

    if isinstance(basic_payloads.get("mobile_number_numerology"), dict):
        cards = basic_payloads["mobile_number_numerology"].get("cards") or []
        if len(cards) >= 5:
            cards[4]["value"] = mobile_value or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

    if isinstance(basic_payloads.get("email_numerology"), dict):
        cards = basic_payloads["email_numerology"].get("cards") or []
        if len(cards) >= 5:
            cards[4]["value"] = email_value or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"

    if isinstance(basic_payloads.get("personal_year_forecast"), dict):
        cards = basic_payloads["personal_year_forecast"].get("cards") or []
        if len(cards) >= 6:
            cards[4]["value"] = str(personal_year)
            cards[5]["value"] = lucky_text

    if isinstance(basic_payloads.get("lucky_numbers_favorable_dates"), dict):
        cards = basic_payloads["lucky_numbers_favorable_dates"].get("cards") or []
        if len(cards) >= 6:
            cards[4]["value"] = target_text
            cards[5]["value"] = lucky_text

    if isinstance(basic_payloads.get("remedies_lifestyle_adjustments"), dict):
        basic_payloads["remedies_lifestyle_adjustments"]["bullets"] = [
            f"Mantra: {vedic_code}",
            f"Practice: {vedic_parameter}",
            f"Lifestyle: {lifestyle_protocol}",
        ]

    if isinstance(basic_payloads.get("name_number_analysis"), dict):
        cards = basic_payloads["name_number_analysis"].get("cards") or []
        if len(cards) >= 6:
            cards[4]["value"] = name_number_text
            cards[5]["value"] = target_text

    return basic_payloads


def build_interpretation_report(
    intake_context: Dict[str, Any],
    numerology_core: Dict[str, Any],
    scores: Dict[str, Any],
    archetype: Dict[str, Any],
    remedies: Dict[str, Any],
    plan_name: str = "basic",
) -> Dict[str, Any]:
    intake_context = intake_context or {}
    numerology_core = numerology_core or {}
    scores = scores or {}
    archetype = archetype or {}
    remedies = remedies or {}

    identity = intake_context.get("identity") or {}
    birth_details = intake_context.get("birth_details") or {}
    focus = intake_context.get("focus") or {}
    career = intake_context.get("career") or {}
    contact = intake_context.get("contact") or {}
    preferences = intake_context.get("preferences") or {}

    full_name = _safe_text(identity.get("full_name"), "Strategic Client")
    first_name = full_name.split()[0]
    date_of_birth = _safe_text(birth_details.get("date_of_birth") or identity.get("date_of_birth"))
    day, month, year = _parse_date(date_of_birth)
    current_problem = _safe_text(intake_context.get("current_problem"), "strategic consistency and calibrated growth")

    city = _safe_text(birth_details.get("birthplace_city") or identity.get("city"), "current city")
    career_industry = _safe_text(career.get("industry") or preferences.get("profession"), "strategy and operations")

    pyth = numerology_core.get("pythagorean") or {}
    chaldean = numerology_core.get("chaldean") or {}
    loshu_grid = numerology_core.get("loshu_grid") or {}
    mobile_analysis = numerology_core.get("mobile_analysis") or {}
    email_analysis = numerology_core.get("email_analysis") or {}
    name_correction = numerology_core.get("name_correction") or {}
    business_analysis = numerology_core.get("business_analysis") or {}
    compatibility = numerology_core.get("compatibility") or {}

    life_path = _safe_int(pyth.get("life_path_number"), 0)
    destiny = _safe_int(pyth.get("destiny_number"), 0)
    expression = _safe_int(pyth.get("expression_number"), 0)
    soul_urge = _safe_int(pyth.get("soul_urge_number"), _reduce_number(_alpha_sum(full_name)))
    personality = _safe_int(pyth.get("personality_number"), expression)
    name_number = _safe_int(chaldean.get("name_number"), _safe_int(name_correction.get("current_number"), 0))

    name_compound = _alpha_sum(full_name)
    name_trait = NUMBER_TRAITS.get(name_number or life_path or 5, NUMBER_TRAITS[5])
    name_strength = name_trait["strength"]
    name_risk = name_trait["risk"]

    dominant_planet = _dominant_planet(life_path, destiny, name_number)

    metric_labels = _metric_labels()
    metric_pairs = _metric_order(scores)
    strongest_key, strongest_score = max(metric_pairs, key=lambda item: item[1])
    weakest_key, weakest_score = min(metric_pairs, key=lambda item: item[1])
    strongest_metric = metric_labels[strongest_key]
    weakest_metric = metric_labels[weakest_key]
    risk_band = _risk_band(scores)

    grid_counts = loshu_grid.get("grid_counts") if isinstance(loshu_grid, dict) else {}
    if not isinstance(grid_counts, dict):
        grid_counts = {}
    loshu_present: List[int] = []
    loshu_missing: List[int] = []
    if isinstance(grid_counts, dict) and grid_counts:
        for number in range(1, 10):
            count = _safe_int(grid_counts.get(str(number), grid_counts.get(number, 0)), 0)
            if count > 0:
                loshu_present.append(number)
            else:
                loshu_missing.append(number)
    else:
        loshu_missing = [3, 5, 6]

    override_missing = [_safe_int(value, 0) for value in _safe_list(loshu_grid.get("missing_numbers")) if _safe_int(value, 0)]
    if override_missing:
        loshu_missing = sorted(set(override_missing))
        loshu_present = [number for number in range(1, 10) if number not in loshu_missing]

    primary_missing = loshu_missing[0] if loshu_missing else 0
    structural_cause = (
        f"à¤¸à¤¬à¤¸à¥‡ à¤•à¤®à¤œà¥‹à¤° à¤…à¤•à¥à¤· {weakest_metric} à¤ªà¤° Lo Shu à¤®à¥‡à¤‚ digit {primary_missing or 'none'} à¤•à¥€ à¤•à¤®à¥€ à¤”à¤° current stress load à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¹à¥ˆà¥¤"
    )
    intervention_focus = (
        f"{weakest_metric.lower()} à¤•à¥‹ rhythm protocol à¤¸à¥‡ à¤¸à¥à¤¥à¤¿à¤° à¤•à¤°à¥‡à¤‚, à¤«à¤¿à¤° identity corrections à¤•à¥‹ architecture à¤•à¥‡ à¤¸à¤¾à¤¥ align à¤•à¤°à¥‡à¤‚à¥¤"
    )

    metric_cards: List[Dict[str, Any]] = []
    for key, score in metric_pairs:
        label = metric_labels[key]
        metric_cards.append(
            {
                "key": key,
                "label": label,
                "score": score,
                "status": _metric_status(score),
                "meaning": f"{label} à¤•à¤¾ score {score} à¤†à¤ªà¤•à¥€ deterministic behavior-risk quality à¤•à¥‹ à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
                "risk": "Low score à¤ªà¤° pressure à¤•à¥‡ à¤¸à¤®à¤¯ execution unstable à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
                "improvement": "Measurable protocol à¤¬à¤¨à¤¾à¤•à¤° weekly review checkpoint à¤œà¥‹à¤¡à¤¼à¥‡à¤‚à¥¤",
            }
        )

    metric_explanations = {
        card["key"]: {
            "label": card["label"],
            "score": card["score"],
            "status": card["status"],
            "meaning": card["meaning"],
            "driver": structural_cause,
            "risk": card["risk"],
            "improvement": card["improvement"],
        }
        for card in metric_cards
    }

    mobile_value = _safe_text(contact.get("mobile_number") or identity.get("mobile_number"))
    mobile_vibration = _safe_int(mobile_analysis.get("mobile_vibration") or mobile_analysis.get("mobile_number_vibration"), _vibration_from_digits(mobile_value))
    mobile_supportive = [_safe_int(value, 0) for value in _safe_list(mobile_analysis.get("supportive_number_energies")) if _safe_int(value, 0)]
    if not mobile_supportive:
        mobile_supportive = [life_path or 1, destiny or 3, 5]
    mobile_compatibility = _safe_text(
        mobile_analysis.get("compatibility_status"),
        "supportive" if mobile_vibration in mobile_supportive else "neutral",
    )
    mobile_summary = _safe_text(
        mobile_analysis.get("compatibility_summary"),
        f"Mobile vibration {mobile_vibration} à¤”à¤° profile compatibility {mobile_compatibility} à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤…à¤¸à¤° communication tone à¤ªà¤° à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    )

    email_value = _safe_text(identity.get("email"))
    email_vibration = _safe_int(email_analysis.get("email_number"), _vibration_from_text(email_value.split("@")[0] if email_value else ""))

    social_handle = _safe_text(contact.get("social_handle"))
    domain_handle = _safe_text(contact.get("domain_handle"))
    residence_number = _safe_text(contact.get("residence_number"))
    vehicle_number = _safe_text(contact.get("vehicle_number"))
    residence_vibration = _vibration_from_digits(residence_number)
    vehicle_vibration = _vibration_from_digits(vehicle_number)

    business_name = _safe_text(identity.get("business_name"))
    business_number = _safe_int(business_analysis.get("business_number"), _vibration_from_text(business_name))
    business_compound = _safe_int(business_analysis.get("compound_number"), _alpha_sum(business_name))
    business_strength = _safe_text(
        business_analysis.get("business_strength"),
        "Business signal disciplined execution à¤•à¥‡ à¤¸à¤¾à¤¥ strategic positioning à¤•à¥‹ support à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    )
    business_risk = _safe_text(
        business_analysis.get("risk_factor"),
        "Commercial outcome pressure à¤•à¥‡ à¤¸à¤®à¤¯ discipline à¤”à¤° clarity à¤ªà¤° à¤¨à¤¿à¤°à¥à¤­à¤° à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
    )
    business_industries = [_safe_text(item) for item in _safe_list(business_analysis.get("compatible_industries")) if _safe_text(item)]
    if not business_industries:
        business_industries = [career_industry, "consulting", "digital services"]

    personal_year = _personal_year(day, month)
    lucky_dates = _lucky_dates(day, month, life_path, destiny)
    karmic_numbers = _karmic_numbers(day, name_compound, business_compound)
    hidden_passion_number, hidden_talent_trait = _hidden_passion(loshu_grid, full_name)
    pinnacle = _pinnacle_challenge(day, month, year)

    name_targets = sorted({value for value in [life_path, destiny, expression, 3, 5, 6] if value and value not in {4, 8}})[:4]
    if not name_targets:
        name_targets = [1, 3, 5]
    name_options = _name_options(full_name, name_targets)

    compatibility_summary = _safe_text(
        compatibility.get("relationship_guidance"),
        f"Compatibility à¤‰à¤¨ profiles à¤•à¥‡ à¤¸à¤¾à¤¥ strongest à¤¹à¥‹à¤¤à¥€ à¤¹à¥ˆ à¤œà¥‹ {strongest_metric.lower()} à¤•à¥‹ reinforce à¤•à¤°à¥‡à¤‚ à¤”à¤° {weakest_metric.lower()} à¤ªà¤° pressure à¤•à¤® à¤•à¤°à¥‡à¤‚à¥¤",
    )

    lifestyle_protocol = "Daily same-time morning anchor, deep-work first block, à¤”à¤° evening shutdown checklist follow à¤•à¤°à¥‡à¤‚à¥¤"
    digital_protocol = "Notification tiering à¤°à¤–à¥‡à¤‚, late-night high-stake decisions avoid à¤•à¤°à¥‡à¤‚, à¤”à¤° weekly digital detox window à¤°à¤–à¥‡à¤‚à¥¤"
    decision_protocol = "High-impact decisions à¤®à¥‡à¤‚ 24-hour delay rule, written criteria, à¤”à¤° weekly assumption audit à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤"
    emotional_protocol = "Key calls à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ breath reset, fixed sleep window, à¤”à¤° post-stress review cadence à¤¬à¤¨à¤¾à¤ à¤°à¤–à¥‡à¤‚à¥¤"

    vedic = remedies.get("vedic_remedies") if isinstance(remedies, dict) else {}
    vedic = vedic if isinstance(vedic, dict) else {}
    vedic_code = _safe_text(vedic.get("mantra_pronunciation") or vedic.get("mantra_sanskrit"), "Om Budhaya Namah")
    vedic_parameter = _safe_text(vedic.get("practice_guideline"), "21 days x 108 repetitions fixed time à¤ªà¤°")
    vedic_output = _safe_text(vedic.get("recommended_donation"), "Weekly practical donation with clear intention")

    correction_priority_lines = [
        f"{weakest_metric.lower()} à¤•à¥‹ rhythm protocol à¤¸à¥‡ à¤¸à¥à¤¥à¤¿à¤° à¤•à¤°à¥‡à¤‚à¥¤",
        "Name à¤”à¤° mobile vibration alignment optimize à¤•à¤°à¥‡à¤‚à¥¤",
        "Email à¤”à¤° signature authority signal upgrade à¤•à¤°à¥‡à¤‚à¥¤",
        "à¤…à¤—à¤° high-pressure pattern à¤¬à¤¨à¤¾ à¤°à¤¹à¥‡ à¤¤à¥‹ residence à¤”à¤° vehicle vibration align à¤•à¤°à¥‡à¤‚à¥¤",
    ]

    payloads: Dict[str, Any] = {}
    payloads["executive_summary"] = _section_payload("executive_summary", f"{full_name} à¤•à¥€ à¤ªà¥à¤°à¥‹à¤«à¤¾à¤‡à¤² à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤¹à¥ˆ, à¤ªà¤° correction-sensitive à¤­à¥€ à¤¹à¥ˆà¥¤ Risk band {risk_band} à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ primary strength {strongest_metric} à¤”à¤° primary deficit {weakest_metric} à¤•à¥‡ à¤¬à¥€à¤š à¤¸à¤‚à¤¤à¥à¤²à¤¨ à¤¬à¤¨à¤¾à¤¨à¤¾ à¤œà¤¼à¤°à¥‚à¤°à¥€ à¤¹à¥ˆà¥¤ Core concern: {current_problem}.", f"Strategic potential à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥ˆ, à¤²à¥‡à¤•à¤¿à¤¨ {weakest_metric.lower()} execution à¤®à¥‡à¤‚ friction à¤²à¤¾ à¤°à¤¹à¤¾ à¤¹à¥ˆà¥¤", structural_cause, f"à¤‡à¤¸à¤•à¤¾ à¤…à¤¸à¤° {career_industry} à¤®à¥‡à¤‚ career momentum, financial discipline, à¤”à¤° decision quality à¤ªà¤° à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤", intervention_focus, [{"label": "Risk Band", "value": risk_band}, {"label": "Dominant Planet", "value": dominant_planet}])
    payloads["intelligence_metrics"] = {**_section_payload("intelligence_metrics", "Metrics à¤•à¥‹ structural diagnostics à¤•à¥€ à¤¤à¤°à¤¹ à¤ªà¤¢à¤¼à¤¨à¤¾ à¤šà¤¾à¤¹à¤¿à¤à¥¤", f"Primary Strength: {strongest_metric}. Primary Deficit: {weakest_metric}.", structural_cause, "Deficit metric volatility à¤¬à¤¢à¤¼à¤¾à¤¤à¤¾ à¤¹à¥ˆ, à¤œà¤¬à¤•à¤¿ strength metric growth leverage à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤", intervention_focus, [{"label": "Primary Strength", "value": strongest_metric}, {"label": "Primary Deficit", "value": weakest_metric}, {"label": "Structural Cause", "value": structural_cause}, {"label": "Intervention Focus", "value": intervention_focus}, {"label": "Risk Band", "value": risk_band}]), "metric_cards": metric_cards, "show_chart": True}
    payloads["core_numerology_numbers"] = _section_payload("core_numerology_numbers", f"à¤®à¥‚à¤² à¤…à¤‚à¤• à¤¸à¤‚à¤°à¤šà¤¨à¤¾: Life Path {life_path}, Destiny {destiny}, Expression {expression}, Soul Urge {soul_urge}, Personality {personality}.", "Core numbers strategic-growth potential à¤¦à¤¿à¤–à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚, à¤²à¥‡à¤•à¤¿à¤¨ protocol dependency à¤­à¥€ à¤¦à¤°à¥à¤¶à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤", "Direction, execution, expression, à¤”à¤° projection à¤‡à¤¸ stack à¤¸à¥‡ à¤¨à¤¿à¤¯à¤‚à¤¤à¥à¤°à¤¿à¤¤ à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤", "Role-fit, leadership style, à¤”à¤° stress response à¤‡à¤¸à¥€ architecture à¤•à¥‹ follow à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤", "Strongest axis leverage à¤•à¤°à¥‡à¤‚ à¤”à¤° weakest behavior loop à¤•à¥‹ patch à¤•à¤°à¥‡à¤‚à¥¤")
    payloads["name_number_analysis"] = _section_payload("name_number_analysis", f"Current name vibration {name_number}, compound {name_compound} ({_compound_meaning(name_compound)}).", "Name signal is active but partially optimized.", "Name frequency impacts authority and trust perception.", "Mismatch can suppress social clarity and strategic momentum.", "Move toward target-aligned spelling where practical.", [{"label": "Current Name Number", "value": str(name_number)}, {"label": "Strength", "value": name_trait['strength']}, {"label": "Risk", "value": name_trait['risk']}, {"label": "Target Numbers", "value": ', '.join(str(value) for value in name_targets)}], [f"Option {index + 1}: {item['option']} -> {item['number']}" for index, item in enumerate(name_options)])
    payloads["birth_date_numerology"] = _section_payload("birth_date_numerology", f"Birth pattern and personal year {personal_year} define timing quality.", "Birth-date rhythm indicates cycle-based opportunities and caution windows.", "Day, month, and year roots shape recurring behavior cadence.", "Cycle alignment improves clarity and reduces decision friction.", "Schedule major actions in favorable date windows.", [{"label": "Favorable Dates", "value": ', '.join(str(v) for v in lucky_dates)}])
    payloads["loshu_grid_intelligence"] = _section_payload("loshu_grid_intelligence", f"Lo Shu present: {', '.join(str(v) for v in loshu_present) or 'none'} | missing: {', '.join(str(v) for v in loshu_missing) or 'none'}.", "Lo Shu reveals naturally available energies and missing capacities.", "Digit distribution maps communication, discipline, and adaptability.", "Missing center/communication digits can amplify instability.", "Target missing number themes with habit-based correction protocol.")
    payloads["karmic_pattern_intelligence"] = _section_payload("karmic_pattern_intelligence", f"Karmic indicators: {', '.join(str(v) for v in karmic_numbers) if karmic_numbers else 'none explicit'}.", "Karmic numbers indicate recurring lesson loops.", "Date and compound patterns repeat during stress cycles.", "Unresolved loops delay consistency and compounding progress.", "Attach one behavior protocol to each active karmic pattern.")
    payloads["hidden_talent_intelligence"] = _section_payload("hidden_talent_intelligence", f"Hidden Passion number {hidden_passion_number} indicates edge in {hidden_talent_trait}.", "Latent skill axis is visible in number-dominance patterns.", "Core and grid signals create compounding potential.", "When activated, this axis boosts speed and confidence.", "Convert hidden talent into weekly measurable outputs.")
    payloads["personal_year_forecast"] = _section_payload("personal_year_forecast", f"Personal year {personal_year} indicates correction-led growth and consolidation.", f"Current cycle number {personal_year} defines the year theme.", "Personal year derives from birth day/month and current year.", "Cycle awareness improves effort-to-result ratio.", "Use favorable dates for launches and directional decisions.")
    payloads["lucky_numbers_favorable_dates"] = _section_payload("lucky_numbers_favorable_dates", "Lucky logic is scheduling calibration, not superstition.", "Selected numbers and dates show higher profile resonance.", "They align with life-path and destiny rhythm.", "Timing alignment can improve confidence and outcomes.", "Use these windows for high-impact actions.", [{"label": "Lucky Numbers", "value": ', '.join(str(v) for v in name_targets[:4])}, {"label": "Favorable Dates", "value": ', '.join(str(v) for v in lucky_dates)}])
    payloads["basic_remedies"] = _section_payload("basic_remedies", "Basic remedies are behavior anchors designed for consistency.", f"Weakest metric {weakest_metric.lower()} requires stabilization.", "Profile sensitivity increases when routine breaks under stress.", "Instability affects strategic clarity and follow-through.", f"{lifestyle_protocol} | {digital_protocol}", bullets=[f"Mantra code: {vedic_code}", f"Practice: {vedic_parameter}", f"Output: {vedic_output}"])
    payloads["archetype_intelligence"] = _section_payload("archetype_intelligence", f"{first_name} archetype blends {name_strength} with risk of {name_risk}.", "Archetype signature shows strategic upside with discipline dependency.", "Core numbers combine analytical depth and adaptive drive.", "Leadership impact depends on rhythm and message clarity.", name_trait["protocol"])
    payloads["career_intelligence"] = _section_payload("career_intelligence", f"Career alignment {career_industry} à¤®à¥‡à¤‚ ownership-driven roles à¤•à¥‡ à¤¸à¤¾à¤¥ strongest à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Growth curve strategic responsibility à¤”à¤° measurable outcomes à¤•à¥‹ favor à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Life-path à¤”à¤° expression alignment depth-based execution à¤•à¥‹ reward à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Role mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° effort à¤¤à¥‹ à¤²à¤—à¤¤à¤¾ à¤¹à¥ˆ, à¤ªà¤° compounding à¤¨à¤¹à¥€à¤‚ à¤¬à¤¨à¤¤à¥€à¥¤", "à¤à¤¸à¥‡ roles à¤šà¥à¤¨à¥‡à¤‚ à¤œà¤¿à¤¨à¤®à¥‡à¤‚ authority, visibility, à¤”à¤° accountability à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥‹à¥¤")
    payloads["financial_intelligence"] = _section_payload("financial_intelligence", f"Financial signal: discipline score {_safe_int(scores.get('financial_discipline_index'), 50)} à¤”à¤° protocol-first improvement pathà¥¤", "Financial behavior correction-ready à¤¹à¥ˆ, à¤ªà¤° structure dependency à¤…à¤§à¤¿à¤• à¤¹à¥ˆà¥¤", "Metric stack stress phase à¤®à¥‡à¤‚ discipline variance à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Protocol à¤•à¥‡ à¤¬à¤¿à¤¨à¤¾ growth reactive decisions à¤®à¥‡à¤‚ leak à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤", "Budget checkpoints à¤”à¤° monthly capital review à¤¤à¥à¤°à¤‚à¤¤ install à¤•à¤°à¥‡à¤‚à¥¤")
    payloads["numerology_architecture"] = _section_payload("numerology_architecture", f"Architecture: Foundation {life_path}, Left Pillar {destiny}, Right Pillar {expression}, Facade {name_number}.", "Core numbers form a unified structural blueprint.", "Each pillar controls direction, execution, and projection.", "Misalignment appears as confidence drift and inconsistency.", "Align corrections (name/mobile/email) to this architecture.")
    payloads["planetary_influence"] = _section_payload("planetary_influence", f"Primary intervention planet: {dominant_planet}.", "Planetary mapping is calibration lens, not fate prediction.", "Core numbers amplify one intervention channel in current cycle.", "Ignoring it increases friction in decision and emotional domains.", "Anchor routines and remedies to intervention-planet discipline.")
    payloads["compatibility_intelligence"] = _section_payload("compatibility_intelligence", _safe_text(compatibility.get("relationship_guidance"), f"Compatibility strongest with profiles reinforcing {strongest_metric.lower()} and reducing pressure on {weakest_metric.lower()}"), "Compatibility signal highlights support and friction patterns.", "Number resonance influences communication pace and expectation alignment.", "Mismatch can drain energy in personal and business collaborations.", "Prioritize partnerships that reinforce strengths and de-risk deficits.")
    payloads["life_cycle_timeline"] = _section_payload("life_cycle_timeline", "Life cycle timeline maps foundation, expansion, and integration phases.", "Current phase requires correction-led consolidation before aggressive scaling.", "Pinnacle progression and personal-year rhythm indicate sequencing needs.", "Right sequencing improves long-term optionality and stability.", "Plan in three phases: stabilize, optimize, scale.")
    payloads["pinnacle_challenge_cycle_intelligence"] = _section_payload("pinnacle_challenge_cycle_intelligence", f"Pinnacles {pinnacle['pinnacles']} | Challenges {pinnacle['challenges']}.", "Pinnacle cycles define opportunities; challenge cycles define resistance.", "Date-derived reductions map developmental sequence.", "Ignoring challenge signatures repeats avoidable errors.", "Match strategy to active pinnacle and neutralize challenge traits.")
    payloads["strategic_guidance"] = _section_payload("strategic_guidance", "Strategic guidance converts numerology into operating decisions.", "System requires correction-first execution before scale expansion.", f"Risk band {risk_band} and weakest axis {weakest_metric.lower()} require stabilization.", "Correct sequence improves clarity and timing quality.", "Run correction stack: behavior -> identity -> timing -> scale.")
    payloads["name_vibration_optimization"] = _section_payload("name_vibration_optimization", f"Current name number {name_number}, compound {name_compound} ({_compound_meaning(name_compound)}).", "Name vibration is active but partially optimized for strategic goals.", "Name frequency encodes authority and trust signal.", "Suboptimal signal can reduce conversion quality and momentum.", "Adopt target-aligned variants where commercial context justifies.", [{"label": "Current Number", "value": str(name_number)}, {"label": "Target Numbers", "value": ', '.join(str(v) for v in name_targets)}, {"label": "Strength", "value": name_trait['strength']}, {"label": "Risk", "value": name_trait['risk']}], [f"Option {index + 1}: {item['option']} -> {item['number']}" for index, item in enumerate(name_options)])
    payloads["mobile_number_intelligence"] = _section_payload("mobile_number_intelligence", mobile_summary, f"Current mobile vibration {mobile_vibration} with {mobile_compatibility} compatibility.", "Mobile frequency influences communication and response cadence.", "Misalignment may increase noise or decision fatigue.", "Shift to supportive ending patterns when feasible.", [{"label": "Current Mobile", "value": mobile_value or 'Not provided'}, {"label": "Target Vibrations", "value": ', '.join(str(v) for v in mobile_supportive[:4])}, {"label": "Ending Logic", "value": "Prefer final digits matching supportive triad"}])
    payloads["email_identity_intelligence"] = _section_payload("email_identity_intelligence", f"Current email vibration {email_vibration} shapes digital authority signal.", "Digital identity is active but can be optimized for trust and visibility.", "Email local-part vibration affects first-impression coding.", "Weak signal can lower credibility and response quality.", "Use cleaner naming pattern aligned with target profile numbers.", [{"label": "Current Email", "value": email_value or 'Not provided'}, {"label": "Email Vibration", "value": str(email_vibration or 0)}, {"label": "Authority Signal", "value": 'High' if email_vibration in {1, 8, 9, 22} else 'Moderate'}], [f"Suggested pattern: {pattern}" for pattern in _handle_patterns(first_name, name_targets)])
    payloads["signature_intelligence"] = _section_payload("signature_intelligence", "Signature energy should communicate authority with controlled flow and completion.", "Current signature behavior can be optimized for growth alignment.", "Stroke structure encodes confidence and decision intent.", "Weak structure can dilute authority signal.", "Use rising start, stable midline, and forward closure stroke.", [{"label": "Starting Stroke", "value": "Begin upward, avoid backward hooks"}, {"label": "Ending Stroke", "value": "Close forward-right with complete finish"}, {"label": "Authority Alignment", "value": 'High' if name_number in {1, 8, 9, 22} else 'Moderate'}])
    payloads["business_name_intelligence"] = _section_payload("business_name_intelligence", f"Business vibration {business_number or 0}, compound {business_compound or 0}, signal: {business_strength}.", "Business name signal affects commercial trust and positioning.", "Brand vibration influences category fit and conversion texture.", "Misalignment can reduce pricing power and authority velocity.", "Adjust naming pattern toward target commercial numbers when required.", [{"label": "Business Name", "value": business_name or 'Not provided'}, {"label": "Industry Fit", "value": ', '.join(business_industries[:3])}, {"label": "Risk", "value": business_risk}])

    handle_source = domain_handle or social_handle or first_name
    handle_vibration = _vibration_from_text(handle_source)
    payloads["brand_handle_optimization"] = _section_payload("brand_handle_optimization", f"Current handle/domain vibration {handle_vibration or 0} should align with visibility strategy.", "Public handle signal can be optimized for trust and discoverability.", "Handle vibration influences memorability and social proof perception.", "Weak naming logic lowers visibility consistency.", "Unify handle/domain root with target vibration endings.", [{"label": "Social Handle", "value": social_handle or 'Not provided'}, {"label": "Domain Handle", "value": domain_handle or 'Not provided'}, {"label": "Authority Signal", "value": 'High' if handle_vibration in {1, 8, 9, 22} else 'Moderate'}], [f"Improved pattern: {pattern}" for pattern in _handle_patterns(handle_source, name_targets)])
    payloads["residence_energy_intelligence"] = _section_payload("residence_energy_intelligence", f"Residence vibration {residence_vibration or 0} affects baseline stability signal.", "Home number creates recurring environmental energy tone.", "Repeated daily exposure amplifies behavior feedback.", "Misfit vibration can reduce recovery quality and clarity.", "Apply symbolic balancing with plate letters and entrance corrections.", [{"label": "Current Residence Number", "value": residence_number or 'Not provided'}, {"label": "Residence Vibration", "value": str(residence_vibration or 0)}])
    payloads["vehicle_number_intelligence"] = _section_payload("vehicle_number_intelligence", f"Vehicle vibration {vehicle_vibration or 0} influences movement tone and confidence expression.", "Vehicle number creates recurring movement-state signal.", "Travel frequency amplifies vibration feedback into transitions.", "Misalignment may increase urgency bias and reactive behavior.", "Prefer compatible number logic during selection or correction.", [{"label": "Current Vehicle Number", "value": vehicle_number or 'Not provided'}, {"label": "Vehicle Vibration", "value": str(vehicle_vibration or 0)}])
    payloads["lifestyle_alignment"] = _section_payload("lifestyle_alignment", "Lifestyle alignment strategic infrastructure à¤¹à¥ˆ, à¤¸à¤¿à¤°à¥à¤« wellness filler à¤¨à¤¹à¥€à¤‚à¥¤", f"Weakest metric {weakest_metric.lower()} à¤•à¥‹ rhythm-led stabilization à¤šà¤¾à¤¹à¤¿à¤à¥¤", "Routine disruption cognitive noise à¤”à¤° volatility à¤¬à¤¢à¤¼à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤", "à¤¯à¤¹ instability clarity, discipline, à¤”à¤° execution quality à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤", lifestyle_protocol)
    payloads["digital_discipline"] = _section_payload("digital_discipline", "Digital behavior à¤¸à¥€à¤§à¥‡ decision quality à¤”à¤° recovery à¤•à¥‹ shape à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Notification overload à¤à¤• hidden performance drain à¤¹à¥ˆà¥¤", "High-frequency context switching deficit metrics à¤•à¥‹ amplify à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤", "à¤‡à¤¸à¤•à¥‡ à¤¬à¤¾à¤¦ reactive decisions à¤”à¤° deep-work quality à¤®à¥‡à¤‚ à¤—à¤¿à¤°à¤¾à¤µà¤Ÿ à¤¦à¤¿à¤–à¤¤à¥€ à¤¹à¥ˆà¥¤", digital_protocol)
    payloads["vedic_remedy"] = _section_payload("vedic_remedy", "Vedic protocol is focus-conditioning and discipline anchor.", "Current profile benefits from ritualized consistency loops.", "Weakest metric and dominant planet point to intervention need.", "Improves composure and timing discipline.", f"Code: {vedic_code} | Parameter: {vedic_parameter}", [{"label": "Focus", "value": weakest_metric}, {"label": "Code", "value": vedic_code}, {"label": "Parameter", "value": vedic_parameter}, {"label": "Output", "value": vedic_output}])
    payloads["correction_protocol_summary"] = _section_payload("correction_protocol_summary", "Correction protocol ranks interventions by impact on stability and monetizable outcomes.", "Multiple correction levers exist and must be sequenced.", "Weakest metric and identity-signal gaps define order.", "Correct sequencing improves measurable improvement speed.", "Execute 21-day and 90-day checkpoints with priority order.", [{"label": "Top Priority", "value": correction_priority_lines[0]}, {"label": "High-Impact Quick Fixes", "value": ' | '.join(correction_priority_lines[:2])}, {"label": "Medium-Term Adjustments", "value": "Email identity, signature protocol, environment alignment"}, {"label": "Premium Advisory", "value": "Run full correction audit quarterly"}], correction_priority_lines)
    payloads["business_intelligence"] = _section_payload("business_intelligence", f"Business signal: {business_strength}. Risk gate: {business_risk}.", "Commercial upside exists with correction-led governance discipline.", "Business vibration and metric stack indicate potential with pressure constraints.", "Without structure, growth can convert into volatility.", "Align offer, pricing, and positioning to cycle window.")
    payloads["wealth_energy_blueprint"] = _section_payload("wealth_energy_blueprint", f"Wealth blueprint: financial discipline {_safe_int(scores.get('financial_discipline_index'), 50)} with business vibration {business_number or 'N/A'}.", "Wealth path depends on behavior architecture.", "Financial metric and identity signals define compounding quality.", "Protocol failure causes leak in high-income phases.", "Use monthly capital governance and staged risk model.")
    payloads["decision_intelligence"] = _section_payload("decision_intelligence", "Decision intelligence à¤•à¥‹ filters, delay rules, à¤”à¤° review loops à¤¸à¥‡ engineer à¤•à¤¿à¤¯à¤¾ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Current profile à¤®à¥‡à¤‚ capability à¤¹à¥ˆ, à¤ªà¤° stress phase inconsistency à¤­à¥€ à¤¹à¥ˆà¥¤", f"Weakest metric {weakest_metric.lower()} high load à¤®à¥‡à¤‚ decision noise à¤¬à¤¢à¤¼à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Fast à¤”à¤° unfiltered calls opportunity cost à¤¬à¤¢à¤¼à¤¾à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤", decision_protocol)
    payloads["emotional_intelligence"] = _section_payload("emotional_intelligence", "Emotional regulation strategic performance infrastructure à¤•à¤¾ core à¤¹à¤¿à¤¸à¥à¤¸à¤¾ à¤¹à¥ˆà¥¤", "Recovery speed à¤à¤• variable risk factor à¤•à¥€ à¤¤à¤°à¤¹ à¤•à¤¾à¤® à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤", "Metric pattern à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤•à¤¿ rhythm à¤Ÿà¥‚à¤Ÿà¤¨à¥‡ à¤ªà¤° reactive windows à¤¬à¤¢à¤¼à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤", "à¤‡à¤¸à¤•à¤¾ à¤ªà¥à¤°à¤­à¤¾à¤µ clarity, relationships, à¤”à¤° financial discipline à¤ªà¤° à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤", emotional_protocol)
    payloads["leadership_intelligence"] = _section_payload("leadership_intelligence", "Leadership signal should combine authority with stable execution cadence.", "Leadership potential is high but governance rhythm is mandatory.", "Core numbers indicate strategic strength with overextension risk.", "Inconsistent cadence reduces trust and execution velocity.", "Weekly leadership protocol: priorities, delegation, review, recovery.")
    payloads["strategic_timing_intelligence"] = _section_payload("strategic_timing_intelligence", "Timing intelligence calibrates when to push, pause, and consolidate.", "Decision quality varies by cycle windows and date resonance.", "Personal-year and pinnacle sequences define timing intensity.", "Poor timing increases effort with lower conversion.", "Use favorable dates for launches and negotiations.", [{"label": "Current Personal Year", "value": str(personal_year)}, {"label": "Favorable Dates", "value": ', '.join(str(v) for v in lucky_dates)}])
    payloads["growth_blueprint"] = _section_payload("growth_blueprint", "Growth blueprint sequences stabilize -> optimize -> scale.", "Current phase is correction-led stabilization before aggressive expansion.", f"Risk band {risk_band} requires structural readiness before scale.", "Premature expansion can lock volatility into operations.", "Run staged roadmap with gate checks across 90 days.")
    payloads["strategic_execution_roadmap"] = _section_payload("strategic_execution_roadmap", "Execution roadmap converts intelligence into a 90-day operating system.", "Multiple interventions need coordinated sequencing.", "Correction outcomes compound only in operational order.", "Unsequenced action wastes effort and obscures ROI.", "Days 1-30 stabilize, 31-60 optimize, 61-90 scale tests.", bullets=["Days 1-30: metric deficit stabilization and behavior lock.", "Days 31-60: identity corrections (name/mobile/email/signature).", "Days 61-90: timing alignment and controlled scale tests."])
    payloads["closing_synthesis"] = _section_payload("closing_synthesis", f"Final synthesis: {full_name} à¤®à¥‡à¤‚ clear leverage potential à¤¹à¥ˆ, à¤¯à¤¦à¤¿ correction priorities à¤•à¥‹ disciplined execution à¤•à¥‡ à¤¸à¤¾à¤¥ à¤šà¤²à¤¾à¤¯à¤¾ à¤œà¤¾à¤à¥¤", "Profile calibration-sensitive à¤¹à¥ˆ, fundamentally blocked à¤¨à¤¹à¥€à¤‚à¥¤", "Strength-deficit architecture à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥ˆ à¤”à¤° à¤¸à¤¹à¥€ sequence à¤¸à¥‡ correct à¤•à¥€ à¤œà¤¾ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤", "Protocol-led execution constraints à¤•à¥‹ strategic advantage à¤®à¥‡à¤‚ à¤¬à¤¦à¤² à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤", "Correction stack, timing control, à¤”à¤° quarterly recalibration à¤ªà¤° committed à¤°à¤¹à¥‡à¤‚à¥¤")

    if plan_name == "basic":
        mulank = _reduce_number(day)
        bhagyank = life_path or _reduce_number(day + month + _reduce_number(year))
        interaction_gap = abs((mulank or 0) - (bhagyank or 0))
        interaction_state = "à¤¸à¤‚à¤¤à¥à¤²à¤¿à¤¤" if interaction_gap <= 2 else "à¤µà¤¿à¤°à¥‹à¤§à¥€ à¤¸à¤‚à¤•à¥‡à¤¤"
        repeating_numbers = [
            number
            for number in range(1, 10)
            if _safe_int(grid_counts.get(str(number), grid_counts.get(number, 0)), 0) > 1
        ]
        repeating_text = ", ".join(str(number) for number in repeating_numbers) if repeating_numbers else "à¤•à¥‹à¤ˆ à¤ªà¥à¤°à¤®à¥à¤– à¤ªà¥à¤¨à¤°à¤¾à¤µà¥ƒà¤¤à¥à¤¤à¤¿ à¤¨à¤¹à¥€à¤‚"
        mobile_classification = "supportive" if mobile_vibration in {mulank, bhagyank, destiny} else "neutral"
        email_available = bool(email_value)
        color_base = (name_number or bhagyank or mulank or 5)
        color_map = {
            1: ("gold, saffron", "dark grey"),
            2: ("white, silver", "muddy brown"),
            3: ("yellow, honey", "dull black"),
            4: ("smoky blue, graphite", "neon red"),
            5: ("green, mint", "overly dark maroon"),
            6: ("cream, rose", "charcoal black"),
            7: ("sea green, turquoise", "rust orange"),
            8: ("navy, steel blue", "faded yellow"),
            9: ("maroon, crimson", "pale grey"),
        }
        favorable_colors, caution_colors = color_map.get(color_base, ("green, blue", "muddy grey"))
        mulank_trait = NUMBER_TRAITS.get(mulank, NUMBER_TRAITS[5])
        bhagyank_trait = NUMBER_TRAITS.get(bhagyank, NUMBER_TRAITS[5])
        focus_key = _safe_text((intake_context.get("focus") or {}).get("life_focus"), "general_alignment")
        focus_text = focus_key.replace("_", " ")
        city_hint = _safe_text(birth_details.get("birthplace_city") or identity.get("city"), "local environment")
        compatibility_level = _safe_text((numerology_core.get("compatibility") or {}).get("compatibility_level"), "Moderate")

        basic_payloads: Dict[str, Any] = {}
        basic_payloads["executive_numerology_summary"] = _section_payload(
            "executive_numerology_summary",
            f"{full_name} à¤•à¥€ numerology profile à¤•à¤¾ à¤®à¥‚à¤² à¤¸à¥à¤µà¤° {mulank}-{bhagyank}-{name_number or '-'} à¤¸à¤‚à¤¯à¥‹à¤œà¤¨ à¤ªà¤° à¤†à¤§à¤¾à¤°à¤¿à¤¤ à¤¹à¥ˆà¥¤ à¤®à¥à¤–à¥à¤¯ à¤¤à¤¾à¤•à¤¤ {strongest_metric} à¤”à¤° à¤šà¥à¤¨à¥Œà¤¤à¥€ {weakest_metric} à¤¹à¥ˆà¥¤ à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ focus: {focus_text}.",
            "Core number stack à¤¸à¥‡ quick nature signal à¤¸à¥à¤ªà¤·à¥à¤Ÿ à¤¹à¥ˆà¥¤",
            "à¤®à¥‚à¤²à¤¾à¤‚à¤•, à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤• à¤”à¤° à¤¨à¤¾à¤®à¤¾à¤‚à¤• à¤•à¤¾ à¤¸à¤‚à¤¯à¥à¤•à¥à¤¤ à¤ªà¥à¤°à¤­à¤¾à¤µ baseline behavior à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            f"à¤‡à¤¸à¤•à¤¾ à¤…à¤¸à¤° à¤¨à¤¿à¤°à¥à¤£à¤¯, à¤¸à¤‚à¤¬à¤‚à¤§, à¤¦à¤¿à¤¨à¤šà¤°à¥à¤¯à¤¾ à¤”à¤° execution consistency à¤ªà¤° à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆ, à¤–à¤¾à¤¸à¤•à¤° {city_hint} à¤œà¥ˆà¤¸à¥‡ environment à¤®à¥‡à¤‚à¥¤",
            f"à¤ªà¤¹à¤²à¥€ correction priority: {weakest_metric.lower()} stabilization à¤”à¤° missing number disciplineà¥¤",
        )
        basic_payloads["core_numbers_analysis"] = _section_payload(
            "core_numbers_analysis",
            f"Mulank {mulank}, Bhagyank {bhagyank}, Destiny {destiny}, Expression {expression}.",
            "à¤¯à¥‡ à¤šà¤¾à¤° à¤¸à¤‚à¤–à¥à¤¯à¤¾ à¤†à¤ªà¤•à¥€ à¤†à¤§à¤¾à¤° à¤¸à¤‚à¤°à¤šà¤¨à¤¾ à¤¦à¤¿à¤–à¤¾à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "à¤œà¤¨à¥à¤®à¤¤à¤¿à¤¥à¤¿ à¤”à¤° à¤¨à¤¾à¤® vibration à¤¸à¥‡ à¤¯à¥‡ numbers deterministic à¤¤à¤°à¥€à¤•à¥‡ à¤¸à¥‡ à¤¨à¤¿à¤•à¤²à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "à¤µà¥à¤¯à¤•à¥à¤¤à¤¿à¤¤à¥à¤µ, à¤…à¤µà¤¸à¤° à¤”à¤° à¤šà¥à¤¨à¥Œà¤¤à¤¿à¤¯à¥‹à¤‚ à¤•à¤¾ à¤®à¥à¤–à¥à¤¯ pattern à¤¯à¤¹à¥€ à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¹à¤° weekly review à¤®à¥‡à¤‚ à¤‡à¤¨ numbers à¤•à¥‡ basis à¤ªà¤° self-observation à¤•à¤°à¥‡à¤‚à¥¤",
        )
        basic_payloads["name_number_analysis"] = _section_payload(
            "name_number_analysis",
            f"à¤¨à¤¾à¤®à¤¾à¤‚à¤• {name_number} à¤”à¤° compound {name_compound} à¤†à¤ªà¤•à¥‡ à¤ªà¤¹à¤šà¤¾à¤¨ à¤¸à¤‚à¤•à¥‡à¤¤ à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "à¤¨à¤¾à¤® à¤¸à¤‚à¤–à¥à¤¯à¤¾ à¤†à¤ªà¤•à¥‡ social impression à¤”à¤° communication tone à¤•à¥‹ à¤¦à¤°à¥à¤¶à¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "à¤…à¤•à¥à¤·à¤°-à¤µà¤¾à¤‡à¤¬à¥à¤°à¥‡à¤¶à¤¨ à¤¸à¥‡ à¤¬à¤¨à¤¾ total à¤†à¤ªà¤•à¥€ à¤ªà¤¹à¤šà¤¾à¤¨ à¤•à¥€ à¤¸à¥à¤¥à¤¿à¤°à¤¤à¤¾ à¤”à¤° trust signal à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¨à¤¾à¤® à¤”à¤° à¤®à¥‚à¤²à¤¾à¤‚à¤•/à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤• à¤®à¥‡à¤‚ mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° clarity à¤”à¤° confidence à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "à¤¨à¤¾à¤® à¤‰à¤ªà¤¯à¥‹à¤— à¤®à¥‡à¤‚ consistency à¤°à¤–à¥‡à¤‚ à¤”à¤° practical à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° target-friendly spelling à¤…à¤ªà¤¨à¤¾à¤à¤‚à¥¤",
            [
                {"label": "Current Name Number", "value": str(name_number)},
                {"label": "Strength", "value": name_trait["strength"]},
                {"label": "Risk", "value": name_trait["risk"]},
            ],
            [f"à¤µà¤¿à¤•à¤²à¥à¤ª {index + 1}: {item['option']} -> {item['number']}" for index, item in enumerate(name_options)],
        )
        basic_payloads["mulank_description"] = _section_payload(
            "mulank_description",
            f"Mulank {mulank} à¤†à¤ªà¤•à¥€ instinctive response style à¤”à¤° daily behavior tone à¤•à¥‹ à¤¦à¤°à¥à¤¶à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤ à¤¯à¤¹ {mulank_trait['strength']} à¤•à¥‹ à¤¬à¤¢à¤¼à¤¾à¤¤à¤¾ à¤¹à¥ˆ à¤”à¤° {mulank_trait['risk']} tendency à¤¦à¤¿à¤–à¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤®à¥‚à¤²à¤¾à¤‚à¤• à¤†à¤ªà¤•à¥€ natural à¤ªà¥à¤°à¤¤à¤¿à¤•à¥à¤°à¤¿à¤¯à¤¾ à¤”à¤° à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾ pattern à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¦à¤¿à¤¨à¤¾à¤‚à¤• à¤œà¤¨à¥à¤® à¤•à¤¾ root number à¤¸à¥€à¤§à¥‡ personality reflexes à¤¸à¥‡ à¤œà¥à¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Strengths à¤”à¤° blind spots à¤¦à¥ˆà¤¨à¤¿à¤• à¤«à¥ˆà¤¸à¤²à¥‹à¤‚ à¤®à¥‡à¤‚ à¤¬à¤¾à¤°-à¤¬à¤¾à¤° à¤¦à¤¿à¤–à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "à¤®à¥‚à¤²à¤¾à¤‚à¤• strength à¤•à¥‹ routine à¤®à¥‡à¤‚ à¤‰à¤ªà¤¯à¥‹à¤— à¤•à¤°à¥‡à¤‚ à¤”à¤° weakness à¤ªà¤° habit correction à¤²à¤—à¤¾à¤à¤‚à¥¤",
        )
        basic_payloads["bhagyank_description"] = _section_payload(
            "bhagyank_description",
            f"Bhagyank {bhagyank} life path theme, growth direction à¤”à¤° recurring lesson cycle à¤•à¥‹ define à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤ à¤‡à¤¸à¤•à¤¾ core strength {bhagyank_trait['strength']} à¤¹à¥ˆà¥¤",
            "à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤• long-term direction à¤”à¤° opportunity flow à¤•à¤¾ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤ªà¥‚à¤°à¤¾ à¤œà¤¨à¥à¤®à¤¾à¤‚à¤• à¤¯à¥‹à¤— (life path) à¤¸à¥‡ destiny pattern à¤¨à¤¿à¤•à¤²à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            f"à¤—à¤²à¤¤ timing à¤¯à¤¾ discipline gap à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° growth à¤§à¥€à¤®à¥€ à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆ à¤”à¤° {bhagyank_trait['risk']} à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            f"à¤µà¥à¤¯à¤•à¥à¤¤à¤¿à¤—à¤¤ à¤µà¤°à¥à¤· {personal_year} à¤”à¤° à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤• à¤•à¥‹ à¤œà¥‹à¤¡à¤¼à¤•à¤° yearly focus à¤¤à¤¯ à¤•à¤°à¥‡à¤‚à¥¤",
        )
        basic_payloads["number_interaction_analysis"] = _section_payload(
            "number_interaction_analysis",
            f"Mulank {mulank}, Bhagyank {bhagyank}, Name Number {name_number or '-'} à¤•à¥‡ à¤¬à¥€à¤š {interaction_state} pattern à¤¦à¤¿à¤–à¤¾à¤ˆ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆ (gap {interaction_gap}).",
            "Numbers à¤®à¥‡à¤‚ harmony à¤¯à¤¾ conflict execution style à¤¬à¤¦à¤²à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤œà¤¬ root numbers à¤¦à¥‚à¤° à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚ à¤¤à¥‹ behavior à¤®à¥‡à¤‚ friction à¤¬à¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤«à¥‹à¤•à¤¸, confidence à¤”à¤° consistency à¤ªà¤° à¤¸à¥€à¤§à¤¾ à¤ªà¥à¤°à¤­à¤¾à¤µ à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤…à¤—à¤° conflict à¤¹à¥ˆ à¤¤à¥‹ routine, mantra à¤”à¤° number-aligned habit à¤¸à¥‡ correction à¤•à¤°à¥‡à¤‚à¥¤",
        )
        basic_payloads["loshu_grid_interpretation"] = _section_payload(
            "loshu_grid_interpretation",
            f"Lo Shu present: {', '.join(str(v) for v in loshu_present) or 'none'} | missing: {', '.join(str(v) for v in loshu_missing) or 'none'}.",
            "Lo Shu grid à¤Šà¤°à¥à¤œà¤¾ layout à¤•à¥‹ practical à¤°à¥‚à¤ª à¤¸à¥‡ à¤¦à¤¿à¤–à¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤œà¤¨à¥à¤®à¤¾à¤‚à¤• digit distribution à¤¸à¥‡ present à¤”à¤° missing energies à¤¨à¤¿à¤•à¤²à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "Present numbers natural strengths à¤”à¤° missing numbers correction areas à¤¬à¤¤à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Grid reading à¤•à¥‹ weekly behavior tracking à¤¸à¥‡ validate à¤•à¤°à¥‡à¤‚à¥¤",
        )
        basic_payloads["missing_numbers_analysis"] = _section_payload(
            "missing_numbers_analysis",
            f"Missing numbers: {', '.join(str(v) for v in loshu_missing) if loshu_missing else 'none'}.",
            "Missing numbers à¤¸à¤‚à¤­à¤¾à¤µà¤¿à¤¤ behavior gaps à¤•à¥‹ à¤¦à¤¿à¤–à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "à¤‡à¤¨ digits à¤•à¥€ à¤•à¤®à¥€ communication, flexibility à¤¯à¤¾ discipline gaps à¤®à¥‡à¤‚ à¤¦à¤¿à¤– à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "à¤—à¥ˆà¤ª untreated à¤°à¤¹à¥‡ à¤¤à¥‹ repeat friction à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¹à¤° missing digit à¤•à¥‡ à¤²à¤¿à¤ à¤à¤• micro-habit correction à¤¨à¤¿à¤°à¥à¤§à¤¾à¤°à¤¿à¤¤ à¤•à¤°à¥‡à¤‚à¥¤",
            [f"Missing {number}: structured correction routine à¤†à¤µà¤¶à¥à¤¯à¤•." for number in loshu_missing[:5]],
        )
        basic_payloads["repeating_numbers_impact"] = _section_payload(
            "repeating_numbers_impact",
            f"Repeating numbers pattern: {repeating_text}.",
            "Repeated digits amplified traits à¤¦à¤¿à¤–à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "à¤à¤• à¤¹à¥€ digit à¤•à¤¾ à¤¬à¤¾à¤°-à¤¬à¤¾à¤° à¤†à¤¨à¤¾ excess tendency à¤•à¥‹ à¤®à¤œà¤¬à¥‚à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Overuse à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° rigidity, impulsivity à¤¯à¤¾ overthinking à¤‰à¤­à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Amplified trait à¤•à¥‹ balance à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ opposite habit anchor à¤œà¥‹à¤¡à¤¼à¥‡à¤‚à¥¤",
        )
        basic_payloads["mobile_number_numerology"] = _section_payload(
            "mobile_number_numerology",
            f"Mobile vibration {mobile_vibration} à¤•à¤¾ classification: {mobile_classification}.",
            "à¤®à¥‹à¤¬à¤¾à¤‡à¤² vibration daily communication tone à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Digit sum vibration profile numbers à¤•à¥‡ à¤¸à¤¾à¤¥ resonance à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¯à¤¾ à¤˜à¤Ÿà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Conflicting vibration à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° distraction à¤”à¤° clarity drop à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Supportive ending pattern à¤šà¥à¤¨à¥‡à¤‚ à¤”à¤° usage discipline maintain à¤°à¤–à¥‡à¤‚à¥¤",
            [{"label": "Current Mobile", "value": mobile_value or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"}],
        )
        basic_payloads["mobile_life_number_compatibility"] = _section_payload(
            "mobile_life_number_compatibility",
            f"Mobile vibration {mobile_vibration} à¤¬à¤¨à¤¾à¤® life numbers {mulank}/{bhagyank}: {mobile_classification}.",
            "à¤¯à¤¹ à¤¸à¥‡à¤•à¥à¤¶à¤¨ mobile à¤”à¤° life-number relationship à¤•à¥‹ simple à¤¤à¤°à¥€à¤•à¥‡ à¤¸à¥‡ à¤ªà¤¢à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Compatibility resonance à¤œà¤¿à¤¤à¤¨à¥€ à¤¬à¥‡à¤¹à¤¤à¤° à¤¹à¥‹à¤—à¥€, communication clarity à¤‰à¤¤à¤¨à¥€ smooth à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° response fatigue à¤¯à¤¾ decision delay à¤¬à¤¢à¤¼ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¯à¤¦à¤¿ mismatch à¤¹à¥ˆ à¤¤à¥‹ à¤…à¤—à¤²à¥€ SIM update à¤®à¥‡à¤‚ supportive digit logic à¤šà¥à¤¨à¥‡à¤‚à¥¤",
        )
        basic_payloads["email_numerology"] = _section_payload(
            "email_numerology",
            f"Email vibration {email_vibration or 0} trust, clarity à¤”à¤° digital identity signal à¤•à¥‹ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤" if email_available else "à¤ˆà¤®à¥‡à¤² à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆ, à¤‡à¤¸à¤²à¤¿à¤ à¤…à¤­à¥€ detailed email numerology analysis à¤¸à¥€à¤®à¤¿à¤¤ à¤¹à¥ˆà¥¤",
            "Email local-part à¤­à¥€ à¤à¤• numerology identity layer à¤®à¤¾à¤¨à¥€ à¤œà¤¾à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Vibration authority perception à¤”à¤° response quality à¤ªà¤° à¤ªà¥à¤°à¤­à¤¾à¤µ à¤¡à¤¾à¤²à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Weak pattern à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° digital signal dilute à¤¹à¥‹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Email à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° clean pattern à¤•à¥‡ à¤¸à¤¾à¤¥ optimized à¤¸à¥à¤à¤¾à¤µ generate à¤•à¤°à¥‡à¤‚à¥¤",
            [{"label": "Current Email", "value": email_value or "à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚"}],
        )
        basic_payloads["numerology_personality_profile"] = _section_payload(
            "numerology_personality_profile",
            f"Personality profile à¤®à¥‡à¤‚ {name_strength} à¤ªà¥à¤°à¤®à¥à¤– à¤¹à¥ˆ, à¤œà¤¬à¤•à¤¿ {name_risk} internal blind spot à¤•à¥€ à¤¤à¤°à¤¹ à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Numbers social style, inner nature à¤”à¤° reaction pattern à¤•à¥‹ summarize à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Mulank + Name Number à¤•à¤¾ à¤®à¤¿à¤¶à¥à¤°à¤£ interpersonal tone à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Blind spots unmanaged à¤°à¤¹à¥‡à¤‚ à¤¤à¥‹ relationship à¤”à¤° confidence à¤¦à¥‹à¤¨à¥‹à¤‚ à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Strength-driven behavior à¤°à¤–à¥‡à¤‚ à¤”à¤° blind spot à¤ªà¤° conscious pause rule à¤²à¤—à¤¾à¤à¤‚à¥¤",
        )
        basic_payloads["current_life_phase_insight"] = _section_payload(
            "current_life_phase_insight",
            f"Current life phase theme: personal year {personal_year} à¤”à¤° risk band {risk_band}.",
            "à¤¯à¤¹ phase correction-led stabilization à¤”à¤° clarity building à¤•à¤¾ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Personal year à¤”à¤° number interaction à¤‡à¤¸ à¤¸à¤®à¤¯ à¤•à¥€ priority à¤¤à¤¯ à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Wrong focus à¤šà¥à¤¨à¤¨à¥‡ à¤ªà¤° effort high à¤”à¤° output low à¤°à¤¹ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤‡à¤¸ phase à¤®à¥‡à¤‚ consistency, timing à¤”à¤° disciplined decisions à¤ªà¤° à¤«à¥‹à¤•à¤¸ à¤°à¤–à¥‡à¤‚à¥¤",
        )
        basic_payloads["career_financial_tendencies"] = _section_payload(
            "career_financial_tendencies",
            f"Career tendency {career_industry} orientation à¤•à¥‡ à¤¸à¤¾à¤¥ à¤”à¤° financial discipline score {_safe_int(scores.get('financial_discipline_index'), 50)} à¤•à¥‡ à¤†à¤¸à¤ªà¤¾à¤¸ à¤¹à¥ˆà¥¤ à¤¯à¤¹ {focus_text} à¤²à¤•à¥à¤·à¥à¤¯ à¤•à¥‡ à¤²à¤¿à¤ à¤‰à¤ªà¤¯à¥‹à¤—à¥€ à¤¸à¤‚à¤•à¥‡à¤¤ à¤¦à¥‡à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¯à¤¹ section à¤•à¥‡à¤µà¤² numerology-based tendencies à¤¬à¤¤à¤¾à¤¤à¤¾ à¤¹à¥ˆ, consulting strategy à¤¨à¤¹à¥€à¤‚à¥¤",
            "Work style, routine discipline à¤”à¤° number resonance earning pattern à¤•à¥‹ shape à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Reactive style à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° income consistency à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Skill depth, role-fit à¤”à¤° money routine à¤ªà¤° steady focus à¤°à¤–à¥‡à¤‚à¥¤",
        )
        basic_payloads["relationship_compatibility_patterns"] = _section_payload(
            "relationship_compatibility_patterns",
            f"{compatibility_summary} Current compatibility level: {compatibility_level}.",
            "Relationship pattern à¤®à¥‡à¤‚ emotional style à¤”à¤° number resonance à¤¦à¥‹à¤¨à¥‹à¤‚ à¤•à¤¾à¤® à¤•à¤°à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Compatibility tendency communication pace à¤”à¤° expectation alignment à¤¸à¥‡ à¤¬à¤¨à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Mismatch à¤¹à¥‹à¤¨à¥‡ à¤ªà¤° repeated misunderstanding cycle à¤¬à¤¨ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Clear boundaries, calm communication à¤”à¤° timing awareness à¤°à¤–à¥‡à¤‚à¥¤",
        )
        basic_payloads["health_tendencies_from_numbers"] = _section_payload(
            "health_tendencies_from_numbers",
            f"Emotional regulation score {_safe_int(scores.get('emotional_regulation_index'), 50)} à¤”à¤° karma pressure {_safe_int(scores.get('karma_pressure_index'), 50)} stress tendency à¤•à¥€ à¤¦à¤¿à¤¶à¤¾ à¤¦à¤¿à¤–à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤ à¤¸à¤¬à¤¸à¥‡ à¤¸à¤‚à¤µà¥‡à¤¦à¤¨à¤¶à¥€à¤² axis: {weakest_metric}.",
            "à¤¯à¤¹ numerology-based wellness tendency à¤¹à¥ˆ, medical diagnosis à¤¨à¤¹à¥€à¤‚à¥¤",
            "Number imbalance sleep rhythm, stress response à¤”à¤° recovery pattern à¤ªà¥à¤°à¤­à¤¾à¤µà¤¿à¤¤ à¤•à¤° à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤…à¤µà¤¹à¥‡à¤²à¤¨à¤¾ à¤•à¤°à¤¨à¥‡ à¤ªà¤° fatigue à¤”à¤° decision quality à¤¦à¥‹à¤¨à¥‹à¤‚ à¤—à¤¿à¤° à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Breath reset, sleep discipline à¤”à¤° low-noise routine à¤…à¤ªà¤¨à¤¾à¤à¤‚à¥¤",
        )
        basic_payloads["personal_year_forecast"] = _section_payload(
            "personal_year_forecast",
            f"à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ personal year {personal_year} à¤‡à¤¸ à¤µà¤°à¥à¤· à¤•à¥€ à¤—à¤¤à¤¿ à¤”à¤° à¤ªà¥à¤°à¤¾à¤¥à¤®à¤¿à¤•à¤¤à¤¾ à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            f"Year {personal_year} à¤®à¥‡à¤‚ focus theme correction + consistency à¤¹à¥ˆà¥¤",
            "Personal year à¤œà¤¨à¥à¤® à¤¦à¤¿à¤¨, à¤®à¤¾à¤¹ à¤”à¤° à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤µà¤°à¥à¤· à¤•à¥‡ à¤¯à¥‹à¤— à¤¸à¥‡ à¤¬à¤¨à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤¸à¤¹à¥€ timing à¤šà¥à¤¨à¤¨à¥‡ à¤ªà¤° effort à¤•à¤¾ à¤ªà¤°à¤¿à¤£à¤¾à¤® à¤¬à¥‡à¤¹à¤¤à¤° à¤®à¤¿à¤²à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ decisions à¤”à¤° launches à¤•à¥‹ favorable date windows à¤®à¥‡à¤‚ à¤°à¤–à¥‡à¤‚à¥¤",
            [
                {"label": "Current Personal Year", "value": str(personal_year)},
                {"label": "Favorable Dates", "value": ", ".join(str(v) for v in lucky_dates)},
            ],
        )
        basic_payloads["lucky_numbers_favorable_dates"] = _section_payload(
            "lucky_numbers_favorable_dates",
            f"Supportive numbers: {', '.join(str(v) for v in name_targets[:4]) or '3, 5, 9'} | favorable dates: {', '.join(str(v) for v in lucky_dates)}.",
            "à¤¯à¤¹ superstition à¤¨à¤¹à¥€à¤‚, à¤¬à¤²à¥à¤•à¤¿ numerology timing utility à¤¹à¥ˆà¥¤",
            "à¤®à¥‚à¤²à¤¾à¤‚à¤•, à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤• à¤”à¤° à¤¨à¤¾à¤®à¤¾à¤‚à¤• resonance à¤¸à¥‡ à¤•à¥à¤› à¤¤à¤¿à¤¥à¤¿à¤¯à¤¾à¤‚ à¤…à¤§à¤¿à¤• supportive à¤°à¤¹à¤¤à¥€ à¤¹à¥ˆà¤‚à¥¤",
            "à¤—à¤²à¤¤ timing à¤®à¥‡à¤‚ à¤µà¤¹à¥€ à¤ªà¥à¤°à¤¯à¤¾à¤¸ à¤§à¥€à¤®à¤¾ à¤¯à¤¾ à¤¥à¤•à¤¾à¤Š à¤²à¤— à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "à¤®à¤¹à¤¤à¥à¤µà¤ªà¥‚à¤°à¥à¤£ meeting, outreach à¤”à¤° à¤¨à¤ˆ à¤¶à¥à¤°à¥à¤†à¤¤ supportive dates à¤ªà¤° à¤•à¤°à¥‡à¤‚à¥¤",
            [
                {"label": "Lucky Numbers", "value": ", ".join(str(v) for v in name_targets[:4]) or "3, 5, 9"},
                {"label": "Favorable Dates", "value": ", ".join(str(v) for v in lucky_dates)},
            ],
        )
        basic_payloads["color_alignment"] = _section_payload(
            "color_alignment",
            f"Favorable colors: {favorable_colors}. Caution colors: {caution_colors}.",
            "Color alignment numerology support layer à¤•à¥€ à¤¤à¤°à¤¹ à¤•à¤¾à¤® à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Dominant number vibration à¤¸à¥‡ aligned tones focus à¤”à¤° steadiness à¤¬à¤¢à¤¼à¤¾ à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
            "Mismatched color overuse à¤¸à¥‡ energy tone dull à¤¹à¥‹ à¤¸à¤•à¤¤à¥€ à¤¹à¥ˆà¥¤",
            "Primary wardrobe/workspace à¤®à¥‡à¤‚ favorable tones à¤•à¤¾ controlled use à¤•à¤°à¥‡à¤‚à¥¤",
        )
        basic_payloads["remedies_lifestyle_adjustments"] = _section_payload(
            "remedies_lifestyle_adjustments",
            f"Basic correction layer = simple mantra + disciplined habit + lifestyle alignment. Dominant planet support: {dominant_planet}.",
            "Remedies à¤•à¥‹ practical routine à¤•à¥‡ à¤¸à¤¾à¤¥ à¤œà¥‹à¤¡à¤¼à¤¨à¤¾ à¤¸à¤¬à¤¸à¥‡ à¤ªà¥à¤°à¤­à¤¾à¤µà¥€ à¤°à¤¹à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Consistency à¤•à¥‡ à¤¬à¤¿à¤¨à¤¾ remedy signal à¤•à¤®à¤œà¥‹à¤° à¤¹à¥‹ à¤œà¤¾à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Irregular practice à¤¸à¥‡ correction outcome à¤§à¥€à¤®à¤¾ à¤ªà¤¡à¤¼à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Daily short mantra, fixed routine, à¤”à¤° weekly review à¤°à¤–à¥‡à¤‚à¥¤",
            [
                f"Mantra: {vedic_code}",
                f"Practice: {vedic_parameter}",
                f"Lifestyle: {lifestyle_protocol}",
            ],
        )
        basic_payloads["closing_numerology_guidance"] = _section_payload(
            "closing_numerology_guidance",
            f"Main life theme: {bhagyank} path refinement with {mulank} day-expression and name signal {name_number}. Primary correction: {weakest_metric}.",
            "à¤†à¤ªà¤•à¥€ numerology profile workable à¤”à¤° correctable à¤¹à¥ˆà¥¤",
            "Core numbers, Lo Shu gaps à¤”à¤° daily habits à¤•à¤¾ à¤œà¥‹à¤¡à¤¼ final outcome à¤¤à¤¯ à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Correction priority ignore à¤•à¤°à¤¨à¥‡ à¤ªà¤° repeat cycle à¤¬à¤¨ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆà¥¤",
            "Next best step: 21-day correction routine + monthly numerology review.",
        )

        basic_payloads = _personalize_basic_payloads(
            basic_payloads,
            full_name=full_name,
            first_name=first_name,
            date_of_birth=date_of_birth,
            current_problem=current_problem,
            city_hint=city_hint,
            focus_text=focus_text,
            mulank=mulank,
            bhagyank=bhagyank,
            life_path=life_path,
            destiny=destiny,
            expression=expression,
            name_number=name_number,
            name_compound=name_compound,
            personal_year=personal_year,
            strongest_metric=strongest_metric,
            weakest_metric=weakest_metric,
            risk_band=risk_band,
            loshu_present=loshu_present,
            loshu_missing=loshu_missing,
            repeating_numbers=repeating_numbers,
            mobile_vibration=mobile_vibration,
            mobile_classification=mobile_classification,
            mobile_value=mobile_value,
            email_value=email_value,
            email_vibration=email_vibration,
            compatibility_summary=compatibility_summary,
            compatibility_level=compatibility_level,
            career_industry=career_industry,
            lucky_dates=lucky_dates,
            name_targets=name_targets,
            favorable_colors=favorable_colors,
            caution_colors=caution_colors,
            dominant_planet=dominant_planet,
            vedic_code=vedic_code,
            vedic_parameter=vedic_parameter,
            lifestyle_protocol=lifestyle_protocol,
            name_options=name_options,
        )

        basic_payloads = _enrich_basic_payloads(
            basic_payloads,
            full_name=full_name,
            first_name=first_name,
            city_hint=city_hint,
            focus_text=focus_text,
            current_problem=current_problem,
            mulank=mulank,
            bhagyank=bhagyank,
            life_path=life_path,
            destiny=destiny,
            expression=expression,
            name_number=name_number,
            name_compound=name_compound,
            loshu_present=loshu_present,
            loshu_missing=loshu_missing,
            repeating_numbers=repeating_numbers,
            mobile_vibration=mobile_vibration,
            mobile_classification=mobile_classification,
            mobile_value=mobile_value,
            email_value=email_value,
            email_vibration=email_vibration,
            compatibility_summary=compatibility_summary,
            compatibility_level=compatibility_level,
            personal_year=personal_year,
            strongest_metric=strongest_metric,
            weakest_metric=weakest_metric,
            risk_band=risk_band,
            lucky_dates=lucky_dates,
            target_numbers=name_targets,
            favorable_colors=favorable_colors,
            caution_colors=caution_colors,
            dominant_planet=dominant_planet,
            vedic_code=vedic_code,
            vedic_parameter=vedic_parameter,
            lifestyle_protocol=lifestyle_protocol,
        )

        payloads.update(basic_payloads)

        # Backward-compatible aliases consumed by current template/context layers.
        payloads["executive_summary"] = basic_payloads["executive_numerology_summary"]
        payloads["core_numerology_numbers"] = basic_payloads["core_numbers_analysis"]
        payloads["birth_date_numerology"] = basic_payloads["current_life_phase_insight"]
        payloads["loshu_grid_intelligence"] = basic_payloads["loshu_grid_interpretation"]
        payloads["mobile_number_intelligence"] = basic_payloads["mobile_number_numerology"]
        payloads["email_identity_intelligence"] = basic_payloads["email_numerology"]
        payloads["archetype_intelligence"] = basic_payloads["numerology_personality_profile"]
        payloads["career_intelligence"] = basic_payloads["career_financial_tendencies"]
        payloads["financial_intelligence"] = basic_payloads["career_financial_tendencies"]
        payloads["decision_intelligence"] = basic_payloads["number_interaction_analysis"]
        payloads["emotional_intelligence"] = basic_payloads["health_tendencies_from_numbers"]
        payloads["compatibility_intelligence"] = basic_payloads["relationship_compatibility_patterns"]
        payloads["lifestyle_alignment"] = basic_payloads["remedies_lifestyle_adjustments"]
        payloads["basic_remedies"] = basic_payloads["remedies_lifestyle_adjustments"]
        payloads["closing_synthesis"] = basic_payloads["closing_numerology_guidance"]

    payloads = _ensure_all_payloads(plan_name, payloads)
    payloads = _localize_payloads(payloads)

    profile_executive = _build_profile_driven_executive_brief(
        full_name=full_name,
        first_name=first_name,
        city_hint=city,
        focus_text=_safe_text(focus.get("life_focus"), "general_alignment"),
        current_problem=current_problem,
        mulank=mulank,
        bhagyank=bhagyank,
        life_path=life_path,
        destiny=destiny,
        expression=expression,
        name_number=name_number,
        personal_year=personal_year,
        loshu_missing=loshu_missing,
        repeating_numbers=repeating_numbers,
        strongest_metric=strongest_metric,
        strongest_score=strongest_score,
        weakest_metric=weakest_metric,
        weakest_score=weakest_score,
        risk_band=risk_band,
        mobile_vibration=mobile_vibration,
        mobile_classification=mobile_classification,
        email_vibration=email_vibration,
        compatibility_level=compatibility_level,
    )
    structural_cause = profile_executive.get("structural_cause") or structural_cause
    intervention_focus = profile_executive.get("intervention_focus") or intervention_focus

    primary_insight = {
        "core_archetype": _safe_text(archetype.get("archetype_name"), "à¤°à¤£à¤¨à¥€à¤¤à¤¿à¤• à¤…à¤¨à¥à¤•à¥‚à¤² archetype"),
        "strength": profile_executive.get("primary_strength") or f"Primary strength axis: {strongest_metric}",
        "critical_deficit": profile_executive.get("primary_deficit") or f"Primary deficit axis: {weakest_metric}",
        "stability_risk": risk_band,
        "phase_1_diagnostic": "Phase 1: deficit triggers diagnose à¤•à¤°à¤•à¥‡ baseline behaviors lock à¤•à¤°à¥‡à¤‚à¥¤",
        "phase_2_blueprint": "Phase 2: architecture-aligned identity corrections deploy à¤•à¤°à¥‡à¤‚à¥¤",
        "phase_3_intervention_protocol": "Phase 3: 90-day timing-calibrated execution protocol à¤šà¤²à¤¾à¤à¤‚à¥¤",
        "narrative": profile_executive.get("summary") or payloads["executive_summary"]["narrative"],
    }

    executive_brief = {
        "summary": profile_executive.get("summary") or payloads["executive_summary"]["narrative"],
        "key_strength": profile_executive.get("key_strength") or primary_insight["strength"],
        "key_risk": profile_executive.get("key_risk") or primary_insight["critical_deficit"],
        "strategic_focus": profile_executive.get("strategic_focus") or intervention_focus,
    }

    analysis_sections = {
        "career_analysis": payloads["career_intelligence"]["narrative"],
        "decision_profile": payloads["decision_intelligence"]["narrative"],
        "emotional_analysis": payloads["emotional_intelligence"]["narrative"],
        "financial_analysis": payloads["financial_intelligence"]["narrative"],
    }

    strategic_guidance = {
        "short_term": profile_executive.get("short_term") or "Short term à¤®à¥‡à¤‚ weakest metric à¤•à¥‹ low-noise behavior protocol à¤¸à¥‡ stabilize à¤•à¤°à¥‡à¤‚à¥¤",
        "mid_term": profile_executive.get("mid_term") or "Mid term à¤®à¥‡à¤‚ identity corrections deploy à¤•à¤°à¤•à¥‡ behavior delta measure à¤•à¤°à¥‡à¤‚à¥¤",
        "long_term": profile_executive.get("long_term") or "Long term scale à¤•à¥‡ à¤²à¤¿à¤ strategic timing à¤”à¤° quarterly recalibration à¤°à¤–à¥‡à¤‚à¥¤",
    }

    growth_blueprint = {
        "phase_1": f"Days 1-30: {strongest_metric} leverage à¤¬à¤¨à¤¾à¤ à¤°à¤–à¤¤à¥‡ à¤¹à¥à¤ {weakest_metric.lower()} baseline stabilize à¤•à¤°à¥‡à¤‚à¥¤",
        "phase_2": f"Days 31-60: concern '{_safe_text(current_problem, 'current challenge')}' à¤•à¥‹ measurable weekly protocols à¤®à¥‡à¤‚ deploy à¤•à¤°à¥‡à¤‚à¥¤",
        "phase_3": f"Days 61-90: personal year {personal_year} theme à¤•à¥‡ à¤¸à¤¾à¤¥ timing-fit growth experiments à¤šà¤²à¤¾à¤à¤‚à¥¤",
    }

    if plan_name == "basic":
        primary_insight = {
            "core_archetype": _safe_text(archetype.get("archetype_name"), "à¤®à¥‚à¤² à¤…à¤‚à¤• à¤µà¥à¤¯à¤•à¥à¤¤à¤¿à¤¤à¥à¤µ"),
            "strength": profile_executive.get("primary_strength") or f"{strongest_metric} profile strength",
            "critical_deficit": profile_executive.get("primary_deficit") or f"{weakest_metric} profile challenge",
            "stability_risk": risk_band,
            "phase_1_diagnostic": "à¤šà¤°à¤£ 1: à¤®à¥‚à¤²à¤¾à¤‚à¤• à¤”à¤° à¤­à¤¾à¤—à¥à¤¯à¤¾à¤‚à¤• pattern à¤¸à¤®à¤à¥‡à¤‚à¥¤",
            "phase_2_blueprint": "à¤šà¤°à¤£ 2: missing numbers à¤”à¤° routine correction à¤²à¤¾à¤—à¥‚ à¤•à¤°à¥‡à¤‚à¥¤",
            "phase_3_intervention_protocol": "à¤šà¤°à¤£ 3: 21-day numerology correction discipline à¤šà¤²à¤¾à¤à¤‚à¥¤",
            "narrative": profile_executive.get("summary") or payloads["executive_numerology_summary"]["narrative"],
        }
        executive_brief = {
            "summary": profile_executive.get("summary") or payloads["executive_numerology_summary"]["narrative"],
            "key_strength": profile_executive.get("key_strength") or primary_insight["strength"],
            "key_risk": profile_executive.get("key_risk") or primary_insight["critical_deficit"],
            "strategic_focus": profile_executive.get("strategic_focus")
            or (
                payloads["remedies_lifestyle_adjustments"]["cards"][3]["value"]
                if payloads["remedies_lifestyle_adjustments"]["cards"]
                else intervention_focus
            ),
        }
        strategic_guidance = {
            "short_term": profile_executive.get("short_term") or "Mulank-Bhagyank understanding à¤•à¥‡ à¤¸à¤¾à¤¥ daily correction à¤¶à¥à¤°à¥‚ à¤•à¤°à¥‡à¤‚à¥¤",
            "mid_term": profile_executive.get("mid_term") or "Missing numbers à¤”à¤° repeating traits à¤ªà¤° structured balancing à¤•à¤°à¥‡à¤‚à¥¤",
            "long_term": profile_executive.get("long_term") or "Personal year timing à¤•à¥‡ à¤¸à¤¾à¤¥ numerology-aligned decisions à¤²à¥‡à¤‚à¥¤",
        }
        growth_blueprint = {
            "phase_1": f"Week 1: core numbers observation + {weakest_metric.lower()} tracker + daily logà¥¤",
            "phase_2": f"Week 2: missing number correction + concern '{_safe_text(current_problem, 'current challenge')}' action loopà¥¤",
            "phase_3": f"Week 3: mobile/email alignment + personal year {personal_year} timing review + follow-through proofà¥¤",
        }

    business_block = {"business_strength": business_strength, "risk_factor": business_risk, "compatible_industries": business_industries}
    compatibility_block = {"compatible_numbers": [value for value in [life_path, destiny, expression] if value], "challenging_numbers": loshu_missing[:3], "relationship_guidance": compatibility_summary}

    return {
        "primary_insight": primary_insight,
        "metric_explanations": metric_explanations,
        "metrics_spine": {"primary_strength": strongest_metric, "primary_deficit": weakest_metric, "structural_cause": structural_cause, "intervention_focus": intervention_focus, "risk_band": risk_band},
        "numerology_architecture": {"foundation": life_path, "left_pillar": destiny, "right_pillar": expression, "facade": name_number, "narrative": payloads["numerology_architecture"]["narrative"]},
        "archetype_intelligence": {"signature": payloads["archetype_intelligence"]["narrative"], "leadership_traits": name_trait["strength"], "shadow_traits": name_trait["risk"], "growth_path": name_trait["protocol"]},
        "loshu_diagnostic": {"present_numbers": loshu_present, "missing_numbers": loshu_missing, "center_presence": 5 in loshu_present, "energy_imbalance": f"Present {len(loshu_present)} à¤¬à¤¨à¤¾à¤® missing {len(loshu_missing)}.", "missing_number_meanings": [f"Missing {number}: conscious correction protocol à¤¬à¤¨à¤¾à¤à¤‚à¥¤" for number in loshu_missing], "narrative": payloads["loshu_grid_intelligence"]["narrative"]},
        "planetary_mapping": {"background_forces": f"Life Path {life_path}, Destiny {destiny}, à¤”à¤° Name {name_number} à¤®à¤¿à¤²à¤•à¤° {dominant_planet} influence channel à¤¬à¤¨à¤¾à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤", "primary_intervention_planet": dominant_planet, "calibration_cluster": "discipline, timing, authority", "narrative": payloads["planetary_influence"]["narrative"]},
        "structural_deficit_model": {"deficit": f"Primary deficit: {weakest_metric}", "symptom": "Stress phase à¤®à¥‡à¤‚ execution inconsistency à¤”à¤° identity mismatch à¤¦à¤¿à¤–à¤¤à¤¾ à¤¹à¥ˆà¥¤", "patch": intervention_focus, "summary": "Deficit -> behavior risk -> protocol patch sequence à¤•à¥‹ strict order à¤®à¥‡à¤‚ à¤šà¤²à¤¾à¤à¤‚à¥¤"},
        "circadian_alignment": {"morning_routine": "10-minute sunlight, breath reset, à¤”à¤° strategic priority lock à¤•à¤°à¥‡à¤‚à¥¤", "work_alignment": "Communication noise à¤¸à¥‡ à¤ªà¤¹à¤²à¥‡ first deep-work block à¤ªà¥‚à¤°à¤¾ à¤•à¤°à¥‡à¤‚à¥¤", "evening_shutdown": "Decision freeze window, digital wind-down, à¤”à¤° short review à¤°à¤–à¥‡à¤‚à¥¤", "narrative": "Rhythm quality à¤¸à¥€à¤§à¥‡ decision quality à¤•à¥‹ drive à¤•à¤°à¤¤à¥€ à¤¹à¥ˆà¥¤"},
        "environment_alignment": {"physical_space": "Focus à¤”à¤° recovery à¤•à¥‡ à¤²à¤¿à¤ low-clutter workspace zones à¤¬à¤¨à¤¾à¤à¤‚à¥¤", "color_alignment": "Workspace à¤”à¤° digital surfaces à¤ªà¤° grounded color palette à¤°à¤–à¥‡à¤‚à¥¤", "mobile_number_analysis": payloads["mobile_number_intelligence"]["narrative"], "digital_behavior": digital_protocol, "narrative": "Environment à¤•à¤¾ à¤•à¤¾à¤® friction à¤•à¤® à¤•à¤°à¤¨à¤¾ à¤”à¤° clarity protect à¤•à¤°à¤¨à¤¾ à¤¹à¥ˆà¥¤"},
        "vedic_remedy_protocol": {"focus": weakest_metric, "code": vedic_code, "parameter": vedic_parameter, "output": vedic_output, "purpose": "Disciplined intention à¤¸à¥‡ deficit metric à¤•à¥‹ stabilize à¤•à¤°à¤¨à¤¾à¥¤", "planetary_alignment": dominant_planet, "pronunciation": vedic_code},
        "execution_plan": {"install_rhythm": growth_blueprint["phase_1"], "deploy_anchor": growth_blueprint["phase_2"], "run_protocol": growth_blueprint["phase_3"], "checkpoints": ["Week 1: rhythm à¤”à¤° metric baseline lock à¤•à¤°à¥‡à¤‚à¥¤", "Week 2: identity corrections deploy à¤•à¤°à¤•à¥‡ behavior delta compare à¤•à¤°à¥‡à¤‚à¥¤", "Week 3: timing windows validate à¤•à¤°à¤•à¥‡ decision quality scale à¤•à¤°à¥‡à¤‚à¥¤"], "summary": "21-day execution à¤ªà¤¹à¤²à¥‡ stability à¤¬à¤¨à¤¾à¤¤à¤¾ à¤¹à¥ˆ, à¤«à¤¿à¤° strategic expansion à¤•à¥‹ support à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆà¥¤"},
        "executive_brief": executive_brief,
        "analysis_sections": analysis_sections,
        "strategic_guidance": strategic_guidance,
        "growth_blueprint": growth_blueprint,
        "business_block": business_block,
        "compatibility_block": compatibility_block,
        "personal_year_forecast": {"current_personal_year": personal_year, "theme": "à¤µà¤°à¥à¤¤à¤®à¤¾à¤¨ à¤µà¤°à¥à¤· à¤®à¥‡à¤‚ structure consolidation à¤”à¤° correction adoption à¤ªà¤° à¤«à¥‹à¤•à¤¸ à¤°à¤–à¥‡à¤‚à¥¤", "opportunities": "Aligned launches, cleaner partnerships, à¤”à¤° stronger authority signal.", "caution_areas": "High-noise windows à¤®à¥‡à¤‚ reactive decisions à¤¸à¥‡ à¤¬à¤šà¥‡à¤‚à¥¤", "favorable_dates": lucky_dates},
        "executive_numerology_summary": payloads.get("executive_numerology_summary"),
        "core_numbers_analysis": payloads.get("core_numbers_analysis"),
        "mulank_description": payloads.get("mulank_description"),
        "bhagyank_description": payloads.get("bhagyank_description"),
        "number_interaction_analysis": payloads.get("number_interaction_analysis"),
        "loshu_grid_interpretation": payloads.get("loshu_grid_interpretation"),
        "missing_numbers_analysis": payloads.get("missing_numbers_analysis"),
        "repeating_numbers_impact": payloads.get("repeating_numbers_impact"),
        "mobile_number_numerology": payloads.get("mobile_number_numerology"),
        "mobile_life_number_compatibility": payloads.get("mobile_life_number_compatibility"),
        "email_numerology": payloads.get("email_numerology"),
        "numerology_personality_profile": payloads.get("numerology_personality_profile"),
        "current_life_phase_insight": payloads.get("current_life_phase_insight"),
        "career_financial_tendencies": payloads.get("career_financial_tendencies"),
        "relationship_compatibility_patterns": payloads.get("relationship_compatibility_patterns"),
        "health_tendencies_from_numbers": payloads.get("health_tendencies_from_numbers"),
        "color_alignment": payloads.get("color_alignment"),
        "remedies_lifestyle_adjustments": payloads.get("remedies_lifestyle_adjustments"),
        "closing_numerology_guidance": payloads.get("closing_numerology_guidance"),
        "name_vibration_optimization": payloads["name_vibration_optimization"],
        "mobile_number_intelligence": payloads["mobile_number_intelligence"],
        "email_identity_intelligence": payloads["email_identity_intelligence"],
        "signature_intelligence": payloads.get("signature_intelligence"),
        "business_name_intelligence": payloads.get("business_name_intelligence"),
        "brand_handle_optimization": payloads.get("brand_handle_optimization"),
        "residence_energy_intelligence": payloads.get("residence_energy_intelligence"),
        "vehicle_number_intelligence": payloads.get("vehicle_number_intelligence"),
        "correction_protocol_summary": payloads["correction_protocol_summary"],
        "karmic_pattern_intelligence": payloads["karmic_pattern_intelligence"],
        "hidden_talent_intelligence": payloads["hidden_talent_intelligence"],
        "pinnacle_challenge_cycle_intelligence": payloads["pinnacle_challenge_cycle_intelligence"],
        "life_cycle_timeline": payloads["life_cycle_timeline"],
        "strategic_timing_intelligence": payloads.get("strategic_timing_intelligence"),
        "wealth_energy_blueprint": payloads.get("wealth_energy_blueprint"),
        "leadership_intelligence": payloads.get("leadership_intelligence"),
        "decision_intelligence": payloads.get("decision_intelligence"),
        "emotional_intelligence": payloads.get("emotional_intelligence"),
        "digital_discipline": payloads.get("digital_discipline"),
        "lifestyle_alignment": payloads.get("lifestyle_alignment"),
        "vedic_remedy": payloads.get("vedic_remedy"),
        "closing_synthesis": payloads["closing_synthesis"],
        "section_payloads": payloads,
        "meta_notes": {"dominant_planet": dominant_planet, "strongest_metric": strongest_metric, "strongest_metric_score": strongest_score, "weakest_metric": weakest_metric, "weakest_metric_score": weakest_score, "focus": _safe_text(focus.get("life_focus"), "general_alignment"), "city": city, "career_industry": career_industry, "risk_band": risk_band, "social_handle": social_handle, "domain_handle": domain_handle, "residence_number": residence_number, "vehicle_number": vehicle_number},
    }


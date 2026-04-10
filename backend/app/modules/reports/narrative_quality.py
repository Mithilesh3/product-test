from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List

from app.modules.reports.problem_policy_config import merge_token_list, merge_token_map

PROBLEM_CRITICAL_SECTIONS = {"focus_snapshot", "remedy", "closing_summary"}
FINANCE_DRIFT_TOKENS = (
    "debt",
    "loan",
    "emi",
    "credit",
    "cashflow",
    "कर्ज",
    "ऋण",
)
PROBLEM_ANCHOR_TOKENS = {
    "finance": ["finance", "money", "cashflow", "debt", "loan", "वित्त", "धन", "कर्ज"],
    "career": ["career", "job", "work", "execution", "promotion", "करियर", "नौकरी", "काम"],
    "business": ["business", "revenue", "sales", "client", "व्यवसाय", "राजस्व"],
    "confidence": ["confidence", "hesitation", "visibility", "self", "आत्मविश्वास", "हिचक"],
    "consistency": ["consistency", "routine", "discipline", "focus", "निरंतरता", "अनुशासन"],
    "relationship": ["relationship", "partner", "marriage", "संबंध", "रिश्ता"],
    "health": ["health", "stress", "sleep", "स्वास्थ्य", "तनाव"],
    "education": ["study", "exam", "learning", "education", "पढ़ाई", "परीक्षा", "शिक्षा"],
    "general": ["challenge", "problem", "execution", "चुनौती", "समस्या", "क्रियान्वयन"],
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _section_text(section: Dict[str, Any]) -> str:
    parts = [
        _clean_text(section.get("summary")),
        _clean_text(section.get("keyStrength")),
        _clean_text(section.get("keyRisk")),
        _clean_text(section.get("practicalGuidance")),
    ]
    return " ".join(part for part in parts if part)


def _normalized_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, _normalized_text(left), _normalized_text(right)).ratio()


def evaluate_narrative_quality(*, sections: List[Dict[str, Any]], ai_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not sections:
        return {
            "sectionsEvaluated": 0,
            "personalizationScore": 0,
            "avgSectionSimilarity": 0.0,
            "weakSectionKeys": [],
            "rewriteRecommended": False,
            "qualityTier": "fallback",
            "sectionScores": {},
        }

    constraints = ai_payload.get("narrativeConstraints") or {}
    personalization = constraints.get("personalization") if isinstance(constraints, dict) else {}
    personalization_tokens = []
    if isinstance(personalization, dict):
        raw_tokens = personalization.get("mustUseTokens") or []
        if isinstance(raw_tokens, list):
            personalization_tokens = [_clean_text(token).lower() for token in raw_tokens if _clean_text(token)]

    section_scores: Dict[str, Dict[str, Any]] = {}
    personalization_hits = 0
    comparisons = 0
    similarity_total = 0.0

    section_texts: Dict[str, str] = {}
    for section in sections:
        key = _clean_text(section.get("sectionKey")) or "unknown_section"
        text = _section_text(section)
        section_texts[key] = text

    keys = list(section_texts.keys())
    max_similarity_by_key = {key: 0.0 for key in keys}
    for index, left_key in enumerate(keys):
        for right_key in keys[index + 1 :]:
            score = _similarity(section_texts[left_key], section_texts[right_key])
            max_similarity_by_key[left_key] = max(max_similarity_by_key[left_key], score)
            max_similarity_by_key[right_key] = max(max_similarity_by_key[right_key], score)
            similarity_total += score
            comparisons += 1

    weak_keys: List[str] = []
    for key in keys:
        text = section_texts[key]
        lowered = text.lower()
        token_hit = any(token in lowered for token in personalization_tokens) if personalization_tokens else False
        if token_hit:
            personalization_hits += 1

        word_count = len([part for part in text.split(" ") if part.strip()])
        max_similarity = max_similarity_by_key.get(key, 0.0)
        too_short = word_count < 36
        too_similar = max_similarity >= 0.9
        weak = bool(too_short or too_similar)
        if weak:
            weak_keys.append(key)

        section_scores[key] = {
            "wordCount": word_count,
            "maxSimilarity": round(max_similarity, 3),
            "hasPersonalizationToken": token_hit,
            "weak": weak,
        }

    personalization_score = int(round((personalization_hits / len(keys)) * 100)) if keys else 0
    avg_similarity = (similarity_total / comparisons) if comparisons > 0 else 0.0
    rewrite_recommended = bool(weak_keys) or avg_similarity >= 0.82
    quality_tier = "strong"
    if rewrite_recommended:
        quality_tier = "needs_rewrite"
    elif personalization_score < 40:
        quality_tier = "acceptable"

    return {
        "sectionsEvaluated": len(keys),
        "personalizationScore": personalization_score,
        "avgSectionSimilarity": round(avg_similarity, 3),
        "weakSectionKeys": weak_keys,
        "rewriteRecommended": rewrite_recommended,
        "qualityTier": quality_tier,
        "sectionScores": section_scores,
    }


def _section_index(sections: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for section in sections:
        key = _clean_text(section.get("sectionKey"))
        if key:
            indexed[key] = section
    return indexed


def _basic_expected_tokens(ai_payload: Dict[str, Any]) -> Dict[str, List[str]]:
    core = ai_payload.get("deterministicBasicCore") if isinstance(ai_payload, dict) else {}
    if not isinstance(core, dict):
        return {}

    inputs = core.get("inputs") if isinstance(core.get("inputs"), dict) else {}
    mobile = core.get("mobile") if isinstance(core.get("mobile"), dict) else {}
    life_path = core.get("life_path") if isinstance(core.get("life_path"), dict) else {}
    lo_shu = core.get("lo_shu") if isinstance(core.get("lo_shu"), dict) else {}
    compatibility = core.get("compatibility") if isinstance(core.get("compatibility"), dict) else {}
    missing_digits = lo_shu.get("missing") if isinstance(lo_shu.get("missing"), list) else []

    missing_joined = ", ".join(str(d) for d in missing_digits[:4]) if missing_digits else ""
    challenge = _clean_text(inputs.get("primary_challenge"))
    mobile_vibration = str(mobile.get("vibration") or "")
    life_path_value = str(life_path.get("value") or "")
    compatibility_en = _clean_text(compatibility.get("english"))
    compatibility_hi = _clean_text(compatibility.get("text"))

    return {
        "mobile_numerology": [mobile_vibration, challenge],
        "lo_shu_grid": [missing_joined] if missing_joined else [],
        "mobile_life_compatibility": [
            life_path_value,
            mobile_vibration,
            compatibility_en,
            compatibility_hi,
        ],
        "remedy": [challenge],
        "closing_summary": [challenge, compatibility_en],
    }


def evaluate_deterministic_alignment(*, sections: List[Dict[str, Any]], ai_payload: Dict[str, Any]) -> Dict[str, Any]:
    expected = _basic_expected_tokens(ai_payload)
    if not sections or not expected:
        return {
            "sectionsEvaluated": len(sections),
            "deterministicCoverage": 100 if sections else 0,
            "weakSectionKeys": [],
            "rewriteRecommended": False,
            "sectionScores": {},
        }

    indexed = _section_index(sections)
    weak_keys: List[str] = []
    section_scores: Dict[str, Dict[str, Any]] = {}
    covered = 0
    total = 0

    for key, tokens in expected.items():
        if not tokens:
            continue
        section = indexed.get(key)
        if not section:
            continue

        text = _section_text(section).lower()
        token_hits = 0
        token_total = 0
        for token in tokens:
            normalized = _clean_text(token).lower()
            if not normalized:
                continue
            token_total += 1
            if normalized in text:
                token_hits += 1

        if token_total == 0:
            continue

        coverage = token_hits / token_total
        total += token_total
        covered += token_hits
        weak = coverage < 0.6
        if weak:
            weak_keys.append(key)

        section_scores[key] = {
            "tokenCoverage": round(coverage, 3),
            "tokenHits": token_hits,
            "tokenTotal": token_total,
            "weak": weak,
        }

    deterministic = ai_payload.get("deterministic") if isinstance(ai_payload, dict) else {}
    if isinstance(deterministic, dict):
        problem_profile = deterministic.get("problemProfile") if isinstance(deterministic.get("problemProfile"), dict) else {}
        category = _clean_text(problem_profile.get("category")).lower() or "general"
        normalized_input = deterministic.get("normalizedInput") if isinstance(deterministic.get("normalizedInput"), dict) else {}
        challenge = _clean_text(normalized_input.get("currentProblem") or normalized_input.get("focusArea")).lower()
        anchor_tokens_by_category = merge_token_map(
            defaults=PROBLEM_ANCHOR_TOKENS,
            config_key="problemCategoryAnchors",
        )
        anchors = [
            token.lower()
            for token in anchor_tokens_by_category.get(category, anchor_tokens_by_category["general"])
        ]
        finance_drift_tokens = merge_token_list(
            defaults=list(FINANCE_DRIFT_TOKENS),
            config_key="financeDriftTokens",
        )

        for section_key in PROBLEM_CRITICAL_SECTIONS:
            section = indexed.get(section_key)
            if not section:
                continue
            text = _section_text(section).lower()
            anchor_hit = bool(challenge and challenge in text) or any(token in text for token in anchors)
            finance_hits = sum(1 for token in finance_drift_tokens if token in text)
            drift = category != "finance" and finance_hits >= 2
            weak = bool((not anchor_hit) or drift)

            total += 1
            if not weak:
                covered += 1

            prev = section_scores.get(section_key) or {}
            section_scores[section_key] = {
                **prev,
                "problemAnchorHit": anchor_hit,
                "financeDriftDetected": drift,
                "problemWeak": weak,
                "weak": bool(prev.get("weak") or weak),
            }
            if weak and section_key not in weak_keys:
                weak_keys.append(section_key)

    deterministic_coverage = int(round((covered / total) * 100)) if total else 100
    rewrite_recommended = bool(weak_keys)

    return {
        "sectionsEvaluated": len(section_scores),
        "deterministicCoverage": deterministic_coverage,
        "weakSectionKeys": weak_keys,
        "rewriteRecommended": rewrite_recommended,
        "sectionScores": section_scores,
    }

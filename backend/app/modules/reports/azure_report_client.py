from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.llm_config import DEPLOYMENT_NAME, azure_client, build_token_param
from app.modules.reports.narrative_quality import (
    evaluate_deterministic_alignment,
    evaluate_narrative_quality,
)
from app.modules.reports.problem_policy_config import merge_token_list, merge_token_map
from app.modules.reports.prompts.developer_prompt import DEVELOPER_PROMPT
from app.modules.reports.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

REQUIRED_SECTION_KEYS = [
    "sectionKey",
    "summary",
    "keyStrength",
    "keyRisk",
    "practicalGuidance",
]

PROBLEM_CRITICAL_SECTIONS = {
    "focus_snapshot",
    "remedy",
    "closing_summary",
}

FINANCE_DRIFT_TOKENS = (
    "debt",
    "loan",
    "emi",
    "credit",
    "cashflow",
    "kard",
    "कर्ज",
    "ऋण",
)

PROBLEM_CATEGORY_ANCHORS = {
    "finance": ["finance", "money", "cashflow", "debt", "loan", "वित्त", "धन", "कर्ज"],
    "career": ["career", "job", "work", "execution", "promotion", "करियर", "नौकरी", "काम"],
    "business": ["business", "revenue", "sales", "client", "व्यवसाय", "बिक्री", "राजस्व"],
    "confidence": ["confidence", "hesitation", "visibility", "self", "आत्मविश्वास", "हिचक", "अभिव्यक्ति"],
    "consistency": ["consistency", "routine", "discipline", "focus", "निरंतरता", "अनुशासन", "दिनचर्या"],
    "relationship": ["relationship", "partner", "marriage", "रिश्ता", "संबंध", "विवाह"],
    "health": ["health", "stress", "sleep", "anxiety", "स्वास्थ्य", "तनाव", "नींद"],
    "education": ["study", "exam", "learning", "education", "पढ़ाई", "परीक्षा", "शिक्षा"],
}

PROBLEM_GUIDANCE_BY_CATEGORY = {
    "finance": "21 दिनों तक cash discipline, weekly budget review, और debt/cashflow tracking को बिना skip चलाएँ।",
    "career": "21 दिनों तक top-3 execution priorities, deep-work blocks, और weekly outcome review को strict रखें।",
    "business": "21 दिनों तक revenue-quality tracking, sales follow-up discipline, और weekly decision review लागू रखें।",
    "confidence": "21 दिनों तक daily visibility action, pre-decision script, और reflection journal का पालन करें।",
    "consistency": "21 दिनों तक same-start-time routine, no-skip tracker, और Sunday reset review लागू करें।",
    "relationship": "21 दिनों तक communication cadence, calm-response rule, और weekly relationship check-in रखें।",
    "health": "21 दिनों तक stress-regulation routine, sleep rhythm, और energy-check reviews को प्राथमिकता दें।",
    "education": "21 दिनों तक fixed study blocks, revision checkpoints, और measurable learning log चलाएँ।",
    "general": "21 दिनों तक एक ही मुख्य चुनौती पर measurable daily actions और weekly review cadence रखें।",
}


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    # Basic mojibake guard for UTF-8/Devanagari text.
    mojibake_tokens = ("à¤", "à¥", "Ã", "Â", "â€™", "â€“", "â€”")
    if not any(token in text for token in mojibake_tokens):
        return text

    def _score(candidate: str) -> Tuple[int, int]:
        devanagari = len(re.findall(r"[\u0900-\u097F]", candidate))
        mojibake_hits = sum(candidate.count(token) for token in mojibake_tokens)
        return devanagari, -mojibake_hits

    best = text
    best_score = _score(text)
    for source, target in (("latin1", "utf-8"), ("cp1252", "utf-8"), ("latin1", "cp1252")):
        try:
            repaired = text.encode(source, errors="ignore").decode(target, errors="ignore").strip()
        except Exception:
            continue
        if not repaired:
            continue
        repaired_score = _score(repaired)
        if repaired_score > best_score:
            best = repaired
            best_score = repaired_score
    return best


def _fallback_closing_insight(*, ai_payload: Dict[str, Any], attempt: int = 0) -> str:
    deterministic = ai_payload.get("deterministic") if isinstance(ai_payload, dict) else {}
    normalized_input = deterministic.get("normalizedInput") if isinstance(deterministic, dict) else {}
    challenge = _clean_text(
        (normalized_input or {}).get("currentProblem")
        or (normalized_input or {}).get("focusArea")
        or "consistency"
    )
    city = _clean_text((normalized_input or {}).get("city")) or "your city"
    fingerprint = _clean_text((deterministic or {}).get("uniquenessFingerprint"))
    seed = f"{fingerprint}|{challenge}|{city}|{attempt}"
    variants = [
        f"Apply your strongest energy through daily discipline; expect measurable movement in '{challenge}' over 21 days.",
        f"In {city}, your profile shows clear potential; stable execution rhythm will improve outcomes faster.",
        f"Focus now: 1) top 3 daily priorities 2) fixed communication windows 3) weekly review for '{challenge}'.",
        f"Your profile has momentum capacity; small but consistent actions will compound on '{challenge}'.",
    ]
    if not seed:
        return variants[0]
    return variants[sum(ord(ch) for ch in seed) % len(variants)]


def _extract_nearest_json_block(text: str) -> str:
    payload = _clean_text(text)
    if not payload:
        return ""

    object_pos = payload.find("{")
    array_pos = payload.find("[")
    starts = [pos for pos in (object_pos, array_pos) if pos >= 0]
    if not starts:
        return payload

    start = min(starts)
    opening = payload[start]
    closing = "}" if opening == "{" else "]"
    stack = [closing]
    in_string = False
    escaped = False

    for index in range(start + 1, len(payload)):
        char = payload[index]
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            stack.append("}")
            continue
        if char == "[":
            stack.append("]")
            continue
        if char in {"}", "]"}:
            if not stack or char != stack[-1]:
                continue
            stack.pop()
            if not stack:
                return payload[start : index + 1]

    return payload[start:]


def _normalize_json_text(raw_text: str) -> Tuple[str, bool]:
    original = _clean_text(raw_text)
    if not original:
        return "", False

    cleaned = original
    cleaned = re.sub(r"^\s*```(?:json)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = _extract_nearest_json_block(cleaned)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    cleaned = cleaned.strip()
    return cleaned, cleaned != original


def _parse_json_response(raw_text: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    text = _clean_text(raw_text)
    if not text:
        return None, False

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, False
        if isinstance(parsed, list):
            return {"sections": parsed}, False
    except Exception:
        pass

    cleaned, repaired = _normalize_json_text(text)
    if not cleaned:
        return None, repaired

    try:
        parsed = json.loads(cleaned)
    except Exception:
        return None, repaired

    if isinstance(parsed, dict):
        return parsed, repaired
    if isinstance(parsed, list):
        return {"sections": parsed}, repaired
    return None, repaired


def _normalize_score_highlights(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    highlights: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = _clean_text(item.get("label"))
        raw_value = item.get("value")
        if not label or raw_value in (None, ""):
            continue
        highlights.append({"label": label, "value": str(raw_value)})
    return highlights


def _normalize_loaded_energies(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(item) for item in value if _clean_text(item)]


def _normalize_section(section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(section, dict):
        return None

    section_key = _clean_text(section.get("sectionKey"))
    if not section_key:
        return None

    if bool(section.get("omitSection")):
        reason = _clean_text(section.get("reason"))
        if not reason:
            return None
        return {
            "sectionKey": section_key,
            "omitSection": True,
            "reason": reason,
        }

    if any(key not in section for key in REQUIRED_SECTION_KEYS):
        return None

    summary = _clean_text(section.get("summary"))
    key_strength = _clean_text(section.get("keyStrength"))
    key_risk = _clean_text(section.get("keyRisk"))
    practical_guidance = _clean_text(section.get("practicalGuidance"))

    if not all((summary, key_strength, key_risk, practical_guidance)):
        return None

    normalized: Dict[str, Any] = {
        "sectionKey": section_key,
        "summary": summary,
        "keyStrength": key_strength,
        "keyRisk": key_risk,
        "practicalGuidance": practical_guidance,
    }

    loaded_energies = _normalize_loaded_energies(section.get("loadedEnergies"))
    if loaded_energies:
        normalized["loadedEnergies"] = loaded_energies

    score_highlights = _normalize_score_highlights(section.get("scoreHighlights"))
    if score_highlights:
        normalized["scoreHighlights"] = score_highlights

    return normalized


def _extract_sections(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_sections = parsed.get("sections")
    if not isinstance(raw_sections, list):
        return []

    normalized_sections: List[Dict[str, Any]] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        normalized = _normalize_section(raw_section)
        if normalized:
            normalized_sections.append(normalized)
    return normalized_sections


def _problem_context(ai_payload: Dict[str, Any]) -> Tuple[str, str]:
    deterministic = ai_payload.get("deterministic") if isinstance(ai_payload, dict) else {}
    if not isinstance(deterministic, dict):
        return "general", ""
    problem_profile = deterministic.get("problemProfile") if isinstance(deterministic.get("problemProfile"), dict) else {}
    category = _clean_text(problem_profile.get("category")).lower() or "general"
    normalized_input = deterministic.get("normalizedInput") if isinstance(deterministic.get("normalizedInput"), dict) else {}
    challenge = _clean_text(normalized_input.get("currentProblem") or normalized_input.get("focusArea"))
    return category, challenge


def _section_problem_text(section: Dict[str, Any]) -> str:
    return " ".join(
        [
            _clean_text(section.get("summary")),
            _clean_text(section.get("keyStrength")),
            _clean_text(section.get("keyRisk")),
            _clean_text(section.get("practicalGuidance")),
        ]
    ).lower()


def _build_problem_first_section(
    *,
    section: Dict[str, Any],
    category: str,
    challenge: str,
    reason: str,
) -> Dict[str, Any]:
    focus_label_map = {
        "finance": "वित्तीय स्थिरता",
        "career": "करियर निष्पादन",
        "business": "व्यवसाय प्रगति",
        "confidence": "आत्मविश्वास और अभिव्यक्ति",
        "consistency": "निरंतरता और अनुशासन",
        "relationship": "संबंध संतुलन",
        "health": "स्वास्थ्य-लय",
        "education": "अध्ययन निष्पादन",
        "general": "मुख्य जीवन चुनौती",
    }
    challenge_text = challenge or "वर्तमान मुख्य समस्या"
    focus_label = focus_label_map.get(category, focus_label_map["general"])
    practical = PROBLEM_GUIDANCE_BY_CATEGORY.get(category, PROBLEM_GUIDANCE_BY_CATEGORY["general"])

    rewritten = dict(section)
    rewritten["summary"] = (
        f"यह अनुभाग '{challenge_text}' को ध्यान में रखकर {focus_label} सुधार पर केंद्रित है।"
    )
    rewritten["keyStrength"] = (
        f"आपकी deterministic profile में इस चुनौती के लिए सुधार क्षमता मौजूद है, इसलिए targeted execution से प्रगति तेज हो सकती है।"
    )
    rewritten["keyRisk"] = (
        f"यदि उपाय समस्या-विशिष्ट न रहें ({reason}), तो परिणाम सतही रहेंगे और पुराना पैटर्न लौट सकता है।"
    )
    rewritten["practicalGuidance"] = practical
    return rewritten


def _enforce_problem_first_consistency(
    *,
    sections: List[Dict[str, Any]],
    ai_payload: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], int]:
    if not sections:
        return sections, 0

    category, challenge = _problem_context(ai_payload)
    anchor_tokens_by_category = merge_token_map(
        defaults=PROBLEM_CATEGORY_ANCHORS,
        config_key="problemCategoryAnchors",
    )
    anchor_tokens = anchor_tokens_by_category.get(category, anchor_tokens_by_category.get("general", []))
    finance_drift_tokens = merge_token_list(
        defaults=list(FINANCE_DRIFT_TOKENS),
        config_key="financeDriftTokens",
    )
    challenge_lower = challenge.lower()

    rewrites = 0
    enforced: List[Dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        if bool(section.get("omitSection")):
            enforced.append(section)
            continue

        key = _clean_text(section.get("sectionKey"))
        if key not in PROBLEM_CRITICAL_SECTIONS:
            enforced.append(section)
            continue

        text = _section_problem_text(section)
        has_challenge_anchor = bool(challenge_lower and challenge_lower in text) or any(
            token.lower() in text for token in anchor_tokens
        )
        finance_hits = sum(1 for token in finance_drift_tokens if token in text)

        drift_reason = ""
        if category != "finance" and finance_hits >= 2:
            drift_reason = "finance drift on non-finance category"
        elif not has_challenge_anchor:
            drift_reason = "missing challenge/category anchoring"

        if not drift_reason:
            enforced.append(section)
            continue

        rewrites += 1
        enforced.append(
            _build_problem_first_section(
                section=section,
                category=category,
                challenge=challenge,
                reason=drift_reason,
            )
        )

    return enforced, rewrites


def _build_report_skeleton(
    *,
    ai_payload: Dict[str, Any],
    parsed: Optional[Dict[str, Any]] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    parsed = parsed or {}
    section_entries = sections or []

    profile_snapshot = parsed.get("profileSnapshot")
    if not isinstance(profile_snapshot, dict):
        profile_snapshot = ai_payload.get("profileSnapshot") or {}

    dashboard = parsed.get("dashboard")
    if not isinstance(dashboard, dict):
        dashboard = ai_payload.get("dashboard") or {}

    return {
        "reportTitle": _clean_text(parsed.get("reportTitle")) or "Premium Numerology Report",
        "plan": _clean_text(parsed.get("plan")) or _clean_text(ai_payload.get("plan")) or "BASIC",
        "profileSnapshot": profile_snapshot,
        "dashboard": dashboard,
        "sections": section_entries,
        "closingInsight": _clean_text(parsed.get("closingInsight"))
        or _fallback_closing_insight(ai_payload=ai_payload),
    }


def _call_azure_json(*, payload: Dict[str, Any], max_tokens: int, temperature: float = 0.2) -> str:
    user_payload = json.dumps(payload, ensure_ascii=False)
    request_kwargs = {
        "model": DEPLOYMENT_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "developer", "content": DEVELOPER_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        "temperature": temperature,
    }
    request_kwargs.update(build_token_param(max_tokens))
    timeout_seconds = float(getattr(settings, "AI_REPORT_AZURE_REQUEST_TIMEOUT_SECONDS", 0) or 0)
    if timeout_seconds > 0:
        request_kwargs["timeout"] = timeout_seconds
    try:
        response = azure_client.chat.completions.create(
            **request_kwargs,
            response_format={"type": "json_object"},
        )
    except TypeError:
        fallback_kwargs = dict(request_kwargs)
        try:
            response = azure_client.chat.completions.create(**fallback_kwargs)
        except TypeError:
            fallback_kwargs.pop("timeout", None)
            response = azure_client.chat.completions.create(**fallback_kwargs)
    return _clean_text((response.choices[0].message.content if response and response.choices else ""))


def _run_blueprint_pass(*, ai_payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    request = {
        "generationMode": "strategy_blueprint",
        "task": {
            "purpose": "Create deterministic-first section strategy before writing sections.",
            "output": {
                "narrativeStrategy": "string",
                "sectionPlans": [
                    {
                        "sectionKey": "string",
                        "angle": "string",
                        "mustUseFacts": ["string"],
                        "avoidThemes": ["string"],
                    }
                ],
            },
            "strict": [
                "Return JSON only",
                "Do not generate report sections in this pass unless legacy parser expects it",
            ],
        },
        "aiPayload": ai_payload,
    }
    raw_text = _call_azure_json(payload=request, max_tokens=1200, temperature=0.1)
    parsed, repaired = _parse_json_response(raw_text)
    if not parsed:
        return None, None, repaired

    if isinstance(parsed.get("sections"), list):
        return parsed, None, repaired

    strategy = parsed.get("strategyBlueprint") if isinstance(parsed.get("strategyBlueprint"), dict) else parsed
    if not isinstance(strategy, dict):
        strategy = {}
    return None, strategy, repaired


def _run_section_pass(*, ai_payload: Dict[str, Any], strategy_blueprint: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], bool]:
    request = {
        "generationMode": "section_generation",
        "task": {
            "purpose": "Generate final report sections with deterministic personalization.",
            "strict": [
                "Return final report JSON envelope only",
                "All enabled sections must follow schema or use omitSection mode",
                "Use sectionFactPacks and contradictionGuards",
            ],
        },
        "strategyBlueprint": strategy_blueprint,
        "aiPayload": ai_payload,
    }
    raw_text = _call_azure_json(payload=request, max_tokens=3000, temperature=0.2)
    return _parse_json_response(raw_text)


def _merge_targeted_rewrites(
    *,
    base_sections: List[Dict[str, Any]],
    rewrite_sections: List[Dict[str, Any]],
    target_keys: List[str],
) -> List[Dict[str, Any]]:
    target_set = set(target_keys)
    rewrite_index = {
        section.get("sectionKey"): section
        for section in rewrite_sections
        if isinstance(section, dict) and section.get("sectionKey") in target_set
    }
    merged: List[Dict[str, Any]] = []
    for section in base_sections:
        key = section.get("sectionKey")
        merged.append(rewrite_index.get(key, section))
    return merged


def _run_targeted_rewrite_pass(
    *,
    ai_payload: Dict[str, Any],
    strategy_blueprint: Dict[str, Any],
    sections: List[Dict[str, Any]],
    weak_section_keys: List[str],
    quality: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], bool]:
    if not weak_section_keys:
        return sections, False

    request = {
        "generationMode": "targeted_rewrite",
        "task": {
            "purpose": "Rewrite only weak sections while preserving deterministic facts.",
            "rewriteOnlySections": weak_section_keys,
            "strict": [
                "Return report envelope JSON only",
                "Preserve sectionKey values",
                "Do not rewrite sections not listed in rewriteOnlySections",
            ],
        },
        "strategyBlueprint": strategy_blueprint,
        "qualitySignals": quality,
        "currentSections": sections,
        "aiPayload": ai_payload,
    }

    raw_text = _call_azure_json(payload=request, max_tokens=2200, temperature=0.15)
    parsed, repaired = _parse_json_response(raw_text)
    if not parsed:
        return sections, repaired

    rewrite_candidates = _extract_sections(parsed)
    if not rewrite_candidates:
        return sections, repaired

    merged_sections = _merge_targeted_rewrites(
        base_sections=sections,
        rewrite_sections=rewrite_candidates,
        target_keys=weak_section_keys,
    )
    return merged_sections, repaired


def generate_report_with_azure(
    *,
    ai_payload: Dict[str, Any],
    max_retries: Optional[int] = None,
    enable_targeted_rewrite: Optional[bool] = None,
) -> Dict[str, Any]:
    requested_sections = len(ai_payload.get("enabledSections") or [])
    retries = max(0, int(settings.AI_REPORT_AZURE_MAX_RETRIES if max_retries is None else max_retries))
    rewrite_enabled = (
        bool(settings.AI_REPORT_AZURE_ENABLE_TARGETED_REWRITE)
        if enable_targeted_rewrite is None
        else bool(enable_targeted_rewrite)
    )

    attempt = 0
    while attempt <= retries:
        try:
            legacy_result, strategy_blueprint, repaired_blueprint = _run_blueprint_pass(ai_payload=ai_payload)
        except Exception as exc:
            logger.warning("Azure blueprint pass failed on attempt %s: %s", attempt + 1, exc)
            attempt += 1
            continue

        if legacy_result:
            valid_sections = _extract_sections(legacy_result)
            alignment = evaluate_deterministic_alignment(sections=valid_sections, ai_payload=ai_payload)
            valid_count = len([section for section in valid_sections if not bool(section.get("omitSection"))])
            repaired_count = valid_count if repaired_blueprint else 0
            fallback_sections = max(requested_sections - valid_count, 0)
            full_fallback = valid_count == 0
            logger.info(
                "azure_narrative_parse_result",
                extra={
                    "requested_sections": requested_sections,
                    "valid_ai_sections": valid_count,
                    "repaired_ai_sections": repaired_count,
                    "fallback_sections": fallback_sections,
                    "full_fallback": full_fallback,
                    "generation_mode": "legacy_single_pass",
                },
            )
            result = _build_report_skeleton(
                ai_payload=ai_payload,
                parsed=legacy_result,
                sections=valid_sections,
            )
            narrative_quality = evaluate_narrative_quality(sections=valid_sections, ai_payload=ai_payload)
            narrative_quality["deterministicAlignment"] = alignment
            result["narrativeQuality"] = narrative_quality
            result["strategyBlueprint"] = {}
            result["generationTrace"] = {
                "attempt": attempt + 1,
                "mode": "legacy_single_pass",
                "rewriteTriggered": False,
            }
            return result

        try:
            parsed, repaired_sections = _run_section_pass(
                ai_payload=ai_payload,
                strategy_blueprint=strategy_blueprint or {},
            )
        except Exception as exc:
            logger.warning("Azure section pass failed on attempt %s: %s", attempt + 1, exc)
            attempt += 1
            continue

        if not parsed:
            logger.warning("Azure section pass parse failed on attempt %s", attempt + 1)
            attempt += 1
            continue

        valid_sections = _extract_sections(parsed)
        valid_sections, problem_rewrite_count = _enforce_problem_first_consistency(
            sections=valid_sections,
            ai_payload=ai_payload,
        )
        quality = evaluate_narrative_quality(sections=valid_sections, ai_payload=ai_payload)
        alignment = evaluate_deterministic_alignment(sections=valid_sections, ai_payload=ai_payload)
        rewrite_triggered = False
        repaired_rewrite = False
        quality_weak_keys = quality.get("weakSectionKeys") if isinstance(quality.get("weakSectionKeys"), list) else []
        alignment_weak_keys = (
            alignment.get("weakSectionKeys") if isinstance(alignment.get("weakSectionKeys"), list) else []
        )
        weak_keys = sorted(set(quality_weak_keys + alignment_weak_keys))
        rewrite_recommended = bool(quality.get("rewriteRecommended") or alignment.get("rewriteRecommended"))

        if rewrite_enabled and valid_sections and rewrite_recommended and weak_keys:
            rewrite_triggered = True
            try:
                rewritten_sections, repaired_rewrite = _run_targeted_rewrite_pass(
                    ai_payload=ai_payload,
                    strategy_blueprint=strategy_blueprint or {},
                    sections=valid_sections,
                    weak_section_keys=weak_keys,
                    quality=quality,
                )
                valid_sections = rewritten_sections
                valid_sections, post_rewrite_problem_count = _enforce_problem_first_consistency(
                    sections=valid_sections,
                    ai_payload=ai_payload,
                )
                problem_rewrite_count += post_rewrite_problem_count
                quality = evaluate_narrative_quality(sections=valid_sections, ai_payload=ai_payload)
                alignment = evaluate_deterministic_alignment(sections=valid_sections, ai_payload=ai_payload)
            except Exception as exc:
                logger.warning("Azure rewrite pass failed on attempt %s: %s", attempt + 1, exc)

        valid_count = len([section for section in valid_sections if not bool(section.get("omitSection"))])
        repaired_count = valid_count if (repaired_blueprint or repaired_sections or repaired_rewrite) else 0
        fallback_sections = max(requested_sections - valid_count, 0)
        full_fallback = valid_count == 0

        logger.info(
            "azure_narrative_parse_result",
            extra={
                "requested_sections": requested_sections,
                "valid_ai_sections": valid_count,
                "repaired_ai_sections": repaired_count,
                "fallback_sections": fallback_sections,
                "full_fallback": full_fallback,
                "generation_mode": "multi_pass",
                "rewrite_triggered": rewrite_triggered,
                "problem_consistency_rewrites": problem_rewrite_count,
                "quality_tier": quality.get("qualityTier"),
                "avg_section_similarity": quality.get("avgSectionSimilarity"),
                "personalization_score": quality.get("personalizationScore"),
                "deterministic_coverage": alignment.get("deterministicCoverage"),
            },
        )

        result = _build_report_skeleton(
            ai_payload=ai_payload,
            parsed=parsed,
            sections=valid_sections,
        )
        quality["deterministicAlignment"] = alignment
        result["narrativeQuality"] = quality
        result["strategyBlueprint"] = strategy_blueprint or {}
        result["generationTrace"] = {
            "attempt": attempt + 1,
            "mode": "multi_pass",
            "rewriteTriggered": rewrite_triggered,
            "problemConsistencyRewrites": problem_rewrite_count,
        }
        return result

    logger.warning(
        "azure_narrative_parse_result",
        extra={
            "requested_sections": requested_sections,
            "valid_ai_sections": 0,
            "repaired_ai_sections": 0,
            "fallback_sections": requested_sections,
            "full_fallback": True,
            "generation_mode": "failed",
        },
    )
    result = _build_report_skeleton(ai_payload=ai_payload, sections=[])
    result["narrativeQuality"] = evaluate_narrative_quality(sections=[], ai_payload=ai_payload)
    result["strategyBlueprint"] = {}
    result["generationTrace"] = {
        "attempt": attempt,
        "mode": "failed",
        "rewriteTriggered": False,
    }
    return result

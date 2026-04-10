from typing import Dict, Any, Optional, Tuple
from app.core.llm_config import azure_client, DEPLOYMENT_NAME, build_token_param
import json
import logging
import re

logger = logging.getLogger(__name__)

PLAN_TOKEN_BASE = {
    "basic": 1600,
    "pro": 2200,
    "premium": 3000,
    "enterprise": 3800,
}

_REQUIRED_EXECUTIVE_FIELDS = ("summary", "key_strength", "key_risk", "strategic_focus")
_REQUIRED_ANALYSIS_FIELDS = (
    "career_analysis",
    "decision_profile",
    "emotional_analysis",
    "financial_analysis",
)


def _normalize_json_text(raw_text: str) -> str:
    cleaned = str(raw_text or "").strip()
    if not cleaned:
        return ""

    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    object_match = re.search(r"\{[\s\S]*\}", cleaned)
    if object_match:
        cleaned = object_match.group(0).strip()

    # Remove trailing commas in objects/arrays.
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _safe_json_parse(raw_text: str) -> Tuple[Dict[str, Any], bool]:
    if not raw_text:
        return {}, False

    try:
        return json.loads(raw_text), False
    except Exception:
        pass

    cleaned = _normalize_json_text(raw_text)
    if not cleaned:
        return {}, False

    try:
        return json.loads(cleaned), True
    except Exception:
        logger.error("AI JSON parsing failed after repair attempt")
        return {}, False


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_payload_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    executive = payload.get("executive_brief")
    analysis = payload.get("analysis_sections")

    if not isinstance(executive, dict) or not isinstance(analysis, dict):
        return {}

    if not all(_is_non_empty_text(executive.get(field)) for field in _REQUIRED_EXECUTIVE_FIELDS):
        return {}

    if not all(_is_non_empty_text(analysis.get(field)) for field in _REQUIRED_ANALYSIS_FIELDS):
        return {}

    return payload


def generate_ai_narrative(
    numerology_core: Dict[str, Any],
    scores: Dict[str, Any],
    current_problem: str,
    plan_name: str,
    token_multiplier: float = 1.0,
    intake_context: Optional[Dict[str, Any]] = None,
    interpretation_draft: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    plan_name = (plan_name or "basic").lower()
    intake_context = intake_context or {}
    interpretation_draft = interpretation_draft or {}
    preferences = intake_context.get("preferences") or {}
    language_preference = str(preferences.get("language_preference") or "hindi").lower()

    is_basic = plan_name == "basic"
    base_tokens = PLAN_TOKEN_BASE.get(plan_name, 1600)
    max_tokens = int(base_tokens * token_multiplier)
    business_signals = numerology_core.get("business_analysis", {})
    numerology_json = json.dumps(numerology_core, ensure_ascii=False)
    scores_json = json.dumps(scores, ensure_ascii=False)
    intake_json = json.dumps(intake_context, ensure_ascii=False)
    draft_json = json.dumps(interpretation_draft, ensure_ascii=False)
    basic_plan_guardrails = ""
    if is_basic:
        basic_plan_guardrails = """
BASIC PLAN CONTENT MODE (STRICT):
- Keep narration numerology-first: Mulank, Bhagyank, Name Number, Lo Shu, Personal Year, Mobile, Email.
- Avoid enterprise consulting language, business intelligence jargon, strategic blueprint framing, and intervention-heavy wording.
- Keep copy simple, premium, and correction-led.
- Use short paragraphs and deterministic interpretation only.
- Do not use words like "enterprise", "consulting framework", "operating system", "strategic execution", or "blueprint" in BASIC output.
"""

    assistant_role = (
        "You are a senior numerology report editor focused on deterministic, correction-led narration."
        if is_basic
        else "You are an elite numerology strategist and behavioral intelligence advisor."
    )
    report_task = (
        "Your task is to refine an already-generated deterministic interpretation into a polished BASIC numerology report."
        if is_basic
        else "Your task is to refine an already-generated deterministic interpretation into a natural strategic life intelligence report."
    )
    english_terms = (
        "career, business, growth, leadership"
        if is_basic
        else "career, business, strategy, growth, leadership, execution"
    )
    tier_tone_line = (
        "The wording should read like a premium North Indian numerology report with quick insight and practical correction."
        if is_basic
        else "The wording should read like a premium North Indian life-intelligence report."
    )

    prompt = f"""
{assistant_role}

Do NOT calculate numerology numbers.
All numerology calculations are already provided.
{report_task}

Writing style requirements:
- The report body must be written in Hindi only using Devanagari script.
- Keep English usage minimal and only for numerology or modern terms with no clean Hindi replacement ({english_terms}).
- Never use Roman Hindi.
- Sound psychologically insightful, practical, and premium.
- Avoid generic astrology statements and avoid mystical exaggeration.
- Make the report feel clearly different for each user by grounding every section in the user's name, numerology values, strongest or weakest scores, and stated life focus.
- Avoid sentence-level repetition across users; vary phrasing using the actual number combinations and profile signals.
- If data is missing, acknowledge the gap instead of inventing facts.
- If confidence_score is low or behavioral inputs are sparse, explicitly say that some intelligence metrics are based on limited inputs.
- Never leave blanks, placeholders, token fragments, empty commas, or partially stitched grammar.
- Do not output templated filler. Every paragraph must mention concrete deterministic signals such as life path, missing numbers, metric behavior, mobile vibration, or dominant planet.

--------------------------------------------------

USER CURRENT PROBLEM
{current_problem}

--------------------------------------------------

USER PROFILE INPUT
{intake_json}

--------------------------------------------------

NUMEROLOGY CORE DATA
{numerology_json}

--------------------------------------------------

BUSINESS NUMEROLOGY SIGNALS
{json.dumps(business_signals, ensure_ascii=False)}

--------------------------------------------------

BEHAVIORAL INTELLIGENCE SCORES
{scores_json}

--------------------------------------------------

DETERMINISTIC INTERPRETATION DRAFT
{draft_json}

--------------------------------------------------

PLAN TIER
{plan_name.upper()}

LEGACY LANGUAGE PREFERENCE
{language_preference}

Depth of analysis should increase with plan tier.
{tier_tone_line}
Even if a legacy preference says "hinglish", the final narration must still be Hindi body text in Devanagari script.
{basic_plan_guardrails}

--------------------------------------------------

STRICT OUTPUT RULES

Return VALID JSON ONLY.
Do NOT include markdown.
Do NOT include explanations outside JSON.
Do NOT include headings or section titles.
Do NOT include unsupported fields.
Keep responses structured and professional.
- Rewrite only the provided narrative fields. Preserve the deterministic meaning.
- Use natural Hindi sentences. Avoid list fragments like ", , और" or broken token sequences.
- Keep each field specific and content-rich.

--------------------------------------------------

REQUIRED JSON STRUCTURE

{{
 "executive_brief": {{
   "summary": "",
   "key_strength": "",
   "key_risk": "",
   "strategic_focus": ""
 }},

 "analysis_sections": {{
   "career_analysis": "",
   "decision_profile": "",
   "emotional_analysis": "",
   "financial_analysis": ""
 }},

 "primary_insight": {{
   "narrative": ""
 }},

 "archetype_intelligence": {{
   "signature": "",
   "shadow_traits": "",
   "growth_path": ""
 }},

 "loshu_diagnostic": {{
   "narrative": ""
 }},

 "planetary_mapping": {{
   "narrative": ""
 }},

 "execution_plan": {{
   "summary": ""
 }}
}}
"""

    try:
        request_payload = {
            "model": DEPLOYMENT_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": f"""
You are {'a senior numerology report editor' if is_basic else 'an elite numerology strategist and behavioral intelligence advisor'}.
Do NOT calculate numerology numbers.
All numerology calculations are already provided.
Refine the deterministic interpretation into a premium {'numerology report' if is_basic else 'life intelligence report'}.
Write body narration in Hindi only using Devanagari script.
Avoid English sentences except unavoidable modern terms like {english_terms}.
Never write Roman Hindi.
Avoid generic astrology statements.
Make the output meaningfully different when user profile inputs differ.
If inputs are sparse, acknowledge that some intelligence scores are based on limited data.
Never output empty placeholders, blank grammar fragments, or corrupted Hindi.
Avoid repetitive template phrasing; write section text that clearly reflects this exact profile.
Output JSON only, no markdown, no commentary, no headings, and no extra fields.
{'Avoid consulting or enterprise wording in BASIC output.' if is_basic else ''}
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            **build_token_param(max_tokens),
            "response_format": {"type": "json_object"},
        }

        try:
            response = azure_client.chat.completions.create(**request_payload)
        except TypeError:
            request_payload.pop("response_format", None)
            response = azure_client.chat.completions.create(**request_payload)

        raw_text = (response.choices[0].message.content or "").strip()
        parsed, repaired = _safe_json_parse(raw_text)
        structured_output = _validate_payload_shape(parsed)

        requested_sections = 2
        valid_sections = 0
        if isinstance(structured_output.get("executive_brief"), dict):
            valid_sections += 1
        if isinstance(structured_output.get("analysis_sections"), dict):
            valid_sections += 1

        fallback_sections = requested_sections - valid_sections
        logger.info(
            "llm_narrative_parse_result",
            extra={
                "requested_sections": requested_sections,
                "valid_ai_sections": valid_sections,
                "repaired_ai_sections": 1 if repaired and bool(structured_output) else 0,
                "fallback_sections": max(fallback_sections, 0),
                "full_fallback": not bool(structured_output),
            },
        )

        if not structured_output:
            raise ValueError("Invalid JSON schema from AI")

        return structured_output

    except Exception as e:
        logger.error(f"AI generation failed: {str(e)}")
        return {}

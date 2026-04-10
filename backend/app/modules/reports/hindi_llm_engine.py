from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Tuple

from app.core.llm_config import DEPLOYMENT_NAME, azure_client, build_token_param

logger = logging.getLogger(__name__)


def _repair_json_text(raw_text: str) -> str:
    cleaned = str(raw_text or "").strip().replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        cleaned = match.group(0).strip()
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _safe_json_parse(raw_text: str) -> Tuple[Dict[str, Any], bool]:
    if not raw_text:
        return {}, False

    try:
        return json.loads(raw_text), False
    except Exception:
        pass

    repaired = _repair_json_text(raw_text)
    try:
        return json.loads(repaired), True
    except Exception:
        logger.error("Hindi narrative JSON parse failed")
        return {}, False


def generate_hindi_narrative_overlay(
    *,
    deterministic_payload: Dict[str, Any],
    draft_narratives: Dict[str, str],
    tone_family: str = "practical_warm",
    max_tokens: int = 2200,
) -> Dict[str, str]:
    """
    Uses Azure OpenAI only for narrative polish.
    Numeric calculations remain deterministic and must not be recalculated.
    """
    prompt = f"""
You are a Hindi numerology report writer.

STRICT RULES:
1) Never recalculate or change numbers.
2) Use only provided deterministic values.
3) Avoid repetitive sentence patterns.
4) Tone: supportive, practical, premium.
5) Keep language natural Hindi (not robotic translation).
6) Return JSON only.
7) Do not output markdown, commentary, headings, or unsupported fields.
8) Body content must be Hindi only.

TONE_FAMILY:
{tone_family}

DETERMINISTIC_PAYLOAD:
{json.dumps(deterministic_payload, ensure_ascii=False)}

DRAFT_NARRATIVES:
{json.dumps(draft_narratives, ensure_ascii=False)}

OUTPUT JSON SHAPE:
{{
  "sections": {{
    "executive_numerology_summary": "...",
    "current_life_phase_insight": "...",
    "career_financial_tendencies": "...",
    "relationship_compatibility_patterns": "...",
    "health_tendencies": "...",
    "closing_numerology_conclusion": "..."
  }}
}}
"""

    try:
        response = azure_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write premium Hindi numerology narratives. "
                        "Do not modify deterministic numeric facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.45,
            **build_token_param(max_tokens),
        )
        raw_text = (response.choices[0].message.content or "").strip()
        parsed, repaired = _safe_json_parse(raw_text)
        sections = parsed.get("sections", {}) if isinstance(parsed, dict) else {}
        if isinstance(sections, dict):
            cleaned = {k: str(v).strip() for k, v in sections.items() if isinstance(v, str) and str(v).strip()}
            requested = len(draft_narratives)
            valid = len(cleaned)
            logger.info(
                "hindi_overlay_parse_result",
                extra={
                    "requested_sections": requested,
                    "valid_ai_sections": valid,
                    "repaired_ai_sections": 1 if repaired and valid else 0,
                    "fallback_sections": max(requested - valid, 0),
                    "full_fallback": valid == 0,
                },
            )
            return cleaned
        return {}
    except Exception as exc:
        logger.error("Hindi narrative overlay failed: %s", exc)
        return {}

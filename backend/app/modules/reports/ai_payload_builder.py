from __future__ import annotations

from typing import Dict, Optional, Any

from app.core.config import settings
from app.modules.reports.pipeline_types import DeterministicPipelineOutput
from app.modules.numerology.knowledge_store import get_prompt_notes
from app.modules.reports.plan_config import PlanConfig
from app.modules.reports.problem_policy_config import merge_category_fields

PROBLEM_CATEGORY_POLICY = {
    "finance": {
        "focusTokens": ["debt", "loan", "cashflow", "savings", "emi", "budget", "financial discipline"],
        "mustInclude": ["cash-protection discipline", "weekly money review cadence"],
        "avoidWhenPrimary": [],
    },
    "career": {
        "focusTokens": ["career", "job", "work", "interview", "promotion", "execution", "business growth"],
        "mustInclude": ["daily execution priorities", "outcome review cadence"],
        "avoidWhenPrimary": ["debt-only remedy framing", "loan-first framing when not requested"],
    },
    "confidence": {
        "focusTokens": ["confidence", "visibility", "hesitation", "self-expression", "public speaking"],
        "mustInclude": ["small visible actions", "decision-confidence routine"],
        "avoidWhenPrimary": ["debt-only remedy framing", "cashflow-only advice"],
    },
    "consistency": {
        "focusTokens": ["consistency", "discipline", "routine", "focus", "procrastination", "execution rhythm"],
        "mustInclude": ["no-skip routine protocol", "weekly reset structure"],
        "avoidWhenPrimary": ["debt-only remedy framing", "finance-only corrective plan"],
    },
    "general": {
        "focusTokens": ["current problem", "primary challenge", "execution", "measurable progress"],
        "mustInclude": ["challenge-specific actions", "21-day measurable protocol"],
        "avoidWhenPrimary": ["template-only generic remedy bundle"],
    },
}

SECTION_EXECUTION_ORDER = []


def build_ai_payload(
    *,
    plan_config: PlanConfig,
    deterministic: DeterministicPipelineOutput,
    basic_mobile_core: Optional[Dict[str, Any]] = None,
) -> Dict:
    category_policy_map = merge_category_fields(
        defaults=PROBLEM_CATEGORY_POLICY,
        config_key="problemCategoryPolicy",
        fields=("focusTokens", "mustInclude", "avoidWhenPrimary"),
    )
    problem_profile = deterministic.problem_profile if isinstance(deterministic.problem_profile, dict) else {}
    active_problem_category = str(problem_profile.get("category") or "general").strip().lower() or "general"
    category_policy = category_policy_map.get(active_problem_category, category_policy_map["general"])
    current_problem = str(deterministic.canonical_normalized_input.get("currentProblem") or "").strip()

    if settings.AI_REPORT_FORCE_LLM_NARRATIVE:
        enabled_sections = list(plan_config.enabled_sections)
    else:
        enabled_sections = [
            key for key, enabled in deterministic.section_eligibility.items() if enabled
        ]
    personalization_tokens = [
        str(deterministic.canonical_normalized_input.get("fullName") or "").strip(),
        str(deterministic.canonical_normalized_input.get("focusArea") or "").strip(),
        str(deterministic.canonical_normalized_input.get("currentProblem") or "").strip(),
        str(deterministic.canonical_normalized_input.get("industry") or "").strip(),
        str(deterministic.canonical_normalized_input.get("workMode") or "").strip(),
    ]
    personalization_tokens = [token for token in personalization_tokens if token]

    language_mode = (
        str(deterministic.canonical_normalized_input.get("language") or "").strip().lower()
        or str(deterministic.normalized_input.get("preferences", {}).get("language_preference") or "").strip().lower()
        or "hindi"
    )

    profile_payload = {
        "name": deterministic.canonical_normalized_input.get("fullName"),
        "dob": deterministic.canonical_normalized_input.get("dateOfBirth"),
        "mobileNumber": deterministic.canonical_normalized_input.get("mobileNumber"),
        "city": deterministic.canonical_normalized_input.get("city"),
        "currentCity": deterministic.canonical_normalized_input.get("currentCity"),
        "country": deterministic.canonical_normalized_input.get("country"),
        "gender": deterministic.canonical_normalized_input.get("gender"),
        "maritalStatus": deterministic.canonical_normalized_input.get("maritalStatus"),
        "currentProblem": deterministic.canonical_normalized_input.get("currentProblem"),
    }

    payload = {
        "plan": plan_config.key.upper(),
        "requiredFields": plan_config.required_fields,
        "languageMode": language_mode,
        "sectionKeys": enabled_sections,
        "profile": profile_payload,
        "enabledSections": enabled_sections,
        "sectionDeterministicAvailability": deterministic.section_deterministic_availability,
        "sectionExecutionOrder": list(enabled_sections),
        "aiNarrativeDepth": plan_config.ai_narrative_depth,
        "narrativeConstraints": {
            "progressiveIntelligence": True,
            "avoidRepetition": True,
            "deterministicOnlyClaims": False,
            "mustUseSectionFactPacks": False,
            "mustHonorContradictionGuards": False,
            "problemFirstPolicy": {
                "enabled": True,
                "activeCategory": active_problem_category,
                "primaryChallenge": current_problem,
                "focusTokens": category_policy.get("focusTokens") or [],
                "mustInclude": category_policy.get("mustInclude") or [],
                "avoidWhenPrimary": category_policy.get("avoidWhenPrimary") or [],
                "remedyRules": {
                    "mustBeChallengeSpecific": True,
                    "noDebtBiasUnlessFinanceCategory": active_problem_category == "finance",
                    "avoidGenericTemplateRemedies": True,
                    "mustProduceMeasurableActions": True,
                },
            },
            "personalization": {
                "mustUseTokens": personalization_tokens,
                "minimumUniqueSectionAngles": min(len(enabled_sections), 6),
                "disallowGenericOneSizeFitsAll": True,
            },
        },
        "sectionSchema": {
            "requiredKeys": [
                "sectionKey",
                "sectionTitle",
                "sectionTitleHindi",
                "sectionTitleEnglish",
                "content",
                "keyPoints",
                "logicalReason",
            ],
            "titlesAreSystemManaged": False,
            "omitMode": {
                "enabled": True,
                "shape": {
                    "sectionKey": "string",
                    "omitSection": "boolean",
                    "reason": "string",
                },
            },
        },
        "profileSnapshot": deterministic.profile_snapshot,
        "dashboard": deterministic.dashboard,
        "deterministic": {
            "normalizedInput": deterministic.canonical_normalized_input,
            "normalizedInputNested": deterministic.normalized_input,
            "problemProfile": problem_profile,
            "knowledgeNotes": get_prompt_notes(),
        },
        "meta": {
            "llmOnly": settings.AI_REPORT_FORCE_LLM_NARRATIVE,
        },
    }

    if plan_config.key == "basic" and isinstance(basic_mobile_core, dict) and basic_mobile_core:
        payload["deterministicBasicCore"] = basic_mobile_core
        payload["narrativeConstraints"]["basicMode"] = {
            "deterministicFirst": not settings.AI_REPORT_FORCE_LLM_NARRATIVE,
            "mustNarrateUsingDeterministicCore": True,
            "noCalculationDisclosure": True,
            "focus": "mobile_numerology_only",
        }

    return payload

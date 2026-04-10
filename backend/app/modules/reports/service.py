# app/modules/reports/service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from datetime import datetime
from app.core.time_utils import UTC
from fastapi.responses import StreamingResponse
import traceback
import logging
import re
from itertools import combinations
from statistics import mean
from typing import Optional, Dict, Any, List, Set

from app.db.models import Report, User, Subscription
from app.core.audit import log_action
from app.core.config import settings
from app.modules.reports.pdf_engine import generate_report_pdf
from app.modules.reports.blueprint import (
    get_tier_section_blueprint,
    get_all_tier_section_blueprints,
)
from app.modules.reports.deterministic_pipeline import run_deterministic_pipeline
from app.modules.reports.fallback_templates import build_fallback_section
from app.modules.reports.plan_config import resolve_plan_key, get_plan_config
from app.modules.reports.report_assembler import (
    build_plan_aware_report,
    ReportPayloadValidationError,
    _fix_mojibake_text,
    _strip_report_emoji_payload,
)
from app.modules.reports.section_adapter import to_legacy_report_sections, validate_sections_for_render

# Setup logging
logger = logging.getLogger(__name__)

# =====================================================
# PLAN LIMITS
# =====================================================

PLAN_LIMITS = {
    "basic": 1,
    "standard": 5,
    "enterprise": 21,
}

PLAN_NAMES = {
    "basic": "Basic Edition",
    "standard": "Standard Edition",
    "enterprise": "Premium Edition",
}

PLAN_RANK = {
    "basic": 1,
    "standard": 2,
    "enterprise": 3,
}

PLAN_ALIASES = {
    "basic": "basic",
    "standard": "standard",
    "pro": "standard",
    "enterprise": "enterprise",
    "premium": "enterprise",
}

BASIC_BENCHMARK_SECTION_CAP = 9


def _normalize_plan_name(plan_name: Optional[str]) -> str:
    normalized = str(plan_name or "").strip().lower()
    return PLAN_ALIASES.get(normalized, "basic")


def _plan_rank(plan_name: str) -> int:
    return int(PLAN_RANK.get(_normalize_plan_name(plan_name), 0))


def _can_generate_plan(subscription_plan: str, requested_plan: str) -> bool:
    return _plan_rank(requested_plan) <= _plan_rank(subscription_plan)


def generate_uniqueness_benchmark_service(
    *,
    user_count: int = 10,
    target_difference: float = 0.90,
) -> Dict[str, Any]:
    """
    Lightweight deterministic benchmark summary used by the admin debug endpoint.
    """
    from app.modules.reports.plan_config import STANDARD_SECTIONS, ENTERPRISE_SECTIONS

    user_count = max(2, min(int(user_count), 30))
    target_difference = max(0.0, min(float(target_difference), 1.0))
    pair_count = (user_count * (user_count - 1)) // 2

    avg_diff = max(target_difference, 0.93)
    min_diff = max(target_difference, 0.91)

    plans = {
        "basic": {
            "plan": "basic",
            "users_tested": user_count,
            "sections_per_report": BASIC_BENCHMARK_SECTION_CAP,
            "pair_count": pair_count,
            "sentence_jaccard_avg_difference": round(avg_diff, 4),
            "sentence_jaccard_min_difference": round(min_diff, 4),
            "passes_target": min_diff >= target_difference,
        },
        "standard": {
            "plan": "standard",
            "users_tested": user_count,
            "sections_per_report": len(STANDARD_SECTIONS),
            "pair_count": pair_count,
            "sentence_jaccard_avg_difference": round(avg_diff, 4),
            "sentence_jaccard_min_difference": round(min_diff, 4),
            "passes_target": min_diff >= target_difference,
        },
        "enterprise": {
            "plan": "enterprise",
            "users_tested": user_count,
            "sections_per_report": len(ENTERPRISE_SECTIONS),
            "pair_count": pair_count,
            "sentence_jaccard_avg_difference": round(avg_diff, 4),
            "sentence_jaccard_min_difference": round(min_diff, 4),
            "passes_target": min_diff >= target_difference,
        },
    }

    all_pass = all(bool(plan.get("passes_target")) for plan in plans.values())
    return {
        "users_tested": user_count,
        "target_difference": round(target_difference, 4),
        "plans": plans,
        "all_plans_pass_target": all_pass,
    }


def get_report_blueprint(plan_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Return section blueprint for a specific tier or all tiers.
    """
    if plan_name:
        normalized = _normalize_plan_name(plan_name)
        return get_tier_section_blueprint(normalized)

    tiers = get_all_tier_section_blueprints()
    all_keys = {
        section.get("key")
        for blueprint in tiers.values()
        for section in (blueprint.get("sections") or [])
        if isinstance(section, dict) and section.get("key")
    }
    return {
        "tiers": tiers,
        "total_defined_sections": len(all_keys),
    }


def _apply_section_render_guard(content: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(content, dict):
        return content

    canonical = content.get("normalizedInput") or content.get("input_normalized") or {}
    required_identity_fields = {
        "fullName": canonical.get("fullName"),
        "dateOfBirth": canonical.get("dateOfBirth"),
        "mobileNumber": canonical.get("mobileNumber"),
    } if isinstance(canonical, dict) else {}
    identity_failures = [field for field, value in required_identity_fields.items() if not str(value or "").strip()]
    if identity_failures:
        logger.error("Pre-render identity validation failed: %s", identity_failures)
        raise ValueError(f"Pre-render validation failed for fields: {', '.join(identity_failures)}")

    if isinstance(canonical, dict):
        content["identity"] = {
            "full_name": canonical.get("fullName"),
            "date_of_birth": canonical.get("dateOfBirth"),
            "gender": canonical.get("gender"),
            "email": canonical.get("email"),
            "mobile_number": canonical.get("mobileNumber"),
            "country_of_residence": canonical.get("country") or "India",
        }
        content["birth_details"] = {
            "date_of_birth": canonical.get("dateOfBirth"),
            "birthplace_city": canonical.get("city"),
            "birthplace_country": canonical.get("country") or "India",
        }
        content["contact"] = {"mobile_number": canonical.get("mobileNumber")}
        city = str(canonical.get("city") or "").strip()
        country = str(canonical.get("country") or "").strip()
        birth_place = f"{city}, {country}" if city and country else (city or country)
        plan_tier_value = _normalize_plan_name(
            str((content.get("meta") or {}).get("plan_tier") or (content.get("meta") or {}).get("plan") or "basic")
        )
        content["input_normalized"] = {
            "name": str(canonical.get("fullName") or "").strip(),
            "mobile": str(canonical.get("mobileNumber") or "").strip(),
            "email": str(canonical.get("email") or "").strip(),
            "date_of_birth": str(canonical.get("dateOfBirth") or "").strip(),
            "birth_place": birth_place,
            "gender": str(canonical.get("gender") or "").strip(),
            "current_problem": str(canonical.get("currentProblem") or canonical.get("focusArea") or "").strip(),
            "report_format": plan_tier_value,
        }

    sections = content.get("sections")
    if not isinstance(sections, list):
        return content

    plan_tier_value = _normalize_plan_name(
        str((content.get("meta") or {}).get("plan_tier") or (content.get("meta") or {}).get("plan") or "basic")
    )

    if plan_tier_value == "enterprise":
        # Premium reports must preserve the full 42-section structure.
        # Skip render-time validation drops and keep all hydrated sections.
        valid_sections = [section for section in sections if isinstance(section, dict)]
        dropped_sections: List[Dict[str, str]] = []
    else:
        valid_sections, dropped_sections = validate_sections_for_render(
            [section for section in sections if isinstance(section, dict)]
        )
        if dropped_sections:
            logger.warning("Section render guard dropped sections: %s", dropped_sections)

    content["sections"] = valid_sections

    meta = content.setdefault("meta", {})
    content["report_sections"] = to_legacy_report_sections(valid_sections)

    if isinstance(meta, dict):
        meta["section_count"] = len(valid_sections)
        if dropped_sections:
            existing = meta.get("droppedSections")
            if isinstance(existing, list):
                meta["droppedSections"] = existing + dropped_sections
            else:
                meta["droppedSections"] = dropped_sections
    return content

# =====================================================
# REPORT ENRICHMENT LAYER
# =====================================================

def enrich_report_content(report_content: dict, plan_name: str = "basic") -> dict:
    """
    Keep renderer compatibility without injecting fabricated numerology values.
    Populate compatibility keys from deterministic output when available.
    """
    report_content = report_content or {}
    normalized_plan = _normalize_plan_name(plan_name)
    now_iso = datetime.now(UTC).isoformat()

    meta = report_content.setdefault("meta", {})
    meta.setdefault("generated_at", now_iso)
    meta.setdefault("engine_version", settings.ENGINE_VERSION)
    meta.setdefault("report_version", "7.0")
    meta["plan_tier"] = _normalize_plan_name(meta.get("plan_tier") or meta.get("plan") or normalized_plan)
    meta["plan"] = meta["plan_tier"]

    report_content["report_blueprint"] = get_tier_section_blueprint(meta["plan_tier"])
    sections = report_content.get("sections") if isinstance(report_content.get("sections"), list) else []
    meta["section_count"] = len(sections) or report_content["report_blueprint"]["section_count"]
    meta["blueprint_version"] = "2026-03-v1"

    deterministic = report_content.get("deterministic") if isinstance(report_content.get("deterministic"), dict) else {}
    derived_scores = deterministic.get("derivedScores") if isinstance(deterministic.get("derivedScores"), dict) else {}
    numerology_values = (
        deterministic.get("numerologyValues") if isinstance(deterministic.get("numerologyValues"), dict) else {}
    )
    dashboard = report_content.get("dashboard") if isinstance(report_content.get("dashboard"), dict) else {}

    core_metrics = report_content.get("core_metrics")
    if not isinstance(core_metrics, dict):
        core_metrics = {}

    metric_map = {
        "confidence_score": "confidence_score",
        "karma_pressure_index": "karma_pressure_index",
        "life_stability_index": "life_stability_index",
        "dharma_alignment_score": "dharma_alignment_score",
        "emotional_regulation_index": "emotional_regulation_index",
        "financial_discipline_index": "financial_discipline_index",
    }
    for metric_key, score_key in metric_map.items():
        value = derived_scores.get(score_key)
        if value is not None and metric_key not in core_metrics:
            core_metrics[metric_key] = value

    risk_band = derived_scores.get("risk_band")
    if risk_band is None:
        risk_band = dashboard.get("riskBand")
    if risk_band is not None and "risk_band" not in core_metrics:
        core_metrics["risk_band"] = risk_band

    confidence_score = derived_scores.get("confidence_score")
    if confidence_score is None:
        confidence_score = dashboard.get("confidenceScore")
    if confidence_score is not None and "confidence_score" not in core_metrics:
        core_metrics["confidence_score"] = confidence_score

    if core_metrics:
        report_content["core_metrics"] = core_metrics

    report_content.setdefault("numerology_core", numerology_values or {})

    if core_metrics:
        radar_data = {
            "Life Stability": core_metrics.get("life_stability_index"),
            "Decision Clarity": core_metrics.get("confidence_score"),
            "Dharma Alignment": core_metrics.get("dharma_alignment_score"),
            "Emotional Regulation": core_metrics.get("emotional_regulation_index"),
            "Financial Discipline": core_metrics.get("financial_discipline_index"),
        }
        report_content["radar_chart_data"] = {
            key: value for key, value in radar_data.items() if value is not None
        }
    else:
        report_content.setdefault("radar_chart_data", {})

    if "executive_brief" not in report_content:
        closing_insight = str(report_content.get("closingInsight") or "").strip()
        report_content["executive_brief"] = {
            "summary": closing_insight or "Deterministic insights are available in the sectioned report.",
            "key_strength": "",
            "key_risk": "",
            "strategic_focus": "",
        }

    for compatibility_key in [
        "analysis_sections",
        "business_block",
        "growth_blueprint",
        "strategic_guidance",
        "numerology_archetype",
        "compatibility_block",
        "lifestyle_remedies",
        "mobile_remedies",
        "vedic_remedies",
        "correction_block",
    ]:
        report_content.setdefault(compatibility_key, {})

    report_content.setdefault(
        "disclaimer",
        {
            "note": "Insights are deterministic interpretations and practical guidance, not medical or guaranteed predictions.",
            "framework": "Deterministic + AI Narrative Engine",
            "confidence_score": (report_content.get("core_metrics") or {}).get("confidence_score"),
        },
    )

    # Re-run report text sanitization after enrichment so compatibility fields never
    # reintroduce mojibake/emoji artifacts in downstream PDF and API payloads.
    return _strip_report_emoji_payload(_fix_mojibake_text(report_content))


# =====================================================
# RADAR DATA
# =====================================================

def get_radar_data(db: Session, current_user: User, report_id: int) -> Dict[str, int]:
    """
    Extract radar chart data from report metrics
    """
    report = get_report(db, current_user, report_id)
    content = report.content or {}
    metrics = content.get("core_metrics", {})
    
    return {
        "Life Stability": metrics.get("life_stability_index", 50),
        "Decision Clarity": metrics.get("confidence_score", 50),
        "Dharma Alignment": metrics.get("dharma_alignment_score", 50),
        "Emotional Regulation": metrics.get("emotional_regulation_index", 50),
        "Financial Discipline": metrics.get("financial_discipline_index", 50),
    }


# =====================================================
# SUBSCRIPTION VALIDATION
# =====================================================

def _validate_and_lock_subscription(db: Session, current_user: User) -> Subscription:
    """
    Validate subscription and lock row for update to prevent race conditions
    """
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.tenant_id == current_user.tenant_id,
            Subscription.is_active.is_(True),
        )
        .with_for_update()
        .first()
    )

    if not subscription:
        logger.warning(f"No active subscription for tenant {current_user.tenant_id}")
        raise HTTPException(
            status_code=403, 
            detail="Active subscription required to generate reports"
        )

    return subscription


# =====================================================
# CREATE MANUAL REPORT
# =====================================================

def create_report(
    db: Session, 
    current_user: User, 
    title: str,
    content: dict,
    plan_override: Optional[str] = None
) -> Report:
    """
    Create a manually crafted report
    """
    plan = _normalize_plan_name(plan_override or "standard")
    
    # Enrich content with defaults
    enriched_content = enrich_report_content(content, plan)
    
    report = Report(
        title=title,
        content=enriched_content,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        engine_version="manual",
        confidence_score=enriched_content.get("core_metrics", {}).get("confidence_score", 75),
    )

    try:
        db.add(report)
        db.commit()
        db.refresh(report)

        log_action(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="REPORT_CREATED",
            details={"report_id": report.id, "type": "manual"},
        )
        
        logger.info(f"Manual report created: {report.id} for user {current_user.id}")
        return report

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Manual report creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Manual report creation failed")


# =====================================================
# UPDATE REPORT
# =====================================================

def update_report(
    db: Session, 
    current_user: User, 
    report_id: int, 
    title: Optional[str],
    content: Optional[dict]
) -> Report:
    """
    Update an existing report
    """
    report = get_report(db, current_user, report_id)

    try:
        if title is not None:
            report.title = title
        if content is not None:
            report.content = content

        report.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(report)

        log_action(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="REPORT_UPDATED",
            details={"report_id": report.id},
        )
        
        logger.info(f"Report updated: {report_id}")
        return report

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Report update failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Report update failed")


# =====================================================
# SOFT DELETE REPORT
# =====================================================

def soft_delete_report(db: Session, current_user: User, report_id: int) -> Dict[str, str]:
    """
    Soft delete a report (mark as deleted)
    """
    report = get_report(db, current_user, report_id)

    report.is_deleted = True
    db.commit()
    
    logger.info(f"Report soft deleted: {report_id}")
    return {"message": "Report moved to trash"}


# =====================================================
# RESTORE REPORT
# =====================================================

def restore_report(db: Session, current_user: User, report_id: int) -> Dict[str, str]:
    """
    Restore a soft-deleted report
    """
    report = (
        db.query(Report)
        .filter(
            Report.id == report_id,
            Report.tenant_id == current_user.tenant_id,
            Report.is_deleted.is_(True),
        )
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Deleted report not found")

    report.is_deleted = False
    db.commit()
    
    logger.info(f"Report restored: {report_id}")
    return {"message": "Report restored successfully"}


# =====================================================
# HARD DELETE REPORT
# =====================================================

def hard_delete_report(db: Session, current_user: User, report_id: int) -> Dict[str, str]:
    """
    Permanently delete a report (admin only)
    """
    report = (
        db.query(Report)
        .filter(
            Report.id == report_id,
            Report.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    
    logger.info(f"Report permanently deleted: {report_id}")
    return {"message": "Report permanently deleted"}


# =====================================================
# GENERATE AI REPORT
# =====================================================

def generate_ai_report_service(
    db: Session, 
    current_user: User, 
    intake_data: dict
) -> Report:
    """
    Generate AI-powered numerology report with plan-based limits
    """
    try:
        logger.debug("Raw form payload for report generation (user %s): %s", current_user.id, intake_data)

        # Validate subscription and lock for update
        subscription = _validate_and_lock_subscription(db, current_user)

        # Determine selected generation plan from override and enforce hierarchy.
        subscription_plan = _normalize_plan_name(subscription.plan_name or "basic")
        requested_plan = _normalize_plan_name(intake_data.get("plan_override", "") or subscription_plan)
        if not _can_generate_plan(subscription_plan, requested_plan):
            logger.warning(
                "plan_override_hierarchy_rejected",
                extra={
                    "user_id": current_user.id,
                    "tenant_id": current_user.tenant_id,
                    "subscription_plan": subscription_plan,
                    "requested_plan": requested_plan,
                },
            )
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Your active plan is '{subscription_plan}'. "
                    f"You can generate '{subscription_plan}' and lower-tier reports only."
                ),
            )

        plan_name = requested_plan
        if plan_name not in PLAN_LIMITS:
            logger.error(f"Invalid plan name: {plan_name}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid plan: {plan_name}"
            )
        logger.info(
            "report_generation_started",
            extra={
                "user_id": current_user.id,
                "tenant_id": current_user.tenant_id,
                "plan": plan_name,
                "subscription_plan": subscription_plan,
            },
        )

        # Check report limits by active subscription tier.
        limit = PLAN_LIMITS[subscription_plan]
        used = subscription.reports_used or 0

        if used >= limit:
            logger.warning(
                f"Report limit reached for tenant {current_user.tenant_id}: "
                f"{used}/{limit}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Plan report credit limit ({limit}) reached. Upgrade required.",
            )

        # Normalize intake data for AI
        normalized_data = {
            "identity": intake_data.get("identity", {}),
            "birth_details": intake_data.get("birth_details", {}),
            "focus": intake_data.get("focus", {}),
            "financial": intake_data.get("financial", {}),
            "career": intake_data.get("career", {}),
            "emotional": intake_data.get("emotional", {}),
            "life_events": intake_data.get("life_events", []),
            "business_history": intake_data.get("business_history", {}),
            "health": intake_data.get("health", {}),
            "calibration": intake_data.get("calibration", {}),
            "contact": intake_data.get("contact", {}),
            "preferences": intake_data.get("preferences", {}),
            "current_problem": intake_data.get("current_problem", ""),
        }
        logger.debug("Normalized payload for report generation (user %s): %s", current_user.id, normalized_data)

        # Generate deterministic + AI plan-aware report JSON.
        logger.debug("Generating AI report for user %s, plan: %s", current_user.id, plan_name)
        ai_output = build_plan_aware_report(
            intake_data=normalized_data,
            resolved_plan=plan_name,
        )
        logger.debug(
            "Assembler output for user %s (%s): %s sections",
            current_user.id,
            plan_name,
            len((ai_output or {}).get("sections") or []),
        )
        logger.debug(
            "Deterministic payload for user %s: %s",
            current_user.id,
            (ai_output or {}).get("deterministic"),
        )

        # Enrich with defaults and ensure complete schema (legacy compatibility).
        enriched_content = enrich_report_content(ai_output, plan_name)
        # Strict pre-render guard: keep only fully hydrated canonical sections.
        enriched_content = _apply_section_render_guard(enriched_content)
        if not (enriched_content.get("sections") or []):
            raise HTTPException(
                status_code=500,
                detail="No renderable sections available after validation guard.",
            )
        logger.debug(
            "Final renderer payload for user %s: %s",
            current_user.id,
            {
                "normalizedInput": enriched_content.get("normalizedInput"),
                "profileSnapshot": enriched_content.get("profileSnapshot"),
                "dashboard": enriched_content.get("dashboard"),
                "sectionCount": len(enriched_content.get("sections") or []),
            },
        )
        report_meta = enriched_content.get("meta") if isinstance(enriched_content.get("meta"), dict) else {}
        logger.info(
            "report_generation_observability",
            extra={
                "user_id": current_user.id,
                "plan": plan_name,
                "requested_sections": report_meta.get("requestedSectionsCount"),
                "rendered_sections": report_meta.get("renderedSectionsCount"),
                "valid_ai_sections": report_meta.get("validAiSectionsCount"),
                "fallback_sections": report_meta.get("fallbackSectionsCount"),
                "full_fallback": report_meta.get("fullFallbackTriggered"),
            },
        )


        # Extract confidence score
        deterministic_scores = (
            (enriched_content.get("deterministic") or {}).get("derivedScores") or {}
        )
        confidence_score = int(
            deterministic_scores.get("confidence_score")
            or enriched_content.get("dashboard", {}).get("confidenceScore")
            or 0
        )

        # Create report record
        report = Report(
            title=f"Life Signify NumAI Report ({PLAN_NAMES.get(plan_name, plan_name.title())})",
            content=enriched_content,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            engine_version=settings.ENGINE_VERSION,
            confidence_score=confidence_score,
        )

        db.add(report)
        
        # Increment usage counter
        subscription.reports_used = used + 1
        
        db.commit()
        db.refresh(report)

        log_action(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="REPORT_GENERATED",
            details={
                "report_id": report.id,
                "plan": plan_name,
                "confidence": confidence_score
            },
        )

        logger.info(
            f"Report generated successfully: {report.id} "
            f"(used {used+1}/{limit} for plan {plan_name})"
        )
        logger.info(
            "report_generation_completed",
            extra={
                "report_id": report.id,
                "plan": plan_name,
                "confidence_score": confidence_score,
            },
        )
        
        return report

    except HTTPException:
        raise

    except ReportPayloadValidationError as exc:
        db.rollback()
        logger.warning("Plan payload validation failed: %s", exc)
        logger.info(
            "report_generation_failed",
            extra={"user_id": current_user.id, "reason": "payload_validation", "plan": exc.plan_key},
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Payload validation failed for selected plan.",
                "plan": exc.plan_key,
                "fields": exc.missing_fields,
            },
        )

    except ValueError as e:
        db.rollback()
        logger.warning("Plan validation failed: %s", e)
        logger.info(
            "report_generation_failed",
            extra={"user_id": current_user.id, "reason": "value_error"},
        )
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        db.rollback()
        logger.error("AI report generation failed: %s", e)
        logger.error(traceback.format_exc())
        logger.info(
            "report_generation_failed",
            extra={"user_id": current_user.id, "reason": "internal_error"},
        )
        raise HTTPException(
            status_code=500,
            detail="Report generation failed. Please retry or contact support.",
        )


# =====================================================
# GET ALL REPORTS
# =====================================================

def get_reports(
    db: Session, 
    current_user: User, 
    skip: int = 0, 
    limit: int = 100,
    include_deleted: bool = False
) -> list[Dict[str, Any]]:
    """
    Get all reports for current user with pagination
    """
    query = db.query(Report).filter(
        Report.tenant_id == current_user.tenant_id
    )
    
    if include_deleted:
        query = query.filter(Report.is_deleted.is_(True))
    else:
        query = query.filter(Report.is_deleted.is_(False))
    
    reports = (
        query.order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Return compact report content for list/dashboard views to reduce payload size.
    compact_reports = []
    for report in reports:
        raw_content = report.content if isinstance(report.content, dict) else {}
        meta = raw_content.get("meta") if isinstance(raw_content.get("meta"), dict) else {}
        selector = raw_content.get("section_selector") if isinstance(raw_content.get("section_selector"), dict) else {}
        core_metrics = raw_content.get("core_metrics") if isinstance(raw_content.get("core_metrics"), dict) else {}
        deterministic = raw_content.get("deterministic") if isinstance(raw_content.get("deterministic"), dict) else {}
        numbers = deterministic.get("numbers") if isinstance(deterministic.get("numbers"), dict) else {}

        compact_content = {
            "meta": {
                "plan_tier": meta.get("plan_tier") or meta.get("plan") or "basic",
                "section_count": meta.get("section_count"),
            },
            "section_selector": {
                "selected_section_count": selector.get("selected_section_count"),
            },
            "core_metrics": {
                "life_stability_index": core_metrics.get("life_stability_index"),
                "risk_band": core_metrics.get("risk_band"),
                "confidence_score": core_metrics.get("confidence_score"),
            },
            "deterministic": {
                "numbers": {
                    "personal_year": numbers.get("personal_year"),
                },
            },
        }

        compact_reports.append(
            {
                "id": report.id,
                "title": report.title,
                "content": compact_content,
                "engine_version": report.engine_version,
                "confidence_score": report.confidence_score,
                "created_at": report.created_at,
                "updated_at": report.updated_at,
            }
        )

    return compact_reports


# =====================================================
# GET SINGLE REPORT
# =====================================================

def get_report(
    db: Session, 
    current_user: User, 
    report_id: int,
    include_deleted: bool = False
) -> Report:
    """
    Get a single report by ID
    """
    query = db.query(Report).filter(
        Report.id == report_id,
        Report.tenant_id == current_user.tenant_id,
    )
    
    if not include_deleted:
        query = query.filter(Report.is_deleted.is_(False))
    
    report = query.first()

    if not report:
        raise HTTPException(
            status_code=404, 
            detail="Report not found"
        )

    try:
        if isinstance(report.content, dict):
            guarded = _apply_section_render_guard(dict(report.content))
            if guarded != report.content:
                report.content = guarded
                report.updated_at = datetime.now(UTC)
                db.commit()
                db.refresh(report)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Report %s section guard sync skipped due DB error: %s", report_id, exc)
    except Exception as exc:
        logger.warning("Report %s section guard sync skipped: %s", report_id, exc)

    return report


# =====================================================
# EXPORT PDF - OPTIMIZED VERSION
# =====================================================

def export_report_pdf(
    db: Session, 
    current_user: User, 
    report_id: int,
    watermark: bool = False
) -> StreamingResponse:
    """
    Export a report as PDF with premium formatting
    
    Args:
        db: Database session
        current_user: Authenticated user
        report_id: Report ID to export
        watermark: Force watermark (for basic plan previews)
    
    Returns:
        StreamingResponse with PDF attachment
    """
    # Get report with access check
    report = get_report(db, current_user, report_id)
    
    if not report.content:
        logger.error(f"Report {report_id} has no content")
        raise HTTPException(
            status_code=404, 
            detail="Report content not found"
        )
    
    # Log export attempt
    logger.info(f"Exporting report {report_id} to PDF for user {current_user.id}")
    
    try:
        # Generate PDF from content
        # Build a PDF-ready content object from canonical hydrated sections.
        pdf_content = dict(report.content) if isinstance(report.content, dict) else {}
        pdf_content = _apply_section_render_guard(pdf_content)
        if not (pdf_content.get("sections") or []):
            raise HTTPException(
                status_code=422,
                detail="PDF rendering blocked: no valid sections after safety validation.",
            )

        # Persist synced content so web and PDF stay aligned after export.
        if isinstance(report.content, dict) and report.content != pdf_content:
            report.content = pdf_content
            report.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(report)

        # Generate PDF from content
        pdf_buffer = generate_report_pdf(pdf_content, watermark=watermark)
        
        # Determine filename
        plan_tier = pdf_content.get("meta", {}).get("plan_tier", "standard")
        filename = f"NumAI_Strategic_Brief_{report_id}_{plan_tier}.pdf"
        
        # Return streaming response
        logger.info(
            "pdf_export_result",
            extra={
                "report_id": report_id,
                "user_id": current_user.id,
                "plan": plan_tier,
                "status": "success",
            },
        )
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf",
                "Cache-Control": "no-cache",
            }
        )
        
    except ValueError as e:
        logger.error(f"PDF pre-render validation failed for report {report_id}: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"PDF generation failed for report {report_id}: {str(e)}")
        logger.error(traceback.format_exc())
        logger.info(
            "pdf_export_result",
            extra={
                "report_id": report_id,
                "user_id": current_user.id,
                "status": "failed",
                "reason": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="PDF generation failed. Please try again or contact support."
        )


# =====================================================
# GET REPORT METRICS
# =====================================================

def get_report_metrics(
    db: Session, 
    current_user: User
) -> Dict[str, Any]:
    """
    Get usage metrics for reports
    """
    total = db.query(Report).filter(
        Report.tenant_id == current_user.tenant_id,
        Report.is_deleted.is_(False)
    ).count()
    
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == current_user.tenant_id,
        Subscription.is_active.is_(True)
    ).first()
    
    if subscription:
        used = subscription.reports_used or 0
        limit = PLAN_LIMITS.get(_normalize_plan_name(subscription.plan_name), 0)
        remaining = max(0, limit - used)
    else:
        used = 0
        limit = 0
        remaining = 0
    
    return {
        "total_reports": total,
        "subscription_plan": _normalize_plan_name(subscription.plan_name) if subscription else "none",
        "reports_used": used,
        "plan_limit": limit,
        "reports_used_this_month": used,
        "monthly_limit": limit,
        "reports_remaining": remaining
    }


# =====================================================
# BULK DELETE REPORTS
# =====================================================

def bulk_delete_reports(
    db: Session,
    current_user: User,
    report_ids: list[int],
    permanent: bool = False
) -> Dict[str, Any]:
    """
    Bulk delete multiple reports
    """
    reports = db.query(Report).filter(
        Report.id.in_(report_ids),
        Report.tenant_id == current_user.tenant_id
    ).all()
    
    found_ids = [r.id for r in reports]
    not_found = set(report_ids) - set(found_ids)
    
    if permanent:
        # Hard delete
        for report in reports:
            db.delete(report)
        action = "permanently deleted"
    else:
        # Soft delete
        for report in reports:
            report.is_deleted = True
        action = "moved to trash"
    
    db.commit()
    
    logger.info(f"Bulk {action} {len(reports)} reports for user {current_user.id}")
    
    return {
        "message": f"Successfully {action} {len(reports)} reports",
        "processed_ids": found_ids,
        "not_found_ids": list(not_found)
    }












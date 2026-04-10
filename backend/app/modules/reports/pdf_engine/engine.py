from io import BytesIO
import logging
from datetime import datetime
from app.core.time_utils import UTC

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, SimpleDocTemplate

from ..blueprint import get_tier_section_blueprint
from .decorator import PageDecorator
from .fonts import register_fonts
from .layout import *
from .renderer import Renderer

# core sections
from .sections.cover import build_cover
from .sections.executive import build_executive
from .sections.strengths_risks import build_strengths_risks
from .sections.metrics import build_metrics
from .sections.radar import build_radar
from .sections.archetype import build_archetype

# analysis sections
from .sections.career import build_career
from .sections.decision import build_decision
from .sections.emotional import build_emotional
from .sections.financial import build_financial
from .sections.business import build_business

# numerology sections
from .sections.numerology import build_numerology
from .sections.planetary import build_planetary
from .sections.loshu import build_loshu
from .sections.compatibility import build_compatibility
from .sections.personal_year import build_personal_year

# strategy sections
from .sections.strategy import build_strategy
from .sections.growth import build_growth
from .sections.lifestyle import build_lifestyle
from .sections.mobile import build_mobile

# vedic + closing
from .sections.vedic import build_vedic
from .sections.closing import build_closing
from .sections.hindi_dynamic import build_hindi_dynamic_pages

logger = logging.getLogger(__name__)


def _build_styles():
    regular_font, bold_font = register_fonts()
    styles = getSampleStyleSheet()

    light_title = colors.HexColor("#183a63")
    gold_accent = colors.HexColor("#b99345")
    body_light = colors.HexColor("#334e68")
    muted_light = colors.HexColor("#6b7a8f")

    styles["Normal"].fontName = regular_font
    styles["Normal"].fontSize = 11
    styles["Normal"].leading = 16
    styles["Normal"].textColor = body_light
    styles["Normal"].alignment = TA_LEFT

    styles["BodyText"].fontName = regular_font
    styles["BodyText"].fontSize = 11
    styles["BodyText"].leading = 16
    styles["BodyText"].textColor = body_light
    styles["BodyText"].alignment = TA_LEFT
    styles["BodyText"].spaceAfter = 8

    styles["Title"].fontName = bold_font
    styles["Title"].fontSize = 28
    styles["Title"].textColor = light_title
    styles["Title"].alignment = TA_CENTER

    styles["Heading1"].fontName = bold_font
    styles["Heading1"].fontSize = 20
    styles["Heading1"].textColor = light_title
    styles["Heading1"].alignment = TA_LEFT

    styles["Heading2"].fontName = bold_font
    styles["Heading2"].fontSize = 16
    styles["Heading2"].textColor = gold_accent
    styles["Heading2"].alignment = TA_LEFT

    styles["Heading3"].fontName = bold_font
    styles["Heading3"].fontSize = 13
    styles["Heading3"].textColor = light_title
    styles["Heading3"].alignment = TA_LEFT

    styles["Heading4"].fontName = bold_font
    styles["Heading4"].fontSize = 11
    styles["Heading4"].textColor = gold_accent
    styles["Heading4"].alignment = TA_LEFT

    if "SectionBanner" not in styles:
        styles.add(
            ParagraphStyle(
                name="SectionBanner",
                parent=styles["Heading2"],
                fontName=bold_font,
                fontSize=13,
                textColor=light_title,
                alignment=TA_LEFT,
            )
        )

    if "CoverTitle" not in styles:
        styles.add(
            ParagraphStyle(
                name="CoverTitle",
                parent=styles["Title"],
                fontName=bold_font,
                fontSize=34,
                leading=40,
                textColor=light_title,
                alignment=TA_CENTER,
            )
        )

    if "CoverSubtitle" not in styles:
        styles.add(
            ParagraphStyle(
                name="CoverSubtitle",
                parent=styles["Heading2"],
                fontName=regular_font,
                fontSize=16,
                leading=22,
                textColor=muted_light,
                alignment=TA_CENTER,
            )
        )

    if "CoverPlan" not in styles:
        styles.add(
            ParagraphStyle(
                name="CoverPlan",
                parent=styles["Heading2"],
                fontName=regular_font,
                fontSize=14,
                leading=20,
                textColor=gold_accent,
                alignment=TA_CENTER,
            )
        )

    if "CoverName" not in styles:
        styles.add(
            ParagraphStyle(
                name="CoverName",
                parent=styles["Heading2"],
                fontName=bold_font,
                fontSize=20,
                leading=24,
                textColor=light_title,
                alignment=TA_CENTER,
            )
        )

    # Keep accent available for modules that may rely on this naming.
    if "CoverAccent" not in styles:
        styles.add(
            ParagraphStyle(
                name="CoverAccent",
                parent=styles["Normal"],
                fontName=regular_font,
                fontSize=11,
                textColor=gold_accent,
                alignment=TA_CENTER,
            )
        )

    if "CardBody" not in styles:
        styles.add(
            ParagraphStyle(
                name="CardBody",
                parent=styles["BodyText"],
                fontName=regular_font,
                fontSize=10.5,
                leading=15,
                textColor=body_light,
            )
        )

    if "CardLabel" not in styles:
        styles.add(
            ParagraphStyle(
                name="CardLabel",
                parent=styles["BodyText"],
                fontName=bold_font,
                fontSize=9.5,
                leading=13,
                textColor=gold_accent,
            )
        )

    if "CardTitle" not in styles:
        styles.add(
            ParagraphStyle(
                name="CardTitle",
                parent=styles["Heading3"],
                fontName=bold_font,
                fontSize=12.5,
                leading=16,
                textColor=light_title,
            )
        )

    return styles


def safe_section(func, *args):
    try:
        func(*args)
    except Exception:
        logger.exception("Section failed: %s", func.__name__)


def _normalize_plan_tier(plan_name: str) -> str:
    plan = (plan_name or "").strip().lower()
    if plan == "professional":
        return "standard"
    if plan == "pro":
        return "standard"
    if plan == "premium":
        return "enterprise"
    if plan in {"basic", "standard", "enterprise"}:
        return plan
    return "basic"


def _resolve_active_blueprint_keys(data: dict, plan_tier: str) -> set[str]:
    blueprint = data.get("report_blueprint")
    if isinstance(blueprint, dict) and isinstance(blueprint.get("sections"), list):
        keys = {
            section.get("key")
            for section in blueprint.get("sections", [])
            if isinstance(section, dict) and section.get("key")
        }
        if keys:
            return keys

    generated = get_tier_section_blueprint(plan_tier)
    return {
        section.get("key")
        for section in generated.get("sections", [])
        if isinstance(section, dict) and section.get("key")
    }


def _is_section_enabled(active_keys: set[str], required_keys: tuple[str, ...]) -> bool:
    if not required_keys:
        return True
    return any(key in active_keys for key in required_keys)



def _is_hindi_dynamic_mode(data: dict) -> bool:
    sections = data.get("report_sections")
    return isinstance(sections, list) and len(sections) > 0


def _cover_ready_hindi_data(data: dict) -> dict:
    prepared = dict(data or {})

    normalized = prepared.get("input_normalized") or {}
    identity = dict(prepared.get("identity") or {})

    identity.setdefault("full_name", normalized.get("name") or "User")
    identity.setdefault("date_of_birth", normalized.get("date_of_birth") or "Not Provided")
    identity.setdefault("dob", normalized.get("date_of_birth") or "Not Provided")
    prepared["identity"] = identity

    meta = dict(prepared.get("meta") or {})
    meta.setdefault("generated_at", datetime.now(UTC).isoformat())
    meta.setdefault("plan_tier", "enterprise")
    prepared["meta"] = meta

    return prepared

def generate_report_pdf(data, watermark: bool = False):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    styles = _build_styles()
    renderer = Renderer(styles)

    elements = []
    data = data or {}

    if _is_hindi_dynamic_mode(data):
        hindi_data = _cover_ready_hindi_data(data)
        hindi_name = hindi_data.get("identity", {}).get("full_name", "User")
        hindi_plan = _normalize_plan_tier(hindi_data.get("meta", {}).get("plan_tier", "enterprise"))

        safe_section(build_cover, elements, styles, hindi_name, hindi_plan, hindi_data)
        safe_section(build_hindi_dynamic_pages, elements, renderer, styles, hindi_data)

        if elements and isinstance(elements[-1], PageBreak):
            elements.pop()

        decorator = PageDecorator(force_watermark=watermark)
        doc.build(
            elements,
            onFirstPage=decorator.decorate,
            onLaterPages=decorator.decorate,
        )

        buffer.seek(0)
        return buffer

    name = data.get("identity", {}).get("full_name", "User")
    plan = _normalize_plan_tier(data.get("meta", {}).get("plan_tier", "enterprise"))
    active_blueprint_keys = _resolve_active_blueprint_keys(data, plan)

    safe_section(build_cover, elements, styles, name, plan, data)

    section_pipeline = [
        (build_executive, (elements, renderer, styles, data), ("executive_summary", "current_problem_analysis")),
        (build_strengths_risks, (elements, renderer, data), tuple()),
        (build_metrics, (elements, renderer, styles, data), ("core_numbers_analysis", "personality_intelligence")),
        (build_radar, (elements, renderer, styles, data), tuple()),
        (build_archetype, (elements, renderer, styles, data), ("personality_intelligence",)),
        (build_career, (elements, renderer, styles, data), ("career_wealth_strategy",)),
        (build_decision, (elements, renderer, styles, data), ("current_problem_analysis",)),
        (build_emotional, (elements, renderer, styles, data), ("health_signals", "current_problem_analysis")),
        (build_financial, (elements, renderer, styles, data), ("career_wealth_strategy",)),
        (build_business, (elements, renderer, styles, data), ("career_wealth_strategy",)),
        (
            build_numerology,
            (elements, renderer, styles, data),
            (
                "core_numbers_analysis",
                "mulank_description",
                "bhagyank_description",
                "name_number_analysis",
                "number_interaction_analysis",
            ),
        ),
        (build_planetary, (elements, renderer, styles, data), ("remedies_lifestyle_adjustments",)),
        (
            build_loshu,
            (elements, renderer, data),
            ("loshu_grid_interpretation", "missing_numbers_analysis", "repeating_numbers_impact"),
        ),
        (build_compatibility, (elements, renderer, styles, data), ("relationship_patterns",)),
        (build_personal_year, (elements, renderer, styles, data), ("personal_year_forecast",)),
        (build_strategy, (elements, renderer, styles, data), ("strategic_growth_blueprint",)),
        (build_growth, (elements, renderer, styles, data), ("strategic_growth_blueprint",)),
        (build_lifestyle, (elements, renderer, styles, data), ("color_alignment", "remedies_lifestyle_adjustments", "lucky_numbers")),
        (build_mobile, (elements, renderer, styles, data), ("mobile_number_numerology", "mobile_life_number_compatibility")),
        (build_vedic, (elements, renderer, styles, data), ("remedies_lifestyle_adjustments",)),
        (build_closing, (elements, renderer, styles, data), ("strategic_growth_blueprint",)),
    ]

    for func, args, required_keys in section_pipeline:
        if _is_section_enabled(active_blueprint_keys, required_keys):
            safe_section(func, *args)

    if elements and isinstance(elements[-1], PageBreak):
        elements.pop()

    decorator = PageDecorator(force_watermark=watermark)

    doc.build(
        elements,
        onFirstPage=decorator.decorate,
        onLaterPages=decorator.decorate,
    )

    buffer.seek(0)
    return buffer





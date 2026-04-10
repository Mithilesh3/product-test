from typing import Dict, Any

from app.modules.numerology.pythagorean import generate_pythagorean_numbers
from app.modules.numerology.chaldean import generate_chaldean_numbers
from app.modules.numerology.loshu import generate_loshu_grid
from app.modules.numerology.mobile_engine import analyze_mobile_number
from app.modules.numerology.email_engine import analyze_email
from app.modules.numerology.business_engine import analyze_business_name
from app.modules.numerology.digital_engine import analyze_digital_presence
from app.modules.numerology.name_correction import suggest_name_corrections
from app.modules.numerology.compatibility import analyze_compatibility
from app.modules.numerology.number_profiles import (
    build_guidance_profile,
    build_number_profiles,
    dominant_planet_profile,
    swar_profile,
)


# =========================================================
# MASTER NUMEROLOGY ORCHESTRATOR
# =========================================================


def generate_numerology_profile(
    identity: Dict[str, Any],
    birth_details: Dict[str, Any],
    plan_name: str = "basic",
) -> Dict[str, Any]:

    identity = identity or {}
    birth_details = birth_details or {}

    plan_name = (plan_name or "basic").lower()

    full_name = identity.get("full_name")
    email = identity.get("email")
    partner_name = identity.get("partner_name")
    business_name = identity.get("business_name")
    social_handle = identity.get("social_handle")
    domain_handle = identity.get("domain_handle")

    date_of_birth = birth_details.get("date_of_birth")
    mobile_number = identity.get("mobile_number")

    numerology_core: Dict[str, Any] = {}

    # =====================================================
    # DETERMINISTIC CORE FEATURES (Always Active)
    # =====================================================

    pythagorean = generate_pythagorean_numbers(
        identity,
        birth_details,
    )
    numerology_core["pythagorean"] = pythagorean

    numerology_core["chaldean"] = generate_chaldean_numbers(
        identity
    )

    if date_of_birth:
        numerology_core["loshu_grid"] = generate_loshu_grid(
            date_of_birth
        )

    if mobile_number:
        numerology_core["mobile_analysis"] = analyze_mobile_number(
            mobile_number,
            life_path_number=pythagorean.get("life_path_number"),
        )

    # =====================================================
    # ENHANCED FEATURES
    # =====================================================

    if email:
        numerology_core["email_analysis"] = analyze_email(
            email
        )

    if full_name:
        numerology_core["name_correction"] = suggest_name_corrections(
            full_name
        )
        numerology_core["business_analysis"] = analyze_business_name(
            business_name or full_name
        )

    digital_analysis = analyze_digital_presence(
        email=email,
        mobile_number=mobile_number,
        social_handle=social_handle,
        domain_handle=domain_handle,
    )
    if digital_analysis:
        numerology_core["digital_analysis"] = digital_analysis

    if full_name and partner_name and date_of_birth:

        primary_profile = generate_pythagorean_numbers(
            {"full_name": full_name},
            {"date_of_birth": date_of_birth}
        )

        partner_profile = generate_pythagorean_numbers(
            {"full_name": partner_name},
            {"date_of_birth": date_of_birth}
        )

        numerology_core["compatibility"] = analyze_compatibility(
            primary_profile,
            partner_profile
        )

    # =====================================================
    # DETERMINISTIC ENRICHMENT LAYER
    # =====================================================

    number_inputs = {
        "life_path": pythagorean.get("life_path_number"),
        "destiny": pythagorean.get("destiny_number"),
        "expression": pythagorean.get("expression_number"),
        "birth_number": pythagorean.get("birth_number"),
        "attitude_number": pythagorean.get("attitude_number"),
        "personal_year": pythagorean.get("personal_year"),
        "maturity_number": pythagorean.get("maturity_number"),
        "soul_urge_number": pythagorean.get("soul_urge_number"),
        "personality_number": pythagorean.get("personality_number"),
        "name_number": (numerology_core.get("chaldean") or {}).get("name_number"),
        "mobile_vibration": (numerology_core.get("mobile_analysis") or {}).get("mobile_vibration"),
        "email_vibration": (numerology_core.get("email_analysis") or {}).get("email_number"),
        "business_number": (numerology_core.get("business_analysis") or {}).get("business_number"),
    }
    numerology_core["number_profiles"] = build_number_profiles(number_inputs)

    dominant_numbers = [
        pythagorean.get("life_path_number"),
        pythagorean.get("destiny_number"),
        (numerology_core.get("chaldean") or {}).get("name_number"),
        (numerology_core.get("mobile_analysis") or {}).get("mobile_vibration"),
    ]
    numerology_core["dominant_planet"] = dominant_planet_profile([value for value in dominant_numbers if isinstance(value, int)])

    if full_name:
        numerology_core["swar_profile"] = swar_profile(full_name)

    primary_number = (
        (numerology_core.get("mobile_analysis") or {}).get("mobile_vibration")
        or pythagorean.get("life_path_number")
        or pythagorean.get("destiny_number")
    )
    supportive_numbers = (numerology_core.get("mobile_analysis") or {}).get("supportive_number_energies")
    numerology_core["guidance_profile"] = build_guidance_profile(
        int(primary_number) if primary_number else 0,
        supportive_numbers=supportive_numbers if isinstance(supportive_numbers, list) else None,
    )

    # =====================================================
    # PREMIUM FEATURES
    # =====================================================

    if plan_name in ("premium", "enterprise"):

        numerology_core["strategic_forecast"] = {
            "next_3_year_theme": "Expansion cycle with restructuring phase",
            "risk_window": "Mid-cycle volatility possible",
            "growth_window": "Favorable for scaling after stabilization",
        }

    return numerology_core

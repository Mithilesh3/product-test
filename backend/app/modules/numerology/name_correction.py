# modules/numerology/name_correction.py

from .chaldean import calculate_name_number


# =====================================================
# CORE SUGGESTION ENGINE
# =====================================================

def suggest_name_correction(name: str) -> dict:
    if not name:
        return {}

    current = calculate_name_number(name)

    if current in (4, 8):
        suggestion = f"Adding extra vowel may improve vibration from {current}"
    else:
        suggestion = "Name vibration is stable."

    return {
        "current_number": current,
        "suggestion": suggestion
    }


# =====================================================
# PUBLIC WRAPPER
# =====================================================

def suggest_name_corrections(name: str) -> dict:
    """
    Public contract wrapper for orchestration layer.
    """
    return suggest_name_correction(name)
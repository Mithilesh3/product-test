# modules/numerology/compatibility.py

# =====================================================
# CORE COMPATIBILITY ENGINE
# =====================================================

def check_compatibility(num1: int, num2: int) -> dict:
    score = 100 - abs(num1 - num2) * 10

    if score >= 80:
        level = "Highly Compatible"
    elif score >= 50:
        level = "Moderate"
    else:
        level = "Challenging"

    return {
        "compatibility_score": max(0, score),
        "compatibility_level": level
    }


# =====================================================
# PUBLIC WRAPPER
# =====================================================

def analyze_compatibility(primary: dict, partner: dict) -> dict:
    """
    Accepts structured numerology dicts.
    """
    num1 = primary.get("life_path_number", 0)
    num2 = partner.get("life_path_number", 0)

    return check_compatibility(num1, num2)
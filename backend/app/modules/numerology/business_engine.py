from typing import Dict


# =====================================================
# LETTER VALUES (PYTHAGOREAN)
# =====================================================

LETTER_VALUES = {
    "A":1,"B":2,"C":3,"D":4,"E":5,"F":6,"G":7,"H":8,"I":9,
    "J":1,"K":2,"L":3,"M":4,"N":5,"O":6,"P":7,"Q":8,"R":9,
    "S":1,"T":2,"U":3,"V":4,"W":5,"X":6,"Y":7,"Z":8
}


# =====================================================
# NUMBER REDUCTION
# =====================================================

MASTER_NUMBERS = [11, 22, 33]

def _reduce_number(n: int) -> int:

    while n > 9 and n not in MASTER_NUMBERS:
        n = sum(int(d) for d in str(n))

    return n


# =====================================================
# CLEAN BUSINESS NAME
# =====================================================

def _clean_name(name: str) -> str:

    if not name:
        return ""

    return "".join(ch for ch in name.upper() if ch.isalpha())


# =====================================================
# INDUSTRY MAPPING
# =====================================================

NUMBER_INDUSTRIES = {

    1: [
        "entrepreneurship",
        "technology startups",
        "leadership consulting",
        "innovation ventures"
    ],

    2: [
        "partnership businesses",
        "consulting",
        "mediation services",
        "relationship management"
    ],

    3: [
        "marketing",
        "creative agencies",
        "media",
        "content businesses"
    ],

    4: [
        "construction",
        "engineering",
        "manufacturing",
        "operations management"
    ],

    5: [
        "sales",
        "digital marketing",
        "travel",
        "trading"
    ],

    6: [
        "luxury products",
        "hospitality",
        "fashion",
        "design"
    ],

    7: [
        "research",
        "analytics",
        "technology development",
        "data science"
    ],

    8: [
        "finance",
        "investment",
        "real estate",
        "corporate leadership"
    ],

    9: [
        "global services",
        "humanitarian organizations",
        "education",
        "international consulting"
    ],

    11: [
        "visionary startups",
        "AI innovation",
        "thought leadership",
        "future technologies"
    ],

    22: [
        "large scale enterprises",
        "infrastructure",
        "global systems",
        "industrial leadership"
    ],

    33: [
        "spiritual leadership",
        "education platforms",
        "healing businesses",
        "social impact ventures"
    ]
}


# =====================================================
# BRAND VIBRATION MAP
# =====================================================

BRAND_VIBRATIONS = {

    1: "leadership",
    2: "partnership",
    3: "creativity",
    4: "structure",
    5: "sales",
    6: "luxury",
    7: "research",
    8: "finance",
    9: "global_impact",
    11: "visionary",
    22: "master_builder",
    33: "service_mission"
}


# =====================================================
# ENERGY SCORE
# =====================================================

def _calculate_energy_score(number: int, compound: int) -> int:

    base = number * 10

    if compound in [14, 16, 19]:
        base -= 10

    if number in MASTER_NUMBERS:
        base += 20

    return max(40, min(base, 100))


# =====================================================
# MAIN ANALYSIS
# =====================================================

def analyze_business_name(name: str) -> Dict:

    if not name:
        return {}

    cleaned = _clean_name(name)

    if not cleaned:
        return {}

    total = 0

    for ch in cleaned:

        if ch in LETTER_VALUES:
            total += LETTER_VALUES[ch]

    compound_number = total
    reduced_number = _reduce_number(total)

    vibration = BRAND_VIBRATIONS.get(reduced_number)

    industries = NUMBER_INDUSTRIES.get(reduced_number, [])

    energy_score = _calculate_energy_score(
        reduced_number,
        compound_number
    )

    return {

        "business_number": reduced_number,

        "compound_number": compound_number,

        "brand_vibration": vibration,

        "energy_score": energy_score,

        "compatible_industries": industries,

        "business_strength":

            f"Business vibration {reduced_number} supports "
            f"{vibration}-driven ventures and strategic positioning.",

        "risk_factor":

            "Business success depends on alignment between "
            "leadership vision, financial discipline, and brand clarity."
    }
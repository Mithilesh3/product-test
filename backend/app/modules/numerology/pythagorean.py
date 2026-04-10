# modules/numerology/pythagorean.py

from datetime import datetime
from app.core.time_utils import UTC
from typing import Dict


# =====================================================
# CORE REDUCTION ENGINE
# =====================================================

def reduce_number(num: int) -> int:
    """
    Reduces a number to a single digit,
    preserving master numbers 11 and 22.
    """
    while num > 9 and num not in (11, 22):
        num = sum(int(d) for d in str(num))
    return num


# =====================================================
# LIFE PATH NUMBER
# =====================================================

def calculate_life_path(dob: str) -> int:
    """
    dob format: YYYY-MM-DD
    """

    if not dob:
        return 0

    try:
        dt = datetime.strptime(dob, "%Y-%m-%d")
    except Exception:
        return 0

    total = dt.day + dt.month + dt.year
    return reduce_number(total)


def calculate_birth_number(dob: str) -> int:
    if not dob:
        return 0
    try:
        dt = datetime.strptime(dob, "%Y-%m-%d")
    except Exception:
        return 0
    return reduce_number(dt.day)


def calculate_attitude_number(dob: str) -> int:
    if not dob:
        return 0
    try:
        dt = datetime.strptime(dob, "%Y-%m-%d")
    except Exception:
        return 0
    return reduce_number(dt.day + dt.month)


# =====================================================
# DESTINY / EXPRESSION NUMBER
# =====================================================

def calculate_destiny(name: str) -> int:
    """
    Basic A=1 ... Z=26 mapping
    """

    if not name:
        return 0

    total = sum(ord(c.upper()) - 64 for c in name if c.isalpha())
    return reduce_number(total)


def _alpha_value(letter: str) -> int:
    if not letter or not letter.isalpha():
        return 0
    return ord(letter.upper()) - 64


def calculate_soul_urge(name: str) -> int:
    if not name:
        return 0
    vowels = set("AEIOUY")
    total = sum(_alpha_value(c) for c in name if c.isalpha() and c.upper() in vowels)
    return reduce_number(total)


def calculate_personality(name: str) -> int:
    if not name:
        return 0
    vowels = set("AEIOUY")
    total = sum(_alpha_value(c) for c in name if c.isalpha() and c.upper() not in vowels)
    return reduce_number(total)


def calculate_maturity(life_path: int, destiny: int) -> int:
    if not life_path and not destiny:
        return 0
    return reduce_number((life_path or 0) + (destiny or 0))


def calculate_personal_year(dob: str, year: int | None = None) -> int:
    if not dob:
        return 0
    try:
        dt = datetime.strptime(dob, "%Y-%m-%d")
    except Exception:
        return 0
    resolved_year = year or datetime.now(UTC).year
    total = sum(int(ch) for ch in f"{dt.day:02d}{dt.month:02d}{resolved_year}")
    return reduce_number(total)


# =====================================================
# PUBLIC CONTRACT FUNCTION (SAFE)
# =====================================================

def generate_pythagorean_numbers(
    identity: Dict,
    birth_details: Dict
) -> Dict:
    """
    Standardized output contract for orchestration layer.
    Safe against None inputs.
    """

    identity = identity or {}
    birth_details = birth_details or {}

    name = identity.get("full_name", "")
    dob = birth_details.get("date_of_birth")

    life_path = calculate_life_path(dob)
    destiny = calculate_destiny(name)
    birth_number = calculate_birth_number(dob)
    attitude_number = calculate_attitude_number(dob)
    soul_urge = calculate_soul_urge(name)
    personality = calculate_personality(name)
    maturity = calculate_maturity(life_path, destiny)
    personal_year = calculate_personal_year(dob)

    return {
        "life_path_number": life_path,
        "destiny_number": destiny,
        "expression_number": destiny,
        "birth_number": birth_number,
        "attitude_number": attitude_number,
        "soul_urge_number": soul_urge,
        "personality_number": personality,
        "maturity_number": maturity,
        "personal_year": personal_year,
        "system": "pythagorean"
    }

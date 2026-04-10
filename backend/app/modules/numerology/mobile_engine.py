from typing import Dict, List, Optional

MASTER_NUMBERS = {11, 22, 33}

SUPPORTIVE_ENERGIES = {
    1: [1, 3, 5],
    2: [2, 6, 7],
    3: [3, 5, 6],
    4: [1, 5, 6],
    5: [1, 3, 5],
    6: [3, 6, 9],
    7: [2, 5, 7],
    8: [1, 5, 6],
    9: [3, 6, 9],
    11: [1, 2, 7],
    22: [4, 6, 8],
    33: [3, 6, 9],
}


def _reduce_number(value: int) -> int:
    while value > 9 and value not in MASTER_NUMBERS:
        value = sum(int(digit) for digit in str(value))
    return value


def _extract_digits(mobile: str) -> List[int]:
    return [int(digit) for digit in str(mobile or "") if digit.isdigit()]


def _digit_frequency(digits: List[int]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for digit in digits:
        counts[digit] = counts.get(digit, 0) + 1
    return counts


def _missing_digits(counts: Dict[int, int]) -> List[int]:
    return [digit for digit in range(1, 10) if counts.get(digit, 0) == 0]


def _present_digits(counts: Dict[int, int]) -> List[int]:
    return [digit for digit in range(1, 10) if counts.get(digit, 0) > 0]


def _repeating_digits(counts: Dict[int, int]) -> List[Dict[str, int]]:
    repeating: List[Dict[str, int]] = []
    for digit, count in counts.items():
        if count > 1:
            repeating.append({"digit": digit, "count": count})
    return repeating


def _compatibility_status(vibration: int, life_path_number: Optional[int]) -> str:
    if not life_path_number:
        return "neutral"
    if vibration == life_path_number:
        return "high"
    if vibration in SUPPORTIVE_ENERGIES.get(life_path_number, []):
        return "supportive"
    if abs(vibration - life_path_number) <= 2:
        return "neutral"
    return "challenging"


def _dominant_digits(digits: List[int]) -> List[int]:
    counts: Dict[int, int] = {}
    for digit in digits:
        counts[digit] = counts.get(digit, 0) + 1

    sorted_digits = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [digit for digit, _count in sorted_digits[:3]]


def analyze_mobile(mobile: str, life_path_number: Optional[int] = None) -> dict:
    if not mobile:
        return {}

    digits = _extract_digits(mobile)
    if not digits:
        return {}

    total = sum(digits)
    vibration = _reduce_number(total)
    status = _compatibility_status(vibration, life_path_number)
    supportive_energies = SUPPORTIVE_ENERGIES.get(life_path_number or vibration, [1, 3, 5])
    dominant_digits = _dominant_digits(digits)
    counts = _digit_frequency(digits)
    present_digits = _present_digits(counts)
    missing_digits = _missing_digits(counts)
    repeating_digits = _repeating_digits(counts)

    correction_suggestion = None
    compatibility_summary = "Mobile vibration gives a steady day-to-day energetic signal."

    if life_path_number:
        compatibility_summary = (
            f"Aapka mobile vibration {vibration} hai aur Life Path {life_path_number} ke saath {status} alignment dikha raha hai. "
            f"Day-to-day communication aur decision energy par iska subtle impact pad sakta hai."
        )
        if status == "challenging":
            energies = ", ".join(str(number) for number in supportive_energies)
            correction_suggestion = (
                f"Number ending {energies} energy aapke liye zyada supportive ho sakti hai. "
                f"Real phone number generate nahi kiya gaya hai, sirf favorable ending energies suggest ki gayi hain."
            )
        elif status == "neutral":
            energies = ", ".join(str(number) for number in supportive_energies[:2])
            correction_suggestion = (
                f"Current vibration neutral hai. Agar future me optimize karna ho, to {energies} ending energies aur supportive ho sakti hain."
            )

    if vibration in (4, 8):
        correction_suggestion = correction_suggestion or (
            "4/8 dominance thoda heavy feel kara sakta hai. 1, 5 ya 6 ending energies zyada fluid support de sakti hain."
        )

    return {
        "digits": digits,
        "digit_frequency": counts,
        "present_digits": present_digits,
        "missing_digits": missing_digits,
        "repeating_digits": repeating_digits,
        "zero_count": counts.get(0, 0),
        "mobile_total": total,
        "mobile_vibration": vibration,
        "mobile_number_vibration": vibration,
        "digit_count": len(digits),
        "dominant_digits": dominant_digits,
        "life_path_number": life_path_number,
        "compatibility_status": status,
        "compatibility_summary": compatibility_summary,
        "supportive_number_energies": supportive_energies,
        "correction_suggestion": correction_suggestion,
    }


# =====================================================
# PUBLIC WRAPPER (STANDARDIZED NAME)
# =====================================================


def analyze_mobile_number(mobile_number: str, life_path_number: Optional[int] = None) -> dict:
    """
    Public contract wrapper used by core_engine.
    """
    return analyze_mobile(mobile_number, life_path_number=life_path_number)

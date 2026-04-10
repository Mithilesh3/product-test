# ==========================================================
# NUMEROLOGY CORE ENGINE (Deterministic Layer)
# ==========================================================

def reduce_to_single_digit(number: int) -> int:
    while number > 9 and number not in [11, 22, 33]:
        number = sum(int(d) for d in str(number))
    return number


def calculate_life_path(date_of_birth: str) -> int:
    """
    Input format: DD/MM/YYYY
    """
    digits = [int(d) for d in date_of_birth if d.isdigit()]
    total = sum(digits)
    return reduce_to_single_digit(total)


def calculate_destiny_number(full_name: str) -> int:
    """
    Simple Pythagorean mapping
    """
    mapping = {
        **dict.fromkeys(list("AJS"), 1),
        **dict.fromkeys(list("BKT"), 2),
        **dict.fromkeys(list("CLU"), 3),
        **dict.fromkeys(list("DMV"), 4),
        **dict.fromkeys(list("ENW"), 5),
        **dict.fromkeys(list("FOX"), 6),
        **dict.fromkeys(list("GPY"), 7),
        **dict.fromkeys(list("HQZ"), 8),
        **dict.fromkeys(list("IR"), 9),
    }

    total = 0
    for char in full_name.upper():
        if char in mapping:
            total += mapping[char]

    return reduce_to_single_digit(total)


def generate_numerology_profile(identity: dict, birth_details: dict):

    dob = birth_details.get("date_of_birth", "")
    name = identity.get("full_name", "")

    return {
        "life_path_number": calculate_life_path(dob),
        "destiny_number": calculate_destiny_number(name),
    }
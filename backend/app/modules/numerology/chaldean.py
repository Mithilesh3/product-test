# modules/numerology/chaldean.py

from typing import Dict

# Commercial Chaldean mapping (Indian market standard)
CHALDEAN_MAP = {
    1: "AIJQY",
    2: "BKR",
    3: "CGLS",
    4: "DMT",
    5: "EHNX",
    6: "UVW",
    7: "OZ",
    8: "FP"
}


def _letter_value(letter: str) -> int:
    letter = letter.upper()
    for number, letters in CHALDEAN_MAP.items():
        if letter in letters:
            return number
    return 0


def calculate_name_number(name: str) -> int:
    if not name:
        return 0

    total = sum(_letter_value(ch) for ch in name if ch.isalpha())

    while total > 9 and total not in (11, 22):
        total = sum(int(d) for d in str(total))

    return total


def calculate_name_compound(name: str) -> int:
    if not name:
        return 0
    return sum(_letter_value(ch) for ch in name if ch.isalpha())

def generate_chaldean_numbers(identity: dict) -> dict:
    name = identity.get("full_name", "")
    number = calculate_name_number(name)
    compound = calculate_name_compound(name)

    return {
        "name_number": number,
        "compound_number": compound,
        "system": "chaldean"
    }

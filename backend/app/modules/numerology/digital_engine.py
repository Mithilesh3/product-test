from __future__ import annotations

from typing import Dict

from app.modules.numerology.chaldean import calculate_name_number


MASTER_NUMBERS = {11, 22, 33}


def _reduce_number(value: int) -> int:
    while value > 9 and value not in MASTER_NUMBERS:
        value = sum(int(char) for char in str(value))
    return value


def _digits_only(text: str) -> str:
    return "".join(char for char in str(text or "") if char.isdigit())


def _clean_token(text: str) -> str:
    # Keep deterministic handle/email local-part signal without punctuation noise.
    return "".join(char for char in str(text or "").lower() if char.isalnum())


def _vibration_from_text(text: str) -> int:
    token = _clean_token(text)
    if not token:
        return 0
    return int(calculate_name_number(token) or 0)


def _mobile_vibration(mobile_number: str) -> int:
    digits = _digits_only(mobile_number)
    if not digits:
        return 0
    return _reduce_number(sum(int(char) for char in digits))


def _profile_signal(vibration: int) -> str:
    signal_map = {
        1: "authority",
        2: "rapport",
        3: "communication",
        4: "structure",
        5: "reach",
        6: "trust",
        7: "depth",
        8: "commercial",
        9: "impact",
        11: "visionary",
        22: "builder",
        33: "service",
    }
    return signal_map.get(vibration, "balanced")


def analyze_digital_presence(
    *,
    email: str | None = None,
    mobile_number: str | None = None,
    social_handle: str | None = None,
    domain_handle: str | None = None,
) -> Dict[str, object]:
    email_local = str(email or "").split("@")[0]
    domain_root = str(domain_handle or "").split(".")[0]

    email_vibration = _vibration_from_text(email_local)
    mobile_vibration = _mobile_vibration(str(mobile_number or ""))
    social_vibration = _vibration_from_text(str(social_handle or ""))
    domain_vibration = _vibration_from_text(domain_root)

    available = [value for value in [email_vibration, mobile_vibration, social_vibration, domain_vibration] if value]
    if not available:
        return {}

    digital_vibration = _reduce_number(sum(available))
    spread = max(available) - min(available) if len(available) > 1 else 0
    consistency_score = max(40, min(100, 100 - (spread * 6)))

    if consistency_score >= 80:
        alignment = "high"
    elif consistency_score >= 60:
        alignment = "moderate"
    else:
        alignment = "volatile"

    return {
        "email_vibration": email_vibration or None,
        "mobile_vibration": mobile_vibration or None,
        "social_handle_vibration": social_vibration or None,
        "domain_vibration": domain_vibration or None,
        "digital_vibration": digital_vibration,
        "profile_signal": _profile_signal(digital_vibration),
        "consistency_score": consistency_score,
        "alignment_band": alignment,
    }

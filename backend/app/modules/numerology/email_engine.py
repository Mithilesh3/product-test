# modules/numerology/email_engine.py

from .chaldean import calculate_name_number


def analyze_email(email: str) -> dict:
    if not email:
        return {}

    local = email.split("@")[0]
    number = calculate_name_number(local)

    return {
        "email_number": number
    }
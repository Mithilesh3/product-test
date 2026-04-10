from datetime import datetime

from app.core.time_utils import UTC

from reportlab.platypus import PageBreak, Spacer


def _safe_int(value, fallback=0):
    try:
        return int(value)
    except Exception:
        return fallback


def _computed_personal_year(data):
    numerology = data.get("numerology_core", {})
    pyth = numerology.get("pythagorean", {})
    life_path = _safe_int(pyth.get("life_path_number", 5), 5)

    year_sum = sum(int(d) for d in str(datetime.now(UTC).year))
    return ((life_path + year_sum - 1) % 9) + 1


def _lucky_numbers(data):
    numerology = data.get("numerology_core", {})
    pyth = numerology.get("pythagorean", {})
    chaldean = numerology.get("chaldean", {})
    email = numerology.get("email_analysis", {})

    candidates = [
        _safe_int(pyth.get("life_path_number"), 0),
        _safe_int(pyth.get("destiny_number"), 0),
        _safe_int(chaldean.get("name_number"), 0),
        _safe_int(email.get("email_number"), 0),
    ]
    unique = sorted({c for c in candidates if c > 0})

    if not unique:
        return [3, 5, 9]

    return unique[:4]


def build_personal_year(elements, renderer, styles, data):
    analysis = data.get("analysis_sections", {})
    strategic = data.get("strategic_guidance", {})

    personal_year = _safe_int(
        data.get("forecast", {}).get("personal_year", 0),
        _computed_personal_year(data),
    )

    forecast_text = analysis.get("personal_year_forecast") or strategic.get(
        "long_term",
        "This cycle favors disciplined expansion, structured partnerships, and long-horizon decisions.",
    )

    lucky = data.get("lucky_numbers")
    if not lucky:
        lucky = _lucky_numbers(data)

    elements.append(renderer.section_banner("व्यक्तिगत वर्ष पूर्वानुमान | Personal Year Forecast"))

    forecast_body = (
        f"<b>Personal Year: {personal_year}</b><br/>"
        f"{forecast_text}"
    )
    elements.append(renderer.insight_box("Year Intelligence", forecast_body, tone="info"))
    elements.append(Spacer(1, 8))

    lucky_text = ", ".join(str(n) for n in lucky)
    elements.append(renderer.insight_box("Lucky Numbers", f"Priority numeric signals: <b>{lucky_text}</b>", tone="success"))

    elements.append(PageBreak())


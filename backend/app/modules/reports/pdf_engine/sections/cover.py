from datetime import datetime

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle


def _fmt_date(raw):
    if not raw:
        return "Not Provided"
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:
        return str(raw)


def _pick_birth_place(data):
    normalized = data.get("input_normalized", {}) if isinstance(data, dict) else {}
    identity = data.get("identity", {}) if isinstance(data, dict) else {}
    birth_details = data.get("birth_details", {}) if isinstance(data, dict) else {}

    if normalized.get("birth_place"):
        return str(normalized.get("birth_place"))

    city = str(birth_details.get("birthplace_city") or "").strip()
    country = str(birth_details.get("birthplace_country") or "").strip()
    if city and country:
        return f"{city}, {country}"
    if city or country:
        return city or country

    return str(identity.get("country_of_residence") or "Not Provided")


def build_cover(elements, styles, name, plan, data):
    identity = data.get("identity", {}) if isinstance(data, dict) else {}
    normalized = data.get("input_normalized", {}) if isinstance(data, dict) else {}
    meta = data.get("meta", {}) if isinstance(data, dict) else {}

    full_name = name or identity.get("full_name") or "User"
    dob = identity.get("date_of_birth") or identity.get("dob") or normalized.get("date_of_birth") or "Not Provided"
    generated_at = _fmt_date(meta.get("generated_at"))
    birth_place = _pick_birth_place(data)
    email = str(identity.get("email") or normalized.get("email") or "Not Provided")
    mobile = str(identity.get("mobile_number") or normalized.get("mobile") or "Not Provided")
    problem = str(data.get("current_problem") or normalized.get("current_problem") or "General Alignment")

    elements.append(Spacer(1, 34))
    elements.append(Paragraph("Life Signify NumAI", styles["CoverTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Strategic Intelligence Report", styles["CoverSubtitle"]))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"{plan.upper()} EDITION", styles["CoverPlan"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Premium Strategic Guidance for Clarity and Growth", styles["CoverAccent"]))

    elements.append(Spacer(1, 16))

    profile_box = Table(
        [
            [Paragraph("<b>Client Identity</b>", styles["CardTitle"])],
            [Paragraph(f"<b>Name:</b> {full_name}", styles["CardBody"])],
            [Paragraph(f"<b>DOB:</b> {dob}", styles["CardBody"])],
            [Paragraph(f"<b>Birth Place:</b> {birth_place}", styles["CardBody"])],
            [Paragraph(f"<b>Email:</b> {email}", styles["CardBody"])],
            [Paragraph(f"<b>Mobile:</b> {mobile}", styles["CardBody"])],
            [Paragraph(f"<b>Current Focus:</b> {problem}", styles["CardBody"])],
            [Paragraph(f"<b>Generated On:</b> {generated_at}", styles["CardBody"])],
        ],
        colWidths=[165 * mm],
    )
    profile_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fffdf8")),
                ("BOX", (0, 0), (-1, -1), 1.2, HexColor("#c9a25b")),
                ("INNERGRID", (0, 1), (-1, -1), 0.35, HexColor("#e8dcc5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(profile_box)

    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Refined interpretation - Clean hierarchy - PDF-friendly presentation", styles["CoverAccent"]))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())


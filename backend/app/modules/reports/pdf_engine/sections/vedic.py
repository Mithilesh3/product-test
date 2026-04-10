import re

from reportlab.platypus import Image, PageBreak, Spacer, Table, TableStyle

from ..assets import DEITIES


DEITY_MAP = {
    "budh": "budh",
    "mercury": "budh",
    "surya": "surya",
    "sun": "surya",
    "chandra": "chandra",
    "moon": "chandra",
    "mangal": "mangal",
    "mars": "mangal",
    "guru": "guru",
    "jupiter": "guru",
    "shukra": "shukra",
    "venus": "shukra",
    "shani": "shani",
    "saturn": "shani",
    "rahu": "rahu",
    "ketu": "ketu",
}


def _deity_key(raw_name):
    cleaned = re.sub(r"[^a-zA-Z ]", " ", (raw_name or "").lower())
    parts = [part for part in cleaned.split() if part]
    for part in parts:
        if part in DEITY_MAP:
            return DEITY_MAP[part]
    return "budh"


def build_vedic(elements, renderer, styles, data):
    section = data.get("vedic_remedy_protocol", {})
    if not section:
        return

    elements.append(renderer.section_banner("वैदिक प्रोटोकॉल | Vedic Remedy Protocol"))

    key = _deity_key(section.get("planetary_alignment", "") + " " + section.get("focus", ""))
    deity_path = DEITIES / f"{key}.png"
    if deity_path.exists():
        img = Image(str(deity_path), width=96, height=96)
        img.hAlign = "CENTER"
        elements.append(img)
        elements.append(Spacer(1, 8))

    table = Table(
        [
            [
                renderer.insight_box("Focus", section.get("focus", ""), tone="neutral", width=renderer.two_col_inner_width),
                renderer.insight_box("Code | Mantra", f"{section.get('code', '')}<br/>{section.get('pronunciation', '')}", tone="info", width=renderer.two_col_inner_width),
            ],
            [
                renderer.insight_box("Parameter | Practice", section.get("parameter", ""), tone="success", width=renderer.two_col_inner_width),
                renderer.insight_box("Output | Donation", section.get("output", ""), tone="neutral", width=renderer.two_col_inner_width),
            ],
        ],
        colWidths=renderer.two_col_widths,
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 8))
    elements.append(renderer.insight_box("Planetary Alignment", section.get("planetary_alignment", ""), tone="neutral"))
    elements.append(Spacer(1, 8))
    elements.append(renderer.insight_box("Purpose", section.get("purpose", ""), tone="info"))

    elements.append(PageBreak())

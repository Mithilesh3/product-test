from reportlab.lib.colors import HexColor
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle


def _row(styles, title, value, meaning):
    return [
        Paragraph(title, styles["BodyText"]),
        Paragraph(str(value), styles["BodyText"]),
        Paragraph(meaning, styles["BodyText"]),
    ]


def build_numerology(elements, renderer, styles, data):
    architecture = data.get("numerology_architecture", {})
    if not architecture:
        return

    elements.append(renderer.section_banner("मूल अंक संरचना | Numerology Architecture"))

    rows = [
        [
            Paragraph("स्तंभ | Structure", styles["TableHeader"]),
            Paragraph("मान | Value", styles["TableHeader"]),
            Paragraph("व्याख्या | Interpretation", styles["TableHeader"]),
        ],
        _row(
            styles,
            "Foundation → Life Path",
            architecture.get("foundation", {}).get("value", "N/A"),
            architecture.get("foundation", {}).get("meaning", ""),
        ),
        _row(
            styles,
            "Left Pillar → Destiny",
            architecture.get("left_pillar", {}).get("value", "N/A"),
            architecture.get("left_pillar", {}).get("meaning", ""),
        ),
        _row(
            styles,
            "Right Pillar → Expression",
            architecture.get("right_pillar", {}).get("value", "N/A"),
            architecture.get("right_pillar", {}).get("meaning", ""),
        ),
        _row(
            styles,
            "Facade → Name Number",
            architecture.get("facade", {}).get("value", "N/A"),
            architecture.get("facade", {}).get("meaning", ""),
        ),
    ]

    table = Table(rows, colWidths=renderer.proportional_widths(1.6, 0.8, 3.2), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1b2f4b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), styles["TableHeader"].fontName),
                ("GRID", (0, 0), (-1, -1), 0.6, HexColor("#d1d8e0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 8))
    elements.append(
        renderer.insight_box(
            "अंतर-क्रिया सार | Interaction Summary",
            architecture.get("interaction_summary", ""),
            tone="neutral",
        )
    )

    elements.append(PageBreak())

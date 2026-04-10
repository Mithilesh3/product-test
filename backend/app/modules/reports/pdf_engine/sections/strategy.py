from reportlab.lib.colors import HexColor
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle


def build_strategy(elements, renderer, styles, data):
    section = data.get("structural_deficit_model", {})
    if not section:
        return

    elements.append(renderer.section_banner("संरचनात्मक कमी मॉडल | Structural Deficit Model"))

    rows = [
        [
            Paragraph("मॉडल | Model", styles["TableHeader"]),
            Paragraph("व्याख्या | Interpretation", styles["TableHeader"]),
        ],
        [Paragraph("Structural Deficit", styles["BodyText"]), Paragraph(section.get("structural_deficit", ""), styles["BodyText"])],
        [Paragraph("Behavioral Symptom", styles["BodyText"]), Paragraph(section.get("behavioral_symptom", ""), styles["BodyText"])],
        [Paragraph("Engineered Patch", styles["BodyText"]), Paragraph(section.get("engineered_patch", ""), styles["BodyText"])],
    ]

    table = Table(rows, colWidths=renderer.proportional_widths(1.3, 3.7), repeatRows=1)
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
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 8))
    elements.append(renderer.insight_box("Rationale", section.get("rationale", ""), tone="neutral"))

    elements.append(PageBreak())

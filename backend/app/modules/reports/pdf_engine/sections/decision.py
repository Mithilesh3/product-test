from reportlab.lib.colors import HexColor
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle


def build_decision(elements, renderer, styles, data):
    analysis = data.get("analysis_sections", {})
    text = analysis.get("decision_profile")

    if not text:
        return

    elements.append(renderer.section_banner("निर्णय स्पष्टता | Decision Intelligence"))

    elements.append(renderer.insight_box("निर्णय व्याख्या | Decision Interpretation", text, tone="info"))
    elements.append(Spacer(1, 8))

    framework_rows = [
        ["रणनीतिक मेल | Strategic Fit", "Long-term mission के साथ alignment"],
        ["वित्तीय स्थिरता | Financial Sustainability", "Resource viability और runway"],
        ["दीर्घकालिक प्रभाव | Long-term Impact", "Short-term gains से आगे टिकाऊ असर"],
        ["भावनात्मक संतुलन | Emotional Alignment", "Pressure में cognitive clarity"],
    ]

    rows = [
        [
            Paragraph("फ्रेमवर्क | Decision Framework", styles["TableHeader"]),
            Paragraph("रणनीतिक दृष्टि | Strategic Lens", styles["TableHeader"]),
        ]
    ]
    for left, right in framework_rows:
        rows.append([Paragraph(left, styles["BodyText"]), Paragraph(right, styles["BodyText"])])

    table = Table(rows, colWidths=renderer.proportional_widths(1.45, 3.35), repeatRows=1)
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

    elements.append(PageBreak())

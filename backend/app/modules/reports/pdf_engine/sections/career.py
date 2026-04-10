from reportlab.platypus import PageBreak, Spacer, Table, TableStyle


def _career_risk_text(data):
    analysis = data.get("analysis_sections", {})
    explicit = analysis.get("career_risk") or analysis.get("career_risk_areas")
    if explicit:
        return explicit

    metrics = data.get("core_metrics", {})
    low = []
    if int(metrics.get("financial_discipline_index", 50) or 50) < 55:
        low.append("financial execution rhythm में कमजोरी")
    if int(metrics.get("emotional_regulation_index", 50) or 50) < 55:
        low.append("decision stress reactivity")

    if low:
        return (
            "Career momentum धीमा हो सकता है जब "
            + " and ".join(low)
            + ". Strategic consistency बनाए रखने के लिए weekly planning और review checkpoints जोड़ें।"
        )

    return "Risk moderate है। Drift से बचने के लिए disciplined planning और milestone review बनाए रखें।"


def build_career(elements, renderer, styles, data):
    analysis = data.get("analysis_sections", {})
    text = analysis.get("career_analysis")

    if not text:
        return

    elements.append(renderer.section_banner("करियर एवं धन विश्लेषण | Career & Money Intelligence"))

    industries = data.get("business_block", {}).get("compatible_industries", [])
    if not industries:
        industries = ["Consulting", "Education", "Advisory Services"]

    sectors_text = "<br/>".join([f"- {i}" for i in industries])

    two_col = Table(
        [
            [
                renderer.insight_box("करियर ताकत | Career Strengths", text, tone="info", width=renderer.two_col_inner_width),
                renderer.insight_box("अनुकूल क्षेत्र | Recommended Industries", sectors_text, tone="neutral", width=renderer.two_col_inner_width),
            ]
        ],
        colWidths=renderer.two_col_widths,
    )
    two_col.setStyle(
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

    elements.append(two_col)
    elements.append(Spacer(1, 8))

    elements.append(renderer.insight_box("करियर जोखिम | Career Risk Areas", _career_risk_text(data), tone="risk"))

    elements.append(PageBreak())

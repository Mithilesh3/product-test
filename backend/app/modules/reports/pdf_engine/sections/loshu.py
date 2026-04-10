from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from ..blocks.loshu_grid import build_loshu_grid


def build_loshu(elements, renderer, data):
    numerology = data.get("numerology_core", {})
    section = data.get("loshu_diagnostic", {})
    loshu = numerology.get("loshu_grid", {})
    grid_counts = loshu.get("grid_counts")
    if not grid_counts:
        return

    elements.append(renderer.section_banner("लो शु निदान | Lo Shu Diagnostic"))
    elements.append(build_loshu_grid(renderer.styles, grid_counts))
    elements.append(Spacer(1, 8))

    present = ", ".join(str(value) for value in section.get("present_numbers", [])) or "None"
    missing = ", ".join(str(value) for value in section.get("missing_numbers", [])) or "None"
    center = "Present" if section.get("center_presence") else "Missing"

    cards = Table(
        [
            [
                renderer.insight_box("Present Numbers", present, tone="success", width=renderer.two_col_inner_width),
                renderer.insight_box("Missing Numbers", missing, tone="risk", width=renderer.two_col_inner_width),
            ],
        ],
        colWidths=renderer.two_col_widths,
    )
    cards.setStyle(
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
    elements.append(cards)
    elements.append(Spacer(1, 8))

    meanings = "<br/>".join(f"- {item}" for item in section.get("missing_number_meanings", []))
    combined = f"Center Presence: {center}<br/>{section.get('energy_imbalance', '')}"
    if meanings:
        combined += f"<br/>{meanings}"
    combined += f"<br/>{section.get('narrative', '')}"
    elements.append(renderer.insight_box("Lo Shu Interpretation", combined, tone="info"))
    elements.append(PageBreak())

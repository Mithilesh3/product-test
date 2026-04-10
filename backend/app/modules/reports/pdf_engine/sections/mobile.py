from reportlab.platypus import PageBreak, Spacer, Table, TableStyle


def build_mobile(elements, renderer, styles, data):
    section = data.get("environment_alignment", {})
    if not section:
        return

    elements.append(renderer.section_banner("पर्यावरण संरेखण | Environment Alignment"))

    cards = Table(
        [
            [
                renderer.insight_box("Physical Space", section.get("physical_space", ""), tone="neutral", width=renderer.two_col_inner_width),
                renderer.insight_box("Color Alignment", section.get("color_alignment", ""), tone="info", width=renderer.two_col_inner_width),
            ],
            [
                renderer.insight_box("Mobile Number Analysis", section.get("mobile_number_analysis", ""), tone="success", width=renderer.full_width - 4),
                "",
            ],
        ],
        colWidths=renderer.two_col_widths,
    )
    cards.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 1), (1, 1)),
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
    elements.append(renderer.insight_box("Digital Behavior", section.get("digital_behavior", ""), tone="neutral"))
    elements.append(Spacer(1, 8))
    elements.append(renderer.insight_box("Environment Narrative", section.get("narrative", ""), tone="info"))

    elements.append(PageBreak())

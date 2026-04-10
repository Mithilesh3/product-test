from reportlab.platypus import PageBreak, Spacer, Table, TableStyle


def build_planetary(elements, renderer, styles, data):
    section = data.get("planetary_mapping", {})
    if not section:
        return

    elements.append(renderer.section_banner("ग्रह मानचित्रण | Planetary Mapping"))

    cards = Table(
        [
            [
                renderer.insight_box("Background Forces", section.get("background_forces", ""), tone="neutral", width=renderer.two_col_inner_width),
                renderer.insight_box("Primary Intervention Planet", section.get("primary_intervention_planet", ""), tone="info", width=renderer.two_col_inner_width),
            ],
            [
                renderer.insight_box("Calibration Cluster", section.get("calibration_cluster", ""), tone="success", width=renderer.full_width - 4),
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
    elements.append(renderer.insight_box("Planetary Interpretation", section.get("narrative", ""), tone="neutral"))

    elements.append(PageBreak())

from reportlab.platypus import PageBreak, Spacer, Table, TableStyle


def build_lifestyle(elements, renderer, styles, data):
    section = data.get("circadian_alignment", {})
    if not section:
        return

    elements.append(renderer.section_banner("दैनिक लय संरेखण | Circadian Alignment"))

    schedule = Table(
        [
            [
                renderer.insight_box("Morning Routine", section.get("morning_routine", ""), tone="success", width=renderer.two_col_inner_width),
                renderer.insight_box("Work Alignment", section.get("work_alignment", ""), tone="info", width=renderer.two_col_inner_width),
            ],
            [
                renderer.insight_box("Evening Shutdown", section.get("evening_shutdown", ""), tone="neutral", width=renderer.full_width - 4),
                "",
            ],
        ],
        colWidths=renderer.two_col_widths,
    )
    schedule.setStyle(
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

    elements.append(schedule)
    elements.append(Spacer(1, 8))
    elements.append(renderer.insight_box("Circadian Narrative", section.get("narrative", ""), tone="neutral"))
    elements.append(PageBreak())

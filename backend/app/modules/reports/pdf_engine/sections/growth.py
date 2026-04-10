from reportlab.platypus import PageBreak, Spacer, Table, TableStyle


def build_growth(elements, renderer, styles, data):
    section = data.get("execution_plan", {})
    if not section:
        return

    elements.append(renderer.section_banner("21-दिवसीय क्रियान्वयन योजना | 21-Day Execution Plan"))

    cards = [
        renderer.insight_box("Install Rhythm", section.get("install_rhythm", ""), tone="neutral"),
        renderer.insight_box("Deploy Anchor", section.get("deploy_anchor", ""), tone="info"),
        renderer.insight_box("Run Protocol", section.get("run_protocol", ""), tone="success"),
    ]

    grid = Table([cards], colWidths=renderer.three_col_widths)
    grid.setStyle(
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
    elements.append(grid)
    elements.append(Spacer(1, 8))

    checkpoints = "<br/>".join(f"- {item}" for item in section.get("checkpoints", []))
    if checkpoints:
        elements.append(renderer.insight_box("Weekly Checkpoints", checkpoints, tone="neutral"))
        elements.append(Spacer(1, 8))

    elements.append(renderer.insight_box("Execution Summary", section.get("summary", ""), tone="info"))
    elements.append(PageBreak())

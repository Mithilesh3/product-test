from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from ..assets import OM_SYMBOL


def _clip(text, limit):
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def build_executive(elements, renderer, styles, data):
    insight = data.get("primary_insight", {})
    if not insight:
        return

    elements.append(renderer.section_banner("मुख्य अंतर्दृष्टि | Primary Insight"))

    headline = (
        f"<b>Core Archetype:</b> {insight.get('core_archetype', 'Strategic Pattern')}<br/>"
        f"{_clip(insight.get('narrative', ''), 360)}"
    )
    elements.append(renderer.icon_block(OM_SYMBOL, "जीवन का केंद्रीय संकेत | Core Signal", headline))
    elements.append(Spacer(1, 8))

    overview = Table(
        [
            [
                renderer.insight_box("ताकत | Strength", _clip(insight.get("strength", ""), 180), tone="success", width=renderer.two_col_inner_width),
                renderer.insight_box("मुख्य कमी | Critical Deficit", _clip(insight.get("critical_deficit", ""), 180), tone="risk", width=renderer.two_col_inner_width),
            ],
            [
                renderer.insight_box("स्थिरता जोखिम | Stability Risk", _clip(insight.get("stability_risk", ""), 220), tone="neutral", width=renderer.full_width - 4),
                "",
            ],
        ],
        colWidths=renderer.two_col_widths,
    )
    overview.setStyle(
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
    elements.append(overview)
    elements.append(Spacer(1, 8))
    elements.append(
        renderer.bullet_block(
            "Audit Roadmap",
            [
                _clip(insight.get("phase_1_diagnostic", ""), 150),
                _clip(insight.get("phase_2_blueprint", ""), 150),
                _clip(insight.get("phase_3_intervention_protocol", ""), 150),
            ],
        )
    )

    elements.append(PageBreak())

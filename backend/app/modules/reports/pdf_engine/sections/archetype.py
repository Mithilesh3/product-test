from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from ..assets import CHAKRA_ICON


def build_archetype(elements, renderer, styles, data):
    section = data.get("archetype_intelligence", {})
    primary = data.get("primary_insight", {})
    if not section:
        return

    elements.append(renderer.section_banner("आर्केटाइप इंटेलिजेंस | Archetype Intelligence"))

    elements.append(
        renderer.icon_block(
            CHAKRA_ICON,
            "आर्केटाइप सिग्नेचर | Archetype Signature",
            f"<b>{primary.get('core_archetype', 'Strategic Pattern')}</b><br/>{section.get('signature', '')}",
        )
    )
    elements.append(Spacer(1, 8))

    leadership_traits = "<br/>".join(f"- {item}" for item in section.get("leadership_traits", []))
    cards = Table(
        [
            [
                renderer.insight_box("नेतृत्व संकेत | Leadership Traits", leadership_traits, tone="success", width=renderer.two_col_inner_width),
                renderer.insight_box("छाया पक्ष | Shadow Traits", section.get("shadow_traits", ""), tone="risk", width=renderer.two_col_inner_width),
            ],
            [
                renderer.insight_box("विकास पथ | Growth Path", section.get("growth_path", ""), tone="neutral", width=renderer.full_width - 4),
                "",
            ]
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
    elements.append(PageBreak())

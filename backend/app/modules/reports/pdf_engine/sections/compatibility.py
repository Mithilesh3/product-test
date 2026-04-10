from reportlab.platypus import PageBreak, Spacer


def build_compatibility(elements, renderer, styles, data):
    comp = data.get("compatibility_block", {})

    if not comp:
        return

    elements.append(renderer.section_banner("संबंध अनुकूलता | Compatibility Intelligence"))

    good = [str(n) for n in comp.get("compatible_numbers", [])]
    tough = [str(n) for n in comp.get("challenging_numbers", [])]

    elements.append(renderer.bullet_block("Compatible Numbers", good))
    elements.append(Spacer(1, 8))
    elements.append(renderer.bullet_block("Challenging Numbers", tough))
    elements.append(Spacer(1, 8))

    guidance = comp.get("relationship_guidance", "Use compatibility insights for strategic collaboration choices.")
    elements.append(renderer.insight_box("Relationship Guidance", guidance, tone="neutral"))

    elements.append(PageBreak())

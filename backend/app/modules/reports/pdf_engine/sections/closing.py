from reportlab.platypus import Spacer


def build_closing(elements, renderer, styles, data):
    elements.append(renderer.section_banner("समापन सार | Closing Synthesis"))
    elements.append(Spacer(1, 10))

    closing_text = (
        "Your strategic intelligence profile shows high adaptability with clear growth leverage. "
        "Stabilize core routines, align decisions with long-term value, and execute in phased expansion cycles."
    )
    elements.append(renderer.insight_box("Final Advisory", closing_text, tone="info"))

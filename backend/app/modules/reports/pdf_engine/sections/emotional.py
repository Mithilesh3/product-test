from reportlab.platypus import PageBreak, Spacer


def build_emotional(elements, renderer, styles, data):
    analysis = data.get("analysis_sections", {})
    text = analysis.get("emotional_analysis")

    if not text or not str(text).strip():
        return

    elements.append(renderer.section_banner("भावनात्मक संतुलन | Emotional Intelligence"))

    elements.append(renderer.insight_box("Emotional Profile", text, tone="info"))
    elements.append(Spacer(1, 8))

    triggers = [
        "Decision overload",
        "Financial uncertainty",
        "Unstructured commitments",
    ]
    elements.append(renderer.bullet_block("Stress Triggers", triggers))
    elements.append(Spacer(1, 8))

    resilience = [
        data.get("lifestyle_remedies", {}).get("meditation", "10-minute daily centering"),
        data.get("lifestyle_remedies", {}).get("daily_routine", "Consistent morning structure"),
        "Weekly reflection and reset discipline",
    ]
    elements.append(renderer.bullet_block("Resilience Practices", resilience))
    elements.append(Spacer(1, 8))

    advice = data.get("executive_brief", {}).get(
        "strategic_focus", "Use structured routines to regulate emotion-driven decisions."
    )
    elements.append(renderer.insight_box("Regulation Advice", advice, tone="neutral"))

    elements.append(PageBreak())

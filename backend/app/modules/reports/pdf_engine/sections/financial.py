from reportlab.platypus import PageBreak, Spacer


def build_financial(elements, renderer, styles, data):
    analysis = data.get("analysis_sections", {})
    text = analysis.get("financial_analysis")

    if not text or not str(text).strip():
        return

    elements.append(renderer.section_banner("वित्तीय विश्लेषण | Financial Intelligence"))

    elements.append(renderer.insight_box("वित्तीय पठन | Financial Reading", text, tone="info"))
    elements.append(Spacer(1, 8))

    actions = [
        "Monthly budget discipline checkpoints सेट करें",
        "Cash flow को weekly variance alerts के साथ track करें",
        "Strategic capital को long-term compounding की तरफ allocate करें",
    ]
    elements.append(renderer.bullet_block("व्यावहारिक धन मार्गदर्शन | Actionable Financial Guidance", actions))
    elements.append(Spacer(1, 8))

    score = data.get("core_metrics", {}).get("financial_discipline_index", 0)
    explanation = (
        f"Financial Stability Score: <b>{score}</b>. "
        "Higher score savings, controls, और investment governance में consistent execution को indicate करता है।"
    )
    elements.append(renderer.insight_box("स्कोर व्याख्या | Score Interpretation", explanation, tone="neutral"))

    elements.append(PageBreak())

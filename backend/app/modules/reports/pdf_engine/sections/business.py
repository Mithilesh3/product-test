from reportlab.platypus import PageBreak, Spacer


def build_business(elements, renderer, styles, data):
    business = data.get("business_block", {})

    if not business:
        return

    elements.append(renderer.section_banner("व्यवसाय संकेत | Business Intelligence"))

    strength = business.get("business_strength", "Business strength का स्पष्ट संकेत उपलब्ध नहीं है।")
    risk = business.get("risk_factor", "Business risk का स्पष्ट संकेत उपलब्ध नहीं है।")

    elements.append(renderer.two_column_cards("व्यवसाय ताकत | Business Strength", strength, "व्यवसाय जोखिम | Business Risk", risk))
    elements.append(Spacer(1, 8))

    industries = business.get("compatible_industries", [])
    if industries:
        formatted = [str(item).replace("_", " ").title() for item in industries]
        elements.append(renderer.bullet_block("अनुकूल क्षेत्र | Recommended Business Verticals", formatted))

    elements.append(PageBreak())

from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from ..blocks.radar_chart import radar_chart


def _pick(metrics, key, default=0):
    value = metrics.get(key, default)
    try:
        return int(value)
    except Exception:
        return default


def build_metrics(elements, renderer, styles, data):
    metrics = data.get("core_metrics", {})
    metric_explanations = data.get("metric_explanations", {})
    if not metrics:
        return

    elements.append(renderer.section_banner("बुद्धि संकेतक | Intelligence Metrics"))

    confidence = _pick(metrics, "confidence_score")
    karma_pressure = _pick(metrics, "karma_pressure_index")
    life_stability = _pick(metrics, "life_stability_index")
    dharma_alignment = _pick(metrics, "dharma_alignment_score")
    emotional_regulation = _pick(metrics, "emotional_regulation_index")
    financial_discipline = _pick(metrics, "financial_discipline_index")

    metric_pairs = [
        ("निर्णय स्पष्टता | Decision Clarity", confidence),
        ("कर्म दबाव | Karma Pressure", karma_pressure),
        ("जीवन स्थिरता | Life Stability", life_stability),
        ("धर्म संतुलन | Dharma Alignment", dharma_alignment),
        ("भावनात्मक संतुलन | Emotional Regulation", emotional_regulation),
        ("वित्तीय अनुशासन | Financial Discipline", financial_discipline),
    ]

    elements.append(renderer.metric_grid(metric_pairs))
    elements.append(Spacer(1, 8))

    radar_data = data.get("radar_chart_data") or {
        "Life Stability": life_stability,
        "Decision Clarity": confidence,
        "Dharma Alignment": dharma_alignment,
        "Emotional Regulation": emotional_regulation,
        "Financial Discipline": financial_discipline,
        "Karma Pressure": karma_pressure,
    }
    elements.append(radar_chart(radar_data, styles, renderer.full_width))
    elements.append(Spacer(1, 8))

    summary = f"Risk Band: <b>{metrics.get('risk_band', 'Not Classified')}</b>"
    if confidence <= 25:
        summary += "<br/>यह report limited behavioral intake पर आधारित है, इसलिए कुछ scores directional संकेत की तरह पढ़े जाने चाहिए।"
    weakest_key = min(metric_explanations, key=lambda key: metric_explanations[key].get("score", 50)) if metric_explanations else None
    confidence_detail = metric_explanations.get("confidence_score", {})
    weakest_detail = metric_explanations.get(weakest_key, {}) if weakest_key else {}
    combined = (
        f"{summary}<br/>"
        f"<b>{weakest_detail.get('label', 'Weakest Metric')}</b>: {weakest_detail.get('driver', '')} "
        f"{weakest_detail.get('improvement', '')}<br/>"
        f"<b>Confidence Explanation</b>: {confidence_detail.get('driver', '')} {confidence_detail.get('risk', '')}"
    )
    elements.append(renderer.insight_box("Metric Interpretation", combined, tone="neutral"))

    elements.append(PageBreak())

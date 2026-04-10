from __future__ import annotations

from typing import Dict

METRIC_LABELS: Dict[str, str] = {
    "dharma_alignment_score": "धर्म संतुलन",
    "financial_discipline_index": "वित्तीय अनुशासन",
    "confidence_score": "आत्मविश्वास",
    "life_stability_index": "जीवन स्थिरता",
    "emotional_regulation_index": "भावनात्मक संतुलन",
    "karma_pressure_index": "कर्म दबाव",
    "data_completeness_score": "डेटा पूर्णता",
    "weakest_metric_score": "सबसे कमजोर संकेतक स्कोर",
    "strongest_metric_score": "सबसे मजबूत संकेतक स्कोर",
}


def to_metric_label(metric_key: str) -> str:
    key = str(metric_key or "").strip()
    if not key:
        return "Metric"
    if key in METRIC_LABELS:
        return METRIC_LABELS[key]
    return key.replace("_", " ").title().replace("  ", " ")

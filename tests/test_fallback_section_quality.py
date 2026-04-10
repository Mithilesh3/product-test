from pathlib import Path
import re
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _DummyAzureOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=self._create),
            )

        def _create(self, *args, **kwargs):
            raise RuntimeError("Azure OpenAI client should not be called in this test.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.modules.reports.fallback_templates import SECTION_METRICS, build_fallback_section


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
INTERNAL_KEYS = (
    "confidence_score",
    "dharma_alignment_score",
    "financial_discipline_index",
    "life_stability_index",
)


def _sample_input() -> dict:
    return {
        "fullName": "Rahul Sharma",
        "focusArea": "general_alignment",
        "currentProblem": "Career decisions are inconsistent",
        "industry": "Technology",
        "occupation": "Engineer",
        "relationshipStatus": "single",
        "workMode": "job",
        "incomeRangeMonthly": 85000,
        "debtRange": 20,
        "stressLevel": 6,
        "goals": ["career growth", "savings stability"],
        "challenges": ["overthink", "discipline"],
    }


def _sample_numbers() -> dict:
    return {
        "pythagorean": {"life_path_number": 5, "destiny_number": 8, "expression_number": 3},
        "chaldean": {"name_number": 6},
        "mobile_analysis": {"mobile_vibration": 5, "compatibility_status": "neutral"},
        "loshu_grid": {"missing_numbers": [4, 7], "grid_counts": {"1": 2, "5": 1, "8": 2}},
    }


def _sample_scores() -> dict:
    return {
        "strongest_metric": "confidence_score",
        "weakest_metric": "karma_pressure_index",
        "risk_band": "सुधार योग्य",
        "confidence_score": 72,
        "life_stability_index": 64,
        "dharma_alignment_score": 61,
        "emotional_regulation_index": 57,
        "financial_discipline_index": 59,
        "karma_pressure_index": 48,
    }


def test_fallback_sections_are_hindi_and_customer_safe():
    for section_key in SECTION_METRICS:
        section = build_fallback_section(
            section_key=section_key,
            plan="enterprise",
            normalized_input=_sample_input(),
            numerology_values=_sample_numbers(),
            derived_scores=_sample_scores(),
        )
        assert DEVANAGARI_RE.search(section["summary"])
        assert DEVANAGARI_RE.search(section["keyStrength"])
        assert DEVANAGARI_RE.search(section["keyRisk"])
        assert DEVANAGARI_RE.search(section["practicalGuidance"])

        joined_text = " ".join(
            [
                section["summary"],
                section["keyStrength"],
                section["keyRisk"],
                section["practicalGuidance"],
            ]
        ).lower()
        assert all(internal_key not in joined_text for internal_key in INTERNAL_KEYS)

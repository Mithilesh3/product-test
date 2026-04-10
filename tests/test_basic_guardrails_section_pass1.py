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

from app.modules.reports.azure_report_client import _clean_text
from app.modules.reports.narrative_quality import evaluate_deterministic_alignment
from app.modules.reports.report_assembler import (
    _basic_compatibility_label_v2,
    _basic_dynamic_dnd_windows,
    _basic_positive_impact_rows,
    _basic_primary_rudraksha,
    _basic_verdict_v2,
)


def _make_core(challenge: str) -> dict:
    return {
        "inputs": {"primary_challenge": challenge},
        "lo_shu": {"present": [1, 2, 5], "missing": [3, 4], "repeating": [{"digit": 8, "count": 3}]},
        "planet": {"energy": ["à¤Šà¤°à¥à¤œà¤¾", "à¤¨à¥‡à¤¤à¥ƒà¤¤à¥à¤µ"]},
    }


def test_compatibility_reduces_one_level_when_missing_4():
    high = _basic_compatibility_label_v2(9, 5, missing_digits=[], repeating_digits=[])
    reduced = _basic_compatibility_label_v2(9, 5, missing_digits=[4], repeating_digits=[])
    assert high["level"] == "HIGH"
    assert reduced["level"] == "MODERATE"


def test_verdict_logic_matches_rule_set():
    assert _basic_verdict_v2(compatibility_level="LOW", missing_digits=[], repeating_digits=[]) == "CHANGE"
    assert _basic_verdict_v2(compatibility_level="HIGH", missing_digits=[4, 7], repeating_digits=[]) == "CHANGE"
    assert _basic_verdict_v2(compatibility_level="HIGH", missing_digits=[4], repeating_digits=[]) == "MANAGE"
    assert _basic_verdict_v2(compatibility_level="MODERATE", missing_digits=[], repeating_digits=[]) == "MANAGE"
    # Repeating 8 alone should not force MANAGE under the new rule.
    assert _basic_verdict_v2(
        compatibility_level="HIGH",
        missing_digits=[],
        repeating_digits=[{"digit": 8, "count": 3}],
    ) == "KEEP"


def test_primary_rudraksha_uses_first_missing_digit_mapping():
    assert _basic_primary_rudraksha([4, 1, 3]).startswith("4 ")
    assert _basic_primary_rudraksha([1, 4]).startswith("1 ")
    assert _basic_primary_rudraksha([]).startswith("5 ")


def test_dynamic_dnd_times_are_deterministic_and_profile_conditioned():
    morning_a, evening_a = _basic_dynamic_dnd_windows(
        full_name="Jay Prakash Vishvakarma",
        city="Jaunpur",
        mobile_number="8817659208",
    )
    morning_b, evening_b = _basic_dynamic_dnd_windows(
        full_name="Jay Prakash Vishvakarma",
        city="Jaunpur",
        mobile_number="8817659208",
    )
    morning_c, evening_c = _basic_dynamic_dnd_windows(
        full_name="Preeti Sharma",
        city="Lucknow",
        mobile_number="9794635665",
    )

    assert (morning_a, evening_a) == (morning_b, evening_b)
    assert (morning_a, evening_a) != (morning_c, evening_c)
    assert re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}\s(?:AM|PM)", morning_a)
    assert re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}\s(?:AM|PM)", evening_a)


def test_positive_impact_is_challenge_conditioned():
    finance_rows = _basic_positive_impact_rows(core=_make_core("Debt & Loans"))
    career_rows = _basic_positive_impact_rows(core=_make_core("Career Growth"))
    finance_text = " ".join(f"{row['effect']} {row['impact']}" for row in finance_rows)
    career_text = " ".join(f"{row['effect']} {row['impact']}" for row in career_rows)
    assert "debt" in finance_text.lower() or "cashflow" in finance_text.lower()
    assert "execution" in career_text.lower() or "career" in career_text.lower()


def test_azure_text_cleaner_repairs_common_mojibake():
    cleaned = _clean_text("Ã Â¤Â¸Ã Â¤Â¤Ã Â¤Â¤Ã Â¤Â¾")
    assert "Ã Â¤" not in cleaned


def test_deterministic_alignment_flags_missing_fact_usage():
    ai_payload = {
        "deterministicBasicCore": {
            "inputs": {"primary_challenge": "Career Growth"},
            "mobile": {"vibration": 9},
            "life_path": {"value": 5},
            "lo_shu": {"missing": [3, 4]},
            "compatibility": {"english": "Moderate", "text": "à¤®à¤§à¥à¤¯à¤®"},
        }
    }
    sections = [
        {
            "sectionKey": "mobile_numerology",
            "summary": "General line only",
            "keyStrength": "No concrete data",
            "keyRisk": "No challenge mention",
            "practicalGuidance": "Keep doing your best",
        }
    ]
    quality = evaluate_deterministic_alignment(sections=sections, ai_payload=ai_payload)
    assert quality["rewriteRecommended"] is True
    assert "mobile_numerology" in quality["weakSectionKeys"]


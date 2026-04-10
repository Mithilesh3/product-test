from pathlib import Path
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
            raise RuntimeError("Azure OpenAI should not be called in this test.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.modules.reports.report_assembler import (  # noqa: E402
    _basic_footer_payload,
    _basic_next_steps_payload,
    _basic_remedies_payload,
    _basic_tracker_payload,
)


def _core(challenge: str = "Debt & Loans") -> dict:
    return {
        "inputs": {
            "first_name": "Jay",
            "full_name": "Jay Prakash Vishvakarma",
            "primary_challenge": challenge,
            "willingness_to_change": "undecided",
        },
        "lo_shu": {
            "missing": [1, 3, 4],
            "present": [2, 5, 6, 7, 8, 9],
            "repeating": [{"digit": 8, "count": 3}],
        },
        "mantra": "ॐ मंगलाय नमः",
        "gemstone": {"name": "मूंगा (Coral)"},
        "cover_color": "लाल या गहरा लाल",
        "wallpaper_theme": "सूर्योदय की तस्वीर",
        "yantra": "मंगल यंत्र",
        "primary_rudraksha": "4 मुखी रुद्राक्ष",
        "dnd_morning": "7:00-8:30 AM",
        "dnd_evening": "7:00-9:00 PM",
        "nickname_base": "Jay Leader 4",
        "contact_prefix_digit": 4,
        "app_folder_limit": 4,
        "affirmation_base": "स्थिरता, अनुशासन, सफलता",
        "charging": {
            "direction": "पूर्व (East)",
            "day": "मंगलवार",
            "time": "सूर्योदय",
            "method": "लाल वस्तु के पास रखें",
        },
        "generated_on": "26 March 2026",
        "uniqueness_seed": "seed-alpha",
    }


def test_section9_remedies_payload_is_seeded_and_deterministic():
    core = _core()
    ai_line = "आपका फोकस अनुशासन और consistency पर रखें। अगले 21 दिन निर्णायक हैं।"
    one = _basic_remedies_payload(
        core=core,
        uniqueness_seed="seed-a",
        remedy_lines={"spiritual": "A", "physical": "B", "digital": "C"},
        ai_narrative=ai_line,
    )
    two = _basic_remedies_payload(
        core=core,
        uniqueness_seed="seed-a",
        remedy_lines={"spiritual": "A", "physical": "B", "digital": "C"},
        ai_narrative=ai_line,
    )
    three = _basic_remedies_payload(
        core=core,
        uniqueness_seed="seed-b",
        remedy_lines={"spiritual": "A", "physical": "B", "digital": "C"},
        ai_narrative=ai_line,
    )

    assert one["intro"]
    assert one["comment"]
    assert one == two
    assert one["intro"] != three["intro"] or one["comment"] != three["comment"]


def test_section10_tracker_payload_is_three_rows_with_note():
    payload = _basic_tracker_payload(
        core=_core("Career Growth"),
        uniqueness_seed="seed-career",
        ai_narrative="Execution rhythm स्थिर करें और weekly review lock रखें।",
    )
    assert len(payload["rows"]) == 3
    assert payload["rows"][2]["week"].startswith("सप्ताह 3")
    assert "|" in payload["rows"][2]["task"]


def test_section13_and_14_are_personalized_and_non_empty():
    core = _core("Career Growth")
    next_steps = _basic_next_steps_payload(
        core=core,
        uniqueness_seed="seed-next",
        ai_narrative="Career execution को measurable cadence में बदलें।",
    )
    footer = _basic_footer_payload(
        core=core,
        uniqueness_seed="seed-footer",
        ai_narrative="आपकी consistency ही आपका growth multiplier है।",
    )

    assert "Jay" in next_steps["thanks"]
    assert len(next_steps["options"]) == 3
    assert next_steps["context"]
    assert next_steps["closing"]

    assert "Jay Prakash Vishvakarma" in footer["generated_for_line"]
    assert footer["gratitude_line"]
    assert footer["tagline_line"]

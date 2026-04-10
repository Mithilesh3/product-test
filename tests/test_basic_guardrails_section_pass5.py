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
)


def _core(willingness: str = "undecided") -> dict:
    return {
        "inputs": {
            "first_name": "Jay",
            "full_name": "Jay Prakash Vishvakarma",
            "primary_challenge": "Debt & Loans",
            "willingness_to_change": willingness,
            "city": "Jaunpur",
        },
        "mobile": {"vibration": 9},
        "life_path": {"value": 5},
        "lo_shu": {"missing": [1, 3, 4]},
        "verdict": "CHANGE",
        "generated_on": "26 March 2026",
        "uniqueness_seed": "seed-pass5",
    }


def test_section13_next_steps_is_seed_stable_and_varies_by_seed():
    ai_line = "Next-step strategy à¤•à¥‹ challenge-specific measurable execution à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¥‡à¤‚à¥¤"
    one = _basic_next_steps_payload(core=_core("undecided"), uniqueness_seed="seed-a", ai_narrative=ai_line)
    two = _basic_next_steps_payload(core=_core("undecided"), uniqueness_seed="seed-a", ai_narrative=ai_line)
    three = _basic_next_steps_payload(core=_core("undecided"), uniqueness_seed="seed-b", ai_narrative=ai_line)

    assert one == two
    assert len(one["rows"]) == 2
    assert len(one["options"]) == 3
    assert one["context"].strip()
    assert one["closing"].strip()
    assert one["thanks"].strip()
    assert one["context"] != three["context"] or one["closing"] != three["closing"] or one["thanks"] != three["thanks"]


def test_section13_next_steps_respects_willingness_ordering():
    no_payload = _basic_next_steps_payload(core=_core("no"), uniqueness_seed="seed-no", ai_narrative="")
    yes_payload = _basic_next_steps_payload(core=_core("yes"), uniqueness_seed="seed-yes", ai_narrative="")

    assert "à¤¸à¤‚à¤­à¤¾à¤²à¥‡à¤‚" in no_payload["options"][0] or "manage" in no_payload["options"][0].lower()
    assert "à¤¨à¤¯à¤¾ à¤¨à¤‚à¤¬à¤°" in yes_payload["options"][0] or "change" in yes_payload["options"][0].lower()


def test_section14_footer_is_seed_stable_and_personalized():
    ai_line = "Closing lines à¤•à¥‹ à¤­à¤¾à¤µà¤¨à¤¾à¤¤à¥à¤®à¤• + actionable tone à¤®à¥‡à¤‚ personalize à¤•à¤°à¥‡à¤‚à¥¤"
    one = _basic_footer_payload(core=_core("undecided"), uniqueness_seed="seed-a", ai_narrative=ai_line)
    two = _basic_footer_payload(core=_core("undecided"), uniqueness_seed="seed-a", ai_narrative=ai_line)
    three = _basic_footer_payload(core=_core("undecided"), uniqueness_seed="seed-b", ai_narrative=ai_line)

    assert one == two
    assert "Jay Prakash Vishvakarma" in one["generated_for_line"]
    assert one["gratitude_line"].strip()
    assert one["tagline_line"].strip()
    assert one["tagline_line"] != three["tagline_line"] or one["gratitude_line"] != three["gratitude_line"]


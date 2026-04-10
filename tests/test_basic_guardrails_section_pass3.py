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
    _basic_charging_payload,
    _basic_key_insight_payload,
    _basic_life_path_context_lines,
    _basic_loshu_challenge_lines,
    _basic_profile_conditioned_line,
    _basic_suggested_numbers_payload,
)


def _core(challenge: str = "Debt & Loans") -> dict:
    return {
        "inputs": {
            "first_name": "Jay",
            "full_name": "Jay Prakash Vishvakarma",
            "primary_challenge": challenge,
            "city": "Jaunpur",
            "willingness_to_change": "undecided",
        },
        "mobile": {"vibration": 9},
        "life_path": {"value": 5, "meaning": "स्वतंत्रता, अनुकूलनशीलता, साहसिक यात्री"},
        "planet": {"energy": ["ऊर्जा", "नेतृत्व", "पूर्णता"]},
        "lo_shu": {
            "missing": [1, 3, 4],
            "present": [2, 5, 6, 7, 8, 9],
            "repeating": [{"digit": 8, "count": 3}],
        },
        "suggested_numbers": [
            {"pattern": "[4] [X] [X] [6] [X] [X] [8] [X] [X] [4]", "vibration": 4, "key_digits": [4, 6, 8]},
            {"pattern": "[8] [X] [X] [4] [X] [X] [2] [X] [X] [6]", "vibration": 8, "key_digits": [8, 4, 2, 6]},
            {"pattern": "[6] [X] [X] [4] [X] [X] [2] [X] [X] [8]", "vibration": 6, "key_digits": [6, 4, 2, 8]},
        ],
        "suggestions": {
            "preferred_vibrations": [4, 8, 6],
            "preferred_digits": [4, 6, 8, 2],
        },
        "verdict": "MANAGE",
        "charging": {
            "direction": "पूर्व (East)",
            "day": "मंगलवार",
            "time": "सूर्योदय",
            "method": "लाल वस्तु के पास रखें",
        },
        "mantra": "ॐ मंगलाय नमः",
        "yantra": "मंगल यंत्र",
        "primary_rudraksha": "4 मुखी रुद्राक्ष",
        "uniqueness_seed": "seed-pass3",
    }


def test_section7_suggested_numbers_is_seeded_and_ai_blended():
    ai_line = "नए नंबर में stability digits रखकर execution consistency मजबूत करें।"
    one = _basic_suggested_numbers_payload(core=_core("Career Growth"), uniqueness_seed="seed-a", ai_narrative=ai_line)
    two = _basic_suggested_numbers_payload(core=_core("Career Growth"), uniqueness_seed="seed-a", ai_narrative=ai_line)
    three = _basic_suggested_numbers_payload(core=_core("Career Growth"), uniqueness_seed="seed-b", ai_narrative=ai_line)

    assert one == two
    assert len(one["options"]) == 3
    assert all(item["reason"].strip() for item in one["options"])
    assert one["intro"] != three["intro"] or one["options"][0]["reason"] != three["options"][0]["reason"]


def test_section8_charging_payload_is_seeded_and_non_empty():
    ai_line = "दिशा पालन और संकल्प repetition से ritual impact बढ़ता है।"
    one = _basic_charging_payload(core=_core(), uniqueness_seed="seed-a", ai_narrative=ai_line)
    two = _basic_charging_payload(core=_core(), uniqueness_seed="seed-a", ai_narrative=ai_line)
    three = _basic_charging_payload(core=_core(), uniqueness_seed="seed-b", ai_narrative=ai_line)

    assert one == two
    assert one["intro"]
    assert one["how_value"]
    assert one["intro"] != three["intro"] or one["how_value"] != three["how_value"]


def test_sections_2_4_12_helpers_use_ai_overlay_without_empty_text():
    core = _core("Debt & Loans")
    ai_line = "ग्रिड असंतुलन को daily structure और review cadence से stabilize करें।"

    loshu_lines = _basic_loshu_challenge_lines(core=core, uniqueness_seed="seed-ls", ai_narrative=ai_line)
    life_lines = _basic_life_path_context_lines(core=core, uniqueness_seed="seed-lp", ai_narrative=ai_line)
    profile_line = _basic_profile_conditioned_line(core=core, uniqueness_seed="seed-pf", ai_narrative=ai_line)
    insight = _basic_key_insight_payload(core=core, uniqueness_seed="seed-ki", ai_narrative=ai_line)

    assert len(loshu_lines) == 4
    assert all(line.strip() for line in loshu_lines)
    assert len(life_lines) == 3
    assert all(line.strip() for line in life_lines)
    assert profile_line.strip()
    assert insight["p1"].strip()
    assert insight["p2"].strip()


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
    BASIC_UNIQUENESS_HISTORY,
    _apply_basic_similarity_gate,
    _basic_summary_payload,
    _report_text_blob,
    _section_text_blob,
)


def _core() -> dict:
    return {
        "inputs": {
            "primary_challenge": "Debt & Loans",
            "city": "Jaunpur",
            "mobile_number": "8817659208",
        },
        "mobile": {"vibration": 9},
        "suggestions": {"preferred_vibrations": [4, 8, 6]},
        "lo_shu": {
            "missing": [1, 3, 4],
            "repeating": [{"digit": 8, "count": 3}],
        },
        "life_path": {"value": 5},
        "compatibility": {"level": "MODERATE", "color": "YELLOW", "english": "Moderate", "text": "à¤®à¤§à¥à¤¯à¤®"},
        "verdict": "CHANGE",
        "mantra": "à¥ à¤®à¤‚à¤—à¤²à¤¾à¤¯ à¤¨à¤®à¤ƒ",
        "primary_rudraksha": "4 à¤®à¥à¤–à¥€ à¤°à¥à¤¦à¥à¤°à¤¾à¤•à¥à¤·",
        "yantra": "à¤®à¤‚à¤—à¤² à¤¯à¤‚à¤¤à¥à¤°",
        "generated_on": "26 March 2026",
        "uniqueness_seed": "seed-pass4",
    }


def test_section11_summary_payload_is_seeded_and_ai_conditioned():
    core = _core()
    ai_line = "à¤¸à¤¾à¤°à¤¾à¤‚à¤¶ à¤•à¥‹ challenge-specific action à¤®à¥‡à¤‚ à¤¬à¤¦à¤²à¤•à¤° 21 à¤¦à¤¿à¤¨à¥‹à¤‚ à¤¤à¤• à¤…à¤¨à¥à¤¶à¤¾à¤¸à¤¨ à¤°à¤–à¥‡à¤‚à¥¤"

    one = _basic_summary_payload(core=core, uniqueness_seed="seed-a", ai_narrative=ai_line)
    two = _basic_summary_payload(core=core, uniqueness_seed="seed-a", ai_narrative=ai_line)
    three = _basic_summary_payload(core=core, uniqueness_seed="seed-b", ai_narrative=ai_line)

    assert one == two
    assert len(one["rows"]) == 7
    assert all(str(row["suggestion"]).strip() for row in one["rows"])
    assert any(
        str(one["rows"][idx]["suggestion"]) != str(three["rows"][idx]["suggestion"])
        for idx in range(len(one["rows"]))
    )


def test_similarity_gate_rewrites_in_place_without_block_growth():
    core = _core()
    sections = [
        {
            "key": "basic_summary_table_v2",
            "title": "11. Summary",
            "blocks": [
                "SUMMARY_ROW 1: à¤®à¥‹à¤¬à¤¾à¤‡à¤² à¤…à¤‚à¤• || 9 || à¤ªà¥à¤°à¤¾à¤¨à¤¾ à¤¸à¥à¤à¤¾à¤µ 1",
                "SUMMARY_ROW 2: à¤…à¤¨à¥à¤•à¥‚à¤²à¤¤à¤¾ || YELLOW Moderate / à¤®à¤§à¥à¤¯à¤® || à¤ªà¥à¤°à¤¾à¤¨à¤¾ à¤¸à¥à¤à¤¾à¤µ 2",
            ],
        },
        {
            "key": "basic_key_insight",
            "title": "12. Key Insight",
            "blocks": [
                "KEY_INSIGHT_P1: à¤¯à¤¹ à¤ªà¥à¤°à¤¾à¤¨à¤¾ insight line 1 à¤¹à¥ˆà¥¤",
                "KEY_INSIGHT_P2: à¤¯à¤¹ à¤ªà¥à¤°à¤¾à¤¨à¤¾ insight line 2 à¤¹à¥ˆà¥¤",
            ],
        },
    ]

    before_blocks = {item["key"]: list(item["blocks"]) for item in sections}
    report_blob = _report_text_blob(sections)
    section_blobs = {str(item["key"]): _section_text_blob(item) for item in sections}

    BASIC_UNIQUENESS_HISTORY.clear()
    BASIC_UNIQUENESS_HISTORY.append(
        {
            "fingerprint": "other-fingerprint",
            "report_blob": report_blob,
            "section_blobs": section_blobs,
        }
    )

    rewritten = _apply_basic_similarity_gate(sections=sections, core=core)
    after_blocks = {item["key"]: list(item["blocks"]) for item in rewritten}

    assert len(after_blocks["basic_summary_table_v2"]) == len(before_blocks["basic_summary_table_v2"])
    assert len(after_blocks["basic_key_insight"]) == len(before_blocks["basic_key_insight"])
    assert after_blocks["basic_summary_table_v2"] != before_blocks["basic_summary_table_v2"] or after_blocks[
        "basic_key_insight"
    ] != before_blocks["basic_key_insight"]


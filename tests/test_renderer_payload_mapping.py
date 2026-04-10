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
            raise RuntimeError("Azure OpenAI client should not be called in this test.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.modules.reports.html_engine.engine import _build_context
from app.modules.reports.section_adapter import normalize_ai_section_shape, to_legacy_report_sections


def test_ai_section_shape_does_not_require_section_title():
    section = {
        "sectionKey": "mobile_numerology",
        "summary": "यह सारांश हिंदी में है।",
        "keyStrength": "मुख्य ताकत स्पष्टता है।",
        "keyRisk": "दबाव में जल्दबाज़ी हो सकती है।",
        "practicalGuidance": "निर्णय से पहले छोटी चेकलिस्ट रखें।",
    }
    normalized = normalize_ai_section_shape(section)
    assert normalized is not None
    assert "sectionTitle" in normalized


def test_legacy_mapping_uses_hindi_labels_and_system_heading():
    section = {
        "sectionKey": "dashboard",
        "sectionTitle": "ignored",
        "summary": "यह सारांश हिंदी में है।",
        "keyStrength": "मुख्य ताकत स्पष्टता है।",
        "keyRisk": "दबाव में जल्दबाज़ी हो सकती है।",
        "practicalGuidance": "निर्णय से पहले छोटी चेकलिस्ट रखें।",
        "loadedEnergies": ["निर्णय स्पष्टता", "जीवन स्थिरता"],
        "scoreHighlights": [{"label": "निर्णय स्पष्टता", "value": "72"}],
    }
    legacy = to_legacy_report_sections([section])
    assert len(legacy) == 1
    assert "\n" in legacy[0]["title"]
    joined_blocks = " ".join(legacy[0]["blocks"])
    assert "सारांश" in joined_blocks
    assert "मुख्य ताकत" in joined_blocks
    assert "confidence_score" not in joined_blocks


def test_basic_renderer_context_reads_report_sections_payload():
    section = {
        "sectionKey": "mobile_numerology",
        "sectionTitle": "ignored",
        "summary": "यह सारांश हिंदी में है।",
        "keyStrength": "मुख्य ताकत स्पष्टता है।",
        "keyRisk": "दबाव में जल्दबाज़ी हो सकती है।",
        "practicalGuidance": "निर्णय से पहले छोटी चेकलिस्ट रखें।",
        "loadedEnergies": ["निर्णय स्पष्टता"],
        "scoreHighlights": [{"label": "निर्णय स्पष्टता", "value": "72"}],
    }
    report_sections = to_legacy_report_sections([section])
    payload = {
        "meta": {"plan_tier": "basic", "generated_at": "2026-01-01T00:00:00"},
        "identity": {"full_name": "Rahul Sharma", "date_of_birth": "1993-08-15"},
        "birth_details": {"date_of_birth": "1993-08-15"},
        "core_metrics": {"confidence_score": 72, "life_stability_index": 64},
        "report_sections": report_sections,
    }

    context = _build_context(payload, watermark=False)
    assert context["basic_report"]["all_sections"]
    assert context["basic_report"]["all_sections"][0]["title"]

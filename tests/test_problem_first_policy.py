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
            raise RuntimeError("Azure OpenAI client should be monkeypatched in tests.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.modules.reports import azure_report_client  # noqa: E402
from app.modules.reports.fallback_templates import _section_text  # noqa: E402


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=content))]


def test_azure_runtime_enforces_problem_first_policy(monkeypatch):
    blueprint_payload = """{
      "strategyBlueprint": {
        "narrativeStrategy": "deterministic-first",
        "sectionPlans": [
          {"sectionKey": "focus_snapshot", "angle": "root cause", "mustUseFacts": [], "avoidThemes": []},
          {"sectionKey": "remedy", "angle": "action", "mustUseFacts": [], "avoidThemes": []}
        ]
      }
    }"""
    section_payload = """{
      "sections": [
        {
          "sectionKey": "focus_snapshot",
          "summary": "करियर प्रगति में execution rhythm का असर दिख रहा है।",
          "keyStrength": "नियमित समीक्षा से सुधार संभव है।",
          "keyRisk": "अनुशासन टूटने पर output गिर सकता है।",
          "practicalGuidance": "daily priorities और weekly review बनाए रखें।"
        },
        {
          "sectionKey": "remedy",
          "summary": "कर्ज और loan pressure को कम करने पर फोकस रखें।",
          "keyStrength": "debt reduction से राहत मिलेगी।",
          "keyRisk": "loan और EMI दबाव बढ़ सकता है।",
          "practicalGuidance": "EMI discipline और cashflow audit करें।"
        },
        {
          "sectionKey": "closing_summary",
          "summary": "यह निष्कर्ष सामान्य है।",
          "keyStrength": "आपमें क्षमता है।",
          "keyRisk": "देरी नुकसान दे सकती है।",
          "practicalGuidance": "नियमित प्रयास जारी रखें।"
        }
      ]
    }"""

    responses = [blueprint_payload, section_payload]

    def _fake_create(**kwargs):
        content = responses.pop(0) if responses else section_payload
        return _FakeResponse(content)

    monkeypatch.setattr(
        azure_report_client.azure_client.chat.completions,
        "create",
        _fake_create,
    )

    ai_payload = {
        "plan": "BASIC",
        "enabledSections": ["focus_snapshot", "remedy", "closing_summary"],
        "profileSnapshot": {"fullName": "Rahul"},
        "dashboard": {"riskBand": "सुधार योग्य"},
        "deterministic": {
            "normalizedInput": {"currentProblem": "Career Growth", "focusArea": "Career Growth"},
            "problemProfile": {"category": "career"},
        },
    }

    result = azure_report_client.generate_report_with_azure(
        ai_payload=ai_payload,
        max_retries=0,
        enable_targeted_rewrite=False,
    )
    sections = result.get("sections") or []
    remedy = next((s for s in sections if str(s.get("sectionKey")) == "remedy"), {})

    assert "Career Growth" in str(remedy.get("summary") or "")
    assert "top-3 execution priorities" in str(remedy.get("practicalGuidance") or "")
    assert int((result.get("generationTrace") or {}).get("problemConsistencyRewrites") or 0) >= 1


def test_fallback_remedy_is_problem_bucketed_for_career():
    summary, key_strength, key_risk, practical_guidance = _section_text(
        section_key="remedy",
        plan="basic",
        normalized_input={"currentProblem": "Career Growth"},
        numerology_values={},
        derived_scores={},
    )

    assert "टॉप-3 दैनिक निष्पादन कार्य" in summary
    assert "वित्त समीक्षा" not in summary
    assert key_strength
    assert key_risk
    assert practical_guidance

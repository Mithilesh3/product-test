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

from app.modules.reports import azure_report_client


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=content))]


def _payload() -> dict:
    return {
        "plan": "BASIC",
        "enabledSections": ["dashboard", "core_numbers"],
        "profileSnapshot": {"fullName": "Rahul"},
        "dashboard": {"riskBand": "सुधार योग्य"},
    }


def test_azure_response_repair_and_partial_success(monkeypatch):
    raw = """```json
{
  "sections": [
    {
      "sectionKey": "dashboard",
      "summary": "यह डैशबोर्ड आपकी मुख्य ऊर्जा स्थिति दिखाता है।",
      "keyStrength": "मुख्य ताकत स्पष्ट निर्णय क्षमता है।",
      "keyRisk": "दबाव में निर्णय गति असंतुलित हो सकती है।",
      "practicalGuidance": "निर्णय से पहले लिखित जाँच सूची अपनाएँ।",
    },
    {
      "sectionKey": "core_numbers",
      "summary": "",
      "keyStrength": "x",
      "keyRisk": "y",
      "practicalGuidance": "z"
    }
  ],
}
```"""

    monkeypatch.setattr(
        azure_report_client.azure_client.chat.completions,
        "create",
        lambda **kwargs: _FakeResponse(raw),
    )

    result = azure_report_client.generate_report_with_azure(ai_payload=_payload(), max_retries=0)
    assert isinstance(result, dict)
    assert "sections" in result
    assert len(result["sections"]) == 1
    assert result["sections"][0]["sectionKey"] == "dashboard"


def test_azure_unusable_response_returns_safe_skeleton(monkeypatch):
    monkeypatch.setattr(
        azure_report_client.azure_client.chat.completions,
        "create",
        lambda **kwargs: _FakeResponse("not a json payload"),
    )

    result = azure_report_client.generate_report_with_azure(ai_payload=_payload(), max_retries=0)
    assert isinstance(result, dict)
    assert result["plan"] == "BASIC"
    assert isinstance(result.get("sections"), list)
    assert result["sections"] == []

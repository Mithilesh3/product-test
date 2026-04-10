from pathlib import Path
import json
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
            raise RuntimeError("Network-disabled test path")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.modules.reports.plan_config import get_plan_config
from app.modules.reports.report_assembler import build_plan_aware_report

RAW_INTERNAL_KEYS = (
    "confidence_score",
    "dharma_alignment_score",
    "financial_discipline_index",
    "life_stability_index",
)


def _load_fixture(plan: str) -> dict:
    fixture_path = ROOT / "tests" / "fixtures" / "report_payloads" / f"{plan}.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_report_generation_for_all_plans():
    expected_sections_by_plan = {
        "basic": {"basic_details", "mobile_numerology", "lo_shu_grid", "remedies_logic"},
        "standard": {"basic_details", "name_numerology", "name_analysis", "mobile_numerology", "summary_and_priority_actions"},
        "enterprise": {
            "full_identity_profile",
            "core_numbers",
            "advanced_name_numerology",
            "mobile_numerology_advanced",
            "premium_summary_narrative",
        },
    }
    for plan in ("basic", "standard", "enterprise"):
        payload = _load_fixture(plan)
        report = build_plan_aware_report(intake_data=payload, resolved_plan=plan)
        config = get_plan_config(plan)

        sections = report.get("sections") or []
        assert sections
        assert len(sections) <= len(config.enabled_sections)
        section_keys = {str(section.get("sectionKey") or "").strip() for section in sections if isinstance(section, dict)}
        assert expected_sections_by_plan[plan].issubset(section_keys)
        if plan == "basic":
            assert "name_numerology" not in section_keys
            assert "email_numerology" not in section_keys
            assert "business_numerology" not in section_keys
            assert "digital_numerology" not in section_keys

        canonical = report.get("normalizedInput") or {}
        for key in ("fullName", "dateOfBirth", "mobileNumber"):
            value = str(canonical.get(key) or "").strip()
            assert value
            assert value.lower() != "not provided"

        report_sections = report.get("report_sections") or []
        assert report_sections
        visible_text = " ".join(
            " ".join(str(block) for block in (section.get("blocks") or []))
            for section in report_sections
        ).lower()
        assert all(raw_key not in visible_text for raw_key in RAW_INTERNAL_KEYS)

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

from app.modules.reports.report_assembler import build_plan_aware_report
from app.modules.reports.intake_schema import LifeSignifyRequest
from app.modules.reports.service import _apply_section_render_guard


def test_enterprise_accepts_minimal_required_payload_with_optional_fields_missing():
    minimal_basic_like_intake = {
        "identity": {
            "full_name": "Rahul Sharma",
            "gender": "male",
            "country_of_residence": "India",
            "email": "rahul@example.com",
            "name_variations": ["Rahul", "Rahul Sharma"],
        },
        "birth_details": {
            "date_of_birth": "1993-08-15",
            "birthplace_city": "Delhi",
            "birthplace_country": "India",
            "time_of_birth": "07:30",
        },
        "contact": {"mobile_number": "9876543210"},
        "focus": {"life_focus": "general_alignment"},
        "preferences": {"language_preference": "hindi", "primary_goal": "career stability"},
        "current_problem": "career growth",
    }

    report = build_plan_aware_report(
        intake_data=minimal_basic_like_intake,
        resolved_plan="enterprise",
    )

    assert str(report.get("plan")).lower() == "enterprise"
    assert isinstance(report.get("sections"), list)
    assert len(report.get("sections") or []) >= 30


def test_life_signify_request_accepts_case_insensitive_gender():
    payload = {
        "identity": {
            "full_name": "Rahul Sharma",
            "date_of_birth": "15-08-1993",
            "gender": "Male",
            "country_of_residence": "India",
        },
        "birth_details": {
            "date_of_birth": "15-08-1993",
            "birthplace_city": "Delhi",
            "birthplace_country": "India",
        },
        "contact": {"mobile_number": "9876543210"},
        "focus": {"life_focus": "general_alignment"},
    }

    request = LifeSignifyRequest.model_validate(payload)
    assert request.identity.gender == "male"
    assert request.birth_details.date_of_birth == "1993-08-15"


def test_flat_basic_contract_is_accepted():
    payload = {
        "plan_override": "basic",
        "name": "Rahul Sharma",
        "dob": "1993-08-15",
        "mobile_number": "9876543210",
    }

    request = LifeSignifyRequest.model_validate(payload)
    assert request.identity.full_name == "Rahul Sharma"
    assert request.birth_details.date_of_birth == "1993-08-15"
    assert request.contact is not None
    assert request.contact.mobile_number == "9876543210"


def test_flat_enterprise_contract_is_accepted():
    payload = {
        "plan_override": "enterprise",
        "name": "Rahul Sharma",
        "dob": "1993-08-15",
        "mobile_number": "9876543210",
        "name_variations": ["Rahul", "Rahul Sharma"],
        "birth_time": "07:30",
        "birth_place": "Delhi, India",
        "goals": ["career_growth", "wealth"],
        "priority_focus": "career",
        "current_status": {
            "career": "growing",
            "relationship": "single",
            "financial": "unstable",
        },
    }

    request = LifeSignifyRequest.model_validate(payload)
    assert request.identity.full_name == "Rahul Sharma"
    assert request.identity.name_variations == "Rahul | Rahul Sharma"
    assert request.birth_details.time_of_birth == "07:30"
    assert request.birth_details.birthplace_city == "Delhi"


def test_render_guard_allows_missing_email_when_core_identity_present():
    content = {
        "normalizedInput": {
            "fullName": "Rahul Sharma",
            "dateOfBirth": "1993-08-15",
            "mobileNumber": "9876543210",
            "gender": "male",
            "city": "Delhi",
            "country": "India",
            "email": "",
            "currentProblem": "career growth",
        }
    }

    guarded = _apply_section_render_guard(content)
    identity = guarded.get("identity") or {}
    input_normalized = guarded.get("input_normalized") or {}

    assert identity.get("full_name") == "Rahul Sharma"
    assert identity.get("mobile_number") == "9876543210"
    assert input_normalized.get("email") == ""

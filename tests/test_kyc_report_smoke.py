from pathlib import Path
import sys
import types

import pytest
from fastapi import HTTPException

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
            raise RuntimeError("Azure OpenAI should be mocked in this test.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.db.models import Organization, User
from app.modules.reports import service as report_service
from app.modules.users import service as user_service


class _FakeQuery:
    def __init__(self, value):
        self._value = value

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self._value


class _FakeDB:
    def __init__(self, values=None):
        self.values = values or {}
        self.added = []

    def query(self, model):
        return _FakeQuery(self.values.get(model))

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        return None

    def refresh(self, value):
        if getattr(value, "id", None) is None:
            value.id = len(self.added) + 1
        return value

    def rollback(self):
        return None


def test_registration_creates_pending_kyc_order(monkeypatch):
    fake_db = _FakeDB(values={User: None})
    monkeypatch.setattr(user_service, "_create_kyc_order", lambda mobile: {"id": "order_test_123"})

    result = user_service.create_user(
        db=fake_db,
        full_name="Rahul Sharma",
        mobile_number="9876543210",
        password="StrongPassword123",
    )

    assert result["registration_pending"] is True
    assert result["kyc_order"]["id"] == "order_test_123"


def test_kyc_pending_blocks_login(monkeypatch):
    user = types.SimpleNamespace(id=11, mobile_number="9876543210", kyc_verified=False)
    monkeypatch.setattr(user_service, "authenticate_user", lambda db, identifier, password: user)

    with pytest.raises(HTTPException) as exc:
        user_service.login_user(_FakeDB(), "9876543210", "pw")
    assert exc.value.status_code == 403


def test_verified_kyc_allows_login(monkeypatch):
    user = types.SimpleNamespace(
        id=11,
        tenant_id=21,
        role="admin",
        email="rahul@example.com",
        mobile_number="9876543210",
        kyc_verified=True,
    )
    organization = types.SimpleNamespace(id=21)
    fake_db = _FakeDB(values={Organization: organization})

    monkeypatch.setattr(user_service, "authenticate_user", lambda db, identifier, password: user)
    monkeypatch.setattr(user_service, "create_access_token", lambda payload: "token_abc")
    monkeypatch.setattr(user_service, "log_action", lambda **kwargs: None)

    result = user_service.login_user(fake_db, "9876543210", "pw")
    assert result["access_token"] == "token_abc"
    assert result["token_type"] == "bearer"


def test_authenticated_user_can_generate_report(monkeypatch):
    subscription = types.SimpleNamespace(plan_name="basic", reports_used=0, end_date=None, is_active=True)
    current_user = types.SimpleNamespace(id=5, tenant_id=9, is_admin=True)
    fake_db = _FakeDB()

    def _fake_build_plan_aware_report(*, intake_data, resolved_plan):
        return {
            "meta": {"plan_tier": "basic"},
            "normalizedInput": {
                "fullName": "Rahul Sharma",
                "dateOfBirth": "1993-08-15",
                "mobileNumber": "9876543210",
                "email": "rahul@example.com",
                "gender": "male",
                "country": "India",
                "city": "Delhi",
            },
            "profileSnapshot": {},
            "dashboard": {"confidenceScore": 72},
            "sections": [
                {
                    "sectionKey": "dashboard",
                    "sectionTitle": "Numerology Dashboard\nन्यूमरोलॉजी डैशबोर्ड",
                    "summary": "यह सारांश हिंदी में है।",
                    "keyStrength": "मुख्य ताकत स्पष्टता है।",
                    "keyRisk": "दबाव में जल्दबाज़ी हो सकती है।",
                    "practicalGuidance": "निर्णय से पहले लिखित जाँच सूची रखें।",
                    "loadedEnergies": ["निर्णय स्पष्टता"],
                    "scoreHighlights": [{"label": "निर्णय स्पष्टता", "value": "72"}],
                }
            ],
            "deterministic": {"derivedScores": {"confidence_score": 72}},
            "report_sections": [],
            "input_normalized": {},
        }

    monkeypatch.setattr(report_service, "_validate_and_lock_subscription", lambda db, user: subscription)
    monkeypatch.setattr(report_service, "build_plan_aware_report", _fake_build_plan_aware_report)
    monkeypatch.setattr(report_service, "log_action", lambda **kwargs: None)

    payload = {
        "identity": {"full_name": "Rahul Sharma"},
        "birth_details": {"date_of_birth": "1993-08-15"},
        "focus": {"life_focus": "general_alignment"},
        "contact": {"mobile_number": "9876543210"},
        "preferences": {"language_preference": "hindi"},
        "current_problem": "career growth",
    }
    report = report_service.generate_ai_report_service(
        db=fake_db,
        current_user=current_user,
        intake_data=payload,
    )
    assert report is not None
    assert subscription.reports_used == 1

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.reports.deterministic_pipeline import run_deterministic_pipeline  # noqa: E402
from app.modules.reports.plan_config import get_plan_config  # noqa: E402


def _intake(current_problem: str) -> dict:
    return {
        "identity": {
            "full_name": "Amit Verma",
            "date_of_birth": "1999-09-14",
            "gender": "male",
            "country_of_residence": "India",
            "email": "amit@example.com",
        },
        "birth_details": {
            "date_of_birth": "1999-09-14",
            "birthplace_city": "Jaipur",
            "birthplace_country": "India",
        },
        "focus": {"life_focus": "general_alignment"},
        "contact": {"mobile_number": "9876543210"},
        "preferences": {
            "language_preference": "hindi",
            "profession": "Technology",
            "career_type": "job",
        },
        "current_problem": current_problem,
    }


def test_exam_problem_prefers_education_category():
    plan = get_plan_config("basic")
    pipeline = run_deterministic_pipeline(
        intake_data=_intake("exam preparation is inconsistent and stressful"),
        plan_config=plan,
    )
    profile = pipeline.problem_profile if isinstance(pipeline.problem_profile, dict) else {}
    assert str(profile.get("category") or "") == "education"


def test_confidence_problem_not_overridden_by_industry_tokens():
    intake = _intake("confidence and visibility in meetings")
    intake["preferences"]["profession"] = "Education"
    plan = get_plan_config("basic")
    pipeline = run_deterministic_pipeline(
        intake_data=intake,
        plan_config=plan,
    )
    profile = pipeline.problem_profile if isinstance(pipeline.problem_profile, dict) else {}
    assert str(profile.get("category") or "") == "confidence"


def test_financial_discipline_maps_to_finance():
    plan = get_plan_config("basic")
    pipeline = run_deterministic_pipeline(
        intake_data=_intake("financial discipline and budgeting pressure"),
        plan_config=plan,
    )
    profile = pipeline.problem_profile if isinstance(pipeline.problem_profile, dict) else {}
    assert str(profile.get("category") or "") == "finance"

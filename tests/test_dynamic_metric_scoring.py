from __future__ import annotations

from itertools import combinations
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
            raise RuntimeError("Azure OpenAI client should not be called in metric scoring tests.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

import app.modules.reports.ai_engine as report_ai_engine
from app.modules.reports.ai_engine import generate_life_signify_report
from app.modules.reports.intake_schema import LifeSignifyRequest


def _minimal_ai_narrative(*_args, **_kwargs):
    return {"executive_brief": {"summary": "short", "key_strength": "short", "key_risk": "short", "strategic_focus": "short"}}


def _profile(
    *,
    full_name: str,
    dob: str,
    mobile: str,
    email: str,
    city: str,
    concern: str,
    gender: str,
) -> dict:
    return {
        "full_name": full_name,
        "date_of_birth": dob,
        "mobile_number": mobile,
        "gender": gender,
        "city": city,
        "country": "India",
        "email": email,
        "language_preference": "hindi",
        "career_type": "job",
        "profession": "Technology",
        "relationship_status": "single",
        "primary_goal": concern,
        "current_problem": concern,
        # Keep behavioral values intentionally close to verify numerology-driven variation.
        "financial": {"monthly_income": 90000, "savings_ratio": 24, "debt_ratio": 20, "risk_tolerance": "moderate"},
        "career": {"industry": "Technology", "years_experience": 6, "stress_level": 6},
        "emotional": {"anxiety_level": 5, "decision_confusion": 5, "impulse_control": 6, "emotional_stability": 6},
        "life_events": {"setback_events_years": [2020]},
    }


def _metric_tuple(report: dict) -> tuple[int, int, int, int, int, int]:
    metrics = report.get("core_metrics") or {}
    return (
        int(metrics.get("life_stability_index", -1)),
        int(metrics.get("financial_discipline_index", -1)),
        int(metrics.get("emotional_regulation_index", -1)),
        int(metrics.get("dharma_alignment_score", -1)),
        int(metrics.get("confidence_score", -1)),
        int(metrics.get("data_completeness_score", -1)),
    )


def test_metric_scoring_varies_for_distinct_profiles():
    profiles = [
        _profile(
            full_name="Rahul Sharma",
            dob="15-08-1993",
            mobile="9876543210",
            email="rahul.sharma@example.com",
            city="Delhi",
            concern="career execution consistency",
            gender="male",
        ),
        _profile(
            full_name="Neha Verma",
            dob="04-11-1998",
            mobile="8899776655",
            email="neha.verma@brand.in",
            city="Lucknow",
            concern="relationship communication and trust",
            gender="female",
        ),
        _profile(
            full_name="Arjun Mehta",
            dob="22-01-1986",
            mobile="7012345678",
            email="arjun.m.consult@workmail.com",
            city="Mumbai",
            concern="cashflow and business decision discipline",
            gender="male",
        ),
        _profile(
            full_name="Pooja Iyer",
            dob="29-09-1991",
            mobile="9001122334",
            email="pooja.iyer.ops@corp.org",
            city="Bengaluru",
            concern="health routine and burnout prevention",
            gender="female",
        ),
        _profile(
            full_name="Karan Kapoor",
            dob="07-03-2001",
            mobile="7665544332",
            email="karan.kapoor.media@studio.net",
            city="Jaipur",
            concern="study focus and exam pressure handling",
            gender="male",
        ),
    ]

    original_generator = report_ai_engine.generate_ai_narrative
    report_ai_engine.generate_ai_narrative = _minimal_ai_narrative
    try:
        reports = [
            generate_life_signify_report(
                LifeSignifyRequest.model_validate(payload).model_dump(exclude_none=True),
                plan_name="basic",
            )
            for payload in profiles
        ]
    finally:
        report_ai_engine.generate_ai_narrative = original_generator

    metric_rows = [_metric_tuple(report) for report in reports]

    assert all(min(row) >= 0 for row in metric_rows), "All metric scores must be present."
    assert all(max(row) <= 100 for row in metric_rows), "All metric scores must be normalized to 0..100."
    assert len(set(metric_rows)) == len(metric_rows), "Distinct profiles must not receive identical metric rows."

    old_static_tuple = (55, 50, 50, 53, 45, 35)
    assert old_static_tuple not in metric_rows, "Legacy static baseline tuple is still present."

    for left, right in combinations(metric_rows, 2):
        assert left != right, "Metric scoring failure: two distinct profiles produced the same metric tuple."
        delta = sum(abs(lv - rv) for lv, rv in zip(left, right))
        assert delta >= 6, f"Metric differentiation is too weak (pair delta={delta})."

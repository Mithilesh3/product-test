from __future__ import annotations

from difflib import SequenceMatcher
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
            raise RuntimeError("Azure OpenAI client should not be called in this personalization test.")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

import app.modules.reports.ai_engine as report_ai_engine
from app.modules.reports.ai_engine import generate_life_signify_report
from app.modules.reports.intake_schema import LifeSignifyRequest


def _minimal_ai_narrative(*_args, **_kwargs):
    # Purposely low-quality/short so merge layer keeps interpretation baseline text.
    return {
        "executive_brief": {
            "summary": "short",
            "key_strength": "short",
            "key_risk": "short",
            "strategic_focus": "short",
        }
    }


def _request(
    *,
    full_name: str,
    date_of_birth: str,
    mobile_number: str,
    email: str,
    city: str,
    gender: str,
    concern: str,
    profession: str,
) -> dict:
    return {
        "full_name": full_name,
        "date_of_birth": date_of_birth,
        "mobile_number": mobile_number,
        "gender": gender,
        "city": city,
        "country": "India",
        "email": email,
        "language_preference": "hindi",
        "profession": profession,
        "career_type": "job",
        "relationship_status": "single",
        "primary_goal": concern,
        "current_problem": concern,
        "financial": {
            "monthly_income": 85000,
            "savings_ratio": 20,
            "debt_ratio": 18,
            "risk_tolerance": "moderate",
        },
        "career": {
            "industry": profession,
            "years_experience": 6,
            "stress_level": 6,
        },
        "emotional": {
            "anxiety_level": 4,
            "decision_confusion": 5,
            "impulse_control": 6,
            "emotional_stability": 6,
        },
    }


def test_executive_brief_personalization_varies_across_profiles():
    profiles = [
        _request(
            full_name="Rahul Sharma",
            date_of_birth="15-08-1993",
            mobile_number="9876543210",
            email="rahul.sharma@example.com",
            city="Delhi",
            gender="male",
            concern="career execution consistency",
            profession="Technology",
        ),
        _request(
            full_name="Neha Verma",
            date_of_birth="04-11-1998",
            mobile_number="8899776655",
            email="neha.verma@brand.in",
            city="Lucknow",
            gender="female",
            concern="relationship clarity and emotional balance",
            profession="Design",
        ),
        _request(
            full_name="Arjun Mehta",
            date_of_birth="22-01-1986",
            mobile_number="7012345678",
            email="arjun.m.consult@workmail.com",
            city="Mumbai",
            gender="male",
            concern="business cashflow and team decision quality",
            profession="Consulting",
        ),
        _request(
            full_name="Pooja Iyer",
            date_of_birth="29-09-1991",
            mobile_number="9001122334",
            email="pooja.iyer.ops@corp.org",
            city="Bengaluru",
            gender="female",
            concern="health routine and burnout prevention",
            profession="Operations",
        ),
        _request(
            full_name="Karan Kapoor",
            date_of_birth="07-03-2001",
            mobile_number="7665544332",
            email="karan.kapoor.media@studio.net",
            city="Jaipur",
            gender="male",
            concern="study focus and exam pressure handling",
            profession="Media",
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

    briefs = [report.get("executive_brief") or {} for report in reports]
    summaries = [str(item.get("summary") or "").strip() for item in briefs]
    strengths = [str(item.get("key_strength") or "").strip() for item in briefs]
    risks = [str(item.get("key_risk") or "").strip() for item in briefs]
    focuses = [str(item.get("strategic_focus") or "").strip() for item in briefs]

    assert all(summaries), "Every profile must produce a non-empty executive summary."
    assert all(strengths), "Every profile must produce a non-empty key strength explanation."
    assert all(risks), "Every profile must produce a non-empty key risk explanation."
    assert all(focuses), "Every profile must produce a non-empty correction focus explanation."

    assert len(set(summaries)) == len(profiles), "Executive summaries should materially vary across distinct profiles."
    assert len(set(strengths)) >= 4, "Key strength explanation is repeating too much."
    assert len(set(risks)) >= 4, "Key risk explanation is repeating too much."
    assert len(set(focuses)) >= 4, "Correction focus explanation is repeating too much."

    banned_exact_patterns = (
        "मुख्य ताकत: Life Stability",
        "मुख्य जोखिम: Karma Pressure",
        "correction को concern 'study' से जोड़कर करें",
    )
    for index, brief in enumerate(briefs):
        merged = " | ".join(
            [
                str(brief.get("summary") or ""),
                str(brief.get("key_strength") or ""),
                str(brief.get("key_risk") or ""),
                str(brief.get("strategic_focus") or ""),
            ]
        )
        for phrase in banned_exact_patterns:
            assert phrase not in merged, f"Profile {index + 1} still contains repeated template phrase: {phrase}"

    for left, right in combinations(summaries, 2):
        similarity = SequenceMatcher(None, left, right).ratio()
        assert similarity < 0.9, f"Executive summary similarity too high: {similarity:.3f}"


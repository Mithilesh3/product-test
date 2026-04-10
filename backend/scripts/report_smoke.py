from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if not (BACKEND_ROOT / "app").exists():
    BACKEND_ROOT = BACKEND_ROOT / "backend"
REPO_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.reports.plan_config import get_plan_config, resolve_plan_key
from app.modules.reports.report_assembler import build_plan_aware_report
from app.modules.reports.service import enrich_report_content

PLACEHOLDER_RE = re.compile(r"(lorem ipsum|tbd|placeholder)", re.IGNORECASE)


def _fixture_path(plan: str) -> Path | None:
    candidates = [
        REPO_ROOT / "tests" / "fixtures" / "report_payloads" / f"{plan}.json",
        BACKEND_ROOT / "tests" / "fixtures" / "report_payloads" / f"{plan}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _fallback_fixture(plan: str) -> dict:
    base = {
        "identity": {
            "full_name": "Rahul Sharma",
            "date_of_birth": "1993-08-15",
            "gender": "male",
            "country_of_residence": "India",
            "email": "rahul@example.com",
        },
        "birth_details": {
            "date_of_birth": "1993-08-15",
            "birthplace_city": "Delhi",
            "birthplace_country": "India",
        },
        "focus": {"life_focus": "general_alignment"},
        "contact": {"mobile_number": "9876543210"},
        "preferences": {
            "language_preference": "hindi",
            "profession": "Technology",
            "relationship_status": "single",
            "career_type": "job",
            "primary_goal": "career growth and stability",
        },
        "current_problem": "career growth and stability",
    }
    if plan == "standard":
        base["career"] = {"industry": "Technology", "stress_level": 6}
        base["financial"] = {"monthly_income": 90000}
    if plan == "enterprise":
        base["focus"] = {"life_focus": "career_growth"}
        base["preferences"]["relationship_status"] = "married"
        base["preferences"]["career_type"] = "business"
        base["career"] = {"industry": "Technology", "role": "entrepreneur", "stress_level": 7}
        base["financial"] = {"monthly_income": 250000, "debt_ratio": 28}
        base["calibration"] = {
            "decision_style": "research",
            "stress_response": "overthink",
            "money_decision_style": "calculated",
            "biggest_weakness": "discipline",
        }
    return base


def _assert_identity(report: dict) -> None:
    canonical = report.get("normalizedInput") or {}
    required = ["fullName", "dateOfBirth", "mobileNumber", "email"]
    missing = [key for key in required if not str(canonical.get(key) or "").strip()]
    if missing:
        raise RuntimeError(f"Missing required canonical identity fields: {', '.join(missing)}")
    if any(str(canonical.get(key) or "").strip().lower() == "not provided" for key in required):
        raise RuntimeError("Canonical identity contains raw 'Not Provided' value")


def _assert_content(report: dict, expected_sections: int) -> None:
    sections = report.get("sections") or []
    if not sections:
        raise RuntimeError("No sections generated.")
    if len(sections) > expected_sections:
        raise RuntimeError(f"Section count {len(sections)} exceeds expected {expected_sections}.")

    joined = " ".join(
        " ".join(
            str(section.get(field) or "")
            for field in ("summary", "keyStrength", "keyRisk", "practicalGuidance")
        )
        for section in sections
    )
    if PLACEHOLDER_RE.search(joined):
        raise RuntimeError("Placeholder content detected in generated sections.")


def run_smoke(plan: str, generate_pdf: bool = False) -> Path | None:
    normalized_plan = resolve_plan_key(plan)
    fixture = _fixture_path(normalized_plan)
    if fixture:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
    else:
        payload = _fallback_fixture(normalized_plan)
    report = build_plan_aware_report(intake_data=payload, resolved_plan=normalized_plan)
    report = enrich_report_content(report, normalized_plan)

    plan_config = get_plan_config(normalized_plan)
    _assert_identity(report)
    _assert_content(report, expected_sections=len(plan_config.enabled_sections))

    if not generate_pdf:
        return None

    from app.modules.reports.html_engine import generate_report_pdf

    output_dir = REPO_ROOT / "smoke_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"smoke_{normalized_plan}.pdf"
    pdf_buffer = generate_report_pdf(report)
    output_path.write_bytes(pdf_buffer.getvalue())
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run report smoke test for a plan tier.")
    parser.add_argument("--plan", choices=["basic", "standard", "premium", "enterprise"], required=True)
    parser.add_argument("--pdf", action="store_true", help="Also generate a smoke PDF artifact.")
    args = parser.parse_args()

    artifact = run_smoke(args.plan, generate_pdf=args.pdf)
    if artifact:
        print(f"Smoke passed. PDF: {artifact}")
    else:
        print("Smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

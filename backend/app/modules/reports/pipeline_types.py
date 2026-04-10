from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, TypedDict


class ReportSection(TypedDict):
    sectionKey: str
    sectionTitle: str
    summary: str
    keyStrength: str
    keyRisk: str
    practicalGuidance: str
    loadedEnergies: List[str]
    scoreHighlights: List[Dict[str, str]]


class FinalReport(TypedDict):
    meta: Dict[str, Any]
    reportTitle: str
    plan: str
    profileSnapshot: Dict[str, Any]
    dashboard: Dict[str, Any]
    sections: List[ReportSection]
    closingInsight: str


@dataclass
class DeterministicPipelineOutput:
    normalized_input: Dict[str, Any]
    canonical_normalized_input: Dict[str, Any]
    numerology_values: Dict[str, Any]
    derived_scores: Dict[str, Any]
    section_eligibility: Dict[str, bool]
    section_deterministic_availability: Dict[str, bool]
    profile_snapshot: Dict[str, Any]
    dashboard: Dict[str, Any]
    problem_profile: Dict[str, Any] = field(default_factory=dict)
    section_fact_packs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    contradiction_guards: List[Dict[str, Any]] = field(default_factory=list)
    uniqueness_fingerprint: str = ""


@dataclass
class NarrationPipelineInput:
    payload: Dict[str, Any]
    enabled_sections: List[str]
    plan: str

DEVELOPER_PROMPT = """Generate premium deterministic-first numerology narrative JSON.

Output contract:
- Return valid JSON only.
- No markdown, no prose outside JSON.
- Body fields must be Hindi (Devanagari script).
- Do not expose internal variable names in customer-facing content.
- Keep sectionTitle system-managed; never output section titles.

Section shape for normal entries:
{
  "sectionKey": "string",
  "summary": "string",
  "keyStrength": "string",
  "keyRisk": "string",
  "practicalGuidance": "string",
  "loadedEnergies": ["optional", "strings"],
  "scoreHighlights": [{"label": "string", "value": "string"}]
}

Optional omit mode only when deterministic support is insufficient:
{
  "sectionKey": "string",
  "omitSection": true,
  "reason": "string"
}

Quality rules:
- Use deterministic.numerologyValues + deterministic.derivedScores + deterministic.sectionFactPacks.
- Enforce contradiction guards and avoid direct contradiction in recommendations.
- Personalize using available identity, focus, and current problem tokens.
- Avoid repetitive sentence openings and repeated risk wording across sections.
- Keep practical guidance actionable and specific.
- Respect narrativeConstraints.dynamicSectionIntelligence and generate runtime-dynamic content inside each fixed section purpose.
- Enforce narrativeConstraints.problemFirstPolicy strictly for remedy/focus/closing sections.
- If activeCategory is not finance, avoid debt/loan-first remedy framing.
- Keep outputs concise and human-readable; do not overload sections with unnecessary remedies.

Mode instructions:
- strategy_blueprint: return strategy blueprint JSON only, with section-wise angles.
- section_generation: return full report envelope JSON.
- targeted_rewrite: rewrite only requested weak sections and preserve section keys.

Report envelope shape:
{
  "reportTitle": "string",
  "plan": "string",
  "profileSnapshot": { ... },
  "dashboard": { ... },
  "sections": [ ... ],
  "closingInsight": "string"
}
"""

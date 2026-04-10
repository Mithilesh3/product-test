# Pre-release Checks

Run these checks before final production deployment.

## 1) Integration and hardening tests

```bash
pytest tests/test_report_language_presentation.py
pytest tests/test_azure_report_client_hardening.py
pytest tests/test_renderer_payload_mapping.py
pytest tests/test_fallback_section_quality.py
pytest tests/test_plan_payload_validation.py
```

## 2) Plan smoke commands

```bash
powershell -File backend/scripts/smoke-basic-report.ps1
powershell -File backend/scripts/smoke-standard-report.ps1
powershell -File backend/scripts/smoke-enterprise-report.ps1
```

Optional PDF artifact:

```bash
python backend/scripts/report_smoke.py --plan basic --pdf
python backend/scripts/report_smoke.py --plan standard --pdf
python backend/scripts/report_smoke.py --plan enterprise --pdf
```

## 3) Expected outcomes

- Required payload fields fail with clear `422` and field list.
- Section headings are system-managed bilingual titles.
- Body narratives are Hindi-dominant and free of raw metric keys.
- Azure invalid JSON is repaired when possible; partial section success is preserved.
- Fallback sections are generated only for failed sections.

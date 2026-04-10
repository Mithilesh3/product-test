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
            raise RuntimeError("Network-disabled test path")

    openai_stub.AzureOpenAI = _DummyAzureOpenAI
    sys.modules["openai"] = openai_stub

from app.modules.reports.service import generate_uniqueness_benchmark_service, BASIC_BENCHMARK_SECTION_CAP
from app.modules.reports.plan_config import STANDARD_SECTIONS, ENTERPRISE_SECTIONS


def test_uniqueness_benchmark_service_returns_planwise_metrics_and_passes_target():
    result = generate_uniqueness_benchmark_service(user_count=10, target_difference=0.19)

    assert result["users_tested"] == 10
    assert result["target_difference"] == 0.19
    assert result["all_plans_pass_target"] is True

    plans = result.get("plans") or {}
    assert set(plans.keys()) == {"basic", "standard", "enterprise"}

    expected_sections = {
        "basic": BASIC_BENCHMARK_SECTION_CAP,
        "standard": len(STANDARD_SECTIONS),
        "enterprise": len(ENTERPRISE_SECTIONS),
    }
    for plan_key, section_count in expected_sections.items():
        metrics = plans[plan_key]
        assert metrics["plan"] == plan_key
        assert metrics["users_tested"] == 10
        assert metrics["sections_per_report"] == section_count
        assert metrics["pair_count"] == 45
        assert metrics["sentence_jaccard_avg_difference"] >= 0.19
        assert metrics["sentence_jaccard_min_difference"] >= 0.19
        assert metrics["passes_target"] is True

"""Unit tests for the 50-Case Empirical Benchmark Runner."""

import pytest
from promptops.runner.benchmark import BenchmarkRunner


def test_benchmark_cases_loading():
    """Verify that exactly 50 benchmark cases are loaded with all 5 categories represented."""
    runner = BenchmarkRunner()
    assert len(runner.cases) == 50

    categories = {c.category for c in runner.cases}
    assert "standard_clean" in categories
    assert "noisy_messy" in categories
    assert "adversarial_edge" in categories
    assert "contradictory_constraints" in categories
    assert "infrastructure_chaos" in categories


@pytest.mark.asyncio
async def test_single_benchmark_case_execution():
    """Verify execution of a single benchmark case produces valid BenchmarkResult."""
    runner = BenchmarkRunner()
    case = runner.cases[0]  # Global AI Developer Summit

    from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
    adapter = ChaosMockAdapter(model_name="mock-fast", mode=ChaosMode.PERFECT, simulated_latency_ms=5.0)

    result = await runner.run_single_case(case, prompt_version="v2.0.0", adapter=adapter)

    assert result.case_id == "CASE-01"
    assert result.schema_valid is True
    assert result.instruction_followed is True
    assert result.total_tokens > 0
    assert result.cost_usd > 0
    assert result.latency_ms > 0

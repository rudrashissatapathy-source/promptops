"""Comprehensive tests for Prompt Registry, Smart Policy Router, and Telemetry/Cache."""

import pytest

from promptops.registry.prompt_store import PromptRegistry
from promptops.telemetry.cache import GenerationCache
from promptops.telemetry.logger import TelemetryStore
from promptops.router.policy_router import PolicyRouter
from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
from promptops.models.telemetry import RoutingPolicy, RunRecord, RepairTier


def test_prompt_registry_loading_and_retrieval():
    """Verify registry loads prompts from disk and retrieves by ID and semver."""
    registry = PromptRegistry()
    prompts = registry.list_prompts()
    assert len(prompts) >= 2

    # Check v1.0.0 and v2.0.0 exist
    p_v1 = registry.get("event_brief_synthesizer", "v1.0.0")
    p_v2 = registry.get("event_brief_synthesizer", "v2.0.0")
    assert p_v1.version == "v1.0.0"
    assert p_v2.version == "v2.0.0"

    # Default retrieval without version returns highest semver (v2.0.0)
    p_latest = registry.get("event_brief_synthesizer")
    assert p_latest.version == "v2.0.0"


def test_prompt_rendering_with_validation():
    """Verify variable validation during prompt template rendering."""
    registry = PromptRegistry()
    
    # Missing required variable 'event_brief'
    with pytest.raises(ValueError) as exc:
        registry.render("event_brief_synthesizer", "v2.0.0", variables={})
    assert "Missing required prompt variables" in str(exc.value)

    # Valid rendering
    sys_prompt, user_prompt = registry.render(
        "event_brief_synthesizer",
        "v2.0.0",
        variables={"event_brief": "Hackathon notes for 200 participants."}
    )
    assert len(sys_prompt) > 50
    assert "Hackathon notes for 200 participants." in user_prompt


def test_prompt_diff_engine():
    """Verify textual diff computation between prompt versions."""
    registry = PromptRegistry()
    diff = registry.diff_versions("event_brief_synthesizer", "v1.0.0", "v2.0.0")

    assert diff["v1"] == "v1.0.0"
    assert diff["v2"] == "v2.0.0"
    assert "MANDATORY SCHEMA RULES" in diff["system_prompt_diff"]
    assert diff["v2_length_chars"] > diff["v1_length_chars"]


def test_exact_match_generation_cache():
    """Verify SHA-256 key determinism, hit/miss tracking, and cache retrieval."""
    cache = GenerationCache()
    key1 = cache.compute_key("mock-fast", "event_brief_synthesizer", "v2.0.0", {"brief": "Test"}, 0.2)
    key2 = cache.compute_key("mock-fast", "event_brief_synthesizer", "v2.0.0", {"brief": "Test"}, 0.2)
    key3 = cache.compute_key("mock-fast", "event_brief_synthesizer", "v2.0.0", {"brief": "Other"}, 0.2)

    assert key1 == key2
    assert key1 != key3

    # Miss
    assert cache.get(key1) is None
    assert cache.stats()["misses"] == 1

    # Put and hit
    payload = {"data": "cached_event_payload"}
    cache.put(key1, payload)
    retrieved = cache.get(key1)
    assert retrieved == payload
    assert cache.stats()["hits"] == 1
    assert cache.stats()["hit_ratio_percent"] == 50.0


def test_telemetry_store_metrics_aggregation(tmp_path):
    """Verify telemetry record ingestion and summary statistical calculations."""
    log_file = tmp_path / "test_runs.jsonl"
    store = TelemetryStore(log_path=log_file)

    # Ingest 3 mock runs
    store.log_run(RunRecord(
        run_id="run-1", timestamp="2026-10-04T12:00:00Z",
        prompt_id="event_brief", prompt_version="v1.0.0",
        model_name="mock-fast", routing_policy=RoutingPolicy.SPEED_FIRST,
        input_text="Brief 1", raw_output="{}", is_valid=True,
        repair_tier=RepairTier.NONE, prompt_tokens=100, completion_tokens=200,
        total_tokens=300, latency_ms=100.0, cost_usd=0.0001
    ))
    store.log_run(RunRecord(
        run_id="run-2", timestamp="2026-10-04T12:01:00Z",
        prompt_id="event_brief", prompt_version="v2.0.0",
        model_name="mock-fast", routing_policy=RoutingPolicy.SPEED_FIRST,
        input_text="Brief 2", raw_output="{}", is_valid=True,
        repair_tier=RepairTier.AST_REGEX, prompt_tokens=150, completion_tokens=250,
        total_tokens=400, latency_ms=200.0, cost_usd=0.00015
    ))
    store.log_run(RunRecord(
        run_id="run-3", timestamp="2026-10-04T12:02:00Z",
        prompt_id="event_brief", prompt_version="v2.0.0",
        model_name="mock-fast", routing_policy=RoutingPolicy.SPEED_FIRST,
        input_text="Brief 3", raw_output="{}", is_valid=False,
        repair_tier=RepairTier.FAILED, prompt_tokens=50, completion_tokens=50,
        total_tokens=100, latency_ms=50.0, cost_usd=0.00005
    ))

    summary_all = store.compute_summary()
    assert summary_all["total_runs"] == 3
    assert summary_all["valid_runs"] == 2
    assert summary_all["schema_validity_percent"] == 66.67
    assert summary_all["total_tokens"] == 800

    # Filtered by version v2.0.0
    summary_v2 = store.compute_summary(prompt_version="v2.0.0")
    assert summary_v2["total_runs"] == 2
    assert summary_v2["valid_runs"] == 1
    assert summary_v2["repair_distribution"]["ast_regex"] == 1
    assert summary_v2["repair_distribution"]["failed"] == 1


def test_policy_router_selection():
    """Verify router policy dispatching for SPEED_FIRST, QUALITY_FIRST, and COST_OPTIMIZED."""
    adapters = {
        "mock-fast": ChaosMockAdapter(model_name="mock-fast", mode=ChaosMode.PERFECT),
        "mock-heavy": ChaosMockAdapter(model_name="mock-heavy", mode=ChaosMode.PERFECT),
    }
    router = PolicyRouter(adapters=adapters)

    # SPEED_FIRST selects mock-fast
    adapter, rationale = router.select_adapter(policy=RoutingPolicy.SPEED_FIRST)
    assert adapter.model_name == "mock-fast"
    assert "high-throughput tier" in rationale

    # QUALITY_FIRST selects mock-heavy
    adapter, rationale = router.select_adapter(policy=RoutingPolicy.QUALITY_FIRST)
    assert adapter.model_name == "mock-heavy"
    assert "frontier reasoning tier" in rationale

    # COST_OPTIMIZED on short input selects mock-fast
    short_input = "Quick meetup for 20 people."
    adapter, rationale = router.select_adapter(policy=RoutingPolicy.COST_OPTIMIZED, input_text=short_input)
    assert adapter.model_name == "mock-fast"
    assert "economical tier" in rationale

    # COST_OPTIMIZED on long input (> 800 chars) selects mock-heavy
    long_input = "Detailed brief: " + ("Requirement details and agenda breakdown. " * 30)
    adapter, rationale = router.select_adapter(policy=RoutingPolicy.COST_OPTIMIZED, input_text=long_input)
    assert adapter.model_name == "mock-heavy"
    assert "routed to heavy tier" in rationale


@pytest.mark.asyncio
async def test_policy_router_fallback_cascade_on_timeout():
    """Verify router automatically cascades to healthy secondary model when primary hangs."""
    # Primary adapter hangs past timeout
    hang_adapter = ChaosMockAdapter(model_name="mock-hang", mode=ChaosMode.TIMEOUT)
    healthy_adapter = ChaosMockAdapter(model_name="mock-fast", mode=ChaosMode.PERFECT, simulated_latency_ms=5.0)

    adapters = {
        "mock-hang": hang_adapter,
        "mock-fast": healthy_adapter,
    }
    router = PolicyRouter(adapters=adapters, fallback_chain=["mock-hang", "mock-fast"])

    # Timeout set to 0.15s, primary hangs for 20s
    result, rationale = await router.execute_with_fallback(
        policy=RoutingPolicy.CASCADE_FALLBACK,
        prompt="Execute with fallback",
        timeout_seconds=0.15,
    )

    # Generation succeeded despite primary failure!
    assert result.model_name == "mock-fast"
    assert "mock-hang failed" in rationale
    assert "Executed via 'mock-fast'" in rationale

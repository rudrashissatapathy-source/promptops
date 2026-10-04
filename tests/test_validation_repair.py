"""Comprehensive tests for the 3-Tier Self-Healing and Validation Pipeline."""

import json
import pytest

from promptops.models.telemetry import RepairTier
from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
from promptops.pipeline.orchestrator import SelfHealingPipeline
from promptops.pipeline.ast_repair import deterministic_repair


@pytest.mark.asyncio
async def test_tier1_clean_json_passes_with_zero_overhead():
    """Verify clean JSON passes Tier 1 direct validation with RepairTier.NONE."""
    adapter = ChaosMockAdapter(mode=ChaosMode.PERFECT)
    gen_result = await adapter.generate(prompt="Sample clean event")

    pipeline = SelfHealingPipeline(enable_llm_reflection=False)
    result = await pipeline.process(raw_text=gen_result.raw_text, adapter=adapter)

    assert result.is_valid is True
    assert result.artifact is not None
    assert result.repair_tier == RepairTier.NONE
    assert "Tier 1 Direct Validation" in result.repair_notes


@pytest.mark.asyncio
async def test_tier2_markdown_fences_healed():
    """Verify markdown fences and conversational wrapper are healed by Tier 2."""
    adapter = ChaosMockAdapter(mode=ChaosMode.MARKDOWN_FENCED)
    gen_result = await adapter.generate(prompt="Sample fenced event")

    pipeline = SelfHealingPipeline(enable_llm_reflection=False)
    result = await pipeline.process(raw_text=gen_result.raw_text, adapter=adapter)

    assert result.is_valid is True
    assert result.artifact is not None
    assert result.repair_tier == RepairTier.AST_REGEX
    assert "Stripped markdown code fence" in result.repair_notes


@pytest.mark.asyncio
async def test_tier2_malformed_syntax_single_quotes_and_trailing_commas():
    """Verify single quotes and trailing commas are healed by Tier 2 AST repair."""
    adapter = ChaosMockAdapter(mode=ChaosMode.MALFORMED_SYNTAX)
    gen_result = await adapter.generate(prompt="Sample malformed event")

    pipeline = SelfHealingPipeline(enable_llm_reflection=False)
    result = await pipeline.process(raw_text=gen_result.raw_text, adapter=adapter)

    assert result.is_valid is True
    assert result.artifact is not None
    assert result.repair_tier == RepairTier.AST_REGEX
    assert result.artifact.event_metadata.title == "Malformed JSON Sample"


@pytest.mark.asyncio
async def test_tier2_truncated_unbalanced_braces_healed():
    """Verify missing closing brackets/braces are dynamically balanced."""
    truncated = '{"event_metadata": {"title": "Truncated Event", "event_type": "summit", "target_audience": "Devs", "estimated_attendees": 100, "budget_tier": "medium", "primary_objective": "Fix syntax"}}'
    # Intentionally strip off the last closing brace
    broken = truncated[:-1]
    
    success, repaired_dict, notes = deterministic_repair(broken)
    assert success is True
    assert repaired_dict["event_metadata"]["title"] == "Truncated Event"
    assert "Balanced truncated syntax" in notes


@pytest.mark.asyncio
async def test_tier3_schema_violation_healed_via_llm_reflector():
    """Verify missing mandatory fields trigger Tier 3 LLM Reflection and heal."""
    # ChaosMode.SCHEMA_VIOLATION produces JSON missing the 'schedule' key
    failing_adapter = ChaosMockAdapter(mode=ChaosMode.SCHEMA_VIOLATION)
    gen_result = await failing_adapter.generate(prompt="Sample schema error event")

    # The reflector adapter will simulate returning clean JSON
    repairing_adapter = ChaosMockAdapter(mode=ChaosMode.PERFECT)

    pipeline = SelfHealingPipeline(enable_llm_reflection=True)
    result = await pipeline.process(raw_text=gen_result.raw_text, adapter=repairing_adapter)

    assert result.is_valid is True
    assert result.artifact is not None
    assert result.repair_tier == RepairTier.LLM_REFLECTOR
    assert "Healed via Level 3 LLM Reflection" in result.repair_notes


@pytest.mark.asyncio
async def test_unsalvageable_garbage_fails_gracefully():
    """Verify random text returns is_valid=False without crashing."""
    garbage = "This is not JSON at all, just a random error page 404 Not Found."
    pipeline = SelfHealingPipeline(enable_llm_reflection=False)
    result = await pipeline.process(raw_text=garbage, adapter=None)

    assert result.is_valid is False
    assert result.artifact is None
    assert result.repair_tier == RepairTier.FAILED
    assert result.error_message is not None

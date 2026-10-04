"""Unit tests for the Provider Adapter Layer and Chaos Mock Engine."""

import asyncio
import json
import pytest

from promptops.adapters.base import BaseModelAdapter
from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
from promptops.adapters.gemini import GeminiAdapter
from promptops.adapters.openai_like import OpenAILikeAdapter
from promptops.models.domain import EventArtifact


@pytest.mark.asyncio
async def test_mock_perfect_mode():
    """Verify that perfect mode produces valid, parseable EventArtifact JSON."""
    adapter = ChaosMockAdapter(model_name="mock-fast", mode=ChaosMode.PERFECT, simulated_latency_ms=10.0)
    result = await adapter.generate(prompt="Organize an AI architecture workshop for 150 engineers.")
    
    assert result.model_name == "mock-fast"
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0
    assert result.latency_ms > 0
    assert result.cost_usd > 0
    
    # Must parse cleanly into domain schema
    parsed_json = json.loads(result.raw_text)
    artifact = EventArtifact.model_validate(parsed_json)
    assert artifact.event_metadata.estimated_attendees == 150
    assert len(artifact.schedule) >= 1
    assert len(artifact.action_items) >= 1


@pytest.mark.asyncio
async def test_mock_markdown_fenced_mode():
    """Verify that markdown fenced mode injects conversational text and code fences."""
    adapter = ChaosMockAdapter(mode=ChaosMode.MARKDOWN_FENCED, simulated_latency_ms=5.0)
    result = await adapter.generate(prompt="Event brief test")
    
    assert "```json" in result.raw_text
    assert "Sure! Here is the structured" in result.raw_text
    # Raw text itself is NOT valid JSON without extraction
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.raw_text)


@pytest.mark.asyncio
async def test_mock_malformed_syntax_mode():
    """Verify that malformed syntax mode outputs single quotes and trailing commas."""
    adapter = ChaosMockAdapter(mode=ChaosMode.MALFORMED_SYNTAX, simulated_latency_ms=5.0)
    result = await adapter.generate(prompt="Event brief test")
    
    assert "'" in result.raw_text
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.raw_text)


@pytest.mark.asyncio
async def test_mock_schema_violation_mode():
    """Verify that schema violation mode produces valid JSON with missing required fields."""
    adapter = ChaosMockAdapter(mode=ChaosMode.SCHEMA_VIOLATION, simulated_latency_ms=5.0)
    result = await adapter.generate(prompt="Event brief test")
    
    parsed = json.loads(result.raw_text)
    assert "schedule" not in parsed
    assert parsed["event_metadata"]["event_type"] == "unsupported_event_category"


@pytest.mark.asyncio
async def test_mock_timeout_simulation():
    """Verify that timeout mode properly triggers asyncio TimeoutError."""
    adapter = ChaosMockAdapter(mode=ChaosMode.TIMEOUT, simulated_latency_ms=0.0)
    
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(adapter.generate(prompt="Hang test"), timeout=0.15)


@pytest.mark.asyncio
async def test_mock_streaming():
    """Verify that stream generation yields chunks with indices and finish reason."""
    adapter = ChaosMockAdapter(mode=ChaosMode.PERFECT, simulated_latency_ms=5.0)
    chunks = []
    
    async for chunk in adapter.generate_stream(prompt="Stream test"):
        chunks.append(chunk)
        
    assert len(chunks) > 5
    assert chunks[0].index == 0
    assert chunks[-1].finish_reason == "stop"
    
    full_text = "".join(c.delta for c in chunks)
    parsed = json.loads(full_text)
    assert "event_metadata" in parsed


@pytest.mark.asyncio
async def test_mock_interrupted_stream():
    """Verify that interrupted stream mode simulates mid-stream connection reset."""
    adapter = ChaosMockAdapter(mode=ChaosMode.INTERRUPTED_STREAM, simulated_latency_ms=5.0)
    
    received_chunks = []
    with pytest.raises(ConnectionResetError) as exc_info:
        async for chunk in adapter.generate_stream(prompt="Stream fail test"):
            received_chunks.append(chunk)
            
    assert len(received_chunks) == 3
    assert "streaming socket terminated prematurely" in str(exc_info.value)


def test_missing_api_keys_raise_informative_errors(monkeypatch):
    """Verify that real adapters give informative error messages when environment keys are missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    gemini_adapter = GeminiAdapter(model_name="gemini-2.5-flash", api_key=None)
    with pytest.raises(ValueError) as exc:
        gemini_adapter._ensure_client()
    assert "GEMINI_API_KEY is not set" in str(exc.value)

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    openai_adapter = OpenAILikeAdapter(model_name="gpt-4o-mini", api_key=None, base_url="https://api.openai.com/v1")
    with pytest.raises(ValueError) as exc2:
        asyncio.run(openai_adapter.generate(prompt="test"))
    assert "OPENAI_API_KEY is not set" in str(exc2.value)

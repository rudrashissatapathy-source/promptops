"""Telemetry, execution tracking, and benchmarking data structures."""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class RoutingPolicy(str, Enum):
    """Dynamic routing strategies."""
    QUALITY_FIRST = "quality_first"
    SPEED_FIRST = "speed_first"
    COST_OPTIMIZED = "cost_optimized"
    CASCADE_FALLBACK = "cascade_fallback"


class RepairTier(str, Enum):
    """Classification of how output achieved schema validity."""
    NONE = "none"                   # Valid on first try (Level 1)
    AST_REGEX = "ast_regex"         # Healed by deterministic AST / Regex (Level 2)
    LLM_REFLECTOR = "llm_reflector" # Healed by LLM Reflection pass (Level 3)
    FAILED = "failed"               # Unsalvageable error / hard validation rejection


class StreamChunk(BaseModel):
    """Individual chunk yielded during streaming generation."""
    delta: str
    finish_reason: Optional[str] = None
    index: int = 0


class GenerationResult(BaseModel):
    """Standardized output from any backend model adapter."""
    raw_text: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    ttft_ms: Optional[float] = None  # Time-to-first-token in milliseconds
    finish_reason: str = "stop"
    cost_usd: float = 0.0


class RunRecord(BaseModel):
    """Immutable audit record of a single generation request."""
    run_id: str = Field(..., description="UUID4 run identifier")
    timestamp: str = Field(..., description="ISO 8601 execution timestamp")
    prompt_id: str
    prompt_version: str
    model_name: str
    routing_policy: RoutingPolicy
    input_text: str
    raw_output: str
    validated_artifact: Optional[Dict[str, Any]] = None
    is_valid: bool = False
    repair_tier: RepairTier = RepairTier.NONE
    repair_notes: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    ttft_ms: Optional[float] = None
    cost_usd: float = 0.0
    cache_hit: bool = False
    error: Optional[str] = None


class BenchmarkCase(BaseModel):
    """Fixed empirical test case definition."""
    id: str
    category: str
    title: str
    raw_input: str
    expected_event_type: Optional[str] = None
    min_schedule_items: int = 1
    min_action_items: int = 1
    adversarial_trigger: Optional[str] = None


class BenchmarkResult(BaseModel):
    """Result of running a single benchmark case through a specific configuration."""
    case_id: str
    category: str
    prompt_version: str
    model_name: str
    schema_valid: bool
    instruction_followed: bool
    repair_applied: bool
    repair_tier: RepairTier
    latency_ms: float
    ttft_ms: Optional[float] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    error_message: Optional[str] = None

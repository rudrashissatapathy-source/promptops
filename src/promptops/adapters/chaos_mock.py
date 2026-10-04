"""Deterministic Chaos Mock Adapter.

Provides reproducible generation and streaming with explicit fault and chaos injection
for testing timeouts, malformed syntax, schema violations, and interrupted streaming.
"""

import asyncio
import json
import time
from enum import Enum
from typing import AsyncIterator, Optional, Dict, Any

from promptops.adapters.base import BaseModelAdapter
from promptops.models.telemetry import GenerationResult, StreamChunk


class ChaosMode(str, Enum):
    """Execution mode for the Chaos Mock Adapter."""
    PERFECT = "perfect"                       # Valid JSON, fast response
    MARKDOWN_FENCED = "markdown_fenced"       # Valid JSON wrapped in ```json and conversational text
    MALFORMED_SYNTAX = "malformed_syntax"     # Invalid JSON syntax (trailing commas, unclosed quotes)
    SCHEMA_VIOLATION = "schema_violation"     # Valid JSON syntax but missing mandatory schema fields
    TIMEOUT = "timeout"                       # Simulates high latency causing client timeout
    INTERRUPTED_STREAM = "interrupted_stream" # Yields partial chunks then raises an abrupt error


class ChaosMockAdapter(BaseModelAdapter):
    """Deterministic Mock Adapter with chaos injection capabilities."""

    def __init__(
        self,
        model_name: str = "mock-fast",
        mode: ChaosMode = ChaosMode.PERFECT,
        simulated_latency_ms: float = 80.0,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name=model_name, config=config)
        self.mode = mode
        self.simulated_latency_ms = simulated_latency_ms

    def set_mode(self, mode: ChaosMode) -> None:
        """Dynamically update chaos injection mode."""
        self.mode = mode

    def _generate_payload(self, prompt: str) -> str:
        """Produce deterministic mock payload corresponding to the active chaos mode."""
        # Derive a topic from the prompt or use fallback
        topic = "AI & Cloud Architecture Operations"
        if "workshop" in prompt.lower():
            topic = "Hands-on Controlled LLM Generation Workshop"
        elif "hackathon" in prompt.lower():
            topic = "Global Agentic AI Hackathon 2026"
        elif "webinar" in prompt.lower():
            topic = "PromptOps Architecture Webinar"

        clean_dict = {
            "event_metadata": {
                "title": topic,
                "event_type": "workshop" if "workshop" in prompt.lower() else "summit",
                "target_audience": "Principal Engineers and Technical Leads",
                "estimated_attendees": 150,
                "budget_tier": "medium",
                "primary_objective": "Master deterministic LLM pipelines and automated self-healing validation."
            },
            "schedule": [
                {
                    "time_slot": "09:00 - 10:30 AM",
                    "session_title": "Deep Dive: Building Resilient Generation Pipelines",
                    "format": "keynote",
                    "speaker_role": "Staff Platform Engineer",
                    "deliverables": ["Production Architecture Blueprint", "AST Repair Cheatsheet"]
                },
                {
                    "time_slot": "10:45 - 12:30 PM",
                    "session_title": "Lab: Multi-Tier Self-Healing and Error Feedback Loops",
                    "format": "hands-on",
                    "speaker_role": "Lead Systems Architect",
                    "deliverables": ["Sample Test Harness", "Docker Compose Sandbox"]
                },
                {
                    "time_slot": "14:00 - 15:30 PM",
                    "session_title": "Panel: Scalable Telemetry, Cost Accounting, and Policy Routing",
                    "format": "panel",
                    "speaker_role": "VP of Engineering & Industry Panelists",
                    "deliverables": ["SLO Benchmark Report", "Session Recording"]
                }
            ],
            "action_items": [
                {
                    "id": "TASK-01",
                    "task": "Provision sandbox environments and pre-seed benchmark datasets",
                    "owner_role": "Infrastructure Lead",
                    "priority": "critical",
                    "due_relative_days": -14,
                    "dependencies": []
                },
                {
                    "id": "TASK-02",
                    "task": "Distribute pre-session setup guide and API keys to attendees",
                    "owner_role": "Community Coordinator",
                    "priority": "high",
                    "due_relative_days": -3,
                    "dependencies": ["TASK-01"]
                },
                {
                    "id": "TASK-03",
                    "task": "Verify AV recording setup and backup streaming link",
                    "owner_role": "Media Operations",
                    "priority": "medium",
                    "due_relative_days": -1,
                    "dependencies": ["TASK-01"]
                }
            ],
            "multi_channel_copy": {
                "slack_announcement": f":zap: *Upcoming Session: {topic}*\nJoin us for a rigorous deep-dive into controlled generation architectures. Reserve your seat now!",
                "email_invitation": {
                    "subject": f"Invitation: {topic}",
                    "preview_text": "Join our comprehensive technical deep-dive into controlled generation.",
                    "body": f"Hi Team,\n\nWe are excited to host '{topic}'. We will review production prompt registries, AST repair mechanisms, and multi-model routing.\n\nSign up today!\n\nBest,\nPromptOps Team"
                },
                "social_x_thread": [
                    f"1/2 Announcing {topic}! Move beyond toy prompts with production-grade validation and automated self-healing. #PromptOps #AI",
                    "2/2 Registration is now open. Limited to 150 participants to ensure deep technical focus: https://promptops.dev/register"
                ]
            }
        }

        if self.mode == ChaosMode.PERFECT:
            return json.dumps(clean_dict, indent=2)

        elif self.mode == ChaosMode.MARKDOWN_FENCED:
            raw_json = json.dumps(clean_dict, indent=2)
            return (
                "Sure! Here is the structured operational brief you requested:\n\n"
                f"```json\n{raw_json}\n```\n\n"
                "I hope this helps! Let me know if you need any adjustments."
            )

        elif self.mode == ChaosMode.MALFORMED_SYNTAX:
            # Trailing commas, single quotes, and missing closing bracket
            return """{
  'event_metadata': {
    'title': 'Malformed JSON Sample',
    'event_type': 'summit',
    'target_audience': 'Engineers',
    'estimated_attendees': 100,
    'budget_tier': 'medium',
    'primary_objective': 'Demonstrate AST syntax repair.',
  },
  'schedule': [
    {
      'time_slot': '10:00 AM',
      'session_title': 'Syntax Repair Session',
      'format': 'keynote',
      'speaker_role': 'Engineer',
      'deliverables': ['Repair Spec',],
    },
  ],
  'action_items': [
    {
      'id': 'TASK-01',
      'task': 'Fix broken brackets',
      'owner_role': 'Dev',
      'priority': 'critical',
      'due_relative_days': -1,
      'dependencies': [],
    },
  ],
  'multi_channel_copy': {
    'slack_announcement': 'Broken syntax broadcast test',
    'email_invitation': {
      'subject': 'Syntax Repair Invite',
      'preview_text': 'Preview test',
      'body': 'This body was generated with single quotes and trailing commas for test verification.',
    },
    'social_x_thread': [
      '1/1 Syntax repair testing in progress. #DevOps',
    ],
  }
"""

        elif self.mode == ChaosMode.SCHEMA_VIOLATION:
            # Missing schedule and invalid event_type
            broken_dict = clean_dict.copy()
            broken_dict["event_metadata"]["event_type"] = "unsupported_event_category"
            del broken_dict["schedule"]
            return json.dumps(broken_dict, indent=2)

        return json.dumps(clean_dict, indent=2)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> GenerationResult:
        """Simulate generation with realistic latency and chaos injection."""
        start_time = time.perf_counter()

        if self.mode == ChaosMode.TIMEOUT:
            # Simulate a hang exceeding common timeout (sleep 20 seconds)
            await asyncio.sleep(20.0)

        # Normal latency simulation
        latency_secs = self.simulated_latency_ms / 1000.0
        if latency_secs > 0:
            await asyncio.sleep(latency_secs)

        raw_text = self._generate_payload(prompt)
        prompt_tokens = self.count_tokens(prompt + system_prompt)
        completion_tokens = self.count_tokens(raw_text)
        total_tokens = prompt_tokens + completion_tokens
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        cost_usd = self.estimate_cost(prompt_tokens, completion_tokens)

        return GenerationResult(
            raw_text=raw_text,
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=elapsed_ms,
            ttft_ms=elapsed_ms * 0.4,
            finish_reason="stop",
            cost_usd=cost_usd,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Simulate token streaming in realistic chunks."""
        if self.mode == ChaosMode.TIMEOUT:
            await asyncio.sleep(20.0)

        raw_text = self._generate_payload(prompt)
        
        # Split text into chunks (~20 characters per chunk)
        chunk_size = 25
        chunks = [raw_text[i:i + chunk_size] for i in range(0, len(raw_text), chunk_size)]

        for idx, chunk_text in enumerate(chunks):
            # Check for interrupted stream chaos mode
            if self.mode == ChaosMode.INTERRUPTED_STREAM and idx == 3:
                raise ConnectionResetError(
                    "Simulated chaos fault: streaming socket terminated prematurely by remote model host"
                )

            # Small inter-chunk delay (~15ms)
            await asyncio.sleep(0.015)
            is_last = (idx == len(chunks) - 1)
            yield StreamChunk(
                delta=chunk_text,
                finish_reason="stop" if is_last else None,
                index=idx,
            )

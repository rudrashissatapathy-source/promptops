"""Comprehensive test suite for Phase 1 Domain Schemas and Telemetry Models."""

import json
import pytest
from pydantic import ValidationError

from promptops.models.domain import (
    EventType,
    BudgetTier,
    PriorityLevel,
    SessionFormat,
    EventMetadata,
    ScheduleItem,
    ActionItem,
    EmailInvitation,
    MultiChannelCopy,
    EventArtifact,
)
from promptops.models.telemetry import (
    RoutingPolicy,
    RepairTier,
    GenerationResult,
    RunRecord,
    BenchmarkCase,
)
from promptops.config import MODEL_PRICING, SCHEMAS_DIR


def get_valid_sample_dict():
    """Return a pristine, valid domain payload."""
    return {
        "event_metadata": {
            "title": "Cloud Native & AI Operations Summit 2026",
            "event_type": "summit",
            "target_audience": "Principal Platform Engineers, DevOps Leads, and AI Architects",
            "estimated_attendees": 450,
            "budget_tier": "enterprise",
            "primary_objective": "Establish operational standards for production AI agent deployment and telemetry."
        },
        "schedule": [
            {
                "time_slot": "09:00 - 10:00 AM",
                "session_title": "Opening Keynote: The State of Controlled LLM Operations",
                "format": "keynote",
                "speaker_role": "VP of AI Infrastructure",
                "deliverables": ["Keynote Recording", "State of PromptOps 2026 Whitepaper"]
            },
            {
                "time_slot": "10:15 - 11:45 AM",
                "session_title": "Workshop: Self-Healing JSON Pipelines in Production",
                "format": "hands-on",
                "speaker_role": "Lead Architect",
                "deliverables": ["GitHub Starter Repo", "Docker Sandbox Environment"]
            }
        ],
        "action_items": [
            {
                "id": "TASK-01",
                "task": "Finalize venue contract and AV stream redundancy provider",
                "owner_role": "Operations Director",
                "priority": "critical",
                "due_relative_days": -30,
                "dependencies": []
            },
            {
                "id": "TASK-02",
                "task": "Publish speaker line-up and initial registration portal",
                "owner_role": "Marketing Lead",
                "priority": "high",
                "due_relative_days": -21,
                "dependencies": ["TASK-01"]
            }
        ],
        "multi_channel_copy": {
            "slack_announcement": ":rocket: *Announcing Cloud Native & AI Operations Summit 2026!*\nJoin 450+ engineering leaders on Nov 15 for deep-dive sessions on reliable LLM systems. Register now!",
            "email_invitation": {
                "subject": "Exclusive Invitation: Cloud Native & AI Operations Summit",
                "preview_text": "Join 450+ engineering leaders shaping production LLM architecture.",
                "body": "Dear Colleague,\n\nWe are excited to invite you to the Cloud Native & AI Operations Summit 2026. This summit brings together the industry's top architects to tackle reliable generation, automated self-healing pipelines, and resilient prompt engineering.\n\nReserve your pass today.\n\nBest regards,\nThe PromptOps Committee"
            },
            "social_x_thread": [
                "1/4 We're thrilled to announce the Cloud Native & AI Operations Summit 2026! How do you move beyond toy prompt demos into controlled generation? Let's discuss. #PromptOps #AI #DevOps",
                "2/4 Featuring hands-on workshops on self-healing JSON pipelines, AST repair, and provider-agnostic LLM routing. No fluff, pure engineering.",
                "3/4 Keynotes from industry leaders deploying agents at scale. Capacity is strictly capped at 450 attendees.",
                "4/4 Early bird registration is officially live. Secure your spot now: https://summit2026.promptops.dev"
            ]
        }
    }


def test_valid_event_artifact_parsing():
    """Verify that a standard valid payload parses and validates without errors."""
    data = get_valid_sample_dict()
    artifact = EventArtifact.model_validate(data)
    
    assert artifact.event_metadata.title == "Cloud Native & AI Operations Summit 2026"
    assert artifact.event_metadata.event_type == EventType.SUMMIT
    assert artifact.event_metadata.estimated_attendees == 450
    assert len(artifact.schedule) == 2
    assert len(artifact.action_items) == 2
    assert len(artifact.multi_channel_copy.social_x_thread) == 4
    
    # Check serialization
    dumped = artifact.model_dump()
    assert dumped["event_metadata"]["event_type"] == "summit"
    assert json.loads(artifact.model_dump_json()) == dumped


def test_missing_required_fields_fails():
    """Verify that missing top-level or nested required fields trigger ValidationError."""
    data = get_valid_sample_dict()
    del data["event_metadata"]["title"]
    
    with pytest.raises(ValidationError) as exc_info:
        EventArtifact.model_validate(data)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("event_metadata", "title") for e in errors)


def test_invalid_enum_rejected():
    """Verify that unsupported enum values are strictly rejected."""
    data = get_valid_sample_dict()
    data["event_metadata"]["event_type"] = "rock_concert"
    
    with pytest.raises(ValidationError) as exc_info:
        EventArtifact.model_validate(data)
    assert "event_type" in str(exc_info.value)

    data = get_valid_sample_dict()
    data["action_items"][0]["priority"] = "whenever_possible"
    with pytest.raises(ValidationError) as exc_info:
        EventArtifact.model_validate(data)
    assert "priority" in str(exc_info.value)


def test_tweet_length_constraints():
    """Verify that tweets over 280 characters or under 5 characters are rejected."""
    data = get_valid_sample_dict()
    # Tweet exceeding 280 chars
    data["multi_channel_copy"]["social_x_thread"][0] = "A" * 285
    
    with pytest.raises(ValidationError) as exc_info:
        EventArtifact.model_validate(data)
    assert "exceeds 280 character limit" in str(exc_info.value)

    # Tweet too short
    data = get_valid_sample_dict()
    data["multi_channel_copy"]["social_x_thread"][0] = "Hi"
    with pytest.raises(ValidationError) as exc_info:
        EventArtifact.model_validate(data)
    assert "too short" in str(exc_info.value)


def test_attendee_bounds():
    """Verify bounds checking on attendee counts."""
    data = get_valid_sample_dict()
    data["event_metadata"]["estimated_attendees"] = 0
    with pytest.raises(ValidationError):
        EventArtifact.model_validate(data)

    data["event_metadata"]["estimated_attendees"] = -10
    with pytest.raises(ValidationError):
        EventArtifact.model_validate(data)


def test_self_dependency_rejected():
    """Verify that a task cannot declare a dependency on itself."""
    data = get_valid_sample_dict()
    data["action_items"][0]["dependencies"] = ["TASK-01"]
    
    with pytest.raises(ValidationError) as exc_info:
        EventArtifact.model_validate(data)
    assert "cannot depend on itself" in str(exc_info.value)


def test_json_schema_file_matches_pydantic_schema():
    """Verify that the generated JSON schema in schemas/ matches the model definition."""
    schema_file = SCHEMAS_DIR / "event_artifact.json"
    assert schema_file.exists(), "schemas/event_artifact.json must exist"
    
    with open(schema_file, "r", encoding="utf-8") as f:
        file_schema = json.load(f)
    
    pydantic_schema = EventArtifact.model_json_schema()
    
    # Key properties must match
    assert "event_metadata" in file_schema["properties"]
    assert "schedule" in file_schema["properties"]
    assert "action_items" in file_schema["properties"]
    assert "multi_channel_copy" in file_schema["properties"]
    assert set(file_schema["required"]) == {"event_metadata", "schedule", "action_items", "multi_channel_copy"}


def test_telemetry_run_record():
    """Verify telemetry RunRecord structure and validation."""
    record = RunRecord(
        run_id="run-123e4567-e89b",
        timestamp="2026-10-04T12:00:00Z",
        prompt_id="event_brief_synthesizer",
        prompt_version="v2.0.0",
        model_name="mock-fast",
        routing_policy=RoutingPolicy.SPEED_FIRST,
        input_text="Need a quick workshop for 50 devs on Saturday.",
        raw_output="{}",
        is_valid=True,
        repair_tier=RepairTier.NONE,
        prompt_tokens=150,
        completion_tokens=420,
        total_tokens=570,
        latency_ms=185.4,
        cost_usd=0.000183,
        cache_hit=False
    )
    assert record.prompt_tokens == 150
    assert record.total_tokens == 570
    assert record.repair_tier == RepairTier.NONE
    assert record.cost_usd > 0


def test_cost_calculation_model_pricing():
    """Verify that model pricing table has valid positive numbers for all registered models."""
    for model_name, pricing in MODEL_PRICING.items():
        assert "input_per_million" in pricing
        assert "output_per_million" in pricing
        assert pricing["input_per_million"] >= 0
        assert pricing["output_per_million"] >= 0

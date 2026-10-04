"""Unit and integration tests for PromptOps Deliverables & Export Engine."""

import pytest
from starlette.testclient import TestClient

from promptops.server.app import app
from promptops.models.domain import (
    EventArtifact,
    EventMetadata,
    EventType,
    BudgetTier,
    ScheduleItem,
    SessionFormat,
    ActionItem,
    PriorityLevel,
    MultiChannelCopy,
    EmailInvitation,
)
from promptops.exporters import export_to_markdown, export_to_ics, export_tasks_to_csv


@pytest.fixture
def sample_artifact() -> EventArtifact:
    return EventArtifact(
        event_metadata=EventMetadata(
            title="Global AI Systems Architecture Summit",
            event_type=EventType.SUMMIT,
            target_audience="Senior ML Infrastructure and Distributed Systems Engineers",
            estimated_attendees=600,
            budget_tier=BudgetTier.ENTERPRISE,
            primary_objective="Establish industry best practices for controlled LLM generation and low-latency inference.",
        ),
        schedule=[
            ScheduleItem(
                time_slot="09:00 - 10:00 AM",
                session_title="Opening Keynote: Deterministic Agent Architectures",
                format=SessionFormat.KEYNOTE,
                speaker_role="VP of Engineering",
                deliverables=["Architecture Reference Blueprint", "Keynote Video Recording"],
            ),
            ScheduleItem(
                time_slot="10:15 - 12:00 PM",
                session_title="Hands-On Lab: AST-Based JSON Self-Healing",
                format=SessionFormat.HANDS_ON,
                speaker_role="Staff Compiler Engineer",
                deliverables=["GitHub Repo Template", "Passing Test Suite"],
            ),
        ],
        action_items=[
            ActionItem(
                id="TASK-01",
                task="Secure auditorium venue and finalize A/V streaming contract",
                owner_role="Head of Operations",
                priority=PriorityLevel.CRITICAL,
                due_relative_days=-30,
                dependencies=["BUDGET-APPROVED"],
            ),
            ActionItem(
                id="TASK-02",
                task="Publish keynote speaker schedule on landing page",
                owner_role="Marketing Lead",
                priority=PriorityLevel.HIGH,
                due_relative_days=-14,
                dependencies=["TASK-01"],
            ),
        ],
        multi_channel_copy=MultiChannelCopy(
            slack_announcement="🚀 *Global AI Systems Architecture Summit* is officially announced! Join 600+ top engineers.",
            email_invitation=EmailInvitation(
                subject="Exclusive Invitation: Global AI Systems Summit",
                preview_text="Join 600+ engineering leaders on cutting-edge LLM ops.",
                body="Dear Colleague,\n\nWe are pleased to invite you to the Global AI Systems Architecture Summit.\n\nBest,\nThe Organizing Committee",
            ),
            social_x_thread=[
                "🚨 Announcing the Global AI Systems Architecture Summit! 600+ engineers, 2 tracks, pure zero-slop engineering. Details 👇 (1/2)",
                "Hands-on labs covering AST self-healing, deterministic routing, and cost accounting. Registration opens today: https://promptops.ai (2/2)",
            ],
        ),
    )


def test_export_to_markdown(sample_artifact):
    """Verify Markdown export contains all mandatory sections and tables."""
    md = export_to_markdown(sample_artifact)
    assert "# Global AI Systems Architecture Summit" in md
    assert "## 1. Executive Event Parameters" in md
    assert "## 2. Chronological Schedule & Timetable" in md
    assert "## 3. Work Breakdown Structure & Action Items" in md
    assert "## 4. Multi-Channel Communications Package" in md
    assert "Opening Keynote: Deterministic Agent Architectures" in md
    assert "TASK-01" in md
    assert "PromptOps Controlled Generation Platform" in md


def test_export_to_ics(sample_artifact):
    """Verify RFC 5545 compliance in iCalendar export."""
    ics = export_to_ics(sample_artifact)
    assert ics.startswith("BEGIN:VCALENDAR")
    assert "VERSION:2.0" in ics
    assert "PRODID:-//PromptOps//Event Synthesizer 0.1//EN" in ics
    assert "BEGIN:VEVENT" in ics
    assert "SUMMARY:Opening Keynote: Deterministic Agent Architectures" in ics
    assert "DTSTART:" in ics
    assert "DTEND:" in ics
    assert "END:VEVENT" in ics
    assert ics.strip().endswith("END:VCALENDAR")


def test_export_tasks_to_csv(sample_artifact):
    """Verify CSV action items formatting for Jira/Linear."""
    csv_text = export_tasks_to_csv(sample_artifact)
    lines = csv_text.strip().splitlines()
    assert len(lines) == 3  # Header + 2 tasks
    header = lines[0]
    assert "Issue Key" in header
    assert "Summary" in header
    assert "Priority" in header
    assert "TASK-01" in lines[1]
    assert "Critical" in lines[1]
    assert "TASK-02" in lines[2]
    assert "High" in lines[2]


def test_api_export_endpoints(sample_artifact):
    """Verify FastAPI export endpoints for Markdown, ICS, and CSV."""
    client = TestClient(app)
    payload = {"artifact": sample_artifact.model_dump()}

    # 1. Markdown JSON
    res_md = client.post("/api/export/markdown", json=payload)
    assert res_md.status_code == 200
    assert "markdown" in res_md.json()
    assert "Global AI Systems Architecture Summit" in res_md.json()["markdown"]

    # 2. Markdown Download Attachment
    res_md_dl = client.post("/api/export/markdown", json={**payload, "download": True})
    assert res_md_dl.status_code == 200
    assert "attachment;" in res_md_dl.headers.get("content-disposition", "")
    assert res_md_dl.text.startswith("# Global AI Systems Architecture Summit")

    # 3. iCalendar (.ics) Attachment
    res_ics = client.post("/api/export/ics", json=payload)
    assert res_ics.status_code == 200
    assert "text/calendar" in res_ics.headers.get("content-type", "")
    assert "BEGIN:VCALENDAR" in res_ics.text

    # 4. Tasks CSV Attachment
    res_csv = client.post("/api/export/tasks-csv", json=payload)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")
    assert "Issue Key,Summary" in res_csv.text

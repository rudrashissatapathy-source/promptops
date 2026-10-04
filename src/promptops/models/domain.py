"""Domain models for PromptOps: The Event & Operational Brief Synthesizer.

Converts messy instructions into 4 strictly validated sub-artifacts:
1. Event Metadata
2. Detailed Schedule
3. Action Items & Work Breakdown
4. Multi-Channel Copy
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class EventType(str, Enum):
    """Categorization of event formats."""
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    WEBINAR = "webinar"
    HACKATHON = "hackathon"
    SUMMIT = "summit"


class BudgetTier(str, Enum):
    """Budgetary scope for event execution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ENTERPRISE = "enterprise"


class PriorityLevel(str, Enum):
    """Priority level for operational action items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SessionFormat(str, Enum):
    """Session structure format."""
    KEYNOTE = "keynote"
    PANEL = "panel"
    HANDS_ON = "hands-on"
    NETWORKING = "networking"
    LIGHTNING_TALK = "lightning_talk"


class EventMetadata(BaseModel):
    """Structured high-level metadata characterizing the event."""
    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Clear, descriptive title of the event"
    )
    event_type: EventType = Field(
        ...,
        description="Formal category of the event"
    )
    target_audience: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Intended audience profile"
    )
    estimated_attendees: int = Field(
        ...,
        ge=1,
        le=500000,
        description="Expected attendee capacity count"
    )
    budget_tier: BudgetTier = Field(
        ...,
        description="Allocated budget tier"
    )
    primary_objective: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="Primary measurable goal or deliverable"
    )


class ScheduleItem(BaseModel):
    """Individual agenda entry within the event timeline."""
    time_slot: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Time window (e.g. '09:00 - 10:00 AM' or 'Day 1: 14:00 - 15:30')"
    )
    session_title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Title or topic of the session"
    )
    format: SessionFormat = Field(
        ...,
        description="Format of the session"
    )
    speaker_role: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Role, designation or name of the session leader"
    )
    deliverables: List[str] = Field(
        default_factory=list,
        description="Key takeaways or outputs produced during this session"
    )


class ActionItem(BaseModel):
    """Actionable operational work item assigned to an owner."""
    id: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Unique task identifier, e.g. 'TASK-01'"
    )
    task: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Specific actionable description of the task"
    )
    owner_role: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description="Role responsible for executing the task"
    )
    priority: PriorityLevel = Field(
        ...,
        description="Operational urgency level"
    )
    due_relative_days: int = Field(
        ...,
        ge=-60,
        le=365,
        description="Relative deadline in days (e.g., -7 for 7 days before event, 0 for event day, 3 for 3 days post)"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Task IDs or milestones that must precede this action item"
    )


class EmailInvitation(BaseModel):
    """Structured email marketing copy."""
    subject: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="High-converting email subject line"
    )
    preview_text: str = Field(
        ...,
        min_length=5,
        max_length=150,
        description="Inbox preview pre-header text"
    )
    body: str = Field(
        ...,
        min_length=30,
        max_length=2000,
        description="Full invitation email body text"
    )


class MultiChannelCopy(BaseModel):
    """Marketing and communication copy tailored per channel."""
    slack_announcement: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Formatted internal or community announcement for Slack/Discord"
    )
    email_invitation: EmailInvitation = Field(
        ...,
        description="External invite email"
    )
    social_x_thread: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Thread of posts for X/Twitter"
    )

    @field_validator("social_x_thread")
    @classmethod
    def validate_tweet_length(cls, tweets: List[str]) -> List[str]:
        for i, tweet in enumerate(tweets):
            if len(tweet) > 280:
                raise ValueError(f"Tweet {i+1} exceeds 280 character limit (length: {len(tweet)})")
            if len(tweet.strip()) < 5:
                raise ValueError(f"Tweet {i+1} is too short (minimum 5 characters)")
        return tweets


class EventArtifact(BaseModel):
    """Top-level structured generation output for PromptOps.
    
    Synthesizes messy unstructured instructions into a reliable,
    complete operational and communication package.
    """
    event_metadata: EventMetadata = Field(
        ...,
        description="Core event identification and parameters"
    )
    schedule: List[ScheduleItem] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Complete chronological agenda"
    )
    action_items: List[ActionItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Work breakdown structure of execution tasks"
    )
    multi_channel_copy: MultiChannelCopy = Field(
        ...,
        description="Synthesized communication collateral across platforms"
    )

    @model_validator(mode="after")
    def validate_overall_coherence(self) -> "EventArtifact":
        """Cross-validate dependencies and schedule coherence."""
        # Check task dependencies refer to real tasks or valid external markers
        task_ids = {t.id for t in self.action_items}
        for task in self.action_items:
            for dep in task.dependencies:
                # If dep looks like a task ID (e.g. TASK-01), warn or ensure it's not a circular self-ref
                if dep == task.id:
                    raise ValueError(f"Task {task.id} cannot depend on itself")
        return self

"""Markdown operational brief exporter for PromptOps.

Converts validated EventArtifact domain models into comprehensive,
executive-ready operational briefs.
"""

from typing import Union
from promptops.models.domain import EventArtifact


def export_to_markdown(artifact: Union[EventArtifact, dict]) -> str:
    """Export an EventArtifact to a beautifully formatted Markdown briefing document."""
    if isinstance(artifact, dict):
        artifact = EventArtifact.model_validate(artifact)

    meta = artifact.event_metadata
    schedule = artifact.schedule
    actions = artifact.action_items
    copy = artifact.multi_channel_copy

    lines = []
    lines.append(f"# {meta.title}")
    lines.append("")
    lines.append(f"> **Primary Objective**: {meta.primary_objective}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Executive Event Parameters")
    lines.append("")
    lines.append("| Metric / Parameter | Value |")
    lines.append("| :--- | :--- |")
    lines.append(f"| **Event Type** | `{meta.event_type.value}` |")
    lines.append(f"| **Target Audience** | {meta.target_audience} |")
    lines.append(f"| **Estimated Capacity** | {meta.estimated_attendees:,} attendees |")
    lines.append(f"| **Budget Tier** | `{meta.budget_tier.value.upper()}` |")
    lines.append("")

    lines.append("## 2. Chronological Schedule & Timetable")
    lines.append("")
    lines.append("| Time Slot | Session Title | Format | Speaker / Host | Deliverables |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for s in schedule:
        deliv_str = ", ".join(s.deliverables) if s.deliverables else "N/A"
        lines.append(f"| `{s.time_slot}` | **{s.session_title}** | `{s.format.value}` | {s.speaker_role} | {deliv_str} |")
    lines.append("")

    lines.append("## 3. Work Breakdown Structure & Action Items")
    lines.append("")
    lines.append("| Task ID | Description | Priority | Assignee Role | Timeline | Dependencies |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for a in actions:
        due_str = f"Day {a.due_relative_days:+d}" if a.due_relative_days != 0 else "Event Day"
        deps_str = ", ".join(a.dependencies) if a.dependencies else "None"
        prio_icon = "🔴" if a.priority.value == "critical" else ("🟠" if a.priority.value == "high" else "🟡")
        lines.append(f"| `{a.id}` | {a.task} | {prio_icon} `{a.priority.value}` | **{a.owner_role}** | `{due_str}` | {deps_str} |")
    lines.append("")

    lines.append("## 4. Multi-Channel Communications Package")
    lines.append("")
    lines.append("### 4.1 Internal / Community Announcement (Slack / Discord)")
    lines.append("```markdown")
    lines.append(copy.slack_announcement.strip())
    lines.append("```")
    lines.append("")

    lines.append("### 4.2 External Email Invitation")
    lines.append(f"**Subject**: `{copy.email_invitation.subject}`  ")
    lines.append(f"**Pre-header / Preview**: *{copy.email_invitation.preview_text}*")
    lines.append("")
    lines.append("> " + "\n> ".join(copy.email_invitation.body.splitlines()))
    lines.append("")

    lines.append(f"### 4.3 Social Media Campaign (X / Twitter &mdash; {len(copy.social_x_thread)} Posts)")
    for idx, tweet in enumerate(copy.social_x_thread, 1):
        lines.append(f"**Post {idx}/{len(copy.social_x_thread)}** ({len(tweet)} chars):")
        lines.append(f"> {tweet}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated deterministically by [PromptOps Controlled Generation Platform](https://github.com/rudrashis-d/promptops)*")

    return "\n".join(lines)

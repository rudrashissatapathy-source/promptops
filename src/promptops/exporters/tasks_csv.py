"""CSV Action Items / WBS exporter for Jira, Linear, and Asana import.

Converts EventArtifact action items into standard CSV files suitable for
batch import into modern project management platforms.
"""

import csv
import io
from typing import Union
from promptops.models.domain import EventArtifact


def export_tasks_to_csv(artifact: Union[EventArtifact, dict]) -> str:
    """Export EventArtifact action items to a Jira/Linear-compatible CSV string."""
    if isinstance(artifact, dict):
        artifact = EventArtifact.model_validate(artifact)

    meta = artifact.event_metadata
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Standard headers for Jira / Linear / Asana
    writer.writerow([
        "Issue Key",
        "Summary",
        "Priority",
        "Assignee Role",
        "Due Relative Days",
        "Dependencies",
        "Event Title",
        "Event Type",
        "Budget Tier"
    ])

    for item in artifact.action_items:
        writer.writerow([
            item.id,
            item.task,
            item.priority.value.capitalize(),
            item.owner_role,
            item.due_relative_days,
            "; ".join(item.dependencies) if item.dependencies else "",
            meta.title,
            meta.event_type.value,
            meta.budget_tier.value
        ])

    return output.getvalue()

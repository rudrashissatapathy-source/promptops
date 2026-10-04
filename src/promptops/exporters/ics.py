"""RFC 5545 iCalendar (.ics) schedule exporter for PromptOps.

Transforms EventArtifact schedule timelines into standard iCalendar (.ics) files
that can be imported directly into Google Calendar, Outlook, and Apple Calendar.
"""

import re
import uuid
from datetime import datetime, date, time, timedelta, timezone
from typing import Union, Optional
from promptops.models.domain import EventArtifact, ScheduleItem


def _parse_time(time_str: str) -> Optional[time]:
    """Parse a time string like '09:00', '9:00 AM', '14:30', '2:30 PM'."""
    clean = time_str.strip().upper()
    formats = [
        "%H:%M",
        "%I:%M %p",
        "%I:%M%p",
        "%I %p",
        "%H",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean, fmt).time()
        except ValueError:
            pass
    return None


def _parse_time_slot(time_slot: str, base_date: date, slot_index: int) -> tuple[datetime, datetime]:
    """Parse time slot string into start and end datetime."""
    # Look for delimiters like '-', 'to', '–'
    parts = re.split(r"\s*(?:-|–|to)\s*", time_slot, flags=re.IGNORECASE)
    
    t_start = None
    t_end = None

    if len(parts) >= 2:
        t_start = _parse_time(parts[0])
        t_end = _parse_time(parts[1])

    # Fallback to sequential 1-hour slots starting at 09:00 AM if parsing fails
    if not t_start:
        base_hour = 9 + slot_index
        t_start = time(base_hour % 24, 0)
    if not t_end:
        end_hour = (t_start.hour + 1) % 24
        t_end = time(end_hour, 0)

    start_dt = datetime.combine(base_date, t_start, tzinfo=timezone.utc)
    end_dt = datetime.combine(base_date, t_end, tzinfo=timezone.utc)
    
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=1)

    return start_dt, end_dt


def _format_ics_date(dt: datetime) -> str:
    """Format datetime to UTC iCalendar format: YYYYMMDDTHHMMSSZ."""
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape_ics_text(text: str) -> str:
    """Escape characters for RFC 5545 iCalendar values."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def export_to_ics(artifact: Union[EventArtifact, dict], event_date: Optional[date] = None) -> str:
    """Export EventArtifact schedule into an RFC 5545 compliant iCalendar string."""
    if isinstance(artifact, dict):
        artifact = EventArtifact.model_validate(artifact)

    if event_date is None:
        # Default to next Monday or 14 days ahead
        event_date = date.today() + timedelta(days=14)

    meta = artifact.event_metadata
    now_stamp = _format_ics_date(datetime.now(timezone.utc))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PromptOps//Event Synthesizer 0.1//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics_text(meta.title)}",
        f"X-WR-CALDESC:{_escape_ics_text(meta.primary_objective)}",
    ]

    for idx, item in enumerate(artifact.schedule):
        start_dt, end_dt = _parse_time_slot(item.time_slot, event_date, idx)
        event_uid = f"promptops-{uuid.uuid5(uuid.NAMESPACE_DNS, f'{meta.title}-{idx}-{item.session_title}')}@promptops.ai"

        deliverables_str = "None"
        if item.deliverables:
            deliverables_str = "\\n  • " + "\\n  • ".join(_escape_ics_text(d) for d in item.deliverables)

        description = (
            f"Format: {item.format.value}\\n"
            f"Host / Speaker: {_escape_ics_text(item.speaker_role)}\\n"
            f"Deliverables:{deliverables_str}\\n\\n"
            f"Event Objective: {_escape_ics_text(meta.primary_objective)}"
        )

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{_format_ics_date(start_dt)}",
            f"DTEND:{_format_ics_date(end_dt)}",
            f"SUMMARY:{_escape_ics_text(item.session_title)}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{_escape_ics_text(meta.event_type.value.upper())}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

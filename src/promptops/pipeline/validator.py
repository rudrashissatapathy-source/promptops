"""Level 1 Validation: Strict Pydantic and JSON Schema enforcement."""

import json
from typing import Tuple, Optional, Any, Dict
from pydantic import ValidationError

from promptops.models.domain import EventArtifact


def validate_dict_against_schema(data: Dict[str, Any]) -> Tuple[bool, Optional[EventArtifact], Optional[str]]:
    """Validate a Python dictionary against the EventArtifact Pydantic model.
    
    Returns:
        (is_valid, validated_artifact, error_message)
    """
    try:
        artifact = EventArtifact.model_validate(data)
        return True, artifact, None
    except ValidationError as e:
        error_lines = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msg = err["msg"]
            error_lines.append(f"- {loc}: {msg}")
        return False, None, "\n".join(error_lines)
    except Exception as ex:
        return False, None, f"Unexpected validation exception: {str(ex)}"


def validate_raw_json_string(raw_text: str) -> Tuple[bool, Optional[EventArtifact], Optional[str]]:
    """Parse raw JSON string directly and validate against schema."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        return False, None, f"JSON syntax error at line {e.lineno}, col {e.colno}: {e.msg}"
    
    if not isinstance(data, dict):
        return False, None, f"Expected top-level JSON object, got {type(data).__name__}"
        
    return validate_dict_against_schema(data)

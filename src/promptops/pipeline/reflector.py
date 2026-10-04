"""Level 3 LLM Self-Healing Reflector Loop.

When deterministic AST repair cannot resolve schema violations, the reflector feeds
the exact Pydantic validation error delta back to the model for a surgical correction pass.
"""

from typing import Tuple, Optional, Any, Dict
from promptops.adapters.base import BaseModelAdapter
from promptops.models.domain import EventArtifact
from promptops.pipeline.validator import validate_dict_against_schema
from promptops.pipeline.ast_repair import deterministic_repair


REPAIR_SYSTEM_PROMPT = """You are an automated, zero-fluff JSON Self-Healing Engine.
Your sole job is to fix schema validation errors in malformed or incomplete JSON payloads.
Rules:
1. Return ONLY the complete, corrected valid JSON object.
2. Do NOT output any markdown backticks, explanations, or conversational filler.
3. Fix all missing keys, invalid enum values, or violated constraints listed in the error report.
"""


async def reflect_and_repair(
    adapter: BaseModelAdapter,
    invalid_text: str,
    validation_error_report: str,
) -> Tuple[bool, Optional[EventArtifact], Optional[Dict[str, Any]], str]:
    """Execute Level 3 LLM Reflection pass.
    
    Returns:
        (success, validated_artifact, raw_dict, repair_notes)
    """
    repair_prompt = f"""The following JSON payload failed schema validation:

```json
{invalid_text}
```

SPECIFIC VALIDATION ERRORS DETECTED:
{validation_error_report}

TASK:
Patch all validation errors listed above. Preserve existing valid fields and supply valid defaults for missing required fields. Return ONLY the valid JSON object.
"""

    try:
        gen_result = await adapter.generate(
            prompt=repair_prompt,
            system_prompt=REPAIR_SYSTEM_PROMPT,
            temperature=0.1,  # Low temperature for deterministic corrections
            max_tokens=2048,
        )

        repaired_text = gen_result.raw_text.strip()
        # Run Level 2 AST repair on reflector output just in case model wrapped it
        success_ast, repaired_dict, notes = deterministic_repair(repaired_text)
        if not success_ast or not repaired_dict:
            return False, None, None, f"Reflector produced non-parseable JSON: {notes}"

        # Validate against domain schema
        valid, artifact, err_msg = validate_dict_against_schema(repaired_dict)
        if valid:
            return True, artifact, repaired_dict, f"Healed via Level 3 LLM Reflection: {notes}"
        else:
            return False, None, repaired_dict, f"Reflector output still violated schema: {err_msg}"

    except Exception as e:
        return False, None, None, f"Level 3 Reflection exception: {str(e)}"

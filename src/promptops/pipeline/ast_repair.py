"""Level 2 Deterministic AST & Regex Healer.

Repairs common LLM failure modes:
1. Markdown code blocks (```json ... ```) and conversational prefixes/suffixes.
2. Single-quoted keys and values (via AST literal evaluation and token normalization).
3. Trailing commas before closing braces/brackets (e.g., [1, 2, ] -> [1, 2]).
4. Truncated outputs with unclosed braces/brackets.
5. Incomplete quotes or unescaped control characters.
"""

import ast
import json
import re
from typing import Tuple, Optional, Any, Dict, List


def extract_json_block(text: str) -> Tuple[str, List[str]]:
    """Extract candidate JSON payload from text, stripping markdown and chat wrappers."""
    notes = []
    cleaned = text.strip()

    # Pattern 1: Fenced code block (```json ... ``` or ``` ...)
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    match = fence_pattern.search(cleaned)
    if match:
        notes.append("Stripped markdown code fence wrapper")
        cleaned = match.group(1).strip()
    else:
        # Pattern 2: Find outermost matching braces { ... }
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            if first_brace > 0 or last_brace < len(cleaned) - 1:
                notes.append("Extracted outermost curly brace boundaries")
            cleaned = cleaned[first_brace:last_brace + 1].strip()

    return cleaned, notes


def repair_trailing_commas(text: str) -> Tuple[str, List[str]]:
    """Remove trailing commas before closing brackets or braces."""
    notes = []
    # Match comma followed by whitespace and a closing bracket or brace
    pattern = re.compile(r",\s*([\]\}])")
    if pattern.search(text):
        repaired = pattern.sub(r"\1", text)
        notes.append("Removed trailing commas before closing braces/brackets")
        return repaired, notes
    return text, notes


def repair_unbalanced_braces(text: str) -> Tuple[str, List[str]]:
    """Append missing closing brackets/braces for truncated generations."""
    notes = []
    open_curlies = text.count("{")
    close_curlies = text.count("}")
    open_squares = text.count("[")
    close_squares = text.count("]")

    diff_curlies = open_curlies - close_curlies
    diff_squares = open_squares - close_squares

    if diff_curlies > 0 or diff_squares > 0:
        # Greedily balance: close open strings if odd number of quotes
        # Close squares then curlies
        repaired = text
        quote_count = repaired.count('"')
        if quote_count % 2 != 0:
            repaired += '"'
            notes.append("Appended missing string quotation mark")

        repaired += ("]" * max(0, diff_squares))
        repaired += ("}" * max(0, diff_curlies))
        notes.append(f"Balanced truncated syntax by appending missing {diff_squares} ']' and {diff_curlies} '}}'")
        return repaired, notes

    return text, notes


def repair_with_ast_eval(text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Attempt safe AST evaluation to handle single-quoted dicts (common in Python-oriented LLMs)."""
    notes = []
    try:
        evaluated = ast.literal_eval(text)
        if isinstance(evaluated, dict):
            notes.append("Parsed single-quoted dictionary via AST evaluation")
            return evaluated, notes
    except Exception:
        pass
    return None, notes


def deterministic_repair(raw_text: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Execute full deterministic repair pipeline on a raw LLM output.
    
    Returns:
        (success, parsed_dict, combined_repair_notes)
    """
    repair_notes = []

    # Fast path: already pristine JSON
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return True, parsed, "Pristine JSON (0 repairs needed)"
    except Exception:
        pass

    # Step 1: Strip Markdown & outer chat conversational text
    cleaned, step1_notes = extract_json_block(raw_text)
    repair_notes.extend(step1_notes)

    # Check if cleaned is now valid JSON
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return True, parsed, "; ".join(repair_notes)
    except Exception:
        pass

    # Step 2: Remove trailing commas
    no_trailing, step2_notes = repair_trailing_commas(cleaned)
    repair_notes.extend(step2_notes)

    # Step 3: Handle unbalanced braces / truncation
    balanced, step3_notes = repair_unbalanced_braces(no_trailing)
    repair_notes.extend(step3_notes)

    # Check if standard json.loads now works
    try:
        parsed = json.loads(balanced)
        if isinstance(parsed, dict):
            return True, parsed, "; ".join(repair_notes)
    except Exception:
        pass

    # Step 4: Try AST evaluation on balanced, cleaned payload (handles single quotes, Python literals)
    ast_dict, ast_notes = repair_with_ast_eval(balanced)
    if ast_dict is not None:
        repair_notes.extend(ast_notes)
        return True, ast_dict, "; ".join(repair_notes)

    # Step 5: Convert single quotes to double quotes for standard keys and simple strings
    sq_normalized = re.sub(r"'([a-zA-Z0-9_\-]+)'\s*:", r'"\1":', balanced)
    sq_normalized = re.sub(r":\s*'([^']*)'", r': "\1"', sq_normalized)
    sq_normalized, _ = repair_trailing_commas(sq_normalized)
    
    try:
        parsed = json.loads(sq_normalized)
        if isinstance(parsed, dict):
            repair_notes.append("Normalized single quotes to double quotes")
            return True, parsed, "; ".join(repair_notes)
    except Exception:
        pass

    return False, None, "; ".join(repair_notes) if repair_notes else "Could not repair JSON via deterministic AST heuristics"

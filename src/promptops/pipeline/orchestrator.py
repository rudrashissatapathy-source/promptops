"""Self-Healing Validation Pipeline Orchestrator.

Combines Level 1 (Strict Pydantic Validation), Level 2 (Deterministic AST & Regex Repair),
and Level 3 (LLM Error-Feedback Reflection) into a single unified execution flow.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel

from promptops.adapters.base import BaseModelAdapter
from promptops.models.domain import EventArtifact
from promptops.models.telemetry import RepairTier
from promptops.pipeline.validator import validate_dict_against_schema
from promptops.pipeline.ast_repair import deterministic_repair
from promptops.pipeline.reflector import reflect_and_repair


class PipelineResult(BaseModel):
    """Result of passing a raw model generation through the self-healing pipeline."""
    is_valid: bool
    artifact: Optional[EventArtifact] = None
    dict_payload: Optional[Dict[str, Any]] = None
    repair_tier: RepairTier
    repair_notes: str = ""
    error_message: Optional[str] = None


class SelfHealingPipeline:
    """Enterprise self-healing pipeline protecting applications from malformed LLM outputs."""

    def __init__(self, enable_llm_reflection: bool = True):
        self.enable_llm_reflection = enable_llm_reflection

    async def process(
        self,
        raw_text: str,
        adapter: Optional[BaseModelAdapter] = None,
    ) -> PipelineResult:
        """Run the 3-Tier validation and self-healing process on raw output."""
        if not raw_text or not raw_text.strip():
            return PipelineResult(
                is_valid=False,
                repair_tier=RepairTier.FAILED,
                error_message="Empty model response received",
            )

        # -------------------------------------------------------------
        # Tier 1: Direct Strict Validation (0 ms overhead)
        # -------------------------------------------------------------
        try:
            import json
            direct_dict = json.loads(raw_text)
            if isinstance(direct_dict, dict):
                valid, artifact, err = validate_dict_against_schema(direct_dict)
                if valid and artifact:
                    return PipelineResult(
                        is_valid=True,
                        artifact=artifact,
                        dict_payload=direct_dict,
                        repair_tier=RepairTier.NONE,
                        repair_notes="Pristine generation (Tier 1 Direct Validation)",
                    )
        except Exception:
            pass  # Fall through to Tier 2

        # -------------------------------------------------------------
        # Tier 2: Deterministic AST & Regex Healing
        # -------------------------------------------------------------
        ast_success, repaired_dict, ast_notes = deterministic_repair(raw_text)
        tier2_error_report = ""

        if ast_success and repaired_dict:
            valid, artifact, err = validate_dict_against_schema(repaired_dict)
            if valid and artifact:
                return PipelineResult(
                    is_valid=True,
                    artifact=artifact,
                    dict_payload=repaired_dict,
                    repair_tier=RepairTier.AST_REGEX,
                    repair_notes=f"Tier 2 Deterministic AST/Regex Healing: {ast_notes}",
                )
            else:
                tier2_error_report = err or "Schema validation failed on repaired AST"
        else:
            tier2_error_report = ast_notes or "Malformed syntax could not be resolved by AST heuristics"

        # -------------------------------------------------------------
        # Tier 3: LLM Self-Healing Reflector Loop
        # -------------------------------------------------------------
        if self.enable_llm_reflection and adapter is not None:
            reflector_success, artifact, reflected_dict, reflector_notes = await reflect_and_repair(
                adapter=adapter,
                invalid_text=raw_text,
                validation_error_report=tier2_error_report,
            )
            if reflector_success and artifact:
                return PipelineResult(
                    is_valid=True,
                    artifact=artifact,
                    dict_payload=reflected_dict,
                    repair_tier=RepairTier.LLM_REFLECTOR,
                    repair_notes=reflector_notes,
                )
            else:
                return PipelineResult(
                    is_valid=False,
                    repair_tier=RepairTier.FAILED,
                    repair_notes=f"Tier 2 note: {ast_notes}; Tier 3 note: {reflector_notes}",
                    error_message=tier2_error_report,
                )

        # If LLM reflection is disabled or no adapter provided, terminate as failed
        return PipelineResult(
            is_valid=False,
            dict_payload=repaired_dict if ast_success else None,
            repair_tier=RepairTier.FAILED,
            repair_notes=ast_notes,
            error_message=tier2_error_report,
        )

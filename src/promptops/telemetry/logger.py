"""Telemetry Logger and Metrics Aggregation Engine."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from promptops.config import RUNS_JSONL_PATH
from promptops.models.telemetry import RunRecord, RepairTier


class TelemetryStore:
    """Records execution runs and calculates operational performance metrics."""

    def __init__(self, log_path: Path = RUNS_JSONL_PATH, max_in_memory: int = 500):
        self.log_path = log_path
        self.max_in_memory = max_in_memory
        self._runs: List[RunRecord] = []
        self._load_existing_runs()

    def _load_existing_runs(self) -> None:
        """Load recent runs from disk if log file exists."""
        if not self.log_path.exists():
            return
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record_dict = json.loads(line)
                        self._runs.append(RunRecord.model_validate(record_dict))
            # Keep only the last max_in_memory runs in RAM
            if len(self._runs) > self.max_in_memory:
                self._runs = self._runs[-self.max_in_memory:]
        except Exception as e:
            print(f"Warning: Could not load existing telemetry runs: {e}")

    def log_run(self, record: RunRecord) -> None:
        """Store run record in memory and append to disk."""
        self._runs.append(record)
        if len(self._runs) > self.max_in_memory:
            self._runs.pop(0)

        # Append to JSONL log
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")
        except Exception as e:
            print(f"Warning: Failed to persist run record to {self.log_path}: {e}")

    def get_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent runs (newest first)."""
        recent = self._runs[-limit:]
        return [r.model_dump() for r in reversed(recent)]

    def compute_summary(
        self,
        prompt_version: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate statistical metrics filtered by prompt version and model name."""
        filtered = self._runs
        if prompt_version:
            filtered = [r for r in filtered if r.prompt_version == prompt_version]
        if model_name:
            filtered = [r for r in filtered if r.model_name == model_name]

        total_count = len(filtered)
        if total_count == 0:
            return {
                "total_runs": 0,
                "valid_runs": 0,
                "schema_validity_percent": 0.0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "repair_distribution": {
                    "none": 0,
                    "ast_regex": 0,
                    "llm_reflector": 0,
                    "failed": 0,
                }
            }

        valid_count = sum(1 for r in filtered if r.is_valid)
        latencies = sorted(r.latency_ms for r in filtered)
        p95_idx = int(0.95 * total_count)
        p95_latency = latencies[min(p95_idx, total_count - 1)]

        repairs = {
            RepairTier.NONE.value: sum(1 for r in filtered if r.repair_tier == RepairTier.NONE),
            RepairTier.AST_REGEX.value: sum(1 for r in filtered if r.repair_tier == RepairTier.AST_REGEX),
            RepairTier.LLM_REFLECTOR.value: sum(1 for r in filtered if r.repair_tier == RepairTier.LLM_REFLECTOR),
            RepairTier.FAILED.value: sum(1 for r in filtered if r.repair_tier == RepairTier.FAILED),
        }

        return {
            "total_runs": total_count,
            "valid_runs": valid_count,
            "schema_validity_percent": round((valid_count / total_count) * 100, 2),
            "avg_latency_ms": round(sum(latencies) / total_count, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "total_tokens": sum(r.total_tokens for r in filtered),
            "total_cost_usd": round(sum(r.cost_usd for r in filtered), 6),
            "repair_distribution": repairs,
        }

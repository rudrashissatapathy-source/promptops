"""Versioned Prompt Registry and Diff Engine."""

import difflib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml
from pydantic import BaseModel, Field

from promptops.config import PROMPTS_DIR


class PromptDefinition(BaseModel):
    """Declarative specification of a versioned prompt."""
    id: str
    version: str
    author: str = "PromptOps Team"
    created_at: str
    description: str
    target_schema: str = "EventArtifact"
    required_variables: List[str] = Field(default_factory=list)
    changelog: str = ""
    system_prompt: str
    user_template: str


class PromptRegistry:
    """In-memory and file-backed versioned prompt store."""

    def __init__(self, prompts_dir: Path = PROMPTS_DIR):
        self.prompts_dir = prompts_dir
        # Store keyed by (prompt_id, version)
        self._prompts: Dict[Tuple[str, str], PromptDefinition] = {}
        self.load_all()

    def load_all(self) -> None:
        """Scan prompts directory and load all .yaml and .yml files."""
        self._prompts.clear()
        if not self.prompts_dir.exists():
            return

        for file_path in self.prompts_dir.glob("*.yaml"):
            self._load_file(file_path)
        for file_path in self.prompts_dir.glob("*.yml"):
            self._load_file(file_path)

    def _load_file(self, file_path: Path) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                prompt = PromptDefinition.model_validate(data)
                self.register(prompt)
        except Exception as e:
            print(f"Warning: Failed to load prompt file {file_path}: {e}")

    def register(self, prompt: PromptDefinition) -> None:
        """Register a prompt definition."""
        self._prompts[(prompt.id, prompt.version)] = prompt

    def get(self, prompt_id: str, version: Optional[str] = None) -> PromptDefinition:
        """Retrieve prompt by ID and version.
        
        If version is omitted, returns the latest registered version.
        """
        matching = [
            (ver, p) for (pid, ver), p in self._prompts.items() if pid == prompt_id
        ]
        if not matching:
            raise KeyError(f"No prompt registered with ID '{prompt_id}'")

        if version is not None:
            for ver, p in matching:
                if ver == version:
                    return p
            raise KeyError(f"Prompt '{prompt_id}' does not have version '{version}'. Available: {[v for v, _ in matching]}")

        # Sort versions semantically or alphabetically descending
        sorted_prompts = sorted(matching, key=lambda item: item[0], reverse=True)
        return sorted_prompts[0][1]

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List summary of all registered prompts."""
        results = []
        for (pid, ver), p in sorted(self._prompts.items()):
            results.append({
                "id": pid,
                "version": ver,
                "author": p.author,
                "created_at": p.created_at,
                "description": p.description,
                "target_schema": p.target_schema,
                "changelog": p.changelog,
                "required_variables": p.required_variables,
            })
        return results

    def list_versions(self, prompt_id: str) -> List[str]:
        """List all version strings for a given prompt ID."""
        versions = [ver for (pid, ver) in self._prompts.keys() if pid == prompt_id]
        return sorted(versions)

    def render(
        self,
        prompt_id: str,
        version: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Validate variables and render the system and user prompts.
        
        Returns:
            (system_prompt, rendered_user_prompt)
        """
        prompt = self.get(prompt_id, version)
        variables = variables or {}

        # Validate required variables
        missing = [v for v in prompt.required_variables if v not in variables]
        if missing:
            raise ValueError(f"Missing required prompt variables for '{prompt_id}@{prompt.version}': {missing}")

        try:
            rendered_user = prompt.user_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Template rendering failed, unsupplied variable: {e}")

        return prompt.system_prompt, rendered_user

    def diff_versions(self, prompt_id: str, v1: str, v2: str) -> Dict[str, Any]:
        """Compute textual and metadata diff between two prompt versions."""
        p1 = self.get(prompt_id, v1)
        p2 = self.get(prompt_id, v2)

        # Unified diff on system prompt
        sys_diff = list(difflib.unified_diff(
            p1.system_prompt.splitlines(keepends=True),
            p2.system_prompt.splitlines(keepends=True),
            fromfile=f"{prompt_id}@{v1} (system)",
            tofile=f"{prompt_id}@{v2} (system)",
        ))

        # Unified diff on user template
        user_diff = list(difflib.unified_diff(
            p1.user_template.splitlines(keepends=True),
            p2.user_template.splitlines(keepends=True),
            fromfile=f"{prompt_id}@{v1} (user_template)",
            tofile=f"{prompt_id}@{v2} (user_template)",
        ))

        return {
            "prompt_id": prompt_id,
            "v1": v1,
            "v2": v2,
            "system_prompt_diff": "".join(sys_diff),
            "user_template_diff": "".join(user_diff),
            "v1_length_chars": len(p1.system_prompt) + len(p1.user_template),
            "v2_length_chars": len(p2.system_prompt) + len(p2.user_template),
            "v2_changelog": p2.changelog,
        }

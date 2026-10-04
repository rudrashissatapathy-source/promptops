"""Deterministic SHA-256 Exact-Match Execution Cache."""

import hashlib
import json
from typing import Dict, Any, Optional, Tuple


class GenerationCache:
    """Exact-match in-memory and serialization cache for LLM runs."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.hits: int = 0
        self.misses: int = 0

    def compute_key(
        self,
        model_name: str,
        prompt_id: str,
        prompt_version: str,
        variables: Dict[str, Any],
        temperature: float = 0.2,
    ) -> str:
        """Derive a deterministic SHA-256 digest from execution parameters."""
        serialized_vars = json.dumps(variables, sort_keys=True)
        raw_key = f"{model_name}::{prompt_id}::{prompt_version}::{temperature}::{serialized_vars}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Look up cached generation payload."""
        if cache_key in self._store:
            self.hits += 1
            return self._store[cache_key]
        self.misses += 1
        return None

    def put(self, cache_key: str, payload: Dict[str, Any]) -> None:
        """Store validated generation payload."""
        self._store[cache_key] = payload

    def clear(self) -> None:
        """Clear cache contents."""
        self._store.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache health and hit statistics."""
        total = self.hits + self.misses
        hit_ratio = (self.hits / total) if total > 0 else 0.0
        return {
            "entries_count": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_ratio_percent": round(hit_ratio * 100, 2),
        }

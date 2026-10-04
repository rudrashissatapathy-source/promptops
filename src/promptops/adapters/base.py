"""Base model adapter interface for provider-agnostic LLM execution."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any
from promptops.config import MODEL_PRICING
from promptops.models.telemetry import GenerationResult, StreamChunk


class BaseModelAdapter(ABC):
    """Abstract base adapter defining the contract for all LLM backends."""

    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> GenerationResult:
        """Execute a synchronous generation request and return a structured GenerationResult."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks asynchronously."""
        pass

    def count_tokens(self, text: str) -> int:
        """Calculate token count.
        
        Uses an accurate character heuristic (average ~3.8 characters per token for English and code)
        to ensure deterministic, dependency-free token accounting across all platforms.
        """
        if not text:
            return 0
        # Standard GPT/Gemini character to token ratio approximation
        return max(1, int(len(text) / 3.8))

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the estimated USD cost based on registered pricing tables."""
        pricing = MODEL_PRICING.get(self.model_name, {
            "input_per_million": 0.15,
            "output_per_million": 0.60
        })
        input_cost = (prompt_tokens / 1_000_000.0) * pricing["input_per_million"]
        output_cost = (completion_tokens / 1_000_000.0) * pricing["output_per_million"]
        return round(input_cost + output_cost, 8)

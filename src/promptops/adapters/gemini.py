"""Google Gemini model adapter using the official google-genai SDK."""

import os
import time
from typing import AsyncIterator, Optional, Dict, Any

from promptops.adapters.base import BaseModelAdapter
from promptops.models.telemetry import GenerationResult, StreamChunk

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


class GeminiAdapter(BaseModelAdapter):
    """Adapter for Google Gemini models (e.g. gemini-2.5-flash, gemini-2.5-pro)."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name=model_name, config=config)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not _GENAI_AVAILABLE:
            self.client = None
        elif self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _ensure_client(self):
        if not _GENAI_AVAILABLE:
            raise RuntimeError("The 'google-genai' library is not installed.")
        if not self.client:
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Please set the GEMINI_API_KEY environment variable "
                    "or select the deterministic Chaos Mock adapter for offline testing."
                )
            self.client = genai.Client(api_key=self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> GenerationResult:
        """Call Gemini model synchronously and record execution telemetry."""
        self._ensure_client()
        start_time = time.perf_counter()

        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )
        if system_prompt:
            gen_config.system_instruction = system_prompt

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=gen_config,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        raw_text = response.text or ""

        # Extract tokens from response usage metadata if available
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        if prompt_tokens == 0:
            prompt_tokens = self.count_tokens(prompt + system_prompt)
        if completion_tokens == 0:
            completion_tokens = self.count_tokens(raw_text)

        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self.estimate_cost(prompt_tokens, completion_tokens)

        return GenerationResult(
            raw_text=raw_text,
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=elapsed_ms,
            ttft_ms=elapsed_ms * 0.35,
            finish_reason="stop",
            cost_usd=cost_usd,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chunks from Gemini model."""
        self._ensure_client()

        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )
        if system_prompt:
            gen_config.system_instruction = system_prompt

        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=gen_config,
        )

        idx = 0
        for chunk in response_stream:
            text_part = chunk.text or ""
            if text_part:
                yield StreamChunk(
                    delta=text_part,
                    finish_reason=None,
                    index=idx,
                )
                idx += 1

        yield StreamChunk(delta="", finish_reason="stop", index=idx)

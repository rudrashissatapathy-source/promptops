"""OpenAI-compatible model adapter supporting OpenAI, Groq, Ollama, and local vLLM."""

import json
import os
import time
from typing import AsyncIterator, Optional, Dict, Any

import httpx

from promptops.adapters.base import BaseModelAdapter
from promptops.models.telemetry import GenerationResult, StreamChunk


class OpenAILikeAdapter(BaseModelAdapter):
    """Universal adapter for any OpenAI-compatible chat completions API."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name=model_name, config=config)
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY", "")

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> GenerationResult:
        """Execute chat completion request over HTTP."""
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set the OPENAI_API_KEY or GROQ_API_KEY environment variable, "
                "or specify a local Ollama endpoint (e.g., http://localhost:11434/v1)."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        choice = data["choices"][0]
        raw_text = choice["message"]["content"]
        finish_reason = choice.get("finish_reason", "stop")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", self.count_tokens(prompt + system_prompt))
        completion_tokens = usage.get("completion_tokens", self.count_tokens(raw_text))
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self.estimate_cost(prompt_tokens, completion_tokens)

        return GenerationResult(
            raw_text=raw_text,
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=elapsed_ms,
            ttft_ms=elapsed_ms * 0.4,
            finish_reason=finish_reason,
            cost_usd=cost_usd,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chunks via Server-Sent Events (SSE)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        idx = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        yield StreamChunk(delta="", finish_reason="stop", index=idx)
                        break
                    try:
                        chunk_obj = json.loads(data_str)
                        choices = chunk_obj.get("choices", [])
                        if not choices:
                            continue
                        delta_obj = choices[0].get("delta", {})
                        content_piece = delta_obj.get("content", "")
                        finish_reason = choices[0].get("finish_reason")
                        if content_piece or finish_reason:
                            yield StreamChunk(
                                delta=content_piece,
                                finish_reason=finish_reason,
                                index=idx,
                            )
                            idx += 1
                    except json.JSONDecodeError:
                        continue

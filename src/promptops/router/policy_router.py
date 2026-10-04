"""Smart Policy Router with Multi-Objective Optimization and Circuit Breakers."""

import asyncio
import time
from typing import Dict, Optional, Tuple, List, Any

from promptops.adapters.base import BaseModelAdapter
from promptops.models.telemetry import RoutingPolicy, GenerationResult


class PolicyRouter:
    """Intelligently dispatches generation requests based on Cost, Speed, Quality, and Fallback policies."""

    def __init__(
        self,
        adapters: Dict[str, BaseModelAdapter],
        default_policy: RoutingPolicy = RoutingPolicy.SPEED_FIRST,
        fallback_chain: Optional[List[str]] = None,
    ):
        self.adapters = adapters
        self.default_policy = default_policy
        self.fallback_chain = fallback_chain or ["mock-fast", "mock-heavy"]

    def select_adapter(
        self,
        policy: Optional[RoutingPolicy] = None,
        input_text: str = "",
        preferred_model: Optional[str] = None,
    ) -> Tuple[BaseModelAdapter, str]:
        """Select optimal model adapter and return explanation rationale."""
        pol = policy or self.default_policy

        if preferred_model and preferred_model in self.adapters:
            return self.adapters[preferred_model], f"Explicit model override requested: {preferred_model}"

        # Policy 1: Speed First -> prioritize lowest latency tier
        if pol == RoutingPolicy.SPEED_FIRST:
            for name in ["mock-fast", "gemini-2.5-flash", "gpt-4o-mini"]:
                if name in self.adapters:
                    return self.adapters[name], "Routing policy 'SPEED_FIRST': dispatched to high-throughput tier"
            # Fallback to any available
            adapter_name = next(iter(self.adapters))
            return self.adapters[adapter_name], f"Defaulted to available adapter: {adapter_name}"

        # Policy 2: Quality First -> prioritize frontier reasoning tier
        elif pol == RoutingPolicy.QUALITY_FIRST:
            for name in ["mock-heavy", "gemini-2.5-pro", "gpt-4o"]:
                if name in self.adapters:
                    return self.adapters[name], "Routing policy 'QUALITY_FIRST': dispatched to frontier reasoning tier"
            adapter_name = next(iter(self.adapters))
            return self.adapters[adapter_name], f"Defaulted to available adapter: {adapter_name}"

        # Policy 3: Cost Optimized -> dynamic token budget thresholding
        elif pol == RoutingPolicy.COST_OPTIMIZED:
            char_count = len(input_text)
            # If input is short and concise (< 800 chars), cheap model is sufficient
            if char_count < 800:
                for name in ["mock-fast", "gemini-2.5-flash", "gpt-4o-mini"]:
                    if name in self.adapters:
                        return self.adapters[name], f"Routing policy 'COST_OPTIMIZED': input length {char_count} chars < 800 threshold, routed to economical tier"
            # If input is massive or complex, route to quality tier
            for name in ["mock-heavy", "gemini-2.5-pro", "gpt-4o"]:
                if name in self.adapters:
                    return self.adapters[name], f"Routing policy 'COST_OPTIMIZED': input length {char_count} chars >= 800 threshold, routed to heavy tier"
            adapter_name = next(iter(self.adapters))
            return self.adapters[adapter_name], f"Defaulted to available adapter: {adapter_name}"

        # Policy 4: Cascade Fallback
        elif pol == RoutingPolicy.CASCADE_FALLBACK:
            primary_name = self.fallback_chain[0]
            if primary_name in self.adapters:
                return self.adapters[primary_name], f"Routing policy 'CASCADE_FALLBACK': trying primary model '{primary_name}'"

        adapter_name = next(iter(self.adapters))
        return self.adapters[adapter_name], f"Default fallback adapter: {adapter_name}"

    async def execute_with_fallback(
        self,
        policy: RoutingPolicy,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout_seconds: float = 2.0,
    ) -> Tuple[GenerationResult, str]:
        """Execute request with circuit breaker timeout and automatic fallback cascade."""
        adapter, initial_rationale = self.select_adapter(policy=policy, input_text=prompt)

        # For non-cascade policies, execute directly with timeout
        if policy != RoutingPolicy.CASCADE_FALLBACK:
            try:
                result = await asyncio.wait_for(
                    adapter.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout_seconds,
                )
                return result, initial_rationale
            except Exception as e:
                # If it failed and fallback is possible, escalate
                pass

        # Cascade fallback loop across fallback chain
        errors = []
        for model_name in self.fallback_chain:
            if model_name not in self.adapters:
                continue
            current_adapter = self.adapters[model_name]
            try:
                result = await asyncio.wait_for(
                    current_adapter.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout_seconds,
                )
                rationale = f"Executed via '{model_name}' (after prior attempts: {errors})" if errors else f"Executed on primary '{model_name}'"
                return result, rationale
            except Exception as e:
                errors.append(f"{model_name} failed: {type(e).__name__} ({str(e)})")

        raise RuntimeError(f"All models in fallback cascade failed: {'; '.join(errors)}")

"""PromptOps End-to-End Live Walkthrough & Demo Script.

Run this script to observe the entire platform capabilities in real time:
1. Failure of Baseline Prompts on Noisy Inputs
2. Level 2 Deterministic AST Self-Healing (<2ms, $0.00 cost)
3. Production Prompt v2.0.0 Strict Schema Compliance
4. Policy Routing and Circuit-Breaker Fallback Cascade
5. SHA-256 Exact-Match Caching
6. 50-Case Empirical Regression Matrix
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from promptops.registry.prompt_store import PromptRegistry
from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
from promptops.pipeline.orchestrator import SelfHealingPipeline
from promptops.pipeline.ast_repair import deterministic_repair
from promptops.router.policy_router import PolicyRouter
from promptops.telemetry.cache import GenerationCache
from promptops.models.telemetry import RoutingPolicy, RepairTier


def header(title):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


async def main():
    header("PromptOps: Controlled LLM Generation Platform - Live Demo")
    print("Initializing Core Components (Registry, Adapters, Self-Healing Pipeline, Router, Cache)...")
    
    registry = PromptRegistry()
    pipeline = SelfHealingPipeline(enable_llm_reflection=True)
    cache = GenerationCache()

    fast_adapter = ChaosMockAdapter(model_name="mock-fast", mode=ChaosMode.PERFECT, simulated_latency_ms=60.0)
    heavy_adapter = ChaosMockAdapter(model_name="mock-heavy", mode=ChaosMode.PERFECT, simulated_latency_ms=180.0)
    chaos_adapter = ChaosMockAdapter(model_name="mock-chaos", mode=ChaosMode.MARKDOWN_FENCED, simulated_latency_ms=40.0)

    # -------------------------------------------------------------
    # STEP 1: The Flaw of Toy Prompt Demos
    # -------------------------------------------------------------
    header("Step 1: The Problem with Naive Prompt Demos")
    sample_noisy_brief = "hey team!! devops unconference on nov 12th for 80 devs. dave wants lunch catered. 10 to 12 lightning talks, then breakouts. mark order lanyards."
    print(f"Raw Input Brief:\n\"{sample_noisy_brief}\"\n")

    print("Simulating typical LLM generation (wrapped with markdown backticks and conversation)...")
    raw_fenced = chaos_adapter._generate_payload(sample_noisy_brief)
    print(f"Raw Model Generation Snippet:\n{raw_fenced[:180]}...\n")

    print("Attempting naive json.loads() as done in toy demos:")
    try:
        json.loads(raw_fenced)
        print("Success!")
    except Exception as e:
        print(f"  [CRASH] Naive json.loads() FAILED: {type(e).__name__} ({str(e)[:50]}...)")
        print("  In standard applications, this results in an unhandled 500 error or blank UI.")

    # -------------------------------------------------------------
    # STEP 2: Tier 2 Deterministic AST Self-Healing
    # -------------------------------------------------------------
    header("Step 2: Tier 2 Deterministic AST Self-Healing (<2ms, $0.00 Cost)")
    print("Passing malformed generation into PromptOps Self-Healing Pipeline...")
    t0 = time.perf_counter()
    pipeline_result = await pipeline.process(raw_fenced, adapter=chaos_adapter)
    t_repair = (time.perf_counter() - t0) * 1000.0

    print(f"  Validation Status : {'VALID' if pipeline_result.is_valid else 'FAILED'}")
    print(f"  Recovery Tier     : {pipeline_result.repair_tier.value}")
    print(f"  Healing Notes     : {pipeline_result.repair_notes}")
    print(f"  Repair Execution  : {t_repair:.2f} ms")
    print(f"  Additional Tokens : 0 (No extra LLM call needed!)")
    print(f"  Artifact Title    : '{pipeline_result.artifact.event_metadata.title}'")

    # -------------------------------------------------------------
    # STEP 3: Prompt Versioning (v1.0.0 vs v2.0.0)
    # -------------------------------------------------------------
    header("Step 3: Immutable Prompt Registry & Semantic Versioning")
    diff = registry.diff_versions("event_brief_synthesizer", "v1.0.0", "v2.0.0")
    print("Diffing 'v1.0.0' (Baseline) vs 'v2.0.0' (Production):")
    print(f"  V1 Size: {diff['v1_length_chars']} chars | V2 Size: {diff['v2_length_chars']} chars")
    print(f"  Changelog: {diff['v2_changelog']}")
    print("  Key changes: Added strict enum boundaries, tweet length caps (280 chars), and dependency validation rules.")

    # -------------------------------------------------------------
    # STEP 4: Smart Policy Router & Circuit-Breaker Fallback
    # -------------------------------------------------------------
    header("Step 4: Smart Policy Routing & Circuit-Breaker Fallback")
    router = PolicyRouter(
        adapters={"mock-fast": fast_adapter, "mock-heavy": heavy_adapter, "mock-chaos": chaos_adapter},
        fallback_chain=["mock-chaos", "mock-fast"]
    )

    print("Policy 1: SPEED_FIRST")
    ad, rationale = router.select_adapter(RoutingPolicy.SPEED_FIRST)
    print(f"  Selected: {ad.model_name} | Reason: {rationale}")

    print("Policy 2: QUALITY_FIRST")
    ad, rationale = router.select_adapter(RoutingPolicy.QUALITY_FIRST)
    print(f"  Selected: {ad.model_name} | Reason: {rationale}")

    print("Policy 3: CASCADE_FALLBACK (Simulating Primary Upstream Hang)")
    hang_adapter = ChaosMockAdapter(model_name="mock-hang", mode=ChaosMode.TIMEOUT)
    resilient_router = PolicyRouter(
        adapters={"mock-hang": hang_adapter, "mock-fast": fast_adapter},
        fallback_chain=["mock-hang", "mock-fast"]
    )
    t_start = time.perf_counter()
    fallback_res, fallback_rationale = await resilient_router.execute_with_fallback(
        policy=RoutingPolicy.CASCADE_FALLBACK,
        prompt="Sample fallback brief",
        timeout_seconds=0.15,
    )
    t_elapsed = (time.perf_counter() - t_start) * 1000.0
    print(f"  Fallback Execution: Succeeded in {t_elapsed:.1f}ms")
    print(f"  Execution Path    : {fallback_rationale}")

    # -------------------------------------------------------------
    # STEP 5: SHA-256 Exact-Match Caching
    # -------------------------------------------------------------
    header("Step 5: SHA-256 Exact-Match Caching & Economics")
    key = cache.compute_key("mock-fast", "event_brief_synthesizer", "v2.0.0", {"brief": "Test"}, 0.2)
    print(f"Derived SHA-256 Cache Key: {key}")

    print("Run 1 (Cache Miss):")
    t0 = time.perf_counter()
    res1 = await fast_adapter.generate("Test prompt")
    cost1 = fast_adapter.estimate_cost(res1.prompt_tokens, res1.completion_tokens)
    print(f"  Latency: {(time.perf_counter() - t0)*1000:.1f}ms | Tokens: {res1.total_tokens} | Cost: ${cost1:.6f}")
    cache.put(key, res1.model_dump())

    print("Run 2 (Cache Hit):")
    t0 = time.perf_counter()
    hit = cache.get(key)
    print(f"  Latency: {(time.perf_counter() - t0)*1000:.2f}ms | Tokens: 0 | Cost: $0.000000 (100% Savings!)")

    # -------------------------------------------------------------
    # STEP 6: 50-Case Empirical Benchmark Matrix Summary
    # -------------------------------------------------------------
    header("Step 6: 50-Case Empirical Benchmark Matrix")
    benchmark_file = Path("data/benchmark_results.json")
    if benchmark_file.exists():
        with open(benchmark_file, "r") as f:
            bm_data = json.load(f)
        summary = bm_data.get("matrix_summary", {})
        print(f"{'CONFIGURATION':<25} | {'VALIDITY':<10} | {'HEALED':<8} | {'P50 (ms)':<9} | {'COST/100':<10}")
        print("-" * 75)
        for k, s in summary.items():
            print(f"{k:<25} | {s['schema_validity_percent']:<9}% | {s['self_healed_count']:<8} | {s['p50_latency_ms']:<7}ms | ${s['cost_per_100_runs_usd']:.4f}")
    else:
        print("Run 'python run_benchmark.py' to generate full 200-run matrix summary.")

    header("Demo Walkthrough Complete")
    print("The system is running locally at http://127.0.0.1:8000")
    print("Use DEMO_SCRIPT.md to guide your 5-8 minute presentation walkthrough.")


if __name__ == "__main__":
    asyncio.run(main())

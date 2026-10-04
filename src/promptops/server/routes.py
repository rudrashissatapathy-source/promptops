"""FastAPI REST API routes and Server-Sent Events (SSE) streaming endpoints."""

import asyncio
import json
import time
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from promptops.config import MODEL_CATALOG, DATA_DIR
from promptops.registry.prompt_store import PromptRegistry
from promptops.adapters.base import BaseModelAdapter
from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
from promptops.adapters.gemini import GeminiAdapter
from promptops.adapters.openai_like import OpenAILikeAdapter
from promptops.pipeline.orchestrator import SelfHealingPipeline
from promptops.router.policy_router import PolicyRouter
from promptops.telemetry.cache import GenerationCache
from promptops.telemetry.logger import TelemetryStore
from promptops.runner.benchmark import BenchmarkRunner
from promptops.models.telemetry import RoutingPolicy, RunRecord, RepairTier

router = APIRouter(prefix="/api")

# Core Engine Singletons
registry = PromptRegistry()
pipeline = SelfHealingPipeline(enable_llm_reflection=True)
cache = GenerationCache()
telemetry_store = TelemetryStore()

# Initialize Adapters
adapters: Dict[str, BaseModelAdapter] = {
    "mock-fast": ChaosMockAdapter(model_name="mock-fast", mode=ChaosMode.PERFECT, simulated_latency_ms=80.0),
    "mock-heavy": ChaosMockAdapter(model_name="mock-heavy", mode=ChaosMode.PERFECT, simulated_latency_ms=250.0),
    "mock-chaos": ChaosMockAdapter(model_name="mock-chaos", mode=ChaosMode.MARKDOWN_FENCED, simulated_latency_ms=100.0),
    "gemini-2.5-flash": GeminiAdapter(model_name="gemini-2.5-flash"),
    "gemini-2.5-pro": GeminiAdapter(model_name="gemini-2.5-pro"),
    "gpt-4o-mini": OpenAILikeAdapter(model_name="gpt-4o-mini"),
    "gpt-4o": OpenAILikeAdapter(model_name="gpt-4o"),
}

router_engine = PolicyRouter(adapters=adapters, default_policy=RoutingPolicy.SPEED_FIRST)


class GenerateRequest(BaseModel):
    event_brief: str = Field(..., min_length=3, description="Unstructured user event brief")
    prompt_id: str = "event_brief_synthesizer"
    prompt_version: str = "v2.0.0"
    model_name: str = "mock-fast"
    routing_policy: RoutingPolicy = RoutingPolicy.SPEED_FIRST
    use_cache: bool = True
    temperature: float = 0.2


@router.get("/models")
async def list_models():
    """Return catalog of supported models with provider metadata and tier."""
    return {"models": MODEL_CATALOG}


@router.get("/prompts")
async def list_prompts():
    """Return all registered prompts and semantic versions."""
    registry.load_all()
    return {"prompts": registry.list_prompts()}


@router.get("/prompts/diff")
async def get_prompt_diff(
    prompt_id: str = Query("event_brief_synthesizer"),
    v1: str = Query("v1.0.0"),
    v2: str = Query("v2.0.0"),
):
    """Return unified diff and length metadata between two prompt versions."""
    try:
        return registry.diff_versions(prompt_id=prompt_id, v1=v1, v2=v2)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/generate")
async def generate_artifact(req: GenerateRequest):
    """Execute complete generation, self-healing validation, caching, and telemetry recording."""
    start_time = time.perf_counter()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. Exact-Match Cache Check
    variables = {"event_brief": req.event_brief}
    cache_key = cache.compute_key(
        model_name=req.model_name,
        prompt_id=req.prompt_id,
        prompt_version=req.prompt_version,
        variables=variables,
        temperature=req.temperature,
    )

    if req.use_cache:
        cached_record = cache.get(cache_key)
        if cached_record:
            cached_record["run_id"] = run_id
            cached_record["timestamp"] = iso_time
            cached_record["cache_hit"] = True
            telemetry_store.log_run(RunRecord.model_validate(cached_record))
            return cached_record

    # 2. Render Prompt
    try:
        sys_prompt, user_prompt = registry.render(
            prompt_id=req.prompt_id,
            version=req.prompt_version,
            variables=variables,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prompt rendering error: {str(e)}")

    # 3. Model Adapter Selection & Execution
    adapter = adapters.get(req.model_name)
    if not adapter:
        adapter, _ = router_engine.select_adapter(
            policy=req.routing_policy,
            input_text=req.event_brief,
            preferred_model=req.model_name,
        )

    try:
        gen_result = await adapter.generate(
            prompt=user_prompt,
            system_prompt=sys_prompt,
            temperature=req.temperature,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model generation error: {str(e)}")

    # 4. Self-Healing Validation Pipeline
    pipeline_res = await pipeline.process(raw_text=gen_result.raw_text, adapter=adapter)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # 5. Formulate RunRecord
    record = RunRecord(
        run_id=run_id,
        timestamp=iso_time,
        prompt_id=req.prompt_id,
        prompt_version=req.prompt_version,
        model_name=adapter.model_name,
        routing_policy=req.routing_policy,
        input_text=req.event_brief,
        raw_output=gen_result.raw_text,
        validated_artifact=pipeline_res.artifact.model_dump() if pipeline_res.artifact else pipeline_res.dict_payload,
        is_valid=pipeline_res.is_valid,
        repair_tier=pipeline_res.repair_tier,
        repair_notes=pipeline_res.repair_notes,
        prompt_tokens=gen_result.prompt_tokens,
        completion_tokens=gen_result.completion_tokens,
        total_tokens=gen_result.total_tokens,
        latency_ms=round(elapsed_ms, 2),
        ttft_ms=round(gen_result.ttft_ms, 2) if gen_result.ttft_ms else None,
        cost_usd=gen_result.cost_usd,
        cache_hit=False,
        error=pipeline_res.error_message,
    )

    # 6. Telemetry & Cache Storage
    telemetry_store.log_run(record)
    if pipeline_res.is_valid and req.use_cache:
        cache.put(cache_key, record.model_dump())

    return record.model_dump()


@router.post("/generate/stream")
async def generate_stream(req: GenerateRequest):
    """Server-Sent Events (SSE) stream yielding token deltas and final self-healed payload."""
    try:
        sys_prompt, user_prompt = registry.render(
            prompt_id=req.prompt_id,
            version=req.prompt_version,
            variables={"event_brief": req.event_brief},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    adapter = adapters.get(req.model_name) or adapters["mock-fast"]

    async def sse_event_generator():
        start_time = time.perf_counter()
        accumulated_text = []

        try:
            async for chunk in adapter.generate_stream(
                prompt=user_prompt,
                system_prompt=sys_prompt,
                temperature=req.temperature,
            ):
                if chunk.delta:
                    accumulated_text.append(chunk.delta)
                    payload = {"type": "token", "delta": chunk.delta, "index": chunk.index}
                    yield f"data: {json.dumps(payload)}\n\n"

            # Stream finished, execute self-healing pipeline
            full_raw_text = "".join(accumulated_text)
            pipeline_res = await pipeline.process(raw_text=full_raw_text, adapter=adapter)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            prompt_tokens = adapter.count_tokens(user_prompt + sys_prompt)
            completion_tokens = adapter.count_tokens(full_raw_text)
            cost_usd = adapter.estimate_cost(prompt_tokens, completion_tokens)

            final_event = {
                "type": "final",
                "is_valid": pipeline_res.is_valid,
                "repair_tier": pipeline_res.repair_tier.value,
                "repair_notes": pipeline_res.repair_notes,
                "artifact": pipeline_res.artifact.model_dump() if pipeline_res.artifact else None,
                "raw_text": full_raw_text,
                "latency_ms": round(elapsed_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost_usd": cost_usd,
                "error": pipeline_res.error_message,
            }
            yield f"data: {json.dumps(final_event)}\n\n"

        except Exception as ex:
            error_event = {"type": "error", "message": str(ex)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@router.get("/telemetry/runs")
async def get_recent_runs(limit: int = 50):
    """Retrieve historical execution audit logs."""
    return {"runs": telemetry_store.get_runs(limit=limit)}


@router.get("/telemetry/summary")
async def get_telemetry_summary(
    prompt_version: Optional[str] = None,
    model_name: Optional[str] = None,
):
    """Retrieve aggregated performance metrics and repair distribution."""
    return telemetry_store.compute_summary(prompt_version=prompt_version, model_name=model_name)


@router.get("/cache/stats")
async def get_cache_stats():
    """Retrieve cache hit/miss performance."""
    return cache.stats()


@router.post("/benchmark/run")
async def run_benchmark():
    """Execute the 50-case benchmark matrix asynchronously and return results."""
    runner = BenchmarkRunner()
    results = await runner.run_suite(
        prompt_versions=["v1.0.0", "v2.0.0"],
        model_names=["mock-fast", "mock-heavy"],
    )
    return results


@router.get("/benchmark/results")
async def get_latest_benchmark_results():
    """Fetch previously persisted benchmark results."""
    results_file = DATA_DIR / "benchmark_results.json"
    if not results_file.exists():
        # Run on the fly if not yet generated
        runner = BenchmarkRunner()
        return await runner.run_suite()

    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)

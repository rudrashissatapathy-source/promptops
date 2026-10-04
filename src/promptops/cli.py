"""Command Line Interface (CLI) for PromptOps.

Provides commands to start the server, execute benchmarks, run live syntheses,
and inspect prompt version diffs.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from promptops.registry.prompt_store import PromptRegistry
from promptops.adapters.chaos_mock import ChaosMockAdapter, ChaosMode
from promptops.pipeline.orchestrator import SelfHealingPipeline
from promptops.runner.benchmark import BenchmarkRunner
from promptops.models.telemetry import RepairTier


def cmd_serve(args):
    """Start the PromptOps FastAPI server and web dashboard."""
    import uvicorn
    print(f"Starting PromptOps Web Studio on http://{args.host}:{args.port}")
    src_dir = str(Path(__file__).resolve().parent.parent)
    uvicorn.run("promptops.server.app:app", host=args.host, port=args.port, app_dir=src_dir, reload=args.reload)


def cmd_benchmark(args):
    """Execute the 50-case empirical regression matrix."""
    import run_benchmark
    asyncio.run(run_benchmark.main())


def cmd_diff(args):
    """Inspect unified diff between two prompt versions."""
    registry = PromptRegistry()
    diff = registry.diff_versions(args.prompt_id, args.v1, args.v2)
    print("=" * 80)
    print(f"PROMPT DIFF: {args.prompt_id} ({args.v1} -> {args.v2})")
    print("=" * 80)
    print(f"Changelog: {diff['v2_changelog']}\n")
    print("SYSTEM PROMPT DIFF:")
    print(diff["system_prompt_diff"] or "No differences in system prompt.")
    print("-" * 80)
    print(f"V1 Character Length: {diff['v1_length_chars']}")
    print(f"V2 Character Length: {diff['v2_length_chars']}")


from promptops.exporters import export_to_markdown, export_to_ics, export_tasks_to_csv
from promptops.telemetry.logger import TelemetryStore


def cmd_run(args):
    """Synthesize a single event brief from the command line and optionally export deliverables."""
    async def _run():
        registry = PromptRegistry()
        pipeline = SelfHealingPipeline(enable_llm_reflection=True)
        adapter = ChaosMockAdapter(model_name=args.model, mode=ChaosMode.PERFECT)

        sys_prompt, user_prompt = registry.render(
            "event_brief_synthesizer",
            version=args.version,
            variables={"event_brief": args.brief},
        )

        print(f"Executing with model: {args.model} | Prompt version: {args.version}...")
        gen_res = await adapter.generate(prompt=user_prompt, system_prompt=sys_prompt)
        pipe_res = await pipeline.process(raw_text=gen_res.raw_text, adapter=adapter)

        print("\n" + "=" * 80)
        print(f"STATUS: {'VALID' if pipe_res.is_valid else 'FAILED'} | TIER: {pipe_res.repair_tier.value}")
        print(f"LATENCY: {gen_res.latency_ms:.1f}ms | TOKENS: {gen_res.total_tokens} | COST: ${gen_res.cost_usd:.6f}")
        print("=" * 80)

        if pipe_res.artifact:
            artifact = pipe_res.artifact
            print(json.dumps(artifact.model_dump(), indent=2))

            # Handle file exports
            if getattr(args, "export_md", None):
                md_path = Path(args.export_md)
                md_path.write_text(export_to_markdown(artifact), encoding="utf-8")
                print(f"[EXPORT] Markdown Brief saved to: {md_path.resolve()}")

            if getattr(args, "export_ics", None):
                ics_path = Path(args.export_ics)
                ics_path.write_text(export_to_ics(artifact), encoding="utf-8")
                print(f"[EXPORT] iCalendar schedule saved to: {ics_path.resolve()}")

            if getattr(args, "export_csv", None):
                csv_path = Path(args.export_csv)
                csv_path.write_text(export_tasks_to_csv(artifact), encoding="utf-8")
                print(f"[EXPORT] Jira/Linear tasks CSV saved to: {csv_path.resolve()}")

            if getattr(args, "export_json", None):
                json_path = Path(args.export_json)
                json_path.write_text(json.dumps(artifact.model_dump(), indent=2), encoding="utf-8")
                print(f"[EXPORT] Structured JSON saved to: {json_path.resolve()}")
        else:
            print("Raw Output:")
            print(gen_res.raw_text)

    asyncio.run(_run())


def cmd_export(args):
    """Export deliverables from an existing artifact JSON file or telemetry run ID."""
    artifact_dict = None

    target = Path(args.source)
    if target.exists() and target.is_file():
        with open(target, "r", encoding="utf-8") as f:
            artifact_dict = json.load(f)
    else:
        # Search telemetry store by run_id
        telemetry = TelemetryStore()
        for run in telemetry.get_runs(limit=200):
            if run.get("run_id") == args.source:
                artifact_dict = run.get("validated_artifact")
                break

    if not artifact_dict:
        print(f"[ERROR] Could not resolve artifact from source: {args.source}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format.lower()
    out = Path(args.out) if args.out else None

    if fmt == "markdown" or fmt == "md":
        content = export_to_markdown(artifact_dict)
        if out:
            out.write_text(content, encoding="utf-8")
            print(f"[EXPORT] Markdown saved to {out}")
        else:
            print(content)
    elif fmt == "ics":
        content = export_to_ics(artifact_dict)
        if out:
            out.write_text(content, encoding="utf-8")
            print(f"[EXPORT] iCalendar saved to {out}")
        else:
            print(content)
    elif fmt == "csv":
        content = export_tasks_to_csv(artifact_dict)
        if out:
            out.write_text(content, encoding="utf-8")
            print(f"[EXPORT] Tasks CSV saved to {out}")
        else:
            print(content)
    else:
        print(f"[ERROR] Unsupported export format '{fmt}'. Choose from: md, ics, csv", file=sys.stderr)
        sys.exit(1)


def cmd_test(args):
    """Execute pytest suite from the CLI."""
    import pytest
    print("Running PromptOps automated test suite...\n")
    exit_code = pytest.main(["-v", "tests"])
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser(description="PromptOps Controlled Generation Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI web studio server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    serve_parser.set_defaults(func=cmd_serve)

    # benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Execute 50-case regression benchmark")
    bench_parser.set_defaults(func=cmd_benchmark)

    # test command
    test_parser = subparsers.add_parser("test", help="Execute automated test suite")
    test_parser.set_defaults(func=cmd_test)

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Diff two prompt versions")
    diff_parser.add_argument("--prompt-id", default="event_brief_synthesizer", help="Prompt identifier")
    diff_parser.add_argument("--v1", default="v1.0.0", help="Baseline version")
    diff_parser.add_argument("--v2", default="v2.0.0", help="Target version")
    diff_parser.set_defaults(func=cmd_diff)

    # run command
    run_parser = subparsers.add_parser("run", help="Synthesize a brief from CLI")
    run_parser.add_argument("brief", help="Raw unstructured text brief")
    run_parser.add_argument("--version", default="v2.0.0", help="Prompt version")
    run_parser.add_argument("--model", default="mock-fast", help="Model name")
    run_parser.add_argument("--export-md", dest="export_md", help="Export path for Markdown brief (.md)")
    run_parser.add_argument("--export-ics", dest="export_ics", help="Export path for iCalendar schedule (.ics)")
    run_parser.add_argument("--export-csv", dest="export_csv", help="Export path for action items CSV (.csv)")
    run_parser.add_argument("--export-json", dest="export_json", help="Export path for structured JSON (.json)")
    run_parser.set_defaults(func=cmd_run)

    # export command
    export_parser = subparsers.add_parser("export", help="Export deliverables from an artifact file or run ID")
    export_parser.add_argument("source", help="Path to artifact JSON file or telemetry run ID")
    export_parser.add_argument("--format", "-f", default="md", choices=["md", "markdown", "ics", "csv"], help="Export format")
    export_parser.add_argument("--out", "-o", help="Output file path (prints to stdout if omitted)")
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

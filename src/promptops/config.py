"""Configuration, pricing models, and system constants for PromptOps."""

from pathlib import Path
from typing import Dict, Any

# Root Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
TEST_CASES_DIR = PROJECT_ROOT / "test_cases"
DATA_DIR = PROJECT_ROOT / "data"

PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
TEST_CASES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Telemetry DB / Log path
TELEMETRY_DB_PATH = DATA_DIR / "telemetry.db"
RUNS_JSONL_PATH = DATA_DIR / "runs.jsonl"
TEST_CASES_FILE = TEST_CASES_DIR / "50_benchmark_cases.json"
BENCHMARK_RESULTS_FILE = DATA_DIR / "benchmark_results.json"

# Execution & Resilience Defaults
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_REPAIR_ATTEMPTS = 1
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_OUTPUT_TOKENS = 2048

# Exact Pricing per 1 Million Tokens (USD)
# Used for exact operational cost accounting
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Real Gemini Models
    "gemini-2.5-flash": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
    },
    "gemini-2.5-pro": {
        "input_per_million": 1.25,
        "output_per_million": 5.00,
    },
    # OpenAI Models
    "gpt-4o-mini": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
    },
    "gpt-4o": {
        "input_per_million": 2.50,
        "output_per_million": 10.00,
    },
    # Groq / Open Models
    "llama-3.3-70b-versatile": {
        "input_per_million": 0.59,
        "output_per_million": 0.79,
    },
    "llama-3.1-8b-instant": {
        "input_per_million": 0.05,
        "output_per_million": 0.08,
    },
    # Chaos Mock Models (Simulated economics for regression testing)
    "mock-fast": {
        "input_per_million": 0.10,
        "output_per_million": 0.40,
    },
    "mock-heavy": {
        "input_per_million": 2.00,
        "output_per_million": 8.00,
    },
    "mock-chaos": {
        "input_per_million": 0.10,
        "output_per_million": 0.40,
    },
}

# Catalog of available models
MODEL_CATALOG: Dict[str, Dict[str, Any]] = {
    "mock-fast": {
        "provider": "mock",
        "name": "Deterministic Mock (Fast/Reliable)",
        "tier": "fast",
        "latency_baseline_ms": 120,
    },
    "mock-heavy": {
        "provider": "mock",
        "name": "Deterministic Mock (Heavy/Frontier)",
        "tier": "quality",
        "latency_baseline_ms": 850,
    },
    "mock-chaos": {
        "provider": "mock",
        "name": "Chaos Mock (Fault Injection)",
        "tier": "chaos",
        "latency_baseline_ms": 300,
    },
    "gemini-2.5-flash": {
        "provider": "gemini",
        "name": "Google Gemini 2.5 Flash",
        "tier": "fast",
        "latency_baseline_ms": 400,
    },
    "gemini-2.5-pro": {
        "provider": "gemini",
        "name": "Google Gemini 2.5 Pro",
        "tier": "quality",
        "latency_baseline_ms": 1400,
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "name": "OpenAI GPT-4o Mini",
        "tier": "fast",
        "latency_baseline_ms": 500,
    },
    "gpt-4o": {
        "provider": "openai",
        "name": "OpenAI GPT-4o",
        "tier": "quality",
        "latency_baseline_ms": 1200,
    },
}

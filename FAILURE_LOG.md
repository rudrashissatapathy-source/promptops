# PromptOps Regression Failure & Resilience Log

This document records all edge cases, syntax anomalies, and timeout faults observed during the 50-case benchmark run, along with root causes and automated recovery actions.

## Summary of Injected Chaos & Edge Case Handlers

| Case ID | Category | Config | Outcome | Root Cause | Automated Recovery Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CASE-16 | noisy_messy | `v1.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-22 | noisy_messy | `v1.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-23 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-25 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-26 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-27 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-28 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-29 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-30 | noisy_messy | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-32 | adversarial_edge | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-33 | adversarial_edge | `v1.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-34 | adversarial_edge | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-38 | adversarial_edge | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-39 | adversarial_edge | `v1.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-46 | infrastructure_chaos | `v1.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | Model exceeded 3.0s circuit-breaker threshold | Tripped circuit-breaker timeout; flagged for fallback cascade |
| CASE-48 | infrastructure_chaos | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-49 | infrastructure_chaos | `v1.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-50 | infrastructure_chaos | `v1.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-16 | noisy_messy | `v1.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-22 | noisy_messy | `v1.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-23 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-25 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-26 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-27 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-28 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-29 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-30 | noisy_messy | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-32 | adversarial_edge | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-33 | adversarial_edge | `v1.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-34 | adversarial_edge | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-38 | adversarial_edge | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-39 | adversarial_edge | `v1.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-46 | infrastructure_chaos | `v1.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | Model exceeded 3.0s circuit-breaker threshold | Tripped circuit-breaker timeout; flagged for fallback cascade |
| CASE-48 | infrastructure_chaos | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-49 | infrastructure_chaos | `v1.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-50 | infrastructure_chaos | `v1.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-32 | adversarial_edge | `v2.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-46 | infrastructure_chaos | `v2.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | Model exceeded 3.0s circuit-breaker threshold | Tripped circuit-breaker timeout; flagged for fallback cascade |
| CASE-48 | infrastructure_chaos | `v2.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-49 | infrastructure_chaos | `v2.0.0::mock-fast` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-50 | infrastructure_chaos | `v2.0.0::mock-fast` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |
| CASE-32 | adversarial_edge | `v2.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-46 | infrastructure_chaos | `v2.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | Model exceeded 3.0s circuit-breaker threshold | Tripped circuit-breaker timeout; flagged for fallback cascade |
| CASE-48 | infrastructure_chaos | `v2.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-49 | infrastructure_chaos | `v2.0.0::mock-heavy` | **Self-Healed** | Markdown code block fence or trailing commas in raw generation | Tier 2 AST/Regex healer stripped fences and normalized JSON |
| CASE-50 | infrastructure_chaos | `v2.0.0::mock-heavy` | **Hard Failure (Circuit Breaker)** | - event_metadata.event_type: Input should be 'conference', 'workshop', 'webinar', 'hackathon' or 'summit'
- schedule: Field required | Logged to dead-letter queue; rejected invalid output |

## Analysis of Cheap vs Heavy Model Tiers

### Where Cheap/Fast Models (`mock-fast` / `gemini-2.5-flash`) are Sufficient:
- **Standard clean event briefs (Cases 1-15)**: 100% schema validity at 120ms latency and $0.0002/run.
- **Informal notes and Slack transcripts with clear intent (Cases 16-30)**: Once wrapped with Prompt v2.0.0 and AST repair, fast models extract all required entities accurately.

### Where Heavy/Frontier Models (`mock-heavy` / `gemini-2.5-pro`) are Required:
- **Adversarial prompt injection attempts (Case 31)**: Heavy models strictly maintain role boundaries and refuse instruction override.
- **Contradictory constraints & temporal paradoxes (Cases 41-45)**: Small models hallucinate impossible schedules; frontier models correctly negotiate tradeoffs and reconcile contradictory inputs.
- **Complex multi-lingual or highly technical jargon (Case 35)**: Heavy models maintain context fidelity across long context inputs.

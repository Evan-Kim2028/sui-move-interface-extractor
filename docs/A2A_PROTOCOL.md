# Agent2Agent (A2A) Protocol Guide

This document is the canonical reference for the A2A protocol implementation in the Sui Move Interface Extractor benchmark. it covers compliance, execution examples, and tuning guidance.

## 1. Protocol Compliance

The benchmark implements Google's [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/) for agent interoperability.

**Implemented Version:** `0.3.0`

### Compliance Checklist
- ✅ **Task Lifecycle**: Full support for `submitted` → `working` → `completed/failed/canceled`.
- ✅ **Streaming Support**: Real-time status updates via SSE (`TaskStatusUpdateEvent`).
- ✅ **Task Cancellation**: Graceful termination support (SIGTERM → SIGKILL).
- ✅ **Version Signaling**: `A2A-Version: 0.3.0` headers and agent card `protocol_version`.
- ✅ **Discovery**: Agent cards available at `/.well-known/agent-card.json`.

### Error Codes
| Error Type | Code | Description |
|------------|------|-------------|
| `InvalidConfigError` | `-32602` | Missing or invalid configuration fields. |
| `TaskNotCancelableError` | `-32001` | Attempting to cancel a task in a terminal state. |
| `ContentTypeNotSupportedError` | `-32002` | Unsupported content type in requests. |

---

## 2. Quick Start Examples

### Minimal Smoke Test (Local)
Run a single package check to validate the environment:
```bash
cd benchmark
uv run smi-a2a-smoke \
  --scenario scenario_smi \
  --corpus-root <CORPUS_ROOT> \
  --dataset type_inhabitation_top25 \
  --samples 1
```

### Full Benchmark Request
Example JSON-RPC payload for a complete Phase II run:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "messageId": "full_run_01",
      "role": "user",
      "parts": [{
        "text": "{\"config\": {
          \"corpus_root\": \"/app/corpus\",
          \"dataset\": \"standard_phase2_benchmark\",
          \"simulation_mode\": \"dry-run\",
          \"max_planning_calls\": 3
        }}"
      }]
    }
  }
}
```

---

## 3. Evaluation Tuning

The performance and cost of Phase II evaluations are highly sensitive to several "tuning knobs."

### Interface Summary Modes
The `summarize_interface()` function supports different densities for the LLM prompt:

| Mode | What's Included | Best For |\n|-------|-----------------|----------|\n| `entry_then_public` | Entry + Public signatures | **Default**: Comprehensive analysis |\n| `entry_only` | Strictly entry points | Cost-sensitive production runs |\n| `names_only` | Only function names | Rapid iteration / smoke tests |\n| `focused` | Specific requested functions | Progressive Exposure only |

### Tuning Guidelines

**1. Context vs. Cost (`max_functions`)**
- **Default (60)**: Balanced. Recommended for most benchmarks.
- **High (100+)**: Better for complex DeFi, but increases token cost.
- **Low (20-30)**: Minimal cost, but higher chance of the model needing "Progressive Exposure."

**2. Progressive Exposure (`--max-planning-calls`)**
This controls how many times the model can ask for "more details" before providing a final plan.
- **1 Call**: Lowest cost. Model must guess based on initial summary.
- **2-3 Calls (Recommended)**: Allows the model to inspect specific modules it identifies as relevant.
- **5+ Calls**: Use only for high-complexity research on frontier models.

**3. Timeout (`--per-package-timeout-seconds`)**
- **90s (Default)**: Standard for Gemini/GPT models.
- **180s+**: Required for "Reasoning" models (DeepSeek-R1, o1) which need time for internal thought.

---

## 4. Troubleshooting SSE Streams

You can monitor the live event stream during an A2A run:
```bash
# Watch structured events in real-time
tail -f logs/a2a_phase2_*/events.jsonl | jq -r '.event, .package_id, .created_hits'
```

Common event patterns:
- `package_started`: Runner is invoking the model.
- `sim_attempt_started`: Model provided a plan; now simulating on-chain.
- `package_finished`: Results are ready for scoring.

# A2A Protocol Examples

This document provides concrete, copy-paste ready examples of the A2A protocol usage for the Sui Move Interface Extractor benchmark.

All examples are based on real executions and can be validated with `smi-a2a-validate-bundle`.

## Quick Start Examples

**Minimal smoke test** (1 package, fast feedback):
```bash
cd benchmark
uv run smi-a2a-smoke \
  --scenario scenario_smi \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 1
```

**Validation**:
```bash
uv run smi-a2a-validate-bundle results/a2a_smoke_response.json
```

## Smoke Test Walkthrough (Annotated)

### Step 1: Start the Scenario

The scenario manager launches both agents (green and purple):

```bash
uv run smi-agentbeats-scenario scenario_smi --launch-mode current
```

This spawns:
- Green agent on port 9999 (`smi-a2a-green`)
- Purple agent on port 9998 (`smi-a2a-purple`)
- Writes PIDs to `scenario_smi/.scenario_pids.json`

### Step 2: Send a Request

The `smi-a2a-smoke` tool constructs a JSON-RPC request:

**Request Payload** (`results/a2a_request_1pkg.json`):
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "messageId": "m_one_pkg",
      "role": "user",
      "parts": [
        {
          "text": "{\"config\": {\"corpus_root\": \"/Users/evandekim/Documents/learning_move/packages/sui-packages/packages/mainnet_most_used\", \"package_ids_file\": \"manifests/standard_phase2_no_framework.txt\", \"samples\": 1, \"rpc_url\": \"https://fullnode.mainnet.sui.io:443\", \"simulation_mode\": \"dry-run\", \"per_package_timeout_seconds\": 90, \"max_plan_attempts\": 2, \"continue_on_error\": true, \"resume\": false }}"
        }
      ]
    }
  }
}
```

**Field-by-field explanation:**

| Field | Meaning | Example Value |
|-------|----------|---------------|
| `jsonrpc` | Protocol version (always 2.0) | `"2.0"` |
| `id` | Request identifier (client can choose) | `"1"` |
| `method` | A2A method name | `"message/send"` |
| `params.message.messageId` | Unique message ID | `"m_one_pkg"` |
| `params.message.role` | Sender role | `"user"` |
| `params.message.parts[0].text` | Config JSON (stringified) | See below |

**Config JSON structure:**
```json
{
  "corpus_root": "/path/to/sui-packages/packages/mainnet_most_used",
  "package_ids_file": "manifests/standard_phase2_no_framework.txt",
  "samples": 1,
  "rpc_url": "https://fullnode.mainnet.sui.io:443",
  "simulation_mode": "dry-run",
  "per_package_timeout_seconds": 90,
  "max_plan_attempts": 2,
  "continue_on_error": true,
  "resume": false
}
```

| Config Key | Description | Default |
|------------|-------------|----------|
| `corpus_root` | Path to bytecode corpus | Required |
| `package_ids_file` | Manifest file (one ID per line) | Required |
| `samples` | Number of packages to process | 1 |
| `rpc_url` | Sui fullnode RPC for simulation | `"https://fullnode.mainnet.sui.io:443"` |
| `simulation_mode` | `"dry-run"`, `"dev-inspect"`, or `"build-only"` | `"dry-run"` |
| `per_package_timeout_seconds` | Wall-clock budget per package | 90 |
| `max_plan_attempts` | Max PTB replanning attempts | 2 |
| `continue_on_error` | Keep going if package fails | `false` |
| `resume` | Resume from existing output file | `false` |

### Step 3: Receive Response

The green agent returns a JSON-RPC response with three artifacts:

**Response structure** (simplified):
```json
{
  "id": "1",
  "jsonrpc": "2.0",
  "result": {
    "artifacts": [
      {
        "name": "evaluation_bundle",
        "parts": [{"kind": "text", "text": "{...}"}]
      },
      {
        "name": "phase2_results.json",
        "parts": [{"kind": "text", "text": "{...}"}]
      },
      {
        "name": "run_metadata.json",
        "parts": [{"kind": "text", "text": "{...}"}]
      }
    ],
    "history": [...],
    "id": "0bdd6112-6577-4565-80a5-2b316b97e648",
    "kind": "task",
    "status": {"state": "completed", "timestamp": "2026-01-02T02:49:34.157720+00:00"}
  }
}
```

### Step 4: Parse Evaluation Bundle

The `evaluation_bundle` artifact contains the most important summary:

**Example bundle** (extracted and formatted):
```json
{
  "schema_version": 1,
  "spec_url": "smi-bench:evaluation_bundle:v1",
  "benchmark": "phase2_inhabit",
  "run_id": "a2a_phase2_1767323740",
  "exit_code": 0,
  "timings": {
    "started_at_unix_seconds": 1767323740,
    "finished_at_unix_seconds": 1767323757,
    "elapsed_seconds": 16.33986186981201
  },
  "config": {
    "continue_on_error": true,
    "corpus_root": "/Users/evandekim/Documents/learning_move/packages/sui-packages/packages/mainnet_most_used",
    "max_plan_attempts": 2,
    "package_ids_file": "manifests/standard_phase2_no_framework.txt",
    "per_package_timeout_seconds": 90.0,
    "resume": false,
    "rpc_url": "https://fullnode.mainnet.sui.io:443",
    "samples": 1,
    "simulation_mode": "dry-run"
  },
  "metrics": {
    "avg_hit_rate": 0.0,
    "errors": 0,
    "packages_timed_out": 0,
    "packages_total": 1,
    "packages_with_error": 0
  },
  "errors": [],
  "artifacts": {
    "events_path": "logs/a2a_phase2_1767323740/events.jsonl",
    "results_path": "results/a2a/a2a_phase2_1767323740.json",
    "run_metadata_path": "logs/a2a_phase2_1767323740/run_metadata.json"
  }
}
```

**Key metrics:**

| Metric | Meaning | Good Value |
|--------|----------|------------|
| `exit_code` | Process exit code (0=success) | `0` |
| `metrics.avg_hit_rate` | Average `created_hits / targets` | Higher is better |
| `metrics.errors` | Number of packages with errors | `0` |
| `metrics.packages_timed_out` | Packages that hit timeout | `0` |
| `metrics.packages_total` | Total packages processed | As expected |

**Artifact paths:**

| Path | Content |
|------|---------|
| `events_path` | Line-delimited event stream (see Event Streaming below) |
| `results_path` | Full Phase II output JSON with per-package details |
| `run_metadata_path` | Exact argv and environment used |

### Step 5: Validate

Check that the bundle conforms to the schema:

```bash
cd benchmark
uv run smi-a2a-validate-bundle results/a2a_smoke_response.json
```

Expected output:
```
valid
```

## Request/Response Reference

### Example 1: Minimal Smoke Request

**Use case:** Quick health check and protocol validation

```bash
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 1
```

**Request characteristics:**
- `samples: 1` (fastest)
- `per_package_timeout_seconds: 90` (default)
- No `--scenario` flag (assumes agents already running)

**Response characteristics:**
- `run_id` generated automatically
- `metrics.packages_total == 1`
- Artifacts written to `results/a2a/` and `logs/`

### Example 2: Standard Phase II Request

**Use case:** Full benchmark run on manifest

```bash
curl -X POST http://127.0.0.1:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "full_manifest_run",
        "role": "user",
        "parts": [{
          "text": "{\"config\": {
            \"corpus_root\": \"/path/to/corpus\",
            \"package_ids_file\": \"manifests/standard_phase2_no_framework.txt\",
            \"rpc_url\": \"https://fullnode.mainnet.sui.io:443\",
            \"simulation_mode\": \"dry-run\",
            \"per_package_timeout_seconds\": 90,
            \"max_plan_attempts\": 2,
            \"continue_on_error\": true,
            \"resume\": false
          }}"
        }]
      }
    }
  }'
```

**Response characteristics:**
- Processes all packages in manifest (290+)
- Checkpoints written if `--checkpoint-every` set (not in A2A mode)
- `metrics.avg_hit_rate` aggregates across all packages

### Example 3: Resume Request

**Use case:** Continue interrupted run from previous output

```bash
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 100 \
  --resume
```

**Config difference:**
- `"resume": true` in config
- Green agent reads existing `results/a2a/<run_id>.json`
- Skips already-processed packages

**Response characteristics:**
- `run_id` reused from existing output
- Only unprocessed packages are run
- Aggregate metrics computed from all (old + new)

## Event Streaming Examples

The green agent streams events as JSONL (one JSON object per line) to `logs/<run_id>/events.jsonl`.

### Typical Event Sequence

For a successful single-package run:

```json
{"agent": "real-openai-compatible", "event": "run_started", "seed": 0, "simulation_mode": "dry-run", "started_at_unix_seconds": 1767323740, "t": 1767323740}
{"api_key": "len=73 suffix=6abef7", "base_url": "https://openrouter.ai/api/v1", "event": "agent_effective_config", "model": "anthropic/claude-sonnet-4.5", "provider": "openai_compatible", "t": 1767323741}
{"event": "package_started", "i": 1, "package_id": "0x00db9a10bb9536ab367b7d1ffa404c1d6c55f009076df1139dc108dd86608bbe", "t": 1767323741}
{"event": "sim_attempt_started", "gas_budget": 10000000, "i": 1, "package_id": "0x00db9a10bb9536ab367b7d1ffa404c1d6c55f009076df1139dc108dd86608bbe", "plan_attempt": 2, "plan_variant": "base", "sim_attempt": 1, "t": 1767323756}
{"created_hits": 0, "dry_run_ok": false, "elapsed_seconds": 15.617967750004027, "error": null, "event": "package_finished", "i": 1, "package_id": "0x00db9a10bb9536ab367b7d1ffa404c1d6c55f009076df1139dc108dd86608bbe", "plan_variant": "base", "t": 1767323756, "targets": 2, "timed_out": false}
{"avg_hit_rate": 0.0, "errors": 0, "event": "run_finished", "finished_at_unix_seconds": 1767323756, "samples": 1, "t": 1767323756}
```

### Event Types

| Event Type | Meaning | Fields |
|------------|----------|---------|
| `run_started` | Benchmark started | `seed`, `simulation_mode`, `started_at_unix_seconds` |
| `agent_effective_config` | Agent config resolved | `api_key` (truncated), `base_url`, `model`, `provider` |
| `package_started` | Package processing started | `i` (index), `package_id` |
| `plan_attempt_harness_error` | Planning failed | `error`, `package_id`, `i` |
| `sim_attempt_started` | Simulation started | `gas_budget`, `plan_attempt`, `plan_variant`, `sim_attempt` |
| `sim_attempt_harness_error` | Simulation failed | `error`, `package_id`, `plan_attempt`, `sim_attempt` |
| `package_finished` | Package completed | `created_hits`, `dry_run_ok`, `elapsed_seconds`, `targets`, `timed_out` |
| `run_finished` | Benchmark finished | `avg_hit_rate`, `errors`, `finished_at_unix_seconds`, `samples` |

### Parsing Events Programmatically

```bash
# Count packages processed
grep "event.*package_finished" logs/a2a_phase2_*/events.jsonl | wc -l

# Extract errors
grep "error" logs/a2a_phase2_*/events.jsonl | jq -r '.event, .error'

# Watch live events
tail -f logs/a2a_phase2_*/events.jsonl | jq -r '.event, .t'
```

## Common Patterns

### Pattern 1: Batch Processing with Checkpoints

**Scenario:** Run 100 packages, writing results after every 10

```bash
# Note: Checkpoints are handled by smi-inhabit directly,
# not via A2A config. For A2A mode, all packages run in one session.
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 100
```

**Verification:**
```bash
# Check how many packages completed
uv run python scripts/phase2_analyze.py results/a2a/<run_id>.json
```

### Pattern 2: Error Recovery

**Scenario:** Continue processing even if some packages fail

```bash
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 50 \
  --per-package-timeout-seconds 90
```

**Config:**
- `"continue_on_error": true` (default in examples)

**Response:**
- `metrics.errors` will be > 0 if any package fails
- `metrics.packages_total` includes both successful and failed packages
- `evaluation_bundle.errors` list contains per-package errors

### Pattern 3: Progressive Timeout Adjustment

**Scenario:** Shorter timeout for known-fast packages, longer for complex ones

```bash
# Fast packages (simple protocols)
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/simple_packages.txt \
  --samples 50 \
  --per-package-timeout-seconds 30

# Complex packages (DeFi, AMMs)
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/complex_packages.txt \
  --samples 50 \
  --per-package-timeout-seconds 300
```

### Pattern 4: Debug Mode for Single Package

**Scenario:** Investigate why a specific package fails

1. Create one-line manifest:
```bash
printf "%s\n" 0x00db9a10bb9536ab367b7d1ffa404c1d6c55f009076df1139dc108dd86608bbe > debug_one_pkg.txt
```

2. Run with extended timeout:
```bash
uv run smi-a2a-smoke \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file debug_one_pkg.txt \
  --per-package-timeout-seconds 300
```

3. Inspect events:
```bash
cat logs/a2a_phase2_*/events.jsonl | jq -r '.event, .error, .package_id'
```

4. Check full error in `results/a2a/<run_id>.json`:
```bash
jq '.packages[0].error' results/a2a/<run_id>.json
```

## Debugging with Examples

### Extract Failing Request/Response from Logs

**Step 1:** Find the run ID from the failure time:
```bash
ls -lt logs/ | head
# Look for logs/a2a_phase2_*/ matching your failure time
```

**Step 2:** Read the events:
```bash
cat logs/a2a_phase2_1767323740/events.jsonl | jq -s
```

**Step 3:** Identify the failure event:
```bash
cat logs/a2a_phase2_1767323740/events.jsonl | grep "error" | jq
```

**Example error event:**
```json
{
  "error": "max planning calls exceeded",
  "event": "plan_attempt_harness_error",
  "i": 1,
  "package_id": "0x00db9a10bb9536ab367b7d1ffa404c1d6c55f009076df1139dc108dd86608bbe",
  "t": 1767323751
}
```

### Compare Successful vs Failed Runs

**Step 1:** Run a known-good package:
```bash
printf "%s\n" <SIMPLE_PACKAGE_ID> > good_pkg.txt
uv run smi-a2a-smoke --package-ids-file good_pkg.txt
```

**Step 2:** Run the failing package:
```bash
printf "%s\n" <FAILING_PACKAGE_ID> > bad_pkg.txt
uv run smi-a2a-smoke --package-ids-file bad_pkg.txt
```

**Step 3:** Compare events:
```bash
diff <(cat logs/good_run/events.jsonl) <(cat logs/bad_run/events.jsonl)
```

**Look for:**
- Different `plan_variant` values
- Presence/absence of `plan_attempt_harness_error` vs `sim_attempt_harness_error`
- Different `elapsed_seconds` (timeout vs normal completion)

### Validate Local Changes Against Known-Good Payloads

**Step 1:** Save a known-good response:
```bash
cp results/a2a_smoke_response.json results/known_good_response.json
```

**Step 2:** Make your changes to the green agent code

**Step 3:** Re-run the same request:
```bash
uv run smi-a2a-smoke --corpus-root <CORPUS_ROOT> --samples 1
```

**Step 4:** Validate the new response:
```bash
uv run smi-a2a-validate-bundle results/a2a_smoke_response.json
```

**Step 5:** Compare metrics:
```bash
# Known good
jq '.result.artifacts[0].parts[0].text | fromjson | .metrics' results/known_good_response.json

# New response
jq '.result.artifacts[0].parts[0].text | fromjson | .metrics' results/a2a_smoke_response.json
```

**Metrics to watch:**
- `avg_hit_rate` (should be stable or better)
- `errors` (should not increase)
- `packages_timed_out` (should not increase)

## Related Documentation

- [A2A_GETTING_STARTED.md](../A2A_GETTING_STARTED.md) - Quick start guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - A2A Layer design details
- [evaluation_bundle.schema.json](evaluation_bundle.schema.json) - Full schema definition

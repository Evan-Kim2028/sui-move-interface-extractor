# A2A Communication Protocol

This document describes the JSON-RPC interface for the `smi-bench-green` agent.

## Request: `run_phase2`

To trigger a benchmark run, send a POST request to the agent's RPC endpoint (default: `http://127.0.0.1:9999/rpc`).

### Example Request Body

```json
{
  "method": "run_agent",
  "params": {
    "metadata": {
      "config": {
        "corpus_root": "/path/to/sui-packages/packages/mainnet_most_used",
        "package_ids_file": "manifests/standard_phase2_no_framework.txt",
        "samples": 1,
        "rpc_url": "https://fullnode.mainnet.sui.io:443",
        "simulation_mode": "dry-run",
        "per_package_timeout_seconds": 300,
        "max_plan_attempts": 2
      },
      "out_dir": "results/a2a"
    }
  },
  "jsonrpc": "2.0",
  "id": "1"
}
```

## Response: Evaluation Bundle

The agent responds with a stream of events. Once complete, it emits an `evaluation_bundle` artifact.

### Example `evaluation_bundle` Schema

```json
{
  "schema_version": 1,
  "spec_url": "smi-bench:evaluation_bundle:v1",
  "benchmark": "phase2_inhabit",
  "run_id": "a2a_phase2_1767322001",
  "exit_code": 0,
  "timings": {
    "started_at_unix_seconds": 1767322001,
    "finished_at_unix_seconds": 1767322050,
    "elapsed_seconds": 49.0
  },
  "config": {
    "corpus_root": "/path/to/corpus",
    "package_ids_file": "manifests/standard_phase2_no_framework.txt",
    "samples": 1,
    "rpc_url": "https://fullnode.mainnet.sui.io:443",
    "simulation_mode": "dry-run"
  },
  "metrics": {
    "avg_hit_rate": 0.5,
    "packages_total": 1,
    "packages_with_error": 0,
    "packages_timed_out": 0
  },
  "artifacts": {
    "results_path": "results/a2a/a2a_phase2_1767322001.json",
    "run_metadata_path": "logs/a2a_phase2_1767322001/run_metadata.json",
    "events_path": "logs/a2a_phase2_1767322001/events.jsonl"
  }
}
```

## Validation

You can validate a returned smoke response using:

```bash
uv run smi-a2a-validate-bundle results/a2a_smoke_response.json
```

# A2A / AgentBeats (Local) — Getting Started

This page is the canonical entrypoint for running the **local A2A green/purple agents** and sending a smoke request.

## One-time setup

```bash
cd benchmark
uv sync --group dev --frozen

cd .. && cargo build --release --locked && cd benchmark
```

## Credentials

Copy `benchmark/.env.example` to `benchmark/.env`.

- For OpenRouter: set `OPENROUTER_API_KEY`.
- For benchmark defaults (used by `real-openai-compatible`): set `SMI_API_KEY`, `SMI_API_BASE_URL`, `SMI_MODEL`.

## Start local scenario (runs both servers)

```bash
cd benchmark
uv run smi-agentbeats-scenario scenario_smi --launch-mode current
```

Health checks:

```bash
curl http://127.0.0.1:9999/.well-known/agent-card.json
curl http://127.0.0.1:9998/.well-known/agent-card.json
```

## Smoke request (recommended)

Run a tiny request against the green agent and print a summary:

```bash
cd benchmark
uv run smi-a2a-smoke \
  --scenario scenario_smi \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 1
```

This writes the raw JSON-RPC response to `benchmark/results/a2a_smoke_response.json` and prints:
- `run_id` / `exit_code`
- `metrics` and `errors_len`
- `results_path` and `events_path`

The green agent also emits an `evaluation_bundle` artifact with a stable schema.
Spec: `docs/evaluation_bundle.schema.json`.

## Validate a bundle

```bash
cd benchmark
uv run smi-a2a-validate-bundle results/a2a_smoke_response.json
```

## Preflight for a full run

```bash
cd benchmark
uv run smi-a2a-preflight --scenario scenario_smi --corpus-root <CORPUS_ROOT>
```

## Next step: full run

Once smoke runs are stable, run Phase II directly:

```bash
uv run smi-inhabit \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --agent real-openai-compatible \
  --rpc-url https://fullnode.mainnet.sui.io:443 \
  --simulation-mode dry-run \
  --continue-on-error \
  --checkpoint-every 1 \
  --per-package-timeout-seconds 90 \
  --max-plan-attempts 2 \
  --out results/phase2_full_run.json \
  --resume
```

## Scenario utilities

Quick status:

```bash
cd benchmark
uv run smi-agentbeats-scenario scenario_smi --status
```

Best-effort stop:

```bash
cd benchmark
uv run smi-agentbeats-scenario scenario_smi --kill
```

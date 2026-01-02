## `benchmark/` (benchmarks)

This directory contains the A2A benchmarking harness.

- **Phase I (key-struct discovery):** ask a model to predict which structs have `key`.
- **Phase II (type inhabitation):** have a model produce a PTB plan, simulate it (dry-run/dev-inspect), and score created key types.

> Start here: [QUICKSTART.md](./QUICKSTART.md)

If you're using the local A2A/AgentBeats flow, start here instead: [A2A_GETTING_STARTED.md](./A2A_GETTING_STARTED.md)

## Phase I caveat (partial information)

Phase I is intentionally designed to avoid trivial leakage:

- The benchmark computes ground-truth key structs from bytecode-derived interfaces (which include `abilities`).
- The model prompt **omits `abilities`** and shows only a bounded subset of struct shapes (fields + types).

This means Phase I scores reflect performance under **partial information** (and can be affected by prompt truncation).
When reporting Phase I results, always record the effective `--max-structs-in-prompt` used.

### Phase I scoring + output format (important)

Phase I is scored as set matching between:

- **truth**: all `key` structs in the package (derived from bytecode interface JSON), and
- **predicted**: the model’s `key_types` list.

Metrics: **precision / recall / F1** over predicted type strings.

Output requirements:

- The model must return **only valid JSON** with a single key: `{"key_types": ["0xADDR::module::Struct", ...]}`.
- Addresses should be **canonical** (32-byte / 64 hex chars) to avoid superficial mismatches (e.g., prefer `0x000...0002` over `0x2`).

## One-time Setup

```bash
cd benchmark
uv sync --group dev --frozen

# Build Rust helpers used by Phase II
cd .. && cargo build --release --locked && cd benchmark
```

## Corpus

You need a local checkout of the `sui-packages` bytecode corpus and should point benchmarks at:
`<sui-packages-checkout>/packages/mainnet_most_used`.

## Configure a Model

Copy `benchmark/.env.example` to `benchmark/.env` and set:
- `SMI_API_KEY`
- `SMI_API_BASE_URL`
- `SMI_MODEL`
- `SMI_SENDER` (funded address for mainnet dry-run)

Sanity checks:
```bash
uv run smi-phase1 --corpus-root <CORPUS_ROOT> --doctor-agent --agent real-openai-compatible
```

## Run Benchmarks

### Quick Start (Recommended Path)

1) One-time setup:

```bash
cd benchmark
uv sync --group dev --frozen

cd .. && cargo build --release --locked && cd benchmark
```

2) Configure credentials:

- Copy `benchmark/.env.example` to `benchmark/.env`.
- Set `SMI_API_KEY`, `SMI_API_BASE_URL`, `SMI_MODEL`.

3) Run a small sample (fast feedback):

```bash
uv run smi-inhabit \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 10 \
  --agent real-openai-compatible \
  --rpc-url https://fullnode.mainnet.sui.io:443 \
  --simulation-mode dry-run \
  --continue-on-error \
  --checkpoint-every 1 \
  --per-package-timeout-seconds 90 \
  --max-plan-attempts 2 \
  --out results/phase2_sample10.json
```

#### “Official” run recommendations (Phase II)

- Prefer strict dry-run-only evaluation: use `--simulation-mode dry-run --require-dry-run`.
- Use a consistent funded sender (`SMI_SENDER`) to reduce variance from inventory-dependent calls.

4) Run a full benchmark:

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

### Phase II (Standard / Leaderboard)

Use the canonical Phase II set:
- `manifests/standard_phase2_benchmark.txt` (n=292; includes framework packages)
- `manifests/standard_phase2_no_framework.txt` (n=290; excludes slow `0x2` and `0x3`)

```bash
uv run smi-inhabit \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --agent real-openai-compatible \
  --rpc-url https://fullnode.mainnet.sui.io:443 \
  --simulation-mode dry-run \
  --continue-on-error \
  --max-plan-attempts 2 \
  --per-package-timeout-seconds 300 \
  --out results/phase2_run.json \
  --resume
```

### Phase II Flags Reference

Common knobs:

- `--corpus-root`: bytecode corpus root (typically `.../sui-packages/packages/mainnet_most_used`).
- `--package-ids-file`: manifest file (one package id per line; comments allowed). Default: unset.
- `--samples`: limit how many package ids to run. Default: `100` (or if using a manifest, takes the first N in order).
- `--seed`: sampling seed. Default: `0`.
- `--agent`: which strategy to use. Default: `real-openai-compatible`.
- `--rpc-url`: Sui fullnode RPC for simulation. Default: `https://fullnode.mainnet.sui.io:443`.
- `--sender`: sender address for tx simulation. Default: `SMI_SENDER` from `--env-file`, otherwise `0x0`.
- `--simulation-mode`: tx simulation mode. Default: `dry-run` (options: `dry-run`, `dev-inspect`, `build-only`).
- `--continue-on-error`: keep going even if some packages fail. Default: off.
- `--max-plan-attempts`: max replanning attempts per package (real agent only). Default: `2`.
- `--max-planning-calls`: max LLM planning calls per package (progressive exposure). Default: `2`.
- `--max-heuristic-variants`: max deterministic PTB variants to try per plan attempt. Default: `4`.
- `--baseline-max-candidates`: max candidates per package in `baseline-search`. Default: `20`.
- `--gas-budget`: gas budget for dry-run simulation. Default: `10000000`.
- `--gas-budget-ladder`: retry budgets for `InsufficientGas`. Default: `20000000,50000000`.
- `--gas-coin`: optional gas coin object id. Default: unset (auto-picks first Coin<SUI> for sender).
- `--per-package-timeout-seconds`: wall-clock budget per package (planning + simulation). Default: `120`.
- `--checkpoint-every`: write partial results to `--out` every N packages. Default: `0` (disabled).
- `--out`: output JSON file. Default: unset.
- `--resume`: resume from an existing `--out`. Default: off.
- `--env-file`: dotenv file. Default: `.env` in current working directory.
- `--log-dir`: JSONL log directory. Default: `benchmark/logs` (use `--no-log` to disable).

### Phase I

```bash
uv run smi-phase1 \
  --corpus-root <CORPUS_ROOT> \
  --agent real-openai-compatible \
  --out results/phase1_run.json \
  --resume
```

## Interpret Results (Phase II)

Given `results/phase2_run.json` and a `package_id`:

1) **Targets / score**
```bash
python scripts/phase2_analyze.py results/phase2_run.json --show <package_id>
```

2) **Progress + timing**
```bash
python scripts/phase2_status.py results/phase2_run.json
python scripts/phase2_metrics.py results/phase2_run.json
```

3) **Live logs** (if you ran with logging enabled)
```bash
python scripts/tail_events.py logs/<run_id>/events.jsonl --follow
```

4) **Which tier failed?**
- Planning: `error` (e.g. `per-call timeout exceeded`, JSON schema errors)
- Build: `tx_build_ok`
- Execution: `dry_run_ok` / `dry_run_error` (and `dev_inspect_ok` if fallback enabled)
- Score: `score.created_hits / score.targets`

### Debug One Package

To reproduce a single `package_id` deterministically, create a one-line manifest and run Phase II on just that package:

```bash
printf "%s\n" <package_id> > results/debug_one_pkg.txt

uv run smi-inhabit \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file results/debug_one_pkg.txt \
  --agent real-openai-compatible \
  --rpc-url https://fullnode.mainnet.sui.io:443 \
  --simulation-mode dry-run \
  --continue-on-error \
  --max-plan-attempts 2 \
  --per-package-timeout-seconds 300 \
  --checkpoint-every 1 \
  --out results/debug_one_pkg.json

python scripts/phase2_analyze.py results/debug_one_pkg.json --show <package_id>
```

If you want identical logging/layout across reruns, pass a fixed `--run-id` and follow logs:

```bash
uv run smi-inhabit ... --run-id debug_<package_id>
python scripts/tail_events.py logs/debug_<package_id>/events.jsonl --follow
```

## Phase II Scoring (TL;DR)

| Metric | Meaning |
|--------|---------|
| `score.targets` | count of `struct ... has key` in the package |
| `score.created_hits` | how many of those targets were created |
| per-package `hit_rate` | `created_hits / targets` |
| `aggregate.avg_hit_rate` | average of per-package hit_rate |

Baseline floor: `baselines/v0.2.2_baseline/` achieves ~**2.6% avg hit rate**.

## Troubleshooting

- **Stuck on `0x2` / `0x3`:** use `manifests/standard_phase2_no_framework.txt`.
- **Many `per-call timeout exceeded`:** increase `--per-package-timeout-seconds` or disable thinking.
- **`A move object is expected, instead a move package is passed: 0x1`:** the plan used a package id where an object id was required; this is a planning error and should be captured under `dry_run_error`.

### Timeout Policy

Phase II uses a **per-package wall-clock budget** (`--per-package-timeout-seconds`) that covers:
- model planning calls (including retries up to `--max-plan-attempts`), and
- transaction simulation (`smi_tx_sim`).

If planning takes most of the budget, you may see `sim_attempts: 0` and `error: per-call timeout exceeded`.

Practical guidance:
- For fast feedback loops: lower `--per-package-timeout-seconds` and/or disable thinking.
- For “heavy thinking” runs: increase `--per-package-timeout-seconds` so at least one plan attempt plus one simulation attempt can complete.

## Deep Docs

- Methodology: `docs/METHODOLOGY.md`
- Schema: `docs/SCHEMA.md`
- Operations / runbook: `docs/RUNBOOK.md`
- Standard manifests: `manifests/README.md`

## AgentBeats / A2A (Local Scenario)

To launch the repo's A2A servers (green + purple) via AgentBeats' `ScenarioManager`:

```bash
cd benchmark
uv run smi-agentbeats-scenario scenario_smi --launch-mode current
```

This starts:
- green: `smi-a2a-green` on `http://127.0.0.1:9999/`
- purple: `smi-a2a-purple` on `http://127.0.0.1:9998/`

Health checks:
```bash
curl http://127.0.0.1:9999/.well-known/agent-card.json
curl http://127.0.0.1:9998/.well-known/agent-card.json
```

### Targets-Only Partial Runs (Skip packages with trivial targets)

If you want to focus Phase II effort on packages with `score.targets >= 2`:

One-command wrapper:

```bash
uv run smi-phase2-targeted-run \
  --corpus-root <CORPUS_ROOT> \
  --min-targets 2 \
  --scan-samples 500 \
  --run-samples 50 \
  --per-package-timeout-seconds 90
```

1) Scan a slice in `build-only` mode (no LLM calls) to compute `score.targets`:

```bash
uv run smi-inhabit \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --samples 200 \
  --agent baseline-search \
  --simulation-mode build-only \
  --continue-on-error \
  --out results/phase2_targets_scan.json
```

2) Filter that output into a manifest:

```bash
uv run smi-phase2-filter-manifest results/phase2_targets_scan.json \
  --min-targets 2 \
  --out-manifest results/manifest_targets_ge2.txt
```

3) Run a real-agent partial run on that filtered manifest:

```bash
uv run smi-inhabit \
  --corpus-root <CORPUS_ROOT> \
  --package-ids-file results/manifest_targets_ge2.txt \
  --samples 25 \
  --agent real-openai-compatible \
  --simulation-mode dry-run \
  --continue-on-error \
  --checkpoint-every 1 \
  --per-package-timeout-seconds 90 \
  --max-plan-attempts 2 \
  --out results/phase2_partial_targets_ge2_25.json \
  --resume
```

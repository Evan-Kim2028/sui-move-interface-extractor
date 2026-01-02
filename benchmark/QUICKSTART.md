# Phase II Benchmark Quickstart

Run an A2A benchmark against Sui Move packages in 3 steps.

For the local A2A server + smoke request flow, see: `A2A_GETTING_STARTED.md`.

## Scoring (TL;DR)

Each package has **target key structs** (Move structs with `key` ability). The benchmark measures:

| Metric | Meaning | Example |
|--------|---------|---------|
| `targets` | Number of `key` structs in the package | 2 |
| `created_hits` | How many targets the transaction actually created | 1 |
| `hit_rate` | `created_hits / targets` per package | 50% |
| `avg_hit_rate` | Average hit_rate across all packages | 10% |

**Example**: A package with structs `VestingLock` and `LinkedTable` (both have `key`) has `targets=2`. If the agent's transaction creates a `VestingLock` but not a `LinkedTable`, that's `1/2 = 50% hit_rate`.

**Baseline**: The mechanical (non-AI) baseline achieves **2.6% avg hit rate**. AI agents should beat this.

## Evaluation notes (important)

- **Primary metric**: We currently use **base-type hit rate** as the primary metric (created key *base* types / target key *base* types). This intentionally ignores type arguments for robustness and comparability across packages.
- **“Official” runs should be strict**: For strict evaluation, prefer dry-run-only scoring with:
  - `--simulation-mode dry-run --require-dry-run`
  - (avoid relying on dev-inspect fallback)
- **Inventory dependence**: Many packages require existing owned objects. Results can vary based on the sender wallet’s inventory and placeholder resolution. Using a consistent, shared funded sender address helps comparability, but it’s still a real limitation to keep in mind when interpreting scores.

## Reproducibility / reporting checklist

When comparing Phase II runs (or sharing results), record:

- corpus identity: the `sui-packages` git SHA (or snapshot name) and `--corpus-root`
- dataset selection: `--package-ids-file` / `--dataset`, and `--samples`, `--seed`
- evaluation strictness: whether you used `--require-dry-run`
- sender setup: `SMI_SENDER` (and whether it is the “standard” shared funded address), plus `--gas-budget` / `--gas-coin` if overridden
- toolchain: benchmark version + model name/provider + key flags (`--max-plan-attempts`, `--max-planning-calls`, `--per-package-timeout-seconds`)

---

## 1. Setup (one-time)

```bash
cd benchmark
uv sync --group dev --frozen

# Build Rust binaries
cd .. && cargo build --release --locked && cd benchmark

# Clone corpus (if not already present)
git clone --depth 1 https://github.com/MystenLabs/sui-packages.git ../sui-packages
```

## 2. Configure API Key

Copy `.env.example` to `.env` and set your model credentials:

```bash
cp .env.example .env
```

**GLM 4.7 (Z.AI Coding API):**
```env
SMI_API_KEY=your_api_key_here
SMI_API_BASE_URL=https://api.z.ai/api/coding/paas/v4
SMI_MODEL=glm-4.7
SMI_THINKING=enabled
SMI_RESPONSE_FORMAT=json_object
SMI_CLEAR_THINKING=true
SMI_SENDER=0xYOUR_FUNDED_MAINNET_ADDRESS
```

**OpenAI:**
```env
SMI_API_KEY=sk-...
SMI_API_BASE_URL=https://api.openai.com/v1
SMI_MODEL=gpt-4o
SMI_SENDER=0xYOUR_FUNDED_MAINNET_ADDRESS
```

Verify connectivity:
```bash
uv run smi-phase1 --corpus-root ../sui-packages/packages/mainnet_most_used --doctor-agent --agent real-openai-compatible
```

### Recommended: dedicated env files for multi-model runs

If you want to switch models frequently (especially via OpenRouter), use a dedicated env file and pass it explicitly with `--env-file`.

This avoids surprises from `benchmark/.env` being loaded by default.

**Example: `benchmark/.env.openrouter`**
```env
OPENROUTER_API_KEY=sk-or-v1-...
SMI_API_BASE_URL=https://openrouter.ai/api/v1
SMI_SENDER=0xYOUR_FUNDED_MAINNET_ADDRESS

# Optional defaults (can be overridden per-run)
SMI_TEMPERATURE=0
SMI_RESPONSE_FORMAT=json_object
SMI_MAX_TOKENS=2048
```

**Single model run (Sonnet 4.5):**
```bash
SMI_MODEL=anthropic/claude-sonnet-4.5 \
uv run smi-inhabit \
  --env-file .env.openrouter \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --agent real-openai-compatible \
  --rpc-url https://fullnode.mainnet.sui.io:443 \
  --simulation-mode dry-run \
  --continue-on-error \
  --per-package-timeout-seconds 300 \
  --max-plan-attempts 2 \
  --out results/sonnet45_run.json
```

**Multi-model runs:**

- Use `models.yaml` + `scripts/run_model.sh` to select the model.
- Ensure the script passes `--env-file .env.openrouter` so the base URL and key come from the dedicated file.

## 3. Run Phase II Benchmark

### Datasets (recommended)

Use `--dataset <name>` to select a named package dataset under `benchmark/manifests/datasets/<name>.txt`.

`packages_with_keys` is a corpus-derived-style dataset intended to focus runs on packages that contain `key` structs (i.e., there are objects worth attempting to create).

**Quick test (3 packages, ~5 min):**
```bash
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
  --dataset packages_with_keys \
  --agent real-openai-compatible \
  --rpc-url https://fullnode.mainnet.sui.io:443 \
  --simulation-mode dry-run \
  --continue-on-error \
  --per-package-timeout-seconds 90 \
  --max-plan-attempts 2 \
  --samples 3 \
  --out results/my_test_run.json
```

**Full benchmark (290 packages):**
```bash
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
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

## Sample / Partial Runs

Use `--samples` to run only the first N package ids from a manifest:

```bash
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
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

## 4. View Results

```bash
# Quick status
python scripts/phase2_status.py results/my_test_run.json

# Detailed metrics
python scripts/phase2_metrics.py results/my_test_run.json

# Compare runs
python scripts/phase2_leaderboard.py results/run_a.json results/run_b.json
```

## Key Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--per-package-timeout-seconds` | 120 | Max time per package (API + simulation) |
| `--max-plan-attempts` | 2 | Retry attempts on compiler errors |
| `--continue-on-error` | off | Don't abort on individual failures |
| `--checkpoint-every` | 0 | Save progress every N packages |
| `--resume` | off | Resume from existing output file |

## Manifests

- `manifests/standard_phase2_benchmark.txt` - Full 292 packages (includes framework)
- `manifests/standard_phase2_no_framework.txt` - 290 packages (excludes slow 0x2, 0x3)

## Baseline Comparison

The mechanical baseline achieves **2.6% hit rate**. Any AI agent should beat this floor.

See `baselines/v0.2.2_baseline/` for reference results.
